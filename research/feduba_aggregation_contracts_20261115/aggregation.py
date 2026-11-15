"""State adapters for the three aggregation rules in the FedUBA paper."""
import math
import torch


def aggregate(states, rule, trim_fraction=.1):
    if not states or rule not in ('fedavg', 'median', 'trim-mean'):
        raise ValueError('nonempty states and a declared rule required')
    if not math.isfinite(trim_fraction) or not 0 <= trim_fraction < .5:
        raise ValueError('trim fraction must be in [0, .5)')
    keys = tuple(states[0])
    for state in states:
        if tuple(state) != keys:
            raise ValueError('state key/order mismatch')
        for key in keys:
            value, first = state[key], states[0][key]
            if value.shape != first.shape or value.dtype != first.dtype or value.device != first.device:
                raise ValueError('state tensor schema mismatch')
            if not bool(torch.isfinite(value).all()):
                raise ValueError('nonfinite state')
    result = {}
    for key in keys:
        dtype = states[0][key].dtype
        if rule == 'fedavg':
            value = torch.zeros_like(states[0][key])
            for state in states:
                value.add_(state[key])
            value = states[-1][key].clone() if 'num_batches_tracked' in key else value / len(states)
        else:
            stack = torch.stack([state[key] for state in states])
            if rule == 'median':
                value = stack.median(dim=0).values
            else:
                k = int(len(states) * trim_fraction)
                ordered = stack.sort(dim=0).values
                middle = ordered[k:len(states)-k]
                value = middle.float().mean(dim=0)
        result[key] = value.to(dtype)
        if not bool(torch.isfinite(result[key]).all()):
            raise ValueError('nonfinite aggregate')
    return result
