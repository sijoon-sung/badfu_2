"""Bounded two-arm Post-initialized public-query compression on large benign deletion."""
import json
import os
from pathlib import Path
import subprocess
import time
import traceback
import torch
import torch.nn.functional as F
import stage05_common as s
import stage05_delete as removed
core=s.core
OUT=s.HERE/'stage08'
PAIR='benign_big19336'


def write(name,obj):
    core.OUT=OUT;core.write(name,obj)


def norm(x):
    mean=x.new_tensor([.4914,.4822,.4465])[None,:,None,None]
    std=x.new_tensor([.2023,.1994,.2010])[None,:,None,None]
    return ((x-mean)/std).contiguous()


def loss(target,z):
    return F.kl_div((z/2).log_softmax(1),target,reduction='batchmean')*4


@torch.inference_mode()
def forward(model,raw):
    outputs=[]
    for i in range(0,len(raw),32):
        outputs.append(model(core.normalise(raw[i:i+32])))
        if i%3200==0:write('PROGRESS.json',{'phase':'evaluation','n':len(raw),'completed':min(i+32,len(raw)),'time':time.time()})
    return torch.cat(outputs).double()


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources();core.OUT=OUT
    frozen=core.read(s.HERE/'STAGE08_FREEZE.json')
    for name,h in frozen['files'].items():assert core.sha(s.HERE/name)==h,name
    cpu=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
        'Get-CimInstance Win32_Processor | Select-Object NumberOfLogicalProcessors,LoadPercentage | ConvertTo-Json -Compress'],text=True))
    assert cpu['NumberOfLogicalProcessors']>=8 and cpu['LoadPercentage']<=60 and not torch.cuda.is_initialized()
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU_guard':cpu},f)
    start=time.monotonic()
    def deadline():assert time.monotonic()-start<1800,'bounded30minute runtime limit'
    selected,sealed,states=s.snapshot();a='clean_pre';b='clean_big_post'
    cls=sealed.model_class(Path(selected['source_root']))
    teacher=cls().eval();post=cls().eval();post.load_state_dict(states[b],strict=True)
    hp=s.OUT/(PAIR+'_aligned_model.pt')
    assert core.sha(hp)==core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['models'][hp.name]
    teacher_state=torch.load(hp,map_location='cpu',weights_only=True);teacher.load_state_dict(teacher_state,strict=True)
    for model in [teacher,post]:
        for p in model.parameters():p.requires_grad_(False)
    info=core.read(s.HERE/'STAGE03_INPUTS.json')
    assert core.sha(info['clean_path'])==info['clean_path_sha256']
    # Only public images are extracted here. Labels remain evaluator-only.
    raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    split=core.read(s.HERE/'PROXY_SPLIT.json');fit=torch.tensor(split['fit_ids']);held=torch.tensor(split['heldout_ids'])
    public=raw['test_x'][fit].permute(0,3,1,2).float().div(255).contiguous()
    with torch.inference_mode():
        tclean=torch.cat([(teacher(norm(x))/2).softmax(1) for x in public.split(32)])
        pclean=torch.cat([(post(norm(x))/2).softmax(1) for x in public.split(32)])
    tclean=tclean.clone();pclean=pclean.clone()
    bank=[];targets=[];query_logs=[];gen=torch.Generator().manual_seed(20261031)
    for batch in range(32):
        deadline();tick=time.monotonic();x=torch.rand((8,3,32,32),generator=gen)
        if batch%2:x=.5*x+.5*public[torch.randint(len(public),(8,),generator=gen)]
        for step in range(10):
            x=x.detach().requires_grad_(True)
            divergence=loss((teacher(norm(x))/2).softmax(1),post(norm(x)))
            grad=torch.autograd.grad(divergence,x)[0]
            assert torch.isfinite(grad).all()
            x=(x+.1*grad.sign()).detach().clamp(0,1)
        with torch.inference_mode():target=(teacher(norm(x))/2).softmax(1)
        bank.append(x);targets.append(target)
        query_logs.append({'batch':batch,'seconds':time.monotonic()-tick,'divergence':float(divergence.detach())})
        write('QUERY_PROGRESS.json',{'batches_completed':batch+1,'total':32,'time':time.time()})
    bank=torch.cat(bank);targets=torch.cat(targets)
    torch.save({'queries':bank,'teacher_prob_T2':targets},OUT/'private_querybank.pt')
    write('QUERYBANK_BEFORE_TRAINING.json',{'sha256':core.sha(OUT/'private_querybank.pt'),'n':len(bank),'logs':query_logs,
                                          'true_labels_used':False,'trigger_used':False,'deleted_data_used':False})
    models={}
    for arm in ['clean_only','query_transfer']:
        torch.manual_seed(20261031)
        model=cls().eval();model.load_state_dict(states[b],strict=True)
        optimizer=torch.optim.Adam(model.parameters(),lr=.0001,weight_decay=0)
        gfit=torch.Generator().manual_seed(20261031+901);gquery=torch.Generator().manual_seed(20261031+902)
        with (OUT/(arm+'_steps.jsonl')).open('x',encoding='utf8') as log:
            for step in range(100):
                deadline();tick=time.monotonic();ix=torch.randint(len(public),(32,),generator=gfit)
                optimizer.zero_grad(set_to_none=True);z=model(norm(public[ix]))
                clean=loss(tclean[ix],z)+loss(pclean[ix],z)
                qloss=z.new_zeros(())
                if arm=='query_transfer':
                    q=torch.randint(len(bank),(8,),generator=gquery)
                    qloss=loss(targets[q],model(norm(bank[q])))
                objective=clean+qloss;assert torch.isfinite(objective)
                objective.backward()
                assert all(p.grad is None or torch.isfinite(p.grad).all() for p in model.parameters())
                optimizer.step()
                assert all(torch.isfinite(v).all() for v in model.state_dict().values())
                row={'step':step+1,'clean_loss':float(clean.detach()),'query_loss':float(qloss.detach()),'seconds':time.monotonic()-tick}
                log.write(json.dumps(row)+'\n');log.flush()
                write('TRAIN_PROGRESS.json',{'arm':arm,**row,'time':time.time()})
        st={k:v.detach().clone() for k,v in model.state_dict().items()}
        for k in st:
            if core.is_buffer(k):assert torch.equal(st[k],states[b][k]),('BN mutated',k)
        path=OUT/(arm+'_final.pt');torch.save(st,path)
        torch.save({'optimizer':optimizer.state_dict(),'torch_rng':torch.get_rng_state(),
                    'public_sampler_rng':gfit.get_state(),'query_sampler_rng':gquery.get_state()},OUT/(arm+'_optimizer_rng.pt'))
        models[arm]={'path':path.name,'sha256':core.sha(path),'steps':100,'pre_weights_copied':False}
    write('MODELS_BEFORE_PRIVATE_EVALUATION.json',models)
    # Only after both models are frozen do actual removed data/true labels enter.
    datasets,extra=removed.data();core.OUT=OUT
    member,my,ids,key,ny=datasets[PAIR]
    import hashlib,numpy as np
    complete=core.read(extra[key]['path'])
    assert hashlib.sha256(np.asarray(sorted(ids),dtype=np.int64).tobytes()).hexdigest()==complete['audit']['removed_indices_sha256']
    assert complete['checkpoint_sha256']==selected['server_inputs'][b]['sha256']
    before=s.feature_cache(PAIR,True);after=s.feature_cache(PAIR,False)
    p=s.logits(before['clean'],s.head(states[a]));q=s.logits(after['clean'],s.head(states[b]))
    labels=raw['test_y'].long();base=core.metrics(q,labels,p,q,held)
    privacybase=core.read(s.HERE/'stage07_cpu_v2/RESULT.json')['cases'][PAIR]['variants']['native_post']
    result={'state':'running','cases':{},'pair':PAIR,'actual_attack_test_loaded':False,'formal_deletion_certificate':False}
    for arm in ['clean_only','query_transfer']:
        deadline();model=cls().eval();st=torch.load(OUT/models[arm]['path'],map_location='cpu',weights_only=True)
        assert core.sha(OUT/models[arm]['path'])==models[arm]['sha256'];model.load_state_dict(st,strict=True)
        cz=forward(model,raw['test_x']);mz=forward(model,member)
        assert core.tensor_digest(st)==core.tensor_digest(model.state_dict())
        torch.save({'clean_logits':cz,'member_logits':mz,'member_labels':my},OUT/('private_'+arm+'_logits.pt'))
        metrics=core.metrics(cz,labels,p,q,held);audit=s.membership(mz,my,cz,ny)
        inc={score:{v:audit['scores'][score][v]-privacybase['scores'][score][v] for v in ['advantage','weighted_class_advantage']} for score in privacybase['scores']}
        gap=abs(audit['weighted_accuracy_gap'])-abs(privacybase['weighted_accuracy_gap'])
        ca=base['CA_pct']-metrics['CA_pct'];worst=max(u-v for u,v in zip(base['class_CA_pct'],metrics['class_CA_pct']))
        row={'clean':metrics,'deletion_audit':audit,'increase_over_post':inc,'absolute_accuracy_gap_increase':gap,
             'overall_CA_drop_pp':ca,'worst_class_CA_drop_pp':worst,
             'necessary_gate':ca<=.5+1e-10 and worst<=2+1e-10 and gap<=.02+1e-12 and all(v<=.04+1e-12 for scores in inc.values() for v in scores.values())}
        result['cases'][arm]=row;write('RESULT.json',result)
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    result.update(state='completed',extension_permitted=any(v['necessary_gate'] for v in result['cases'].values()),finished_unix=time.time(),CUDA_initialized=False)
    write('RESULT.json',result)
    write('COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),'files':{p.name:core.sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
    print('STAGE08_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);write('FAILURE.json',{'traceback':traceback.format_exc()});raise
