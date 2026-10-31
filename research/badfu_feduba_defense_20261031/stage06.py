"""Post-backbone semantic-head transport, fixed before cached evaluator data."""
import json
import os
from pathlib import Path
import time
import traceback
import torch
import stage05_common as s
core=s.core
OUT=s.HERE/'stage06'


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources()
    frozen=core.read(s.HERE/'STAGE06_FREEZE.json')
    for n,h in frozen['files'].items():assert core.sha(s.HERE/n)==h,n
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'device':'CPU'},f)
    selected,sealed,states=s.snapshot()
    declarations={}
    for pair,a,b in core.PAIRS:
        path=s.OUT/(pair+'_alignment.pt')
        assert core.sha(path)==core.read(s.OUT/'FIT_COMPLETED.json')['files'][path.name]
        d=torch.load(path,map_location='cpu',weights_only=True)
        rot=d['rotation'];mx=d['mean_pre'];my=d['mean_post'];h=s.head(states[a])
        w=h['weight']@rot;bias=h['bias']+mx@h['weight'].T-my@rot.T@h['weight'].T
        head={'weight':w.float(),'bias':bias.float()}
        hp=OUT/(pair+'_head.pt');torch.save(head,hp)
        st={k:v.clone() for k,v in states[b].items()};st['model.fc.weight']=head['weight'];st['model.fc.bias']=head['bias']
        mp=OUT/(pair+'_model.pt');torch.save(st,mp)
        declarations[pair]={'head_sha256':core.sha(hp),'model_sha256':core.sha(mp),'backbone':'post',
                            'true_labels_used':False,'ASR_used':False}
    core.OUT=OUT;core.write('CANDIDATES_BEFORE_EVALUATION.json',declarations)
    fixed=core.sha(OUT/'CANDIDATES_BEFORE_EVALUATION.json')
    y=s.original_cache('clean_predictions.pt')['labels'].long()
    ids=torch.tensor(core.read(s.HERE/'PROXY_SPLIT.json')['heldout_ids'])
    result={'state':'running','cases':{},'evaluator':'post_coordinate_head_transport_v1',
            'candidate_declaration_sha256':fixed,'deletion_checked':False}
    for pair,a,b in core.PAIRS:
        before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
        p=s.logits(before['clean'],s.head(states[a]));q=s.logits(after['clean'],s.head(states[b]))
        baseline=core.metrics(q,y,p,q,ids)
        h=torch.load(OUT/(pair+'_head.pt'),map_location='cpu',weights_only=True)
        z=s.logits(after['clean'],h);za=s.logits(after['attack'],h)
        m=core.metrics(z,y,p,q,ids)
        row={'clean':m,'attack_target_n':int((za.argmax(1)==0).sum()),'attack_n':len(za),
             'ASR_pct':100*float((za.argmax(1)==0).double().mean()),
             'overall_drop_pp':baseline['CA_pct']-m['CA_pct'],
             'worst_class_drop_pp':max(u-v for u,v in zip(baseline['class_CA_pct'],m['class_CA_pct']))}
        row['CA_necessary_gate']=row['overall_drop_pp']<=.5+1e-10 and row['worst_class_drop_pp']<=2+1e-10
        row['strict_prior_correction_gate']=not pair.startswith('benign') or m['beneficial_kept_fraction']>=.9
        result['cases'][pair]=row;core.write('RESULT.json',result)
    assert core.sha(OUT/'CANDIDATES_BEFORE_EVALUATION.json')==fixed
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    result.update(state='completed_cache_only',necessary_CA_ASR_gates=all(v['CA_necessary_gate'] for v in result['cases'].values()) and result['cases']['attack_cover850']['ASR_pct']<=10)
    core.write('RESULT.json',result)
    core.write('COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),
           'files':{p.name:core.sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);core.OUT=OUT;core.write('FAILURE.json',{'traceback':traceback.format_exc()});raise
