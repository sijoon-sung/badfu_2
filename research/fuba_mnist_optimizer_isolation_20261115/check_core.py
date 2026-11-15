"""CPU optimizer equivalence and the limited constant-weight Adam cancellation example."""
import copy
import hashlib
import json
from pathlib import Path
import torch
from torch import nn
import original_core as old
from diagnostic_core import learn

ROOT=Path(__file__).resolve().parent


def exact(a,b):
    if isinstance(a,torch.Tensor):assert isinstance(b,torch.Tensor) and torch.equal(a,b)
    elif isinstance(a,dict):
        assert a.keys()==b.keys()
        for k in a:exact(a[k],b[k])
    elif isinstance(a,(list,tuple)):
        assert len(a)==len(b)
        for x,y in zip(a,b):exact(x,y)
    else:assert a==b


def main():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    for name,digest in json.loads((ROOT/'CPU_FREEZE.json').read_text())['files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    torch.manual_seed(53);base=nn.Linear(4,3);x=torch.rand(17,4);y=torch.arange(17)%3
    w={k:torch.full_like(v,.7) for k,v in base.named_parameters()};settings=old.Settings(epochs=2,batch=8)
    a=old.learn(copy.deepcopy(base),x,y,settings,phase_seed=7,phase='test',gradient_weights=w)
    b=learn(copy.deepcopy(base),x,y,settings,phase_seed=7,phase='test',gradient_weights=w,optimizer_policy='algorithm_sgd')
    exact(a[0].state_dict(),b[0].state_dict());exact(a[1].state_dict(),b[1].state_dict());exact(a[2:],b[2:])
    model=copy.deepcopy(base);opt=torch.optim.Adam(model.parameters(),lr=.001,foreach=True);rng=torch.Generator().manual_seed(7)
    for epoch in range(2):
        for ids in torch.randperm(17,generator=rng).split(8):
            opt.zero_grad(set_to_none=True);nn.functional.cross_entropy(model(x[ids]),y[ids]).backward()
            with torch.no_grad():
                for k,p in model.named_parameters():p.grad.mul_(w[k])
            opt.step()
    b=learn(copy.deepcopy(base),x,y,settings,phase_seed=7,phase='test',gradient_weights=w,optimizer_policy='experimental_adam')
    exact(model.state_dict(),b[0].state_dict());exact(opt.state_dict(),b[1].state_dict());exact(rng.get_state(),b[2]);assert b[3]==6
    ratios=torch.tensor([0.,.1,.5,1.],dtype=torch.float64)
    adam=nn.Parameter(torch.zeros(4,dtype=torch.float64));sgd=nn.Parameter(torch.zeros(4,dtype=torch.float64))
    oa=torch.optim.Adam([adam],lr=.001);os=torch.optim.SGD([sgd],lr=.001)
    for i in range(50):
        gradient=ratios*(1+(i%3)*.1);adam.grad=gradient.clone();sgd.grad=gradient.clone();oa.step();os.step()
    assert adam[0]==sgd[0]==0 and abs(float(adam[1]/adam[3])-1)<1e-6
    assert torch.allclose(sgd[1:]/sgd[3],ratios[1:],rtol=1e-12,atol=1e-12)
    result={'state':'passed','SGD_model_optimizer_loader_matches_original':True,
        'Adam_model_optimizer_loader_matches_independent_loop':True,'synthetic_steps_per_training':6,
        'constant_gradient_demo':{'weights':ratios.tolist(),'Adam_deltas':adam.detach().tolist(),
          'SGD_deltas':sgd.detach().tolist(),'scope':'Positive constant per-coordinate scaling; epsilon prevents exact cancellation. Zero weight stays zero. Not a learned-model performance claim.'},
        'real_training':0,'CUDA_initialized':torch.cuda.is_initialized()}
    with (ROOT/'CPU_CONTRACT.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
