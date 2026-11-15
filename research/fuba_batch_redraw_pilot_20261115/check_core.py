"""Synthetic CPU training-equivalence check; no real model/data inference."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import torch
from torch import nn
import reference_core as core

ROOT=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


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
    freeze=json.loads((ROOT/'CPU_FREEZE.json').read_text())
    for name,digest in freeze['files'].items():assert sha(ROOT/name)==digest
    baseline=Path('D:/FUBA_GAMMA_DETERMINISTIC_20261115/reference_core.py')
    assert sha(baseline)=='158d7b80b114c7c2a0a11d425066959930a03382bcbb680bc9f3d65e3a37b812'
    spec=importlib.util.spec_from_file_location('fixed_reference',baseline)
    old=importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name]=old;spec.loader.exec_module(old)
    torch.manual_seed(902)
    model=nn.Sequential(nn.Flatten(),nn.Linear(784,10))
    x=torch.rand(17,1,28,28);y=torch.arange(17)%10
    config=core.Settings(epochs=2,batch=8)
    clean_checks=[]
    for method in ['Adam','weighted_SGD','recovery_SGD']:
        kwargs={'phase_seed':512,'phase':'synthetic'}
        if method=='weighted_SGD':kwargs['gradient_weights']={k:torch.full_like(v,.7) for k,v in model.named_parameters()}
        if method=='recovery_SGD':kwargs['reference']=copy.deepcopy(model)
        a=old.learn(copy.deepcopy(model),x,y,config,**kwargs)
        b=core.learn(copy.deepcopy(model),x,y,config,**kwargs)
        exact(a[0].state_dict(),b[0].state_dict());exact(a[1].state_dict(),b[1].state_dict());exact(a[2:],b[2:])
        clean_checks.append(method)

    # Independent training loop uses the original public batch statements.
    public=Path('D:/FUBA_BATCH_TRIGGER_ALIGNMENT_20261115/upstream/train_method_dba.py')
    assert sha(public)=='a4541d0969c413e1d7e3731fcaf8b46be83a18cc97af42ba49f38e56c8b50d85'
    fn=next(n for n in ast.parse(public.read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='defender_train')
    nodes=sorted([n for n in ast.walk(fn) if isinstance(n,ast.Assign) and 63<=n.lineno<=66],key=lambda n:n.lineno)
    assert len(nodes)==4
    code=compile(ast.Module(body=nodes,type_ignores=[]),'original_batch_statements','exec')
    trigger_path=Path('D:/FUBA_AUTHOR_MODELS_20261115/upstream/utils/dba_attack_utils.py')
    assert sha(trigger_path)=='1234bf5ebf1805f11e7854f04b2d69e7124cb6aab5a72e0698ec7248771d1c18'
    triggers={};exec(compile(trigger_path.read_text(),'original_trigger_functions','exec'),triggers)
    records=[]
    for role in [0,4]:
        for weighted in [False,True]:
            weights={k:torch.full_like(v,.7) for k,v in model.named_parameters()} if weighted else None
            a=copy.deepcopy(model);a.train()
            opt=(torch.optim.SGD(a.parameters(),lr=.001,foreach=True) if weighted
                 else torch.optim.Adam(a.parameters(),lr=.001,foreach=True))
            order_rng=torch.Generator().manual_seed(512)
            torch.manual_seed(70000512);masks=[]
            for epoch in range(2):
                for idx in torch.randperm(len(y),generator=order_rng).split(8):
                    env={'torch':torch,'inputs':x[idx],'labels':y[idx],'config':SimpleNamespace(target_label=8),
                         'attack_func':triggers['add_backdoor_all' if role==4 else 'add_backdoor_1']}
                    exec(code,env)
                    opt.zero_grad(set_to_none=True)
                    nn.functional.cross_entropy(a(env['perturbed_inputs']),env['labels']).backward()
                    if weighted:
                        with torch.no_grad():
                            for k,p in a.named_parameters():p.grad.mul_(weights[k])
                    opt.step();masks.append(bytes(env['mask'].to(torch.uint8).tolist()).hex())
            expected_mask_state=torch.get_rng_state()
            b=core.learn(copy.deepcopy(model),x,y,config,phase_seed=512,phase='synthetic',
                         gradient_weights=weights,redraw_role=role)
            exact(a.state_dict(),b[0].state_dict());exact(opt.state_dict(),b[1].state_dict())
            exact(b[2]['shuffle'],order_rng.get_state());exact(b[2]['mask'],expected_mask_state)
            assert b[2]['mask_hex']==masks and b[3]==6
            records.append({'role':role,'optimizer':'SGD' if weighted else 'Adam','steps':6,'public_oracle_exact':True})
    with (ROOT/'CPU_CONTRACT.json').open('x') as f:
        json.dump({'state':'passed','clean_modes_exact':clean_checks,'dynamic':records,'CUDA_initialized':torch.cuda.is_initialized(),
                   'synthetic_examples':17,'real_data_training':0,'real_model_inference':0,'full_paper_reproduced':False,
                   'executed_files':freeze['files']},f,indent=2)
    print('Passed unchanged Adam/SGD/recovery and public-oracle dynamic Adam/SGD on CPU',flush=True)


if __name__=='__main__':main()
