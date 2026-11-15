"""Compare actual full-batch updates against an independent BatchSampler loop on CPU."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import torch
from torch import nn
import reference_core as core

ROOT=Path(__file__).resolve().parent


def exact(a,b):
    if isinstance(a,torch.Tensor):assert isinstance(b,torch.Tensor) and torch.equal(a,b)
    elif isinstance(a,dict):
        assert a.keys()==b.keys()
        for k in a:exact(a[k],b[k])
    elif isinstance(a,(list,tuple)):
        assert type(a)==type(b) and len(a)==len(b)
        for x,y in zip(a,b):exact(x,y)
    else:assert a==b


def main():
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    freeze=json.loads((ROOT/'CPU_FREEZE.json').read_text(encoding='utf-8'))
    for name,digest in freeze['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    source=ROOT/'upstream/train_main.py'
    assert hashlib.sha256(source.read_bytes()).hexdigest()=='cb2ca6279bf4bc352631418375a541e45dbbf66a9985d4b475820a55772225e9'
    calls=[n for n in ast.walk(ast.parse(source.read_text(encoding='utf-8'))) if isinstance(n,ast.Call)
           and isinstance(n.func,ast.Attribute) and n.func.attr=='DataLoader'
           and any(k.arg=='drop_last' and isinstance(k.value,ast.Constant) and k.value.value is True for k in n.keywords)]
    assert len(calls)==1
    torch.manual_seed(107);base=nn.Sequential(nn.Flatten(),nn.Linear(784,10))
    x=torch.rand(17,1,28,28);y=torch.arange(17)%10;settings=core.Settings(epochs=2,batch=8)
    rows=[]
    modes=[('Adam',None),('weighted_SGD',None),('recovery_SGD',None),
           ('Adam',0),('weighted_SGD',0),('Adam',4),('weighted_SGD',4)]
    for mode,role in modes:
        model=copy.deepcopy(base);kwargs={};weights=None;ref=None
        if mode=='weighted_SGD':
            weights={k:torch.full_like(v,.7) for k,v in model.named_parameters()};kwargs['gradient_weights']=weights
        if mode=='recovery_SGD':
            reference=copy.deepcopy(base)
            with torch.no_grad():
                for p in reference.parameters():p.add_(.01)
            kwargs['reference']=reference;ref=torch.nn.utils.parameters_to_vector(reference.parameters()).detach()
        opt=(torch.optim.Adam(model.parameters(),lr=.001,foreach=True) if mode=='Adam'
             else torch.optim.SGD(model.parameters(),lr=.001,foreach=True))
        rng=torch.Generator().manual_seed(512);mrng=torch.Generator().manual_seed(70000512)
        masks=[];steps=0
        for epoch in range(2):
            order=torch.randperm(17,generator=rng).tolist()
            for ids in torch.utils.data.BatchSampler(order,batch_size=8,drop_last=True):
                assert len(ids)==8;bx=x[ids].clone();by=y[ids].clone()
                if role is not None:
                    mask=torch.rand(8,generator=mrng)<.3
                    # Direct stamp loop independent from compose_batch.
                    for y0,y1,x0,x1 in core.PATCHES if role==4 else [core.PATCHES[role]]:
                        bx[mask,:,y0:y1,x0:x1]=1
                    by[mask]=8;masks.append(bytes(mask.to(torch.uint8).tolist()).hex())
                opt.zero_grad(set_to_none=True);loss=nn.functional.cross_entropy(model(bx),by)
                if ref is not None:loss=loss+2*(torch.nn.utils.parameters_to_vector(model.parameters())-ref).square().sum()
                loss.backward()
                if weights:
                    with torch.no_grad():
                        for k,p in model.named_parameters():p.grad.mul_(weights[k])
                opt.step();steps+=1
        logs=[]
        candidate=core.learn(copy.deepcopy(base),x,y,settings,phase_seed=512,phase='synthetic',
                             redraw_role=role,log=lambda **v:logs.append(v),**kwargs)
        exact(model.state_dict(),candidate[0].state_dict());exact(opt.state_dict(),candidate[1].state_dict())
        assert steps==candidate[3]==4
        assert all(e['examples']==16 and e['dropped_examples']==1 for e in logs)
        if role is None:exact(candidate[2],rng.get_state())
        else:
            exact(candidate[2]['shuffle'],rng.get_state());exact(candidate[2]['mask'],mrng.get_state())
            assert candidate[2]['mask_hex']==masks and all(len(bytes.fromhex(m))==8 for m in masks)
        rows.append({'mode':mode,'role':role,'steps':4,'model_optimizer_RNG_exact':True})
    result={'state':'passed','rows':rows,'source_drop_last_true_line':calls[0].lineno,
            'independent_oracle':'torch.utils.data.BatchSampler(drop_last=True)',
            'real_data_training':0,'real_model_inference':0,'CUDA_initialized':torch.cuda.is_initialized()}
    with (ROOT/'CPU_CONTRACT.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
