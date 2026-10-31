"""Matched sharing x Post-feature consistency; method receives no evaluator truth."""
import gc,hashlib,json,time
import torch
import stage05_common as s
from endpoint_interface import BADFU,forward_raw
from stage08 import norm,loss
from stage09 import mix,proxy_metrics
from stage10 import write,forward
core=s.core
ARMS=['pointwise_logits','shared_logits','pointwise_features','shared_features']


def objective(tz,pz,sources,k):
    return ((pz/2).log_softmax(1)[:,k]+(tz/2).log_softmax(1).gather(1,sources[:,None]).squeeze(1)).mean()


def transform(anchors,delta):
    return (anchors+delta).clamp(0,1)


def features(model,x):
    z,h=forward_raw(model,x,BADFU,with_features=True)
    return z,h.to('cpu')


def feature_loss(h,target,scale):
    return (h-target).square().mean()/scale


def frozen(state,cls):
    m=cls().eval();m.load_state_dict(state,strict=True)
    for p in m.parameters():p.requires_grad_(False)
    return m


def generate(native,teacherstate,public,cls,root,deadline):
    post=frozen(native,cls);teacher=frozen(teacherstate,cls)
    x=public.permute(0,3,1,2).float().div(255).contiguous()
    with torch.no_grad():
        tp=torch.cat([teacher(norm(v)) for v in x.split(32)]).argmax(1)
        pp=torch.cat([post(norm(v)) for v in x.split(32)]).argmax(1)
    pools=[torch.where((tp==c)&(pp==c))[0] for c in range(10)]
    assert all(len(v)>0 for v in pools),'insufficient public agreement source classes; no efficacy claim'
    g=torch.Generator().manual_seed(20261101+1700);ids=[];sources=[]
    for k in range(10):
        labels=torch.tensor([c for c in range(10) if c!=k])
        ids.append(torch.stack([pools[int(c)][torch.randint(len(pools[int(c)]),(1,),generator=g)[0]] for c in labels]))
        sources.append(labels)
    indices=torch.cat(ids);starts=x[indices].clone();src=torch.cat(sources);requested=torch.arange(10).repeat_interleave(9)
    torch.save({'starts':starts,'sources':src,'requested':requested,'public_indices':indices,
                'source_pools':pools,'source_sampler_rng':g.get_state(),'teacher_predictions':tp,'post_predictions':pp},root/'private_initials.pt')
    write(root,'INITIALS.json',{'n':90,'source_pool_counts':[len(v) for v in pools],
        'sha256':core.sha(root/'private_initials.pt'),'groundtruth_labels_used':False,'seed':20261101+1700})
    summary={};banks={}
    initial_digests=[core.tensor_digest(m.state_dict()) for m in [post,teacher]]
    for kind in ['pointwise','shared']:
        qs=[];tzs=[];pzs=[];trace=[]
        for k in range(10):
            a=starts[k*9:(k+1)*9];labels=src[k*9:(k+1)*9]
            delta=torch.zeros((9 if kind=='pointwise' else 1,3,32,32));snapshots=[];rows=[]
            for step in range(20):
                deadline();delta=delta.detach().requires_grad_(True);q=transform(a,delta)
                tz=teacher(norm(q));pz=post(norm(q));value=objective(tz,pz,labels,k)
                assert torch.isfinite(value);grad=torch.autograd.grad(value,delta)[0];assert torch.isfinite(grad).all()
                rows.append({'step':step+1,'objective':float(value.detach()),'gradient_sha256':core.tensor_digest({'gradient':grad.detach()})})
                delta=(delta+.1*grad.sign()).detach().clamp(-1,1)
                snapshots.append({'delta':delta.clone(),'queries':transform(a,delta).detach().clone()})
            q=transform(a,delta).detach()
            with torch.no_grad():tz=teacher(norm(q));pz=post(norm(q))
            torch.save({'steps':snapshots,'source':labels,'requested':k},root/('private_'+kind+'_k'+str(k)+'_generation.pt'))
            qs.append(q);tzs.append(tz);pzs.append(pz);trace.append({'k':k,'steps':rows})
            write(root,'GENERATION_PROGRESS.json',{'kind':kind,'requested_completed':k+1,'time':time.time()})
        raw=torch.cat(qs);tz=torch.cat(tzs);pz=torch.cat(pzs);valid=tz.argmax(1)==src
        effective=raw.clone();effective[~valid]=starts[~valid]
        with torch.no_grad():
            et=torch.cat([teacher(norm(v)) for v in effective.split(32)])
            ep=torch.cat([post(norm(v)) for v in effective.split(32)])
        assert torch.equal(et.argmax(1),src)
        bank={'queries':effective,'raw_queries':raw,'raw_source_valid':valid,'teacher_logits':et,'post_logits':ep,
              'raw_teacher_logits':tz,'raw_post_logits':pz,'sources':src,'requested':requested,'starts':starts}
        p=root/('private_'+kind+'_bank.pt');torch.save(bank,p);banks[kind]=bank
        summary[kind]={'n':90,'raw_source_valid_n':int(valid.sum()),'identity_replacement_n':int((~valid).sum()),
            'raw_post_requested_n':int((pz.argmax(1)==requested).sum()),
            'raw_joint_n':int((valid&(pz.argmax(1)==requested)).sum()),
            'raw_source_valid_counts':[int((valid&(src==c)).sum()) for c in range(10)],
            'effective_source_n':90,'sha256':core.sha(p),'image_gradient_evaluations':1800,'trace':trace}
        write(root,'BANK_BEFORE_TRAINING.json',summary)
    assert [core.tensor_digest(m.state_dict()) for m in [post,teacher]]==initial_digests
    del post,teacher;gc.collect()
    return banks


