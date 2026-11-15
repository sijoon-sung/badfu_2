"""One-time synthetic CPU oracle contracts; no real-data experiment."""
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
import torch
from sga_kernel import public_sga_objective,boundary_return


ROOT=Path(__file__).resolve().parent


def main():
    torch.set_num_threads(1)
    frozen=json.loads((ROOT/'SGA_FREEZE.json').read_text())
    for name,digest in frozen['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    tree=ast.parse((ROOT/'upstream/sga.py').read_text(encoding='utf-8'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('cross_entropy_loss','unlearning_loss')]
    assert len(nodes)==2
    env={'torch':torch,'nn':torch.nn,'Config':SimpleNamespace}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'original_public_FUBA_SGA','exec'),env)
    torch.manual_seed(23);m=torch.nn.Linear(2,2)
    reference={k:torch.zeros_like(p) for k,p in m.named_parameters()}
    fisher={k:torch.ones_like(p)*.125 for k,p in m.named_parameters()}
    x=torch.tensor([[1.,2.],[-2.,1.]]);y=torch.tensor([0,1])
    ours,_=public_sga_objective(m,reference,fisher,x,y,strength=100.)
    a=torch.autograd.grad(ours,tuple(m.parameters()))
    with contextlib.redirect_stdout(io.StringIO()):original=env['unlearning_loss'](m,reference,fisher,x,y,100.,SimpleNamespace(device='cpu'))
    b=torch.autograd.grad(original,tuple(m.parameters()))
    assert torch.equal(ours,original) and all(torch.equal(u,v) for u,v in zip(a,b))
    theta=torch.tensor([2.],requires_grad=True)
    penalty=.5*100*(theta-1).square().sum()
    ascent_negative=theta+.001*torch.autograd.grad(-penalty,theta,retain_graph=True)[0]
    ascent_positive=theta+.001*torch.autograd.grad(penalty,theta)[0]
    assert abs(float(ascent_negative.detach()-1))<1<abs(float(ascent_positive.detach()-1))
    previous={'w':torch.tensor([1.])};current={'w':torch.tensor([2.])}
    returned,stopped=boundary_return(current,previous,5.01);assert stopped and torch.equal(returned['w'],previous['w'])
    returned,stopped=boundary_return(current,previous,5.);assert not stopped and torch.equal(returned['w'],current['w'])
    try:boundary_return(current,None,6.)
    except ValueError:pass
    else:raise AssertionError('Missing previous state accepted')
    result={'state':'passed','public_loss_and_gradient_exact':True,'negative_EWC_ascent_moves_toward_reference':True,
            'positive_EWC_ascent_moves_away_from_reference':True,'strict5_boundary_previous_state':True,
            'CUDA_initialized':torch.cuda.is_initialized(),'real_training':0,'inference':0,'actual_FU':False,'executed_files':frozen['files']}
    with (ROOT/'SGA_CONTRACT.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))


if __name__=='__main__':main()
