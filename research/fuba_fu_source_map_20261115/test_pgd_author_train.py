"""Compare all gradient steps with the original notebook AST on CPU only."""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import torch
from torch import nn
from pgd_author_kernel import squared_distance
from pgd_author_train import unlearn_author

ROOT=Path(__file__).resolve().parent


def exact(a,b):
    if isinstance(a,torch.Tensor):assert torch.equal(a,b)
    elif isinstance(a,dict):
        assert a.keys()==b.keys()
        for k in a:exact(a[k],b[k])
    elif isinstance(a,(list,tuple)):
        assert len(a)==len(b)
        for x,y in zip(a,b):exact(x,y)
    else:assert a==b


def main():
    torch.set_num_threads(1)
    for n,h in json.loads((ROOT/'PGD_STEP_FREEZE.json').read_text())['files'].items():
        assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h,n
    assert not (ROOT/'PGD_STEP_CONTRACT.json').exists()
    notebooks=list((ROOT/'upstream/ibm_pgd').glob('*.ipynb'));assert len(notebooks)==1
    source=''.join(json.loads(notebooks[0].read_text(encoding='utf-8'))['cells'][34]['source'])
    tree=ast.parse(source)
    loops=[x for x in ast.walk(tree) if isinstance(x,ast.For) and isinstance(x.target,ast.Name) and x.target.id=='epoch']
    assert len(loops)==1
    code=compile(ast.Module(body=loops,type_ignores=[]),'IBM-notebook-cell34-original-epoch-loop','exec')
    torch.manual_seed(17)
    reference=nn.Linear(3,2);deleted=copy.deepcopy(reference)
    batches=[(torch.randn(4,3),torch.tensor([0,1,1,0])) for _ in range(4)]
    records=[]
    for radius,threshold,steps in [(1e-5,100.,20),(1e-5,0.,1),(100.,100.,20)]:
        oracle=copy.deepcopy(reference).train();opt=torch.optim.SGD(oracle.parameters(),lr=.01,momentum=.9)
        forwards=[];hook=oracle.register_forward_hook(lambda *a:forwards.append(1))
        env={'torch':torch,'nn':nn,'np':np,'Utils':SimpleNamespace(get_distance=squared_distance),
             'model':oracle,'model_ref':reference,'party0_model':deleted,'opt':opt,
             'criterion':nn.CrossEntropyLoss(),'threshold':radius,'distance_threshold':threshold,
             'num_local_epochs_unlearn':5,'clip_grad':5,'flag':False,'num_updates_in_epoch':None,
             'trainloader_lst':[batches],'party_to_be_erased':0,'print':lambda *a,**k:None}
        exec(code,env);hook.remove()
        model,optimizer,trace=unlearn_author(reference,deleted,batches,radius_squared=radius,distance_threshold=threshold)
        exact(model.state_dict(),oracle.state_dict());exact(optimizer.state_dict(),opt.state_dict())
        assert len(forwards)==len(trace)==steps
        if radius==1e-5:assert any(x['projected'] for x in trace)
        exact(reference.state_dict(),deleted.state_dict())
        records.append({'radius_squared':radius,'distance_threshold':threshold,'steps':steps,
                        'projection_count':sum(x['projected'] for x in trace),
                        'stop':trace[-1]['stop'],'model_and_optimizer_tensor_exact':True})
    result={'state':'passed','cases':records,'device':'CPU','CUDA_initialized':torch.cuda.is_initialized(),
            'real_data_or_models':False,'full_FU_executed':False,'notebook_SHA256':hashlib.sha256(notebooks[0].read_bytes()).hexdigest()}
    with (ROOT/'PGD_STEP_CONTRACT.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
