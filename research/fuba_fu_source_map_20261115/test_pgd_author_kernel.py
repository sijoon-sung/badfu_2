"""One synthetic CPU contract against actual IBM source AST nodes."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from torch import nn
import pgd_author_kernel as kernel

ROOT=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def model(values):
    net=nn.Linear(2,1,bias=False)
    with torch.no_grad():net.weight.copy_(torch.tensor([values]))
    return net


def main():
    torch.set_num_threads(1)
    for name,digest in json.loads((ROOT/'PGD_FREEZE.json').read_text(encoding='utf-8'))['files'].items():assert sha(ROOT/name)==digest
    metadata=json.loads((ROOT/'PGD_IBM_SOURCE.json').read_text(encoding='utf-8'));base=ROOT/'upstream/ibm_pgd'
    for name,item in metadata['files'].items():assert sha(base/name)==item['sha256']
    env={};exec(compile((base/'utils/utils.py').read_text(encoding='utf-8'),'original_IBM_utils','exec'),env)
    Utils=env['Utils']
    source=json.loads((base/'federated_unlearning.ipynb').read_text(encoding='utf-8'))['cells'][34]['source']
    tree=ast.parse(''.join(source))
    projections=[n for n in ast.walk(tree) if isinstance(n,ast.With) and 'proj_vec' in ast.unparse(n)]
    stops=[n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=='distance_ref_party_0 > distance_threshold']
    thresholds=[n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='threshold' for t in n.targets)]
    assert len(projections)==len(stops)==len(thresholds)==1
    projection=compile(ast.Module(body=projections,type_ignores=[]),'original_projection','exec')
    stop=compile(ast.Expression(stops[0].test),'original_termination','eval')
    radius=compile(ast.Module(body=thresholds,type_ignores=[]),'original_radius','exec')
    reference=model([0.,0.]);rows=[]
    for values,threshold in [([3.,4.],4.),([.6,.8],4.),([3.,4.],0.)]:
        a=model(values);b=copy.deepcopy(a)
        scope={'torch':torch,'np':np,'nn':nn,'Utils':Utils,'model':a,'model_ref':reference,'threshold':threshold}
        exec(projection,scope);kernel.project_author_(b,reference,radius_squared=threshold)
        assert all(torch.equal(x,y) for x,y in zip(a.parameters(),b.parameters()))
        assert bool(torch.isclose(Utils.get_distance(a,reference),kernel.squared_distance(b,reference)))
        rows.append({'input':values,'squared_radius':threshold,'exact':True})
    random_models=[model([float(i),float(i+1)]) for i in range(10)]
    scope={'np':np,'dist_ref_random_lst':[Utils.get_distance(reference,m) for m in random_models]}
    exec(radius,scope);assert kernel.radius_squared(reference,random_models)==scope['threshold']
    decisions=[]
    for length in [1.,3.]:
        net=model([length,0.]);d=Utils.get_distance(net,reference)
        original=bool(eval(stop,{'distance_ref_party_0':d,'distance_threshold':2.2}))
        calculated=kernel.stop_author(net,reference,distance_threshold=2.2)
        assert original==calculated and calculated!=(length<2.2)
        decisions.append({'euclidean_distance':length,'IBM_squared_greater_2_2':calculated,'v3_euclidean_less_2_2':length<2.2})
    for value in [-1.,float('nan')]:
        try:kernel.project_author_(model([1.,2.]),reference,radius_squared=value)
        except ValueError:pass
        else:raise AssertionError('Invalid radius accepted')
    result={'state':'passed','source_commit':metadata['commit'],'projection_cases':rows,
            'random_radius_exact':True,'distinct_stop_rules':decisions,'CUDA_initialized':torch.cuda.is_initialized(),
            'real_models':0,'real_training':0,'actual_FU':False,'interpretation':'IBM notebook; not unique FUBA PGD setting'}
    with (ROOT/'PGD_CONTRACT.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
