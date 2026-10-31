"""Matched model-pseudo-source query generation; no classifier learner/evaluator."""
import json,os,shutil,subprocess,time,traceback
from pathlib import Path
import torch
import stage05_common as s
from stage08 import norm
from stage11_method import disjoint_objective
core=s.core;OUT=s.HERE/'sourcepair_pilot'
ARMS=['teacher_not_k','teacher_source']


def write(root,name,obj):
    p=root/name;t=p.with_suffix('.tmp');t.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf8');os.replace(t,p)


def source_objective(tz,pz,source,k):
    return ((pz/2).log_softmax(1)[:,k]+(tz/2).log_softmax(1).gather(1,source[:,None]).squeeze(1)).mean()


def cpu_guard():
    z=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Processor | Select-Object NumberOfLogicalProcessors,LoadPercentage | ConvertTo-Json -Compress'],text=True))
    if z.get('LoadPercentage') is None:
        fallback=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -eq '_Total' | Select-Object PercentProcessorTime | ConvertTo-Json -Compress"],text=True))
        assert fallback.get('PercentProcessorTime') is not None
        z['LoadPercentage']=fallback['PercentProcessorTime'];z['load_source']='PerfOS_total'
    else:z['load_source']='Win32_Processor'
    assert z['NumberOfLogicalProcessors']>=8 and 0<=z['LoadPercentage']<=60
    return z


def objective_contract():
    t=torch.tensor([[0.,8.,0.]],dtype=torch.float64,requires_grad=True)
    p=torch.tensor([[8.,0.,0.]],dtype=torch.float64,requires_grad=True);label=torch.tensor([1])
    v=source_objective(t,p,label,0)
    direct=torch.log((p/2).softmax(1)[:,0]*(t/2).softmax(1)[:,1]).mean()
    assert abs(float((v-direct).detach()))<1e-12
    gt,gp=torch.autograd.grad(v,(t,p));assert gt[0,1]>0 and gp[0,0]>0
    return {'state':'passed','probability_identity':True,'teacher_source_and_post_target_gradient_signs':True}


