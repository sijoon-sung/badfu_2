"""Independent finite ranking and known-rotation checks before real-data execution."""
import json
import numpy as np
import torch
from stage05_common import rank_auc
from stage05_fit import align

torch.set_num_threads(2)
cases=[([1,2,2],[0,2,3]),([4,4],[4,4]),([0,1],[2,3]),([2,3],[0,1])]
for member,nonmember in cases:
    brute=sum((m>n)+.5*(m==n) for m in member for n in nonmember)/(len(member)*len(nonmember))
    assert abs(rank_auc(member,nonmember)-brute)<1e-15
g=torch.Generator().manual_seed(614)
x=torch.randn(80,7,generator=g,dtype=torch.float64)
w=torch.randn(3,7,generator=g,dtype=torch.float64);b=torch.randn(3,generator=g,dtype=torch.float64)
h,details=align(x,x,{'weight':w,'bias':b})
assert (details['rotation']-torch.eye(7,dtype=torch.float64)).abs().max()<1e-12
assert (h['weight'].double()-w).abs().max()<2e-7
# With a nontrivial rotation/translation, check the saved head against the
# explicitly mapped features, independently of the implementation's bias formula.
q=torch.linalg.qr(torch.randn(7,7,generator=g,dtype=torch.float64)).Q
shift=torch.randn(7,generator=g,dtype=torch.float64)
h,d=align(x,x@q+shift,{'weight':w,'bias':b})
mapped=(x-d['mean_pre'])@d['rotation']+d['mean_post']
direct=mapped@w.T+b;derived=x@h['weight'].double().T+h['bias'].double()
assert (direct-derived).abs().max()<2e-6
print(json.dumps({'state':'passed','independent_rank_cases':len(cases),
                  'identity_alignment':True,'mapped_feature_vs_saved_head_max_error':float((direct-derived).abs().max())}))
