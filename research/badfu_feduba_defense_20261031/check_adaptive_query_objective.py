"""Independent two-row heterogeneous-target probability/gradient contract."""
import hashlib,json,math,sys
from pathlib import Path
r=Path(__file__).resolve().parent
sys.stdout=(r/'adaptive_query_objective_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'adaptive_query_objective_stderr.log').open('x',encoding='utf8',buffering=1)
import torch
from adaptive_query_method import vector_source_objective
torch.set_num_threads(2)
t=torch.tensor([[0.,4.,0.],[4.,0.,0.]],dtype=torch.float64,requires_grad=True)
g=torch.tensor([[4.,0.,0.],[0.,0.,4.]],dtype=torch.float64,requires_grad=True)
source=torch.tensor([1,0]);requested=torch.tensor([0,2])
v=vector_source_objective(t,g,source,requested)
expected=2*(2-math.log(math.exp(2)+2));assert abs(float(v.detach())-expected)<1e-12
gt,gg=torch.autograd.grad(v,(t,g));p=math.exp(2)/(math.exp(2)+2)
for i in range(2):
    assert abs(float(gt[i,source[i]])-(1-p)/4)<1e-12
    assert abs(float(gg[i,requested[i]])-(1-p)/4)<1e-12
    assert all(gt[i,j]<0 for j in range(3) if j!=source[i])
    assert all(gg[i,j]<0 for j in range(3) if j!=requested[i])
assert not torch.cuda.is_initialized()
result={'state':'passed','two_different_requested_classes':True,'independent_closed_form_probability':True,
    'independent_desired_gradient_and_other_signs':True,'method_sha256':hashlib.sha256((r/'adaptive_query_method.py').read_bytes()).hexdigest(),
    'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'real_model_or_training_executed':False}
with (r/'ADAPTIVE_QUERY_OBJECTIVE_CONTRACT.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result),flush=True)
