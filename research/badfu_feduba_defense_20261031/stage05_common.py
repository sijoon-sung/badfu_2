"""Pinned snapshot/cache loading and finite membership-audit primitives."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import torch
import stage03 as core

HERE=Path(__file__).resolve().parent
OUT=HERE/'stage05'
core.OUT=OUT


def verify_sources():
    frozen=core.read(HERE/'STAGE05_FREEZE.json')
    for name,digest in frozen['files'].items():
        assert core.sha(HERE/name)==digest,('source',name)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)


def snapshot():
    info=core.read(HERE/'STAGE03_INPUTS.json')
    selected=json.loads(subprocess.check_output([sys.executable,info['selector'],
        'badfu.confirmed.s20261023.v1','--purpose','purification_pilot'],text=True,encoding='utf8'))
    g=selected['checkpoint_guard'];root=Path(selected['source_root'])
    assert g['manifest_sha256']=='52adb46e6fd056125acf07e2baa244605f56f09f4db927d068f1e37082e3374e'
    assert g['seal_sha256']=='ed5f75d57a4526191f9ee1c201a8147d285d3beea940fbaf267b5e4507ec88fd'
    assert core.sha(g['manifest_path'])==g['manifest_sha256']
    assert core.sha(g['seal_path'])==g['seal_sha256']
    assert core.sha(g['loader_path'])==core.read(g['manifest_path'])['files']['load_confirmed.py']['sha256']
    spec=importlib.util.spec_from_file_location('sealed_stage05',g['loader_path'])
    sealed=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealed)
    sealed.verify(root,g['manifest_sha256'])
    states={}
    for role,entry in selected['server_inputs'].items():
        assert core.sha(entry['path'])==entry['sha256']
        s=torch.load(entry['path'],map_location='cpu',weights_only=True)
        states[role]=s if entry['payload_key'] is None else s[entry['payload_key']]
        assert all(torch.isfinite(v).all() for v in states[role].values())
    return selected,sealed,states


def original_cache(name):
    p=HERE/'inputs'/name
    assert core.sha(p)==core.read(HERE/'INPUT_MANIFEST.json')['cache_files'][name]
    return torch.load(p,map_location='cpu',weights_only=True)


def feature_cache(pair,pre):
    report=core.read(HERE/'stage03/RESULT.json')
    receipt=core.read(HERE/'stage03/COMPLETED.json')
    assert core.sha(HERE/'stage03/RESULT.json')==receipt['result_sha256']
    row=next(r for r in report['rows'] if r['pair']==pair and r['W']==r['BN']==r['head']==(0 if pre else 1))
    p=HERE/'stage03'/row['feature_path']
    assert core.sha(p)==receipt['files'][p.name]
    return torch.load(p,map_location='cpu',weights_only=True)


def head(state):
    return {'weight':state['model.fc.weight'].double(),'bias':state['model.fc.bias'].double()}


def logits(features,h):
    return features.double()@h['weight'].double().T+h['bias'].double()


def heads(pair,a,b,states):
    p=HERE/('transport_'+pair.replace('attack_cover850','attack_cover850_clean_only')+'.pt')
    assert core.sha(p)==core.read(HERE/'COMPLETED.json')['files'][p.name]
    h5p=OUT/(pair+'_aligned_head.pt')
    assert core.sha(h5p)==core.read(OUT/'CANDIDATES_BEFORE_EVALUATION.json')['heads'][h5p.name]
    return {'native_pre':(True,head(states[a])), 'native_post':(False,head(states[b])),
            'H1':(True,head(states[b])),
            'H2':(True,torch.load(p,map_location='cpu',weights_only=True)),
            'H5':(True,torch.load(h5p,map_location='cpu',weights_only=True))}


def rank_auc(member,nonmember):
    """Exact Mann-Whitney AUC; ties count one half, higher score predicts member."""
    m=np.asarray(member,dtype=np.float64);n=np.sort(np.asarray(nonmember,dtype=np.float64))
    assert len(m) and len(n) and np.isfinite(m).all() and np.isfinite(n).all()
    wins=np.searchsorted(n,m,side='left');ties=np.searchsorted(n,m,side='right')-wins
    return float((wins+.5*ties).sum()/(len(m)*len(n)))


def membership(member_logits,member_y,nonmember_logits,nonmember_y):
    ml=member_logits.log_softmax(1);nl=nonmember_logits.log_softmax(1)
    scores={'true_label_logprob':(ml.gather(1,member_y[:,None]).squeeze(1),
                                   nl.gather(1,nonmember_y[:,None]).squeeze(1)),
            'max_logprob':(ml.max(1).values,nl.max(1).values)}
    result={'member_n':len(ml),'nonmember_n':len(nl),'scores':{}}
    weights=np.array([int((member_y==c).sum())/len(ml) for c in range(10)])
    for name,(ms,ns) in scores.items():
        rows=[]
        for c in range(10):
            m=ms[member_y==c].numpy();n=ns[nonmember_y==c].numpy()
            auc=rank_auc(m,n) if len(m) else .5
            rows.append({'class':c,'member_n':len(m),'nonmember_n':len(n),'AUC':auc,'advantage':2*abs(auc-.5)})
        auc=float(sum(w*r['AUC'] for w,r in zip(weights,rows)))
        result['scores'][name]={'class_rows':rows,'weighted_AUC':auc,'advantage':2*abs(auc-.5),
            'weighted_class_advantage':float(sum(w*r['advantage'] for w,r in zip(weights,rows)))}
    mp=member_logits.argmax(1);npred=nonmember_logits.argmax(1)
    gaps=[]
    for c in range(10):
        if not (member_y==c).any():
            gaps.append(0.);continue
        assert (nonmember_y==c).any(),('missing matched nonmember class',c)
        accm=float((mp[member_y==c]==c).double().mean()) if (member_y==c).any() else 0.
        accn=float((npred[nonmember_y==c]==c).double().mean())
        gaps.append(accm-accn)
    result['weighted_accuracy_gap']=float(sum(weights*np.asarray(gaps)))
    result['class_accuracy_gaps']=gaps
    return result
