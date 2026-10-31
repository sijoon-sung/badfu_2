"""New CPU-only evaluation semantics fixture; no stored victim, real data, or old tests."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import io
import json
import torch
from pair_eval_core import evaluation_input, counts, percentages, operational_gate
from runtime_common import ROOT, read, write, freeze_check

freeze_check('PAIR_EVAL_CPU_FREEZE.json')
with (ROOT / 'PAIR_EVAL_CPU_ONCE.json').open('x', encoding='utf-8') as stream:
    json.dump({'pid': os.getpid()}, stream)
torch.set_num_threads(1)
assert not torch.cuda.is_initialized()

# Binary-exact boundary fixture; independent scalar calculation checks +1.5 and clipping.
x = torch.empty(23, 3, 32, 32, dtype=torch.float32)
delta = torch.empty(1, 3, 32, 32, dtype=torch.float32)
for c, offset in enumerate([1 / 16, -1 / 16, 0]):
    delta[:, c].fill_(offset)
    x[:, c] = torch.tensor([-1 + i / 16 for i in range(23)])[:, None, None]
x[0, 1].fill_(-1); x[-1, 0].fill_(1)
noisy = evaluation_input(x, delta)
for i in range(23):
    for c in range(3):
        expected = min(1.0, max(-1.0, float(x[i, c, 0, 0]) + 1.5 * float(delta[0, c, 0, 0])))
        assert bool((noisy[i, c] == expected).all())
assert torch.equal(noisy[:, 2], x[:, 2])
assert float(noisy[-1, 0, 0, 0]) == 1 and float(noisy[0, 1, 0, 0]) == -1

labels = torch.tensor([2 if i in [2, 5, 10, 20] else (i % 2) for i in range(23)])
clean_logits = torch.full((23, 10), -2., dtype=torch.float32)
trigger_logits = clean_logits.clone()
expected_clean, expected_hits = 0, 0
for i, y in enumerate(labels.tolist()):
    clean_pred = y if i % 3 else (y + 1) % 10
    trigger_pred = 2 if i % 4 else 1
    clean_logits[i, clean_pred] = 3; trigger_logits[i, trigger_pred] = 3
    expected_clean += clean_pred == y
    expected_hits += trigger_pred == 2 and y != 2
# Last row ties at 0 and 2: first-index argmax must choose 0, not target 2.
trigger_logits[-1].fill_(-2); trigger_logits[-1, 0] = trigger_logits[-1, 2] = 3
expected_hits -= 1
totals = dict(N=0, clean_correct=0, non_target_N=0, triggered_target_hits=0)
for start in range(0, 23, 7):
    row = counts(labels[start:start + 7], clean_logits[start:start + 7], trigger_logits[start:start + 7])
    for key in totals: totals[key] += row[key]
assert totals == {'N': 23, 'clean_correct': expected_clean, 'non_target_N': 19, 'triggered_target_hits': expected_hits}
permutation = torch.arange(22, -1, -1)
assert totals == counts(labels[permutation], clean_logits[permutation], trigger_logits[permutation])
value = percentages(totals)
assert value['ASR_pct'] == expected_hits * 100 / 19
stream = io.BytesIO(); torch.save({'labels': labels, 'clean_logits': clean_logits, 'triggered_logits': trigger_logits}, stream)
stream.seek(0); recovered = torch.load(stream, map_location='cpu', weights_only=True)
assert counts(**recovered) == totals

limits = read(ROOT / 'FU_PROFILE.json')['minimum_operational_latent_pair_gate']
rows = {name: {'N': 10000, 'clean_correct': ca, 'non_target_N': 9000, 'triggered_target_hits': hits}
        for name, ca, hits in [('pre', 8500, 1800), ('benign', 8000, 2700), ('attack', 8000, 7200)]}
assert operational_gate(rows, limits)['passed']
failed = {}
for name, field, new in [('pre', 'triggered_target_hits', 1801), ('attack', 'triggered_target_hits', 7199),
                         ('benign', 'triggered_target_hits', 2701), ('benign', 'clean_correct', 7999)]:
    changed = {k: dict(v) for k, v in rows.items()}; changed[name][field] = new
    failed[name + '.' + field] = operational_gate(changed, limits)
    assert not failed[name + '.' + field]['passed']
assert not torch.cuda.is_initialized()
write(ROOT / 'PAIR_EVAL_CPU_RESULT.json', {'state': 'passed', 'CPU_only': True,
      'contracts': ['plus1.5_clip_boundary_exact_unchanged_channel',
                    'all23_labels_target_exclusion_B7_tail2_tie_IDorder_roundtrip',
                    'fixed_operational_gate_boundary_and_one_count_failures'],
      'synthetic_counts': totals, 'gate_boundary_passed': True, 'gate_one_count_failures': failed,
      'source_hashes': read(ROOT / 'PAIR_EVAL_CPU_FREEZE.json')['files'],
      'real_models_or_data_used': False, 'real_SSS_FU_or_pair_evaluation_executed': False,
      'prior_finite_contracts_repeated': False})
print(json.dumps({'state': 'passed', 'contracts': 3, 'CPU_only': True, 'synthetic_N': 23}))
