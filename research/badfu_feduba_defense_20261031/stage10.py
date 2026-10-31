"""Source-frozen attack-first extension of public-query compression + output guard."""
import hashlib,json,os,shutil,subprocess,time,traceback
from pathlib import Path
import numpy as np
import torch
import stage05_common as s
import stage05_delete as removed
from stage08 import norm,loss
from stage09 import mix,proxy_metrics
core=s.core
OUT=s.HERE/'stage10'
ARMS=['clean_only','query_transfer']


def write(root,name,obj):
    p=root/name;t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8');os.replace(t,p)


@torch.inference_mode()
def forward(model,raw,root,phase):
    parts=[]
    for i in range(0,len(raw),32):
        parts.append(model(core.normalise(raw[i:i+32])))
        if i%3200==0:write(root,'PROGRESS.json',{'phase':phase,'n':len(raw),'completed':min(i+32,len(raw)),'time':time.time()})
    z=torch.cat(parts).double();assert torch.isfinite(z).all();return z


def train_and_select(native,teacher_state,public,cls,root,deadline):
    """Receives model states/public images only; no labels, trigger or request truth."""
    teacher=cls().eval();post=cls().eval()
    teacher.load_state_dict(teacher_state,strict=True);post.load_state_dict(native,strict=True)
    for model in [teacher,post]:
        for p in model.parameters():p.requires_grad_(False)
    x=public.permute(0,3,1,2).float().div(255).contiguous()
    with torch.no_grad():
        tc=torch.cat([(teacher(norm(v))/2).softmax(1) for v in x.split(32)])
        pc=torch.cat([(post(norm(v))/2).softmax(1) for v in x.split(32)])
    gen=torch.Generator().manual_seed(20261031);bank=[];targets=[];querylogs=[]
    for batch in range(32):
        deadline();tick=time.monotonic();q=torch.rand((8,3,32,32),generator=gen)
        if batch%2:q=.5*q+.5*x[torch.randint(len(x),(8,),generator=gen)]
        for _ in range(10):
            q=q.detach().requires_grad_(True);value=loss((teacher(norm(q))/2).softmax(1),post(norm(q)))
            gradient=torch.autograd.grad(value,q)[0];assert torch.isfinite(gradient).all()
            q=(q+.1*gradient.sign()).detach().clamp(0,1)
        with torch.no_grad():target=(teacher(norm(q))/2).softmax(1)
        bank.append(q);targets.append(target)
        querylogs.append({'batch':batch,'seconds':time.monotonic()-tick,'divergence':float(value.detach())})
        write(root,'QUERY_PROGRESS.json',{'completed':batch+1,'total':32,'time':time.time()})
    bank=torch.cat(bank);targets=torch.cat(targets)
    torch.save({'queries':bank,'teacher_prob_T2':targets},root/'private_querybank.pt')
    write(root,'QUERYBANK_BEFORE_TRAINING.json',{'sha256':core.sha(root/'private_querybank.pt'),'n':256,'logs':querylogs})
    raw_models={}
    for arm in ARMS:
        torch.manual_seed(20261031);student=cls().eval();student.load_state_dict(native,strict=True)
        optimizer=torch.optim.Adam(student.parameters(),lr=.0001,weight_decay=0)
        gf=torch.Generator().manual_seed(20261031+901);gq=torch.Generator().manual_seed(20261031+902)
        with (root/(arm+'_steps.jsonl')).open('x',encoding='utf8') as f:
            for step in range(100):
                deadline();tick=time.monotonic();ix=torch.randint(len(x),(32,),generator=gf)
                optimizer.zero_grad(set_to_none=True);z=student(norm(x[ix]))
                c=loss(tc[ix],z)+loss(pc[ix],z);q=z.new_zeros(())
                if arm=='query_transfer':
                    qi=torch.randint(len(bank),(8,),generator=gq);q=loss(targets[qi],student(norm(bank[qi])))
                v=c+q;assert torch.isfinite(v);v.backward()
                assert all(p.grad is None or torch.isfinite(p.grad).all() for p in student.parameters())
                optimizer.step();assert all(torch.isfinite(t).all() for t in student.state_dict().values())
                row={'step':step+1,'clean_loss':float(c.detach()),'query_loss':float(q.detach()),'seconds':time.monotonic()-tick}
                f.write(json.dumps(row)+'\n');f.flush();write(root,'TRAIN_PROGRESS.json',{'arm':arm,**row,'time':time.time()})
        st={k:v.detach().clone() for k,v in student.state_dict().items()}
        for k in st:
            if core.is_buffer(k):assert torch.equal(st[k],native[k]),k
        path=root/(arm+'_raw.pt');torch.save(st,path)
        torch.save({'optimizer':optimizer.state_dict(),'torch_rng':torch.get_rng_state(),'public_sampler_rng':gf.get_state(),'query_sampler_rng':gq.get_state()},root/(arm+'_optimizer_rng.pt'))
        raw_models[arm]={'path':path.name,'sha256':core.sha(path),'steps':100}
    write(root,'RAW_MODELS_BEFORE_SELECTION.json',raw_models)
    proxy=forward(post,public,root,'proxy_nativepost');choices={};selected_models={};allrows={}
    for arm in ARMS:
        parent=raw_models[arm];assert core.sha(root/parent['path'])==parent['sha256']
        st=torch.load(root/parent['path'],map_location='cpu',weights_only=True);model=cls().eval();rows=[];zs=[]
        def probe(alpha):
            deadline();state=mix(native,st,alpha);model.load_state_dict(state,strict=True)
            z=forward(model,public,root,'proxy_'+arm);r={'alpha':alpha,**proxy_metrics(proxy,z),'tensor_sha256':core.tensor_digest(state)}
            rows.append(r);zs.append(z);write(root,'SELECTION_PROGRESS.json',{'arm':arm,'tested':len(rows),'latest':r,'time':time.time()});return r
        for i in range(11):probe(i/10)
        best=max((r for r in rows if r['eligible']),key=lambda r:r['alpha'])
        if best['alpha']<1:
            lo=best['alpha'];hi=min(r['alpha'] for r in rows if r['alpha']>lo)
            for _ in range(6):
                mid=(lo+hi)/2;r=probe(mid)
                if r['eligible']:lo=mid
                else:hi=mid
        choice=max((r for r in rows if r['eligible']),key=lambda r:r['alpha']);choices[arm]=choice;allrows[arm]=rows
        state=mix(native,st,choice['alpha']);path=root/(arm+'_selected.pt');torch.save(state,path)
        torch.save({'teacher_logits':proxy,'alphas':[r['alpha'] for r in rows],'candidate_logits':torch.stack(zs)},root/('private_'+arm+'_proxy.pt'))
        selected_models[arm]={'path':path.name,'sha256':core.sha(path),'alpha':choice['alpha']}
    declaration={'raw_models':raw_models,'models':selected_models,'choices':choices,'all_points':allrows,
                 'labels_used':False,'member_used':False,'actual_trigger_used':False,'ASR_used':False}
    write(root,'SELECTION_BEFORE_PRIVATE_EVALUATION.json',declaration)
    return declaration


