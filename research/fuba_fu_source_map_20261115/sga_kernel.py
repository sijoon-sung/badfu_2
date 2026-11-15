"""Explicit public-FUBA SGA objective and supplementary rollback boundary."""
import copy
import math
import torch


def public_sga_objective(model, reference, fisher, inputs, targets, *, strength):
    parameters=dict(model.named_parameters())
    if parameters.keys()!=reference.keys() or parameters.keys()!=fisher.keys():
        raise ValueError('SGA parameter IDs must match reference and Fisher')
    if not math.isfinite(strength) or strength<0:raise ValueError('Invalid EWC strength')
    ce=torch.nn.functional.cross_entropy(model(inputs),targets)
    penalty=torch.zeros((),device=ce.device,dtype=ce.dtype)
    for name,param in parameters.items():
        ref,importance=reference[name].detach().to(param),fisher[name].detach().to(param)
        if ref.shape!=param.shape or importance.shape!=param.shape:raise ValueError('SGA tensor shape mismatch')
        if not bool(torch.isfinite(ref).all()&torch.isfinite(importance).all()&(importance>=0).all()):
            raise ValueError('Fisher must be finite and nonnegative')
        penalty=penalty+(importance*(param-ref).square()).sum()
    objective=ce-(strength/2)*penalty
    if not bool(torch.isfinite(objective)):raise FloatingPointError('Nonfinite SGA objective')
    return objective,{'cross_entropy':ce.detach(),'EWC_penalty':(strength/2*penalty).detach()}


def boundary_return(current, previous, current_loss, *, threshold=5.):
    """Caller defines round granularity; never silently returns a crossed model."""
    if not math.isfinite(current_loss):raise FloatingPointError('Nonfinite SGA boundary')
    if current_loss>threshold:
        if previous is None:raise ValueError('No previous admissible round exists')
        return copy.deepcopy(previous),True
    return copy.deepcopy(current),False