def train_and_select(native,public,cls,root,deadline,banks):
    x=public.permute(0,3,1,2).float().div(255).contiguous();post=frozen(native,cls)
    with torch.no_grad():
        clean_outputs=[features(post,v) for v in x.split(32)]
        pz=torch.cat([v[0] for v in clean_outputs]);pc=(pz/2).softmax(1);ph=torch.cat([v[1] for v in clean_outputs])
        initial=banks['pointwise']['starts'];assert torch.equal(initial,banks['shared']['starts'])
        original=[features(post,v) for v in initial.split(32)]
        az=torch.cat([v[0] for v in original]);anchor=(az/2).softmax(1);ah=torch.cat([v[1] for v in original])
    assert torch.equal(anchor.argmax(1),banks['pointwise']['sources'])
    scale=ph.square().mean().clamp_min(1e-8).detach();assert torch.isfinite(scale)
    torch.save({'public_logits':pz,'public_prob_T2':pc,'public_features':ph,'anchor_logits':az,
                'anchor_prob_T2':anchor,'anchor_features':ah,'feature_scale':scale},root/'private_targets.pt')
    raw_models={}
    for arm in ARMS:
        bank=banks[arm.split('_')[0]];src=bank['sources'];buckets=[torch.where(src==c)[0] for c in range(10)]
        torch.manual_seed(20261101+1701);student=cls().eval();student.load_state_dict(native,strict=True)
        head=student.get_submodule(BADFU.head_path)
        for p in head.parameters():p.requires_grad_(False)
        trainable=[p for p in student.parameters() if p.requires_grad];optimizer=torch.optim.Adam(trainable,lr=.0001,weight_decay=0)
        gf=torch.Generator().manual_seed(20261101+901);gq=torch.Generator().manual_seed(20261101+902)
        with (root/(arm+'_steps.jsonl')).open('x',encoding='utf8') as log:
            for step in range(100):
                deadline();tick=time.monotonic();ix=torch.randint(len(x),(32,),generator=gf)
                qi=torch.stack([bucket[torch.randint(len(bucket),(1,),generator=gq)[0]] for bucket in buckets])
                optimizer.zero_grad(set_to_none=True)
                cz,ch=features(student,x[ix]);qz,qh=features(student,bank['queries'][qi])
                clean=loss(pc[ix],cz);query=loss(anchor[qi],qz)
                cf=feature_loss(ch,ph[ix],scale);qf=feature_loss(qh,ah[qi],scale)
                value=clean+query+(cf+qf if arm.endswith('_features') else 0)
                assert torch.isfinite(value);value.backward()
                assert all(p.grad is None for p in head.parameters())
                assert all(p.grad is None or torch.isfinite(p.grad).all() for p in trainable)
                optimizer.step();state=student.state_dict();assert all(torch.isfinite(v).all() for v in state.values())
                row={'step':step+1,'clean_loss':float(clean.detach()),'query_loss':float(query.detach()),
                    'clean_feature_loss':float(cf.detach()),'query_feature_loss':float(qf.detach()),
                    'feature_loss_in_objective':arm.endswith('_features'),'seconds':time.monotonic()-tick,
                    'public_draw_sha256':hashlib.sha256(ix.numpy().tobytes()).hexdigest(),
                    'query_draw_sha256':hashlib.sha256(qi.numpy().tobytes()).hexdigest()}
                log.write(json.dumps(row)+'\n');log.flush();write(root,'TRAIN_PROGRESS.json',{'arm':arm,**row,'time':time.time()})
                if arm=='shared_features' and step==9:torch.save(state,root/'shared_features_step010.pt')
        for k in state:
            if core.is_buffer(k) or k.startswith(BADFU.head_path+'.'):assert torch.equal(state[k],native[k]),k
        p=root/(arm+'_raw.pt');torch.save(state,p)
        torch.save({'optimizer':optimizer.state_dict(),'torch_rng':torch.get_rng_state(),
                    'public_sampler_rng':gf.get_state(),'query_sampler_rng':gq.get_state()},root/(arm+'_optimizer_rng.pt'))
        with torch.no_grad():qz=torch.cat([student(norm(v)) for v in bank['queries'].split(32)]).double()
        torch.save({'query_logits':qz,'sources':src},root/('private_'+arm+'_bank_diagnostic.pt'))
        raw_models[arm]={'path':p.name,'sha256':core.sha(p),'steps':100,'identity_fallback':False}
        del optimizer,student,trainable,state;gc.collect()
    write(root,'RAW_MODELS_BEFORE_SELECTION.json',raw_models)
    proxy=forward(post,public,root,'proxy_nativepost');choices={};models={};allrows={}
    for arm in ARMS:
        raw=raw_models[arm];student=torch.load(root/raw['path'],map_location='cpu',weights_only=True)
        model=cls().eval();rows=[];zs=[]
        def probe(alpha):
            deadline();st=mix(native,student,alpha);model.load_state_dict(st,strict=True)
            z=forward(model,public,root,'proxy_'+arm);row={'alpha':alpha,**proxy_metrics(proxy,z),'tensor_sha256':core.tensor_digest(st)}
            rows.append(row);zs.append(z);write(root,'SELECTION_PROGRESS.json',{'arm':arm,'tested':len(rows),'latest':row,'time':time.time()});return row
        for i in range(11):probe(i/10)
        best=max((v for v in rows if v['eligible']),key=lambda v:v['alpha'])
        if best['alpha']<1:
            lo=best['alpha'];hi=min(v['alpha'] for v in rows if v['alpha']>lo)
            for _ in range(6):
                row=probe((lo+hi)/2)
                if row['eligible']:lo=row['alpha']
                else:hi=row['alpha']
        choice=max((v for v in rows if v['eligible']),key=lambda v:v['alpha']);choices[arm]=choice;allrows[arm]=rows
        st=mix(native,student,choice['alpha']);p=root/raw['path'] if choice['alpha']==1 else root/(arm+'_selected.pt')
        if choice['alpha']!=1:torch.save(st,p)
        torch.save({'teacher_logits':proxy,'alphas':[v['alpha'] for v in rows],'candidate_logits':torch.stack(zs)},root/('private_'+arm+'_proxy.pt'))
        models[arm]={'path':p.name,'sha256':core.sha(p),'alpha':choice['alpha'],'identity':core.tensor_digest(st)==core.tensor_digest(native)}
        del model,student;gc.collect()
    declaration={'raw_models':raw_models,'models':models,'choices':choices,'all_points':allrows,
        'feature_scale':float(scale),'groundtruth_labels_used':False,'member_used':False,'actual_trigger_used':False,'ASR_used':False,
        'common_head_fixed':True,'BN_buffers_fixed':True,'clean_target':'native_Post_public','query_target':'native_Post_original_anchor',
        'feature_target':'native_Post_original_feature_only_feature_arms'}
    write(root,'SELECTION_BEFORE_PRIVATE_EVALUATION.json',declaration);return declaration
