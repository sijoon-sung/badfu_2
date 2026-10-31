"""Known-logit mathematical checks before any real-data corrected training."""
import json,math
import torch
from stage11_method import disjoint_objective

torch.set_num_threads(2)
t=torch.tensor([[0.,8.,0.]],dtype=torch.float64,requires_grad=True)
p=torch.tensor([[8.,0.,0.]],dtype=torch.float64,requires_grad=True)
v=disjoint_objective(t,p,0)
direct=torch.log((p/2).softmax(1)[:,0]*(1-(t/2).softmax(1)[:,0])).mean()
assert abs(float((v-direct).detach()))<1e-12
gt,gp=torch.autograd.grad(v,(t,p))
assert gt[0,0]<0 and gp[0,0]>0
wrong=disjoint_objective(p.detach(),p.detach(),0)
assert v>wrong
# Complement arithmetic must remain finite even when naive1-softmax rounds to0.
ts=torch.tensor([[10000.,0.,-10000.]],requires_grad=True)
ps=torch.tensor([[10000.,0.,-10000.]],requires_grad=True)
sv=disjoint_objective(ts,ps,0);sg=torch.autograd.grad(sv,(ts,ps))
assert torch.isfinite(sv) and all(torch.isfinite(g).all() for g in sg)
assert not torch.cuda.is_initialized()
print(json.dumps({'state':'passed','analytic_probability_identity':True,'input_direction_signs':True,
                  'saturated_complement_and_gradients_finite':True,'direct_error':abs(float((v-direct).detach()))}))
