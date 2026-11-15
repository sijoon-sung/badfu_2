"""Paper-derived FU numerical operations; no implicit experiment or retuning.

PGD: Halimi et al., arXiv:2207.05521v3, Algorithm 1 / Appendix A.
RobustFU: Sheng et al., CIKM 2024, Algorithm 1. Multiclass conflict
count follows the FUBA wrapper. Zero-score limit is an explicit extension.
These operations do not certify a complete FUBA reproduction.
"""
from collections.abc import Mapping
import math
import torch


def _compatible(states):
    if not states:
        raise ValueError('At least one model is required')
    first = states[0]
    for state in states:
        if state.keys() != first.keys():
            raise ValueError('Mismatched model keys')
        for key, value in state.items():
            ref = first[key]
            if value.shape != ref.shape or value.dtype != ref.dtype or value.device != ref.device:
                raise ValueError(f'Mismatched tensor: {key}')
            if not value.is_floating_point() or not bool(torch.isfinite(value).all()):
                raise ValueError(f'Non-floating or nonfinite tensor: {key}')


def retained_reference(submitted: Mapping[int, dict], erased_client: int):
    """Equal-size clients in the same actual round, with the erased client present.

An absent client is an unresolved protocol case, not a zero update or a stale
model silently combined with a newer global model.
"""
    if erased_client not in submitted or len(submitted) < 2:
        raise ValueError('Need the erased client and a retained client in the same round')
    states = list(submitted.values())
    _compatible(states)
    retained = [state for client, state in submitted.items() if client != erased_client]
    return {key: torch.stack([s[key] for s in retained]).mean(0) for key in states[0]}


def project_l2(state, reference, radius: float):
    """One L2 ball over all parameters, not separate per-layer balls."""
    _compatible([state, reference])
    if not math.isfinite(radius) or radius < 0:
        raise ValueError('radius must be finite and nonnegative')
    distance = torch.sqrt(sum((state[k].double()-reference[k].double()).square().sum() for k in state))
    factor = min(1., radius / float(distance)) if float(distance) else 1.
    result = {k: reference[k] + factor*(state[k]-reference[k]) for k in state}
    _compatible([result, reference])
    return result


def pgd_should_stop(state, last_erased_client, tau: float):
    """Literal Algorithm 1 '< tau'; not an ASR-based stopping rule."""
    _compatible([state, last_erased_client])
    if not math.isfinite(tau) or tau < 0:
        raise ValueError('tau must be finite and nonnegative')
    distance = torch.sqrt(sum((state[k].double()-last_erased_client[k].double()).square().sum() for k in state))
    return bool(distance < tau)


def inverse_conflict_weights(conflicts: Mapping[int, int]):
    """Maintain client IDs including zero counts.

For zero counts, use the common-epsilon -> 0 limit: equal weights on zeros,
zero weights elsewhere. This edge policy is declared, not author-certified.
"""
    if not conflicts or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in conflicts.values()):
        raise ValueError('Nonempty nonnegative integer conflict counts required')
    zero = [client for client, count in conflicts.items() if count == 0]
    if zero:
        return {client: 1./len(zero) if client in zero else 0. for client in conflicts}
    inv = {client: 1./count for client, count in conflicts.items()}
    total = sum(inv.values())
    return {client: value/total for client, value in inv.items()}


def conflict_samples(sample_ids, teacher_labels, local_labels):
    """Return sample IDs and teacher pseudolabels, never evaluator truth."""
    if sample_ids.ndim != 1 or teacher_labels.shape != sample_ids.shape or local_labels.shape != sample_ids.shape:
        raise ValueError('Expected aligned one-dimensional arrays')
    if len(torch.unique(sample_ids)) != len(sample_ids):
        raise ValueError('Server sample IDs must be unique within a round')
    mask = local_labels != teacher_labels
    return sample_ids[mask].clone(), teacher_labels[mask].clone(), int(mask.sum())
