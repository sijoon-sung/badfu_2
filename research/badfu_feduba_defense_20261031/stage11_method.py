"""Matched query objectives; public-model information only, no evaluator inputs."""
import hashlib,json,time
import torch
import stage05_common as s
from stage08 import norm,loss
from stage09 import mix,proxy_metrics
from stage10 import write,forward
core=s.core
ARMS=['matched_kl','all_class_disjoint']


def disjoint_objective(teacher_logits,post_logits,k):
    t=(teacher_logits/2).log_softmax(1);p=(post_logits/2).log_softmax(1)
    others=torch.arange(t.shape[1],device=t.device)!=k
    return (p[:,k]+torch.logsumexp(t[:,others],1)).mean()


def train_and_select(native,teacher_state,public,cls,root,deadline):
    teacher=cls().eval();post=cls().eval();teacher.load_state_dict(teacher_state,strict=True);post.load_state_dict(native,strict=True)
    for model in [teacher,post]:
        for param in model.parameters():param.requires_grad_(False)
    x=public.permute(0,3,1,2).float().div(255).contiguous()
    with torch.no_grad():
        tc=torch.cat([(teacher(norm(v))/2).softmax(1) for v in x.split(32)])
        pc=torch.cat([(post(norm(v))/2).softmax(1) for v in x.split(32)])
    assert tc.shape[1]==10
    # Exactly the same240 starts and requested output indices for both objectives.
    gen=torch.Generator().manual_seed(20261031);starts=[];requested=[];fallback=[]
    for batch in range(30):
        k=batch%10;q=torch.rand((8,3,32,32),generator=gen)
        pool=torch.where(tc.argmax(1)!=k)[0]
        if not len(pool):pool=torch.arange(len(x));fallback.append(k)
        ix=pool[torch.randint(len(pool),(4,),generator=gen)]
        q[4:]=.5*q[4:]+.5*x[ix]
        starts.append(q);requested.extend([k]*8)
    starts=torch.cat(starts);requested=torch.tensor(requested)
    assert torch.bincount(requested,minlength=10).tolist()==[24]*10
    torch.save({'starts':starts,'requested_classes':requested},root/'private_shared_initials.pt')
    write(root,'INITIAL_BANK_CONTRACT.json',{'sha256':core.sha(root/'private_shared_initials.pt'),
        'requested_count_per_output':[24]*10,'teacher_empty_pool_fallback':fallback,'groundtruth_labels_used':False})
    banks={};generation={}
    for arm in ARMS:
        images=[];targets=[];post_outputs=[];logs=[]
        for batch in range(30):
            deadline();tick=time.monotonic();k=batch%10;q=starts[batch*8:(batch+1)*8].clone()
            for _ in range(20):
                q=q.detach().requires_grad_(True);tz=teacher(norm(q));pz=post(norm(q))
                objective=loss((tz/2).softmax(1),pz) if arm=='matched_kl' else disjoint_objective(tz,pz,k)
                gradient=torch.autograd.grad(objective,q)[0];assert torch.isfinite(gradient).all()
                q=(q+.1*gradient.sign()).detach().clamp(0,1)
            with torch.no_grad():tz=teacher(norm(q));pz=post(norm(q));prob=(tz/2).softmax(1)
            images.append(q);targets.append(prob);post_outputs.append(pz)
            logs.append({'batch':batch,'requested_class':k,'inner_steps':20,'seconds':time.monotonic()-tick,
                         'last_preupdate_objective':float(objective.detach()),
                         'joint_success_n':int(((pz.argmax(1)==k)&(tz.argmax(1)!=k)).sum())})
            write(root,'QUERY_PROGRESS.json',{'arm':arm,'completed':batch+1,'total':30,'time':time.time()})
        images=torch.cat(images);targets=torch.cat(targets);pz=torch.cat(post_outputs)
        bank={'queries':images,'teacher_prob_T2':targets,'post_logits':pz,'requested_classes':requested}
        path=root/('private_'+arm+'_querybank.pt');torch.save(bank,path);banks[arm]=bank
        generation[arm]={'sha256':core.sha(path),'n':240,'inner_steps':600,'image_gradient_evaluations':4800,
            'nativepost_class_counts':torch.bincount(pz.argmax(1),minlength=10).tolist(),
            'teacher_class_counts':torch.bincount(targets.argmax(1),minlength=10).tolist(),
            'joint_success_per_requested_class':[sum(r['joint_success_n'] for r in logs if r['requested_class']==k) for k in range(10)],'logs':logs}
    write(root,'QUERYBANKS_BEFORE_TRAINING.json',generation)
    raw_models={}
    for arm in ARMS:
        bank=banks[arm];torch.manual_seed(20261031);student=cls().eval();student.load_state_dict(native,strict=True)
        optimizer=torch.optim.Adam(student.parameters(),lr=.0001,weight_decay=0)
        gf=torch.Generator().manual_seed(20261031+901);gq=torch.Generator().manual_seed(20261031+902)
        buckets=[torch.where(requested==k)[0] for k in range(10)]
        with (root/(arm+'_steps.jsonl')).open('x',encoding='utf8') as log:
            for step in range(100):
                deadline();tick=time.monotonic();ix=torch.randint(len(x),(32,),generator=gf)
                draws=torch.randint(24,(10,),generator=gq);qi=torch.stack([buckets[k][draws[k]] for k in range(10)])
                optimizer.zero_grad(set_to_none=True);z=student(norm(x[ix]))
                clean=loss(tc[ix],z)+loss(pc[ix],z);query=loss(bank['teacher_prob_T2'][qi],student(norm(bank['queries'][qi])))
                value=clean+query;assert torch.isfinite(value);value.backward()
                assert all(p.grad is None or torch.isfinite(p.grad).all() for p in student.parameters())
                optimizer.step();assert all(torch.isfinite(v).all() for v in student.state_dict().values())
                row={'step':step+1,'clean_loss':float(clean.detach()),'query_loss':float(query.detach()),
                     'query_n':10,'seconds':time.monotonic()-tick,
                     'public_draw_sha256':hashlib.sha256(ix.numpy().tobytes()).hexdigest(),
                     'query_draw_sha256':hashlib.sha256(qi.numpy().tobytes()).hexdigest()}
                log.write(json.dumps(row)+'\n');log.flush();write(root,'TRAIN_PROGRESS.json',{'arm':arm,**row,'time':time.time()})
        state={k:v.detach().clone() for k,v in student.state_dict().items()}
        for k in state:
            if core.is_buffer(k):assert torch.equal(state[k],native[k]),k
        path=root/(arm+'_raw.pt');torch.save(state,path)
        torch.save({'optimizer':optimizer.state_dict(),'torch_rng':torch.get_rng_state(),
                    'public_sampler_rng':gf.get_state(),'query_sampler_rng':gq.get_state()},root/(arm+'_optimizer_rng.pt'))
        with torch.inference_mode():qz=torch.cat([student(norm(v)) for v in bank['queries'].split(32)]).double()
        assert core.tensor_digest(student.state_dict())==core.tensor_digest(state)
        torch.save({'query_logits':qz},root/('private_'+arm+'_bank_diagnostic.pt'))
        raw_models[arm]={'path':path.name,'sha256':core.sha(path),'steps':100}
    write(root,'RAW_MODELS_BEFORE_SELECTION.json',raw_models)
    proxy=forward(post,public,root,'proxy_nativepost');choices={};models={};allrows={}
    for arm in ARMS:
        student=torch.load(root/raw_models[arm]['path'],map_location='cpu',weights_only=True)
        model=cls().eval();rows=[];zs=[]
        def probe(alpha):
            deadline();state=mix(native,student,alpha);model.load_state_dict(state,strict=True)
            z=forward(model,public,root,'proxy_'+arm);r={'alpha':alpha,**proxy_metrics(proxy,z),'tensor_sha256':core.tensor_digest(state)}
            rows.append(r);zs.append(z);write(root,'SELECTION_PROGRESS.json',{'arm':arm,'tested':len(rows),'latest':r,'time':time.time()});return r
        for i in range(11):probe(i/10)
        best=max((r for r in rows if r['eligible']),key=lambda r:r['alpha'])
        if best['alpha']<1:
            lo=best['alpha'];hi=min(r['alpha'] for r in rows if r['alpha']>lo)
            for _ in range(6):
                r=probe((lo+hi)/2)
                if r['eligible']:lo=r['alpha']
                else:hi=r['alpha']
        choice=max((r for r in rows if r['eligible']),key=lambda r:r['alpha']);choices[arm]=choice;allrows[arm]=rows
        state=mix(native,student,choice['alpha']);path=root/(arm+'_selected.pt');torch.save(state,path)
        torch.save({'teacher_logits':proxy,'alphas':[r['alpha'] for r in rows],'candidate_logits':torch.stack(zs)},root/('private_'+arm+'_proxy.pt'))
        models[arm]={'path':path.name,'sha256':core.sha(path),'alpha':choice['alpha']}
    declaration={'raw_models':raw_models,'models':models,'choices':choices,'all_points':allrows,
                 'groundtruth_labels_used':False,'member_used':False,'actual_trigger_used':False,'ASR_used':False}
    write(root,'SELECTION_BEFORE_PRIVATE_EVALUATION.json',declaration);return declaration
