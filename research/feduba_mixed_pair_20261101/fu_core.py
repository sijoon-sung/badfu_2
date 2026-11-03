"""FedUBA owner-aware paired FU policy; kernel calibration stays in frozen core."""
import math
from torch.utils.data import Subset
import core


def owned_selection(parts, selected_by_owner, owners, budget):
    assert set(selected_by_owner) == set(owners)
    assert len(parts) == 20 and sorted(sum(parts, [])) == list(range(50000))
    selected = []
    for owner in owners:
        ids = selected_by_owner[owner]
        assert len(ids) == len(set(ids)) and set(ids).issubset(set(parts[owner]))
        selected.extend(ids)
    assert len(selected) == len(set(selected)) == budget
    return {client: list(selected_by_owner.get(client, [])) for client in range(20)}


def branch_dataset(train, source_ids, selected_ids, delta, branch):
    assert branch in ['benign', 'attack']
    indexed = core.IndexedDataset(Subset(train, source_ids), source_ids)
    if branch == 'benign':
        return core.RetainedDataset(indexed, selected_ids)
    return core.RequestDataset(indexed, selected_ids, delta, malicious=True)


def calibration_round(round_number, participants, owners, old_states, trained_states, old_global, new_global):
    assert round_number >= 1 and len(participants) == len(set(participants))
    assert set(old_states) == set(trained_states) == set(participants)
    reused = [client for client in participants if round_number == 1 and client not in owners]
    effective = {client: old_states[client] if client in reused else trained_states[client] for client in participants}
    result, calibrated = core.fed_eraser_step([old_states[c] for c in participants],
                                            [effective[c] for c in participants], old_global, new_global)
    return result, effective, dict(zip(participants, calibrated)), reused


def local_schedule(round_number, client, count):
    assert 1 <= round_number <= 20 and 0 <= client < 20 and count > 0
    return {'seed': 42 + 500000 + round_number * 10000 + client * 100,
            'epochs': 5, 'batch_size': 128, 'expected_batches': math.ceil(count / 128) * 5,
            'lr': .01 * (1 + math.cos(math.pi * (round_number - 1) / 20)) / 2}