def evaluate(pair,a,b,states,declaration,cls,root,info,labels,held,large_passed,deadline):
    """Evaluator-only: never passes truth or results into training/selection."""
    selected_path=root/'SELECTION_BEFORE_PRIVATE_EVALUATION.json';fixed=core.sha(selected_path)
    datasets,extra=removed.data();member,my,ids,key,ny=datasets[pair]
    complete=core.read(extra[key]['path'])
    assert hashlib.sha256(np.asarray(sorted(ids),dtype=np.int64).tobytes()).hexdigest()==complete['audit']['removed_indices_sha256']
    assert complete['checkpoint_sha256']==core.read(root/'SOURCE_INPUTS.json')['post_sha256']
    if pair=='attack_cover850':clean,y,attack=core.load_data(info)
    else:
        assert core.sha(info['clean_path'])==info['clean_path_sha256']
        raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
        clean=raw['test_x'];y=raw['test_y'].long();attack=None
    assert torch.equal(y,labels)
    result={'state':'running','cases':{},'selection_sha256':fixed,'formal_deletion_certificate':False}
    model=cls().eval()
    if pair=='attack_cover850':
        asr={}
        for arm in ARMS:
            asr[arm]={}
            for variant,entry in [('raw',declaration['raw_models'][arm]),('selected',declaration['models'][arm])]:
                deadline();path=root/entry['path'];assert core.sha(path)==entry['sha256']
                state=torch.load(path,map_location='cpu',weights_only=True);model.load_state_dict(state,strict=True)
                if core.tensor_digest(state)==core.tensor_digest(states[b]):
                    previous=next(r for r in core.read(s.HERE/'stage03/RESULT.json')['rows']
                                  if r['pair']==pair and r['W']==r['BN']==r['head']==1)
                    asr[arm][variant]={'target_n':previous['attack_target_n'],'n':previous['attack_n'],
                        'ASR_pct':previous['ASR_pct'],'identity_original_counts_reused':True}
                    continue
                z=forward(model,attack,root,arm+'_'+variant+'_attack')
                assert core.tensor_digest(state)==core.tensor_digest(model.state_dict())
                torch.save({'attack_logits':z},root/('private_'+arm+'_'+variant+'_attack.pt'))
                asr[arm][variant]={'target_n':int((z.argmax(1)==0).sum()),'n':len(z),'ASR_pct':100*float((z.argmax(1)==0).double().mean())}
        result['all_ASR']=asr
        eligible=[arm for arm in ARMS if arm in large_passed and declaration['models'][arm]['alpha']>0 and asr[arm]['selected']['ASR_pct']<=10]
        if not eligible:
            result.update(state='failed_necessary_ASR',extension_permitted=False,clean_member_audits='skipped_by_preregistered_ASR_stop')
            assert core.sha(selected_path)==fixed;write(root,'RESULT.json',result);return result
    else:eligible=[arm for arm in ARMS if arm in large_passed and declaration['models'][arm]['alpha']>0]
    before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
    p=s.logits(before['clean'],s.head(states[a]));q=s.logits(after['clean'],s.head(states[b]))
    base=core.metrics(q,labels,p,q,held)
    privacybase=core.read(s.HERE/'stage07_cpu_v2/RESULT.json')['cases'][pair]['variants']['native_post']
    for arm in ARMS:
        if arm not in eligible:
            result['cases'][arm]={'necessary_gate':False,'reason':'failed prior necessary gate or identity'};continue
        deadline();entry=declaration['models'][arm];path=root/entry['path'];assert core.sha(path)==entry['sha256']
        state=torch.load(path,map_location='cpu',weights_only=True);model.load_state_dict(state,strict=True)
        cz=forward(model,clean,root,arm+'_clean');mz=forward(model,member,root,arm+'_removed')
        assert core.tensor_digest(state)==core.tensor_digest(model.state_dict())
        torch.save({'clean_logits':cz,'member_logits':mz,'member_labels':my},root/('private_'+arm+'_evaluation.pt'))
        if pair.startswith('attack'):
            za=torch.load(root/('private_'+arm+'_selected_attack.pt'),weights_only=True)['attack_logits']
            nonmember=za
        else:nonmember=cz
        metric=core.metrics(cz,labels,p,q,held);audit=s.membership(mz,my,nonmember,ny)
        increases={name:{measure:audit['scores'][name][measure]-privacybase['scores'][name][measure] for measure in ['advantage','weighted_class_advantage']} for name in privacybase['scores']}
        gap=abs(audit['weighted_accuracy_gap'])-abs(privacybase['weighted_accuracy_gap'])
        drop=base['CA_pct']-metric['CA_pct'];worst=max(u-v for u,v in zip(base['class_CA_pct'],metric['class_CA_pct']))
        result['cases'][arm]={'alpha':entry['alpha'],'clean':metric,'deletion_audit':audit,'increase_over_post':increases,
            'absolute_accuracy_gap_increase':gap,'overall_drop_pp':drop,'worst_class_drop_pp':worst,
            'necessary_gate':drop<=.5+1e-10 and worst<=2+1e-10 and gap<=.02+1e-12 and all(v<=.04+1e-12 for scores in increases.values() for v in scores.values())}
        write(root,'RESULT.json',result)
    assert core.sha(selected_path)==fixed
    result.update(state='completed',extension_permitted=any(v['necessary_gate'] for v in result['cases'].values()))
    write(root,'RESULT.json',result);return result


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources()
    freeze=core.read(s.HERE/'STAGE10_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    prior=core.read(s.HERE/'stage09/RESULT.json');verification=core.read(s.HERE/'stage09/INDEPENDENT_VERIFICATION.json')
    assert prior['state']=='completed' and verification['state']=='passed'
    large_passed=[arm for arm in ARMS if prior['cases'][arm]['necessary_gate']]
    assert large_passed,'large benign prerequisite failed; do not launch'
    cpu=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Processor | Select-Object NumberOfLogicalProcessors,LoadPercentage | ConvertTo-Json -Compress'],text=True))
    assert cpu['NumberOfLogicalProcessors']>=8 and cpu['LoadPercentage']<=60 and not torch.cuda.is_initialized()
    assert shutil.disk_usage(OUT).free>=4*1024**3
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu,'large_passed_arms':large_passed},f)
    whole=time.monotonic();selected,sealed,states=s.snapshot();cls=sealed.model_class(Path(selected['source_root']))
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    split=core.read(s.HERE/'PROXY_SPLIT.json');public=raw['test_x'][split['fit_ids']];held=torch.tensor(split['heldout_ids'])
    summary={'state':'running','large_passed_arms':large_passed,'cases':{},'new_FL_seeds':0,
             'scope':'one_existing_BadFU_seed_three_case_necessary_test','FedUBA_evaluated':False}
    for pair,a,b in [('attack_cover850','pre','post'),('benign_same850','clean_pre','clean_post')]:
        root=OUT/pair;root.mkdir(exist_ok=False);tick=time.monotonic()
        def deadline():assert time.monotonic()-tick<3000 and time.monotonic()-whole<6300,'bounded profile runtime'
        hp=s.OUT/(pair+'_aligned_model.pt')
        assert core.sha(hp)==core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['models'][hp.name]
        teacher=torch.load(hp,map_location='cpu',weights_only=True)
        write(root,'SOURCE_INPUTS.json',{'case_id':selected['case_id'],'purpose':'purification_pilot',
            'pre_role':a,'post_role':b,'post_sha256':selected['server_inputs'][b]['sha256'],'teacher_sha256':core.sha(hp)})
        declaration=train_and_select(states[b],teacher,public,cls,root,deadline)
        report=evaluate(pair,a,b,states,declaration,cls,root,info,raw['test_y'].long(),held,large_passed,deadline)
        write(root,'COMPLETED.json',{'result_sha256':core.sha(root/'RESULT.json'),
            'files':{p.name:core.sha(p) for p in root.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
        summary['cases'][pair]=report;write(OUT,'RESULT.json',summary)
        sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
        if pair=='attack_cover850':
            survivors=[arm for arm in large_passed if report.get('cases',{}).get(arm,{}).get('necessary_gate',False)]
            if not survivors:break
            large_passed=survivors
    assert not torch.cuda.is_initialized()
    summary['method_necessary_gates']={arm:arm in summary['large_passed_arms'] and
        all(summary['cases'].get(pair,{}).get('cases',{}).get(arm,{}).get('necessary_gate',False)
            for pair in ['attack_cover850','benign_same850']) for arm in ARMS}
    summary.update(state='completed',same850_executed='benign_same850' in summary['cases'],finished_unix=time.time(),CUDA_initialized=False)
    write(OUT,'RESULT.json',summary);write(OUT,'COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),
        'source_freeze_sha256':core.sha(s.HERE/'STAGE10_FREEZE.json')})
    print('STAGE10_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);write(OUT,'FAILURE.json',{'traceback':traceback.format_exc()});raise
