"""Once-only CPU coordinate alignment, then evaluation of pinned feature caches."""
import json
import os
import time
import traceback

import torch
import stage05_common as s
core=s.core


def align(x,y,post_head):
    """No labels, attack metadata, or heldout inputs are accepted."""
    x=x.double();y=y.double();mx=x.mean(0);my=y.mean(0)
    xc=x-mx;yc=y-my;d=x.shape[1]
    lam=.01*(xc.square().sum()+yc.square().sum())/(2*d)
    u,_,vh=torch.linalg.svd(xc.T@yc+lam*torch.eye(d,dtype=torch.float64))
    a=u@vh;w=post_head['weight'];b=post_head['bias']
    transported={'weight':(a@w.T).T.float(),'bias':(b+my@w.T-mx@a@w.T).float()}
    err=float((a.T@a-torch.eye(d,dtype=torch.float64)).abs().max())
    assert err<1e-10
    return transported,{'rotation':a,'mean_pre':mx,'mean_post':my,'lambda':float(lam),
                        'orthogonality_max_error':err}


def main():
    s.OUT.mkdir(exist_ok=True);s.verify_sources()
    with (s.OUT/'FIT_STARTED.json').open('x',encoding='utf8') as f:
        json.dump({'pid':os.getpid(),'time':time.time(),'device':'CPU','threads':2},f)
    selected,sealed,states=s.snapshot();core.write('SELECTED_CASE.json',selected)
    split=core.read(s.HERE/'PROXY_SPLIT.json')
    fit=torch.tensor(split['fit_ids']);heldout=torch.tensor(split['heldout_ids'])
    declarations={'heads':{},'models':{},'fit_uses_labels':False,'fit_uses_ASR':False,
                  'cached_trigger_features_opened':False,'deleted_data_opened':False}
    alignment={}
    for pair,a,b in core.PAIRS:
        x=s.original_cache('features_'+a+'.pt')[fit]
        y=s.original_cache('features_'+b+'.pt')[fit]
        h,details=align(x,y,s.head(states[b]))
        hp=s.OUT/(pair+'_aligned_head.pt');torch.save(h,hp)
        state={k:v.clone() for k,v in states[a].items()}
        state['model.fc.weight']=h['weight'];state['model.fc.bias']=h['bias']
        mp=s.OUT/(pair+'_aligned_model.pt');torch.save(state,mp)
        torch.save(details,s.OUT/(pair+'_alignment.pt'))
        declarations['heads'][hp.name]=core.sha(hp);declarations['models'][mp.name]=core.sha(mp)
        alignment[pair]={'lambda':details['lambda'],'orthogonality_max_error':details['orthogonality_max_error']}
    core.write('CANDIDATES_BEFORE_EVALUATION.json',declarations)
    fixed=core.sha(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')
    y=s.original_cache('clean_predictions.pt')['labels'].long()
    result={'state':'running','candidate_declaration_sha256':fixed,'alignment':alignment,'cases':{},
            'evaluator':'aligned_feature_cache_v1_FP64_head_saved_FP32','deletion_audit':'pending_resource_guard',
            'new_FL_seeds':0}
    for pair,a,b in core.PAIRS:
        before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
        nativepre=s.logits(before['clean'],s.head(states[a]));nativepost=s.logits(after['clean'],s.head(states[b]))
        base=core.metrics(nativepost,y,nativepre,nativepost,heldout)
        rows={}
        for name,(use_pre,h) in s.heads(pair,a,b,states).items():
            features=before if use_pre else after
            z=s.logits(features['clean'],h);za=s.logits(features['attack'],h)
            metric=core.metrics(z,y,nativepre,nativepost,heldout)
            row={'clean':metric,'ASR_pct':100*float((za.argmax(1)==0).double().mean()),
                 'attack_target_n':int((za.argmax(1)==0).sum()),'attack_n':len(za),
                 'overall_drop_pp':base['CA_pct']-metric['CA_pct'],
                 'worst_class_drop_pp':max(u-v for u,v in zip(base['class_CA_pct'],metric['class_CA_pct']))}
            row['CA_necessary_gate']=row['overall_drop_pp']<=.5+1e-10 and row['worst_class_drop_pp']<=2+1e-10
            row['strict_prior_correction_gate']=not pair.startswith('benign') or metric['beneficial_kept_fraction']>=.9
            rows[name]=row
        result['cases'][pair]=rows;core.write('FIT_RESULT.json',result)
    assert core.sha(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')==fixed
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    result.update(state='completed_CPU_fit_only',finished_unix=time.time())
    core.write('FIT_RESULT.json',result)
    core.write('FIT_COMPLETED.json',{'result_sha256':core.sha(s.OUT/'FIT_RESULT.json'),
        'freeze_sha256':core.sha(s.HERE/'STAGE05_FREEZE.json'),
        'files':{p.name:core.sha(p) for p in s.OUT.iterdir() if p.is_file() and p.name!='FIT_COMPLETED.json'}})
    print(json.dumps({'state':result['state'],'H5':{k:v['H5'] for k,v in result['cases'].items()}},ensure_ascii=False),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        s.OUT.mkdir(exist_ok=True);core.write('FIT_FAILURE.json',{'traceback':traceback.format_exc()});raise
