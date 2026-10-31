"""One same-batch optimizer comparison, never resumes or changes the live H8 job."""
import json,os,time,subprocess
from pathlib import Path
import torch
import stage05_common as s
from stage08 import norm,loss
core=s.core
OUT=s.HERE/'step_diagnosis'


@torch.no_grad()
def objective(model,public,tclean,pclean,ix,bank,targets,q,arm):
    z=model(norm(public[ix]));value=loss(tclean[ix],z)+loss(pclean[ix],z)
    if arm=='query_transfer':value=value+loss(targets[q],model(norm(bank[q])))
    return float(value)


@torch.no_grad()
def full_clean(model,public,tclean,pclean):
    value=0.
    for i in range(0,len(public),32):
        z=model(norm(public[i:i+32]));value+=float(loss(tclean[i:i+32],z)+loss(pclean[i:i+32],z))*len(z)
    return value/len(public)


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources();core.OUT=OUT
    frozen=core.read(s.HERE/'STEP_DIAGNOSIS_FREEZE.json')
    for n,h in frozen['files'].items():assert core.sha(s.HERE/n)==h,n
    cpu=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Processor | Select-Object NumberOfLogicalProcessors,LoadPercentage | ConvertTo-Json -Compress'],text=True))
    assert cpu['NumberOfLogicalProcessors']>=8 and cpu['LoadPercentage']<=60 and not torch.cuda.is_initialized()
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu},f)
    selected,sealed,states=s.snapshot();cls=sealed.model_class(Path(selected['source_root']))
    native=states['clean_big_post'];teacher=cls().eval();post=cls().eval()
    hp=s.OUT/'benign_big19336_aligned_model.pt'
    assert core.sha(hp)==core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['models'][hp.name]
    teacher.load_state_dict(torch.load(hp,map_location='cpu',weights_only=True),strict=True);post.load_state_dict(native,strict=True)
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    fit=core.read(s.HERE/'PROXY_SPLIT.json')['fit_ids']
    public=torch.load(info['clean_path'],map_location='cpu',weights_only=True)['test_x'][fit].permute(0,3,1,2).float().div(255).contiguous()
    with torch.no_grad():
        tclean=torch.cat([(teacher(norm(x))/2).softmax(1) for x in public.split(32)])
        pclean=torch.cat([(post(norm(x))/2).softmax(1) for x in public.split(32)])
    qb=s.HERE/'stage08/private_querybank.pt';qr=core.read(s.HERE/'stage08/QUERYBANK_BEFORE_TRAINING.json')
    assert core.sha(qb)==qr['sha256'];qd=torch.load(qb,map_location='cpu',weights_only=True)
    bank=qd['queries'];targets=qd['teacher_prob_T2']
    ix=torch.randint(500,(32,),generator=torch.Generator().manual_seed(20261031+901))
    q=torch.randint(256,(8,),generator=torch.Generator().manual_seed(20261031+902))
    result={'state':'running','arms':{}}
    for arm in ['clean_only','query_transfer']:
        model=cls().eval();model.load_state_dict(native,strict=True)
        before=objective(model,public,tclean,pclean,ix,bank,targets,q,arm)
        source_log=s.HERE/'stage08'/(arm+'_steps.jsonl')
        if source_log.exists():
            actual=json.loads(source_log.read_text(encoding='utf8').splitlines()[0])
            assert abs(before-(actual['clean_loss']+actual['query_loss']))<1e-6
        full_before=full_clean(model,public,tclean,pclean)
        optimizer=torch.optim.Adam(model.parameters(),lr=.0001,weight_decay=0)
        z=model(norm(public[ix]));v=loss(tclean[ix],z)+loss(pclean[ix],z)
        if arm=='query_transfer':v=v+loss(targets[q],model(norm(bank[q])))
        v.backward();grad={name:p.grad.clone() for name,p in model.named_parameters()}
        optimizer.step();adam=objective(model,public,tclean,pclean,ix,bank,targets,q,arm)
        afull=full_clean(model,public,tclean,pclean)
        ap=OUT/(arm+'_adam_once.pt');torch.save(model.state_dict(),ap)
        trials=[];accepted=None
        for i in range(8):
            lr=.01/(2**i);model.load_state_dict(native,strict=True)
            with torch.no_grad():
                for name,p in model.named_parameters():p.add_(grad[name],alpha=-lr)
            after=objective(model,public,tclean,pclean,ix,bank,targets,q,arm)
            trials.append({'lr':lr,'same_batch_after':after})
            if after<=before-1e-8:
                accepted={'lr':lr,'same_batch_after':after,'full500_after':full_clean(model,public,tclean,pclean)}
                sp=OUT/(arm+'_sgd_once.pt');torch.save(model.state_dict(),sp)
                accepted['sha256']=core.sha(sp);break
        result['arms'][arm]={'same_batch_before':before,'full500_before':full_before,
            'adam_same_batch_after':adam,'adam_full500_after':afull,'adam_sha256':core.sha(ap),
            'sgd_trials':trials,'sgd_accepted':accepted,'hypothesis_supported':adam>before and accepted is not None}
        core.write('RESULT.json',result)
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256']);assert not torch.cuda.is_initialized()
    result.update(state='completed');core.write('RESULT.json',result)
    core.write('COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),'freeze_sha256':core.sha(s.HERE/'STEP_DIAGNOSIS_FREEZE.json')})
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
