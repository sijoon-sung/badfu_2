"""Parked one-factor candidate library. No runner or automatic launch."""
import hashlib,json,time
from pathlib import Path
import torch
import stage05_common as s
from stage08 import norm,loss
from stage09 import mix,proxy_metrics
from stage10 import write,forward
core=s.core


def check_parent(bank_path,expected_sha):
    root=s.HERE/'stage11'
    parent=core.read(root/'RESULT.json');completed=core.read(root/'COMPLETED.json')
    assert parent['state']=='completed' and completed['result_sha256']==core.sha(root/'RESULT.json')
    audit=core.read(root/'INDEPENDENT_VERIFICATION.json')
    assert audit['state']=='passed' and audit['scope']=='finished_pipeline' and audit['pipeline_completed']
    assert not any(parent['method_necessary_gates'].values()),'H11 succeeded: prioritize independent evaluation'
    path=Path(bank_path).resolve();assert path.parent.parent==root.resolve()
    assert path.name=='private_all_class_disjoint_querybank.pt'
    receipt=core.read(path.parent/'COMPLETED.json')
    assert expected_sha==receipt['files'][path.name]==core.sha(path)
    return path


def train_and_select(native,teacher_state,public,cls,root,deadline,bank_path,bank_sha):
    path=check_parent(bank_path,bank_sha)
    bank=torch.load(path,map_location='cpu',weights_only=True)
    requested=bank['requested_classes']
    assert torch.equal(requested,torch.tensor([batch%10 for batch in range(30) for _ in range(8)]))
    assert bank['queries'].shape==(240,3,32,32) and bank['teacher_prob_T2'].shape==(240,10)
    assert torch.isfinite(bank['queries']).all() and torch.isfinite(bank['teacher_prob_T2']).all()
    write(root,'INHERITED_QUERYBANK.json',{'path':str(path),'sha256':bank_sha,'new_queries_generated':0,
        'actual_target_or_labels_used':False,'comparison':'same_H11_bank_new_frozen_head_student'})
    teacher=cls().eval();post=cls().eval()
    teacher.load_state_dict(teacher_state,strict=True);post.load_state_dict(native,strict=True)
    for model in [teacher,post]:
        for p in model.parameters():p.requires_grad_(False)
    x=public.permute(0,3,1,2).float().div(255).contiguous()
    with torch.no_grad():
        tc=torch.cat([(teacher(norm(v))/2).softmax(1) for v in x.split(32)])
        pc=torch.cat([(post(norm(v))/2).softmax(1) for v in x.split(32)])
    torch.manual_seed(20261031);student=cls().eval();student.load_state_dict(native,strict=True)
    head=student.get_submodule('model.fc')
    assert isinstance(head,torch.nn.Linear) and (head.in_features,head.out_features)==(512,10)
    for p in head.parameters():p.requires_grad_(False)
    parameters=[p for p in student.parameters() if p.requires_grad]
    optimizer=torch.optim.Adam(parameters,lr=.0001,weight_decay=0)
    gf=torch.Generator().manual_seed(20261031+901);gq=torch.Generator().manual_seed(20261031+902)
    buckets=[torch.where(requested==k)[0] for k in range(10)];arm='backbone_only'
    with (root/(arm+'_steps.jsonl')).open('x',encoding='utf8') as log:
        for step in range(100):
            deadline();tick=time.monotonic();ix=torch.randint(len(x),(32,),generator=gf)
            draws=torch.randint(24,(10,),generator=gq);qi=torch.stack([buckets[k][draws[k]] for k in range(10)])
            optimizer.zero_grad(set_to_none=True);z=student(norm(x[ix]))
            clean=loss(tc[ix],z)+loss(pc[ix],z)
            query=loss(bank['teacher_prob_T2'][qi],student(norm(bank['queries'][qi])))
            value=clean+query;assert torch.isfinite(value);value.backward()
            assert all(p.grad is None for p in head.parameters())
            assert all(p.grad is None or torch.isfinite(p.grad).all() for p in parameters)
            optimizer.step();assert all(torch.isfinite(v).all() for v in student.state_dict().values())
            state=student.state_dict()
            for k in ['model.fc.weight','model.fc.bias']:assert torch.equal(state[k],native[k])
            row={'step':step+1,'clean_loss':float(clean.detach()),'query_loss':float(query.detach()),'query_n':10,'seconds':time.monotonic()-tick,
                 'head_grad_none':True,'public_draw_sha256':hashlib.sha256(ix.numpy().tobytes()).hexdigest(),
                 'query_draw_sha256':hashlib.sha256(qi.numpy().tobytes()).hexdigest()}
            log.write(json.dumps(row)+'\n');log.flush();write(root,'TRAIN_PROGRESS.json',{'arm':arm,**row})
    state={k:v.detach().clone() for k,v in student.state_dict().items()}
    for k in state:
        if core.is_buffer(k) or k.startswith('model.fc.'):assert torch.equal(state[k],native[k]),k
    raw_path=root/(arm+'_raw.pt');torch.save(state,raw_path)
    torch.save({'optimizer':optimizer.state_dict(),'torch_rng':torch.get_rng_state(),
        'public_sampler_rng':gf.get_state(),'query_sampler_rng':gq.get_state(),
        'optimized_parameter_count':len(parameters)},root/(arm+'_optimizer_rng.pt'))
    with torch.inference_mode():qz=torch.cat([student(norm(v)) for v in bank['queries'].split(32)]).double()
    torch.save({'query_logits':qz},root/('private_'+arm+'_bank_diagnostic.pt'))
    raw={arm:{'path':raw_path.name,'sha256':core.sha(raw_path),'steps':100}}
    write(root,'RAW_MODELS_BEFORE_SELECTION.json',raw)
    proxy=forward(post,public,root,'proxy_nativepost');model=cls().eval();rows=[];zs=[]
    def probe(alpha):
        deadline();st=mix(native,state,alpha);model.load_state_dict(st,strict=True)
        for k in ['model.fc.weight','model.fc.bias']:assert torch.equal(st[k],native[k])
        z=forward(model,public,root,'proxy_'+arm)
        row={'alpha':alpha,**proxy_metrics(proxy,z),'tensor_sha256':core.tensor_digest(st)}
        rows.append(row);zs.append(z);return row
    for i in range(11):probe(i/10)
    best=max((r for r in rows if r['eligible']),key=lambda r:r['alpha'])
    if best['alpha']<1:
        lo=best['alpha'];hi=min(r['alpha'] for r in rows if r['alpha']>lo)
        for _ in range(6):
            v=probe((lo+hi)/2)
            if v['eligible']:lo=v['alpha']
            else:hi=v['alpha']
    choice=max((r for r in rows if r['eligible']),key=lambda r:r['alpha'])
    chosen=mix(native,state,choice['alpha']);p=root/(arm+'_selected.pt');torch.save(chosen,p)
    torch.save({'teacher_logits':proxy,'alphas':[r['alpha'] for r in rows],
        'candidate_logits':torch.stack(zs)},root/('private_'+arm+'_proxy.pt'))
    declaration={'raw_models':raw,'models':{arm:{'path':p.name,'sha256':core.sha(p),'alpha':choice['alpha']}},
        'choices':{arm:choice},'all_points':{arm:rows},'groundtruth_labels_used':False,'member_used':False,
        'actual_trigger_used':False,'ASR_used':False,'frozen_head':'model.fc','inherited_bank_sha256':bank_sha}
    write(root,'SELECTION_BEFORE_PRIVATE_EVALUATION.json',declaration);return declaration
