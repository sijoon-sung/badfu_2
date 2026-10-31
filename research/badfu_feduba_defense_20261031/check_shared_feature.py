"""New CPU synthetic gradient/head/feature contract, not a defense evaluation."""
import json,os,time,traceback
from pathlib import Path
import torch
import stage05_common as s
from sourcepair_pilot import cpu_guard
from shared_feature_method import transform,objective,feature_loss,features
core=s.core;OUT=s.HERE/'SHARED_FEATURE_CONTRACT.json'


def main():
    assert not OUT.exists();s.verify_sources();cpu=cpu_guard()
    freeze=core.read(s.HERE/'SHARED_FEATURE_PREPARATION_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    a=torch.tensor([[.2,.8],[.4,.6]],dtype=torch.float64)
    delta=torch.tensor([[.1,-.1]],dtype=torch.float64,requires_grad=True)
    q=transform(a,delta);shared=torch.autograd.grad(q.square().mean(),delta)[0]
    independent=delta.detach().expand_as(a).clone().requires_grad_(True)
    point=torch.autograd.grad(transform(a,independent).square().mean(),independent)[0]
    assert torch.allclose(shared,point.sum(0,keepdim=True),atol=1e-14,rtol=0)
    edge=torch.tensor([[-.5,1.5]],dtype=torch.float64,requires_grad=True)
    assert torch.equal(torch.autograd.grad(transform(torch.zeros_like(edge),edge).sum(),edge)[0],torch.zeros_like(edge))
    t=torch.tensor([[1.,2.,3.],[3.,2.,1.]],dtype=torch.float64,requires_grad=True)
    p=t.detach().flip(1).requires_grad_(True);sources=torch.tensor([1,0]);v=objective(t,p,sources,2)
    direct=sum((p[i]/2).log_softmax(0)[2]+(t[i]/2).log_softmax(0)[int(sources[i])] for i in range(2))/2
    assert torch.allclose(v,direct,atol=1e-14,rtol=0)
    for one,two in zip(torch.autograd.grad(v,(t,p),retain_graph=True),torch.autograd.grad(direct,(t,p))):assert torch.equal(one,two)
    hf=torch.tensor([[2.,4.]],requires_grad=True);target=torch.tensor([[1.,2.]]);sc=torch.tensor(2.)
    fv=feature_loss(hf,target,sc);fg=torch.autograd.grad(fv,hf)[0]
    assert torch.equal(fv,torch.tensor(1.25)) and torch.equal(fg,torch.tensor([[.5,1.]]))
    selected,sealed,states=s.snapshot();cls=sealed.model_class(Path(selected['source_root']))
    native=states['post'];model=cls().eval();model.load_state_dict(native,strict=True)
    for p in model.get_submodule('model.fc').parameters():p.requires_grad_(False)
    x=torch.rand((2,3,32,32),generator=torch.Generator().manual_seed(20261101+1702)).requires_grad_(True)
    z,h=features(model,x);assert z.shape==(2,10) and h.shape==(2,512) and h.requires_grad
    opt=torch.optim.Adam([p for p in model.parameters() if p.requires_grad],lr=.0001)
    value=feature_loss(h,torch.zeros_like(h),torch.tensor(1.))+z.square().mean();value.backward()
    assert torch.isfinite(x.grad).all() and bool((x.grad!=0).any())
    assert all(p.grad is None for p in model.get_submodule('model.fc').parameters())
    opt.step();after=model.state_dict();assert all(torch.isfinite(v).all() for v in after.values())
    assert any(not torch.equal(after[k],v) for k,v in native.items())
    for k,v in native.items():
        if core.is_buffer(k) or k.startswith('model.fc.'):assert torch.equal(after[k],v),k
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    result={'state':'passed','pid':os.getpid(),'finished_unix':time.time(),'CPU':cpu,
        'shared_gradient_equals_sum_of_pointwise':True,'true_clipping_gradient':True,'explicit_row_objective_and_gradient_exact':True,
        'feature_loss_value_and_gradient_exact':True,'actual_CPU_featurehook_gradient':True,'head_and_BN_exact_fixed':True,
        'one_disposable_synthetic_backbone_update':True,'real_data_or_trigger_used':False,'CUDA_initialized':False,
        'method_sha256':core.sha(s.HERE/'shared_feature_method.py'),'checker_sha256':core.sha(__file__),
        'preparation_freeze_sha256':core.sha(s.HERE/'SHARED_FEATURE_PREPARATION_FREEZE.json')}
    with OUT.open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
