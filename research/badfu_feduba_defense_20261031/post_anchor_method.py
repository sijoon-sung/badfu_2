"""Same-bank query-target comparison; primary target is Post(original anchor)."""
import hashlib,json,time
from pathlib import Path
import torch
import stage05_common as s
from stage08 import norm,loss
from stage09 import mix,proxy_metrics
from stage10 import write,forward
core=s.core;ARMS=['teacher_query','post_anchor']


def train_and_select(native,public,cls,root,deadline,bank_path,initial_path,bank_sha,initial_sha):
    assert core.sha(bank_path)==bank_sha and core.sha(initial_path)==initial_sha
    bank=torch.load(bank_path,map_location='cpu',weights_only=True)
    initial=torch.load(initial_path,map_location='cpu',weights_only=True)
    src=bank['sources'];assert torch.equal(src,initial['sources']) and torch.equal(bank['requested'],initial['requested'])
    valid=bank['teacher_logits'].argmax(1)==src
    buckets=[torch.where(valid&(src==c))[0] for c in range(10)]
    teacher_counts=torch.bincount(bank['teacher_logits'].argmax(1),minlength=10)
    usable=all(len(v)>0 for v in buckets) and int(valid.sum())>=72 and int(teacher_counts.max())<=18
    write(root,'BANK_BEFORE_TRAINING.json',{'bank_path':str(bank_path),'initial_path':str(initial_path),
        'bank_sha256':bank_sha,'initial_sha256':initial_sha,'source_valid_n':int(valid.sum()),
        'source_valid_counts':[len(v) for v in buckets],'groundtruth_labels_used':False})
    x=public.permute(0,3,1,2).float().div(255).contiguous()
    post=cls().eval();post.load_state_dict(native,strict=True)
    for p in post.parameters():p.requires_grad_(False)
    with torch.no_grad():
        pc=torch.cat([(post(norm(v))/2).softmax(1) for v in x.split(32)])
        anchor=torch.cat([(post(norm(v))/2).softmax(1) for v in initial['starts'].split(32)])
    assert torch.equal(anchor.argmax(1),src),'original anchor no longer agrees with its declared source'
    raw_models={}
    for arm in ARMS:
        torch.manual_seed(20261031);student=cls().eval();student.load_state_dict(native,strict=True)
        optimizer=torch.optim.Adam(student.parameters(),lr=.0001,weight_decay=0)
        gf=torch.Generator().manual_seed(20261031+901);gq=torch.Generator().manual_seed(20261031+902)
        target=bank['teacher_prob_T2'] if arm=='teacher_query' else anchor
        nsteps=100 if usable else 0
        with (root/(arm+'_steps.jsonl')).open('x',encoding='utf8') as log:
            for step in range(nsteps):
                deadline();tick=time.monotonic();ix=torch.randint(len(x),(32,),generator=gf)
                qi=torch.stack([bucket[torch.randint(len(bucket),(1,),generator=gq)[0]] for bucket in buckets])
                optimizer.zero_grad(set_to_none=True);clean=loss(pc[ix],student(norm(x[ix])))
                query=loss(target[qi],student(norm(bank['queries'][qi])));value=clean+query
                assert torch.isfinite(value);value.backward()
                assert all(p.grad is None or torch.isfinite(p.grad).all() for p in student.parameters())
                optimizer.step();assert all(torch.isfinite(v).all() for v in student.state_dict().values())
                row={'step':step+1,'clean_loss':float(clean.detach()),'query_loss':float(query.detach()),'query_n':10,
                    'seconds':time.monotonic()-tick,'public_draw_sha256':hashlib.sha256(ix.numpy().tobytes()).hexdigest(),
                    'query_draw_sha256':hashlib.sha256(qi.numpy().tobytes()).hexdigest()}
                log.write(json.dumps(row)+'\n');log.flush();write(root,'TRAIN_PROGRESS.json',{'arm':arm,**row,'time':time.time()})
        state={k:v.detach().clone() for k,v in student.state_dict().items()}
        for k in state:
            if core.is_buffer(k):assert torch.equal(state[k],native[k]),k
        p=root/(arm+'_raw.pt');torch.save(state,p)
        torch.save({'optimizer':optimizer.state_dict(),'torch_rng':torch.get_rng_state(),
                    'public_sampler_rng':gf.get_state(),'query_sampler_rng':gq.get_state()},root/(arm+'_optimizer_rng.pt'))
        with torch.inference_mode():qz=torch.cat([student(norm(v)) for v in bank['queries'].split(32)]).double()
        torch.save({'query_logits':qz,'source_valid_mask':valid,'native_anchor_prob_T2':anchor},root/('private_'+arm+'_bank_diagnostic.pt'))
        raw_models[arm]={'path':p.name,'sha256':core.sha(p),'steps':nsteps,'identity_fallback':not usable}
    write(root,'RAW_MODELS_BEFORE_SELECTION.json',raw_models)
    proxy=forward(post,public,root,'proxy_nativepost');choices={};models={};allrows={}
    for arm in ARMS:
        raw=raw_models[arm];student=torch.load(root/raw['path'],map_location='cpu',weights_only=True)
        model=cls().eval();rows=[];zs=[]
        def probe(alpha):
            deadline();st=mix(native,student,alpha);model.load_state_dict(st,strict=True)
            z=forward(model,public,root,'proxy_'+arm);r={'alpha':alpha,**proxy_metrics(proxy,z),'tensor_sha256':core.tensor_digest(st)}
            rows.append(r);zs.append(z);write(root,'SELECTION_PROGRESS.json',{'arm':arm,'tested':len(rows),'latest':r,'time':time.time()});return r
        if not usable:
            probe(0.);choice=rows[0]
        else:
            for i in range(11):probe(i/10)
            best=max((r for r in rows if r['eligible']),key=lambda r:r['alpha'])
            if best['alpha']<1:
                lo=best['alpha'];hi=min(r['alpha'] for r in rows if r['alpha']>lo)
                for _ in range(6):
                    r=probe((lo+hi)/2)
                    if r['eligible']:lo=r['alpha']
                    else:hi=r['alpha']
            choice=max((r for r in rows if r['eligible']),key=lambda r:r['alpha'])
        choices[arm]=choice;allrows[arm]=rows
        st=mix(native,student,choice['alpha'])
        if choice['alpha']==1.:p=root/raw['path']
        else:p=root/(arm+'_selected.pt');torch.save(st,p)
        torch.save({'teacher_logits':proxy,'alphas':[r['alpha'] for r in rows],
                    'candidate_logits':torch.stack(zs)},root/('private_'+arm+'_proxy.pt'))
        models[arm]={'path':p.name,'sha256':core.sha(p),'alpha':choice['alpha'],
            'identity':core.tensor_digest(st)==core.tensor_digest(native)}
    declaration={'raw_models':raw_models,'models':models,'choices':choices,'all_points':allrows,
        'groundtruth_labels_used':False,'member_used':False,'actual_trigger_used':False,'ASR_used':False,
        'common_clean_target':'native_Post_public','query_targets':{'teacher_query':'saved_H5_query','post_anchor':'native_Post_original_anchor'}}
    write(root,'SELECTION_BEFORE_PRIVATE_EVALUATION.json',declaration);return declaration