def run_case(pair,poststate,teacherstate,public,cls,root,deadline):
    post=cls().eval();teacher=cls().eval();post.load_state_dict(poststate,strict=True);teacher.load_state_dict(teacherstate,strict=True)
    for m in [post,teacher]:
        for p in m.parameters():p.requires_grad_(False)
    x=public.permute(0,3,1,2).float().div(255).contiguous()
    with torch.no_grad():
        tp=torch.cat([teacher(norm(v)) for v in x.split(32)]).argmax(1)
        pp=torch.cat([post(norm(v)) for v in x.split(32)]).argmax(1)
    pools=[torch.where((tp==c)&(pp==c))[0] for c in range(10)]
    assert all(len(pool)>0 for pool in pools),'public model-agreement source class missing'
    g=torch.Generator().manual_seed(20261031+1300);starts=[];sources=[]
    for k in range(10):
        labels=torch.tensor([c for c in range(10) if c!=k])
        indices=torch.stack([pools[int(c)][torch.randint(len(pools[int(c)]),(1,),generator=g)[0]] for c in labels])
        starts.append(x[indices].clone());sources.append(labels)
    starts=torch.cat(starts);sources=torch.cat(sources);requested=torch.arange(10).repeat_interleave(9)
    torch.save({'starts':starts,'sources':sources,'requested':requested,'rng':g.get_state()},root/'private_initials.pt')
    write(root,'INITIALS.json',{'sha256':core.sha(root/'private_initials.pt'),'n':90,'source_pool_counts':[len(v) for v in pools],'groundtruth_labels_used':False})
    result={'state':'running','arms':{}}
    for arm in ARMS:
        qs=[];ts=[];ps=[];logs=[]
        for k in range(10):
            deadline();q=starts[k*9:(k+1)*9].clone();labels=sources[k*9:(k+1)*9];steps=[]
            for step in range(20):
                q=q.detach().requires_grad_(True);tz=teacher(norm(q));pz=post(norm(q))
                value=disjoint_objective(tz,pz,k) if arm=='teacher_not_k' else source_objective(tz,pz,labels,k)
                assert torch.isfinite(value);grad=torch.autograd.grad(value,q)[0];assert torch.isfinite(grad).all()
                steps.append({'step':step+1,'objective':float(value.detach())})
                q=(q+.1*grad.sign()).detach().clamp(0,1)
            with torch.no_grad():tz=teacher(norm(q));pz=post(norm(q))
            qs.append(q);ts.append(tz);ps.append(pz);logs.append({'k':k,'steps':steps})
            write(root,'PROGRESS.json',{'arm':arm,'target_batches_completed':k+1,'total':10,'time':time.time()})
        q=torch.cat(qs);tz=torch.cat(ts);pz=torch.cat(ps);t=tz.argmax(1);p=pz.argmax(1)
        success=(p==requested)&(t==sources);matrix=[[0]*10 for _ in range(10)]
        for a,b,ok in zip(sources.tolist(),requested.tolist(),success.tolist()):matrix[a][b]+=int(ok)
        path=root/('private_'+arm+'_bank.pt')
        torch.save({'queries':q,'teacher_prob_T2':(tz/2).softmax(1),'teacher_logits':tz,'post_logits':pz,
                    'requested':requested,'sources':sources},path)
        counts=torch.bincount(t,minlength=10).tolist()
        result['arms'][arm]={'n':90,'sha256':core.sha(path),'assigned_source_correct_n':int((t==sources).sum()),
            'teacher_class_counts':counts,'post_class_counts':torch.bincount(p,minlength=10).tolist(),
            'joint_pair_success_n':int(success.sum()),'source_target_success_matrix':matrix,'logs':logs}
        write(root,'RESULT.json',result)
    a=result['arms']['teacher_not_k'];b=result['arms']['teacher_source']
    feasible={arm:r['assigned_source_correct_n']>=72 and min(r['teacher_class_counts'])>0 and max(r['teacher_class_counts'])<=18 for arm,r in result['arms'].items()}
    result.update(state='completed',source_feasibility_gate=any(feasible.values()),feasible_arms=feasible,
                  extra_source_objective_fidelity_gain_n=b['assigned_source_correct_n']-a['assigned_source_correct_n'])
    write(root,'RESULT.json',result);write(root,'COMPLETED.json',{'result_sha256':core.sha(root/'RESULT.json'),'files':{p.name:core.sha(p) for p in root.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
    return result


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources();freeze=core.read(s.HERE/'SOURCEPAIR_PILOT_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    audit=core.read(s.HERE/'stage11/INDEPENDENT_VERIFICATION.json')
    assert audit['state']=='passed' and audit['scope']=='finished_pipeline' and audit['root_result_snapshot_sha256']==core.sha(s.HERE/'stage11/RESULT.json')
    cpu=cpu_guard();assert shutil.disk_usage(OUT).free>=4*1024**3 and not torch.cuda.is_initialized()
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu},f)
    write(OUT,'OBJECTIVE_CONTRACT.json',objective_contract())
    selected,sealed,states=s.snapshot();cls=sealed.model_class(Path(selected['source_root']))
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    public=raw['test_x'][core.read(s.HERE/'PROXY_SPLIT.json')['fit_ids']]
    whole=time.monotonic();summary={'state':'running','cases':{},'new_classifier_training':False,'actual_trigger_evaluated':False,'FedUBA_evaluated':False}
    for pair,role in [('benign_big19336','clean_big_post'),('attack_cover850','post')]:
        tick=time.monotonic();root=OUT/pair;root.mkdir(exist_ok=False)
        def deadline():assert time.monotonic()-tick<900 and time.monotonic()-whole<1800
        path=s.OUT/(pair+'_aligned_model.pt');expected=core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['models'][path.name]
        assert core.sha(path)==expected
        write(root,'SOURCE_INPUTS.json',{'case_id':selected['case_id'],'purpose':'purification_pilot','post_role':role,
            'post_sha256':selected['server_inputs'][role]['sha256'],'teacher_sha256':expected})
        summary['cases'][pair]=run_case(pair,states[role],torch.load(path,map_location='cpu',weights_only=True),public,cls,root,deadline)
        write(OUT,'RESULT.json',summary)
        if not summary['cases'][pair]['source_feasibility_gate']:break
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    summary['state']='completed';write(OUT,'RESULT.json',summary)
    write(OUT,'COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),'source_freeze_sha256':core.sha(s.HERE/'SOURCEPAIR_PILOT_FREEZE.json')})
    print('SOURCEPAIR_PILOT_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);write(OUT,'FAILURE.json',{'traceback':traceback.format_exc()});raise
