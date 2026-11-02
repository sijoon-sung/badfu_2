"""Declared FedUBA Eq.5--8 and FedEraser adapter; no FUBA attacker/defender split."""
import copy
from dataclasses import dataclass
import torch
from torch.utils.data import Dataset


class IndexedDataset(Dataset):
    def __init__(self, dataset, global_ids):
        self.dataset, self.global_ids = dataset, tuple(int(i) for i in global_ids)
        assert len(self.dataset) == len(self.global_ids) == len(set(self.global_ids))

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        x, y = self.dataset[index]
        return x, y, self.global_ids[index]


def add_trigger(x, delta, sign=1, multiplier=1, clip=True):
    assert sign in [-1, 1] and multiplier > 0
    if x.ndim == 3 and delta.ndim == 4:
        assert delta.shape[0] == 1
        delta = delta[0]
    assert x.shape[-3:] == delta.shape[-3:]
    out = x + sign * multiplier * delta.to(x)
    return out.clamp(-1, 1) if clip else out


@torch.inference_mode()
def sensitivity_rank(query_logits, indexed_loader, delta, device):
    """Eq.6: two forward queries, stable source IDs, no labels/gradients in score."""
    scores = []
    for x, _, ids in indexed_loader:
        x = x.to(device)
        clean = query_logits(x)
        perturbed = query_logits(add_trigger(x, delta, clip=False))
        values = torch.linalg.vector_norm(perturbed - clean, ord=2, dim=1)
        assert bool(torch.isfinite(values).all()) and len(values) == len(ids)
        scores.extend((int(i), float(v)) for i, v in zip(ids, values.cpu()))
    assert len(scores) == len({i for i, _ in scores})
    return sorted(scores, key=lambda item: (-item[1], item[0]))


def select_requests(ranked_by_owner, ownership, budget):
    """Eq.7 global top-n, restricted to the explicitly malicious owners."""
    assert isinstance(budget, int) and budget > 0
    candidates = []
    for owner, ranked in ranked_by_owner.items():
        own = set(ownership[owner])
        assert len(own) == len(ownership[owner])
        assert {i for i, _ in ranked} == own
        candidates.extend((float(score), int(source_id), int(owner)) for source_id, score in ranked)
    assert len({source_id for _, source_id, _ in candidates}) == len(candidates)
    assert budget <= len(candidates)
    selected = sorted(candidates, key=lambda item: (-item[0], item[1]))[:budget]
    result = {owner: [] for owner in ranked_by_owner}
    for _, source_id, owner in selected:
        result[owner].append(source_id)
    assert sum(map(len, result.values())) == budget
    return result


class RequestDataset(Dataset):
    """Eq.8 replacement of selected owned images, preserving labels and dataset size."""
    def __init__(self, indexed_dataset, selected_global_ids, delta, malicious):
        self.dataset = indexed_dataset
        self.selected = frozenset(int(i) for i in selected_global_ids)
        assert self.selected.issubset(set(indexed_dataset.global_ids))
        self.delta, self.malicious = delta.detach().cpu().clone(), bool(malicious)

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        x, y, source_id = self.dataset[index]
        # The benign-FU branch removes the selected source samples, using RetainedDataset.
        if self.malicious and source_id in self.selected:
            x = add_trigger(x, self.delta, sign=-1, clip=True)
        return x, y


class RetainedDataset(Dataset):
    def __init__(self, indexed_dataset, removed_global_ids):
        removed = frozenset(int(i) for i in removed_global_ids)
        assert removed.issubset(set(indexed_dataset.global_ids))
        self.dataset = indexed_dataset
        self.positions = [j for j, source_id in enumerate(indexed_dataset.global_ids) if source_id not in removed]

    def __len__(self):
        return len(self.positions)

    def __getitem__(self, index):
        x, y, _ = self.dataset[self.positions[index]]
        return x, y


def fedavg(states):
    """Public Fed_train.fedavg: equal weights, last client's BN counter policy."""
    assert states and all(s.keys() == states[0].keys() for s in states)
    result = {}
    for key in states[0]:
        value = torch.zeros_like(states[0][key])
        for state in states:
            value += state[key]
        result[key] = states[-1][key].clone() if 'num_batches_tracked' in key else value / len(states)
    return result


def fed_eraser_step(old_clients, new_clients, old_global, new_global):
    """Public unlearning_step_once calibration; norms are FU math, not detection."""
    assert len(old_clients) == len(new_clients) > 0
    calibrated = []
    for old, new in zip(old_clients, new_clients):
        state = {}
        for key in old_global:
            old_delta = old[key] - old_global[key]
            new_delta = new[key] - new_global[key]
            length = torch.norm(old_delta.float())
            denom = torch.norm(new_delta.float())
            direction = new_delta if denom == 0 else new_delta / denom
            value = new_global[key] + length * direction
            state[key] = value.to(new_global[key].dtype)
            assert bool(torch.isfinite(state[key]).all()), key
        calibrated.append(state)
    return fedavg(calibrated), calibrated


@dataclass(frozen=True)
class STGSettings:
    surrogate_epochs: int = 100
    warmup_epochs: int = 5
    trigger_epochs: int = 100
    surrogate_lr: float = .1
    warmup_lr: float = .001
    trigger_lr: float = .1
    epsilon_model: float = 32 / 255


def trigger_step(surrogate, x, target, delta, optimizer, epsilon_model):
    """Eq.5 objective with projected trigger; caller owns optimizer and phase logs."""
    x_triggered = add_trigger(x, delta, clip=True)
    logits = surrogate(x_triggered)
    loss = torch.nn.functional.cross_entropy(logits, target)
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    assert delta.grad is not None and bool(torch.isfinite(delta.grad).all())
    optimizer.step()
    with torch.no_grad():
        delta.clamp_(-epsilon_model, epsilon_model)
    assert bool(torch.isfinite(delta).all()) and float(delta.detach().abs().max()) <= epsilon_model + 1e-7
    return float(loss.detach())
