"""Frozen-model, three-distribution fidelity audit; only256-image extra forwards."""
import json,os,time,traceback
from pathlib import Path
import torch
import stage05_common as s
from stage08 import norm
core=s.core
OUT=s.HERE/'fidelity_diagnosis'


def stats(p,z):
    p=p.double();p=p/p.sum(1,keepdim=True);q=(z.double()/2).log_softmax(1)
    kl=torch.where(p>0,p*(p.log()-q),torch.zeros_like(p)).sum(1)
    a=p.argmax(1);b=z.argmax(1)
    return {'n':len(z),'teacher_student_agreement':float((a==b).double().mean()),
            'distillation_loss_T2':max(0.,4*float(kl.mean())),
            'teacher_class_counts':torch.bincount(a,minlength=10).tolist(),
            'student_class_counts':torch.bincount(b,minlength=10).tolist()}


@torch.inference_mode()
def query_forward(model,x):
    return torch.cat([model(norm(v)) for v in x.split(32)]).double()


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources();core.OUT=OUT
    freeze=core.read(s.HERE/'FIDELITY_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time()},f)
    selected,sealed,states=s.snapshot();root=s.HERE/'stage10/attack_cover850'
    receipt=core.read(root/'COMPLETED.json');decl=core.read(root/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
    qpath=root/'private_querybank.pt';assert core.sha(qpath)==receipt['files'][qpath.name]
    bank=torch.load(qpath,map_location='cpu',weights_only=True)
    split=core.read(s.HERE/'PROXY_SPLIT.json');fit=torch.tensor(split['fit_ids']);held=set(split['heldout_ids'])
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['record_path'])==info['record_path_sha256']
    record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    tids=[int(i) for i in record['bd_test']['bd_data_container']['data_dict']];mask=torch.tensor([i in held for i in tids])
    hp=s.OUT/'attack_cover850_aligned_head.pt';assert core.sha(hp)==core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['heads'][hp.name]
    head=torch.load(hp,map_location='cpu',weights_only=True);features=s.feature_cache('attack_cover850',True)
    public_teacher=s.logits(features['clean'][fit],head);actual_teacher=s.logits(features['attack'],head)
    model=sealed.model_class(Path(selected['source_root']))().eval()
    model.load_state_dict(states['post'],strict=True);native_query=query_forward(model,bank['queries'])
    result={'state':'running','query_reference':'actual saved CPU-FP32 teacher probabilities atT2',
            'public_trigger_reference':'pinned GPU-FP32 features/FP64 head cache',
            'nativepost_on_queries':stats(bank['teacher_prob_T2'],native_query),'arms':{},
            'heldout_trigger_n':int(mask.sum()),'new_model_forward_images':256,'new_training':False}
    for arm in ['clean_only','query_transfer']:
        pp=root/('private_'+arm+'_proxy.pt');assert core.sha(pp)==receipt['files'][pp.name]
        proxy=torch.load(pp,map_location='cpu',weights_only=True);rows={}
        for variant,entry,alpha in [('raw',decl['raw_models'][arm],1.),('selected',decl['models'][arm],decl['models'][arm]['alpha'])]:
            path=root/entry['path'];assert core.sha(path)==entry['sha256'];state=torch.load(path,map_location='cpu',weights_only=True)
            model.load_state_dict(state,strict=True);qz=query_forward(model,bank['queries'])
            assert core.tensor_digest(state)==core.tensor_digest(model.state_dict())
            position=proxy['alphas'].index(alpha);pz=proxy['candidate_logits'][position]
            ap=root/('private_'+arm+'_'+variant+'_attack.pt');assert core.sha(ap)==receipt['files'][ap.name]
            az=torch.load(ap,map_location='cpu',weights_only=True)['attack_logits']
            pa=actual_teacher.argmax(1);pb=az.argmax(1)
            row={'publicfit':stats((public_teacher/2).softmax(1),pz),
                 'generated':stats(bank['teacher_prob_T2'],qz),
                 'heldout_trigger':stats((actual_teacher[mask]/2).softmax(1),az[mask]),
                 'full_ASR_pct':100*float((pb==0).double().mean()),'full_target_n':int((pb==0).sum()),
                 'heldout_ASR_pct':100*float((pb[mask]==0).double().mean()),'heldout_target_n':int((pb[mask]==0).sum()),
                 'teacher_heldout_ASR_pct':100*float((pa[mask]==0).double().mean()),
                 'directional_risk_heldout':float(((pb[mask]==0)&(pa[mask]!=0)).double().mean())}
            assert row['heldout_ASR_pct']/100<=row['teacher_heldout_ASR_pct']/100+row['directional_risk_heldout']+1e-12
            row['heldout_and_full_ASR_gate']=row['heldout_ASR_pct']<=10 and row['full_ASR_pct']<=10
            rows[variant]=row;result['new_model_forward_images']+=256
        result['arms'][arm]=rows;core.write('RESULT.json',result)
    assert result['new_model_forward_images']==1280 and not torch.cuda.is_initialized()
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    result.update(state='completed',finished_unix=time.time());core.write('RESULT.json',result)
    core.write('COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),'freeze_sha256':core.sha(s.HERE/'FIDELITY_FREEZE.json')})
    print(json.dumps({'state':'completed','native_Q_agreement':result['nativepost_on_queries']['teacher_student_agreement'],
       'arms':{a:{v:{'Q_agreement':r['generated']['teacher_student_agreement'],'trigger_agreement':r['heldout_trigger']['teacher_student_agreement'],
                    'heldout_ASR':r['heldout_ASR_pct']} for v,r in values.items()} for a,values in result['arms'].items()}}),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);core.OUT=OUT;core.write('FAILURE.json',{'traceback':traceback.format_exc()});raise
