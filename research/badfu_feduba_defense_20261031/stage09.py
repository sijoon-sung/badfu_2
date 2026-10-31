"""Finite public-only interpolation selection, then separate large-benign audit."""
import hashlib,json,os,subprocess,time,traceback
from pathlib import Path
import numpy as np
import torch
import stage05_common as s
core=s.core
OUT=s.HERE/'stage09'


def write(name,obj):core.OUT=OUT;core.write(name,obj)


@torch.inference_mode()
def forward(model,raw):
    result=[]
    for offset in range(0,len(raw),32):
        result.append(model(core.normalise(raw[offset:offset+32])))
        if offset%3200==0:write('PROGRESS.json',{'n':len(raw),'completed':min(offset+32,len(raw)),'time':time.time()})
    return torch.cat(result).double()


def mix(post,student,alpha):
    return {k:torch.lerp(v,student[k],alpha) if v.is_floating_point() else v.clone() for k,v in post.items()}


def proxy_metrics(teacher,z):
    p=teacher.softmax(1);label=teacher.argmax(1);pred=z.argmax(1)
    kl=float((p*(teacher.log_softmax(1)-z.log_softmax(1))).sum(1).mean())
    r={'mean_KL':max(0.,kl),'agreement':float((pred==label).double().mean()),
       'class_agreement':[float((pred[label==c]==c).double().mean()) if (label==c).any() else 1. for c in range(10)]}
    r['eligible']=r['mean_KL']<=.010+1e-12 and r['agreement']>=.98-1e-12 and min(r['class_agreement'])>=.95-1e-12
    return r


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources();core.OUT=OUT
    freeze=core.read(s.HERE/'STAGE09_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    cpu=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Processor | Select-Object NumberOfLogicalProcessors,LoadPercentage | ConvertTo-Json -Compress'],text=True))
    assert cpu['NumberOfLogicalProcessors']>=8 and cpu['LoadPercentage']<=60 and not torch.cuda.is_initialized()
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu},f)
    start=time.monotonic()
    def deadline():assert time.monotonic()-start<1800,'30minute bounded profile'
    selected,sealed,states=s.snapshot();post=states['clean_big_post'];cls=sealed.model_class(Path(selected['source_root']))
    parent=core.read(s.HERE/'stage08/MODELS_BEFORE_PRIVATE_EVALUATION.json')
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    data=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    split=core.read(s.HERE/'PROXY_SPLIT.json');fit=torch.tensor(split['fit_ids']);held=torch.tensor(split['heldout_ids'])
    public=data['test_x'][fit];model=cls().eval();model.load_state_dict(post,strict=True)
    # This helper only forwards raw images; it uses no labels or attack metadata.
    teacher=forward(model,public);choices={};models={};allrows={}
    for arm in ['clean_only','query_transfer']:
        pp=s.HERE/'stage08'/parent[arm]['path'];assert core.sha(pp)==parent[arm]['sha256']
        student=torch.load(pp,map_location='cpu',weights_only=True);rows=[];cache={}
        def probe(alpha):
            deadline();state=mix(post,student,alpha);model.load_state_dict(state,strict=True)
            z=forward(model,public);r={'alpha':alpha,**proxy_metrics(teacher,z),'tensor_sha256':core.tensor_digest(state)}
            rows.append(r);cache[alpha]=z;write('SELECTION_PROGRESS.json',{'arm':arm,'tested_n':len(rows),'latest':r,'time':time.time()})
            return r
        for i in range(11):probe(i/10)
        best=max((r for r in rows if r['eligible']),key=lambda r:r['alpha'])
        if best['alpha']<1:
            lo=best['alpha'];hi=min(r['alpha'] for r in rows if r['alpha']>lo)
            for _ in range(6):
                mid=(lo+hi)/2;r=probe(mid)
                if r['eligible']:lo=mid
                else:hi=mid
        choice=max((r for r in rows if r['eligible']),key=lambda r:r['alpha']);choices[arm]=choice;allrows[arm]=rows
        st=mix(post,student,choice['alpha']);path=OUT/(arm+'_selected.pt');torch.save(st,path)
        torch.save({'teacher_logits':teacher,'alphas':[r['alpha'] for r in rows],
                    'candidate_logits':torch.stack([cache[r['alpha']] for r in rows])},OUT/('private_'+arm+'_proxy.pt'))
        models[arm]={'path':path.name,'sha256':core.sha(path),'alpha':choice['alpha']}
    write('SELECTION_BEFORE_PRIVATE_EVALUATION.json',{'choices':choices,'all_points':allrows,'models':models,
          'labels_used':False,'member_used':False,'actual_trigger_used':False,'ASR_used':False})
    fixed=core.sha(OUT/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
    extra=core.read(s.HERE/'STAGE05_INPUTS.json')
    for key in ['train','split','big_complete']:assert core.sha(extra[key]['path'])==extra[key]['sha256']
    ids=core.read(extra['split']['path'])['clean_cifar10_indices'][4]
    complete=core.read(extra['big_complete']['path'])
    assert len(ids)==9668 and hashlib.sha256(np.asarray(sorted(ids),dtype=np.int64).tobytes()).hexdigest()==complete['audit']['removed_indices_sha256']
    assert complete['checkpoint_sha256']==selected['server_inputs']['clean_big_post']['sha256']
    train=torch.load(extra['train']['path'],map_location='cpu',weights_only=True)
    member=train['train_x'][ids];my=train['train_y'][ids].long();labels=data['test_y'].long()
    prefeatures=s.feature_cache('benign_big19336',True);postfeatures=s.feature_cache('benign_big19336',False)
    p=s.logits(prefeatures['clean'],s.head(states['clean_pre']));q=s.logits(postfeatures['clean'],s.head(post))
    base=core.metrics(q,labels,p,q,held)
    privacybase=core.read(s.HERE/'stage07_cpu_v2/RESULT.json')['cases']['benign_big19336']['variants']['native_post']
    result={'state':'running','cases':{},'selection_sha256':fixed,'actual_trigger_evaluated':False,'formal_deletion_certificate':False}
    for arm in ['clean_only','query_transfer']:
        deadline();entry=models[arm]
        if entry['alpha']==0:
            result['cases'][arm]={'alpha':0,'identity':True,'necessary_gate':False,'reason':'identity is not active correction'}
            continue
        path=OUT/entry['path'];assert core.sha(path)==entry['sha256']
        st=torch.load(path,map_location='cpu',weights_only=True);model.load_state_dict(st,strict=True)
        cz=forward(model,data['test_x']);mz=forward(model,member)
        assert core.tensor_digest(model.state_dict())==core.tensor_digest(st)
        torch.save({'clean_logits':cz,'member_logits':mz,'member_labels':my},OUT/('private_'+arm+'_evaluation.pt'))
        m=core.metrics(cz,labels,p,q,held);audit=s.membership(mz,my,cz,labels)
        increases={n:{key:audit['scores'][n][key]-privacybase['scores'][n][key] for key in ['advantage','weighted_class_advantage']} for n in privacybase['scores']}
        gap=abs(audit['weighted_accuracy_gap'])-abs(privacybase['weighted_accuracy_gap'])
        drop=base['CA_pct']-m['CA_pct'];worst=max(a-b for a,b in zip(base['class_CA_pct'],m['class_CA_pct']))
        result['cases'][arm]={'alpha':entry['alpha'],'identity':False,'clean':m,'deletion_audit':audit,
            'increase_over_post':increases,'absolute_accuracy_gap_increase':gap,'overall_drop_pp':drop,'worst_class_drop_pp':worst,
            'necessary_gate':drop<=.5+1e-10 and worst<=2+1e-10 and gap<=.02+1e-12 and all(v<=.04+1e-12 for score in increases.values() for v in score.values())}
        write('RESULT.json',result)
    assert core.sha(OUT/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')==fixed
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256']);assert not torch.cuda.is_initialized()
    result.update(state='completed',extension_permitted=any(v['necessary_gate'] for v in result['cases'].values()),finished_unix=time.time())
    write('RESULT.json',result);write('COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),
          'files':{p.name:core.sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
    print('STAGE09_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);write('FAILURE.json',{'traceback':traceback.format_exc()});raise
