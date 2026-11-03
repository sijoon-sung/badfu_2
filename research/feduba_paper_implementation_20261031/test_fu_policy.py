"""New variable-participant/paired-data/first-round policy contracts, no old reruns."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import json
import math
import torch
from torch.utils.data import TensorDataset
from fu_core import owned_selection, branch_dataset, calibration_round, local_schedule
from runtime_common import ROOT, read, write, freeze_check

assert not (ROOT / 'FU_POLICY_CPU_RESULT.json').exists()
freeze_check('FU_POLICY_CPU_FREEZE.json')
torch.set_num_threads(1)
assert not torch.cuda.is_initialized()
parts = [list(range(i * 2500, (i + 1) * 2500)) for i in range(20)]
chosen = {5: parts[5][:50], 7: parts[7][:75]}
selected = owned_selection(parts, chosen, [5, 7], 125)
assert selected[5] == chosen[5] and selected[7] == chosen[7] and selected[2] == []
try:
    owned_selection(parts, {5: parts[2][:50], 7: parts[7][:75]}, [5, 7], 125)
except AssertionError:
    pass
else:
    raise AssertionError('position2 leaked into owner5')
images = torch.arange(12 * 3 * 32 * 32).reshape(12, 3, 32, 32).float().remainder_(17).div_(16).sub_(.5)
labels = torch.arange(12).remainder_(10)
train = TensorDataset(images, labels)
delta = torch.full((1, 3, 32, 32), .1)
source, removed = [1, 3, 5, 7, 9, 11], [3, 9]
attack = branch_dataset(train, source, removed, delta, 'attack')
benign = branch_dataset(train, source, removed, delta, 'benign')
assert len(attack) == 6 and len(benign) == 4
for i, source_id in enumerate(source):
    x, y = attack[i]
    expected = (images[source_id] - .1).clamp(-1, 1) if source_id in removed else images[source_id]
    assert torch.equal(x, expected) and y == labels[source_id]
for i, source_id in enumerate([1, 5, 7, 11]):
    x, y = benign[i]
    assert torch.equal(x, images[source_id]) and y == labels[source_id]
assert local_schedule(1, 5, 2500)['expected_batches'] == 100
assert local_schedule(1, 7, 2425)['expected_batches'] == 95
assert local_schedule(20, 5, 2500)['lr'] == .01 * (1 + math.cos(math.pi * 19 / 20)) / 2
def state(x, y, counter):
    return {'weight': torch.tensor([x, y]), 'bn.num_batches_tracked': torch.tensor(counter)}
old_global, new_global = state(0., 0., 0), state(0., 0., 0)
clients = [1, 5, 9]
old = {1: state(3., 4., 10), 5: state(0., 10., 20), 9: state(-4., 3., 30)}
trained = {1: state(4., 3., 5), 5: state(3., 4., 5), 9: state(3., -4., 5)}
result, effective, calibrated, reused = calibration_round(1, clients, [5, 7], old, trained, old_global, new_global)
assert reused == [1, 9] and effective[1] is old[1] and effective[5] is trained[5]
# Hand-computed 3-4-5 vectors: nonowners retain (3,4),(-4,3); owner5 calibrates to (6,8).
assert torch.allclose(result['weight'], torch.tensor([5 / 3, 5.]), rtol=0, atol=1e-6)
assert result['bn.num_batches_tracked'] == 30
result2, effective2, _, reused2 = calibration_round(2, clients, [5, 7], old, trained, old_global, new_global)
assert reused2 == [] and all(effective2[c] is trained[c] for c in clients)
assert torch.allclose(result2['weight'], torch.tensor([13 / 3, 7 / 3]), rtol=0, atol=1e-6)
assert not torch.cuda.is_initialized()
write(ROOT / 'FU_POLICY_CPU_RESULT.json', {'state': 'passed', 'CPU_only': True, 'count': 4,
      'contracts': ['actual_owner_IDs_exact125_and_foreign_owner_rejection',
                    'paired_BEA_label_preserving_minus_and_same_ID_true_removal',
                    'dynamic_batch_counts_and_fixed_role_lr_seed',
                    'variable_participant_first_round_effective_history_reuse_and_later_new_states'],
      'source_hashes': read(ROOT / 'FU_POLICY_CPU_FREEZE.json')['files'],
      'old_core_or_original_AST_audits_repeated': False, 'real_SSS_or_FU_executed': False})
print(json.dumps({'state': 'passed', 'new_FU_policy_contracts': 4, 'CPU_only': True}))
