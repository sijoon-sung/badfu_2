"""ID-preserving form of the linked FedEraser author's calibration function.

Author code averages clients first and then calibrates each state tensor.
This ordering is explicit; it is not silently equated with per-client Eq.1.
No history schedule or local-training configuration is chosen here.
"""
import torch
from unlearning_kernels import _compatible


def calibrate_author_layers(old_global, old_clients, new_global, new_clients, *, erased_client):
    if not old_clients or old_clients.keys()!=new_clients.keys():
        raise ValueError('Calibration requires matching retained client IDs')
    if erased_client in old_clients:
        raise ValueError('The erased client must not contribute to calibration')
    ids=sorted(old_clients)
    _compatible([old_global,new_global]+[old_clients[i] for i in ids]+[new_clients[i] for i in ids])
    result={};lengths={}
    for key in old_global:
        before=torch.zeros_like(old_global[key]);after=torch.zeros_like(new_global[key])
        for client in ids:
            before+=old_clients[client][key]
            after+=new_clients[client][key]
        before=before/len(ids)-old_global[key]
        after=after/len(ids)-new_global[key]
        old_length=torch.norm(before)
        new_length=torch.norm(after)
        if not bool(torch.isfinite(old_length)&torch.isfinite(new_length)):
            raise FloatingPointError('Nonfinite calibration norm')
        if float(old_length)==0:
            # Zero old update contributes zero. Avoid the original 0/0 edge.
            result[key]=new_global[key].clone()
        elif float(new_length)==0:
            raise ValueError('Undefined calibration direction for a nonzero retained update')
        else:
            result[key]=new_global[key]+old_length*(after/new_length)
        lengths[key]={'old':float(old_length),'new':float(new_length)}
    _compatible([result,new_global])
    return result,{'retained_clients':ids,'tensor_norms':lengths,
                   'policy':'official-code: mean clients, then per-tensor old norm/new direction'}
