"""New query logger/ID/analytic integration contracts, not the previous core audit."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import io
import json
import torch
from torch.utils.data import DataLoader, TensorDataset
import core
from sss_logging import observe_and_rank
from runtime_common import ROOT, read, write, freeze_check

assert not (ROOT / 'SSS_LOGGER_CPU2_RESULT.json').exists()
freeze_check('SSS_LOGGER_CPU2_FREEZE.json')
assert read(ROOT / 'SSS_ROUNDOFF_DIAGNOSIS.json')['rows'][1]['max_abs_error'] == 0
torch.set_num_threads(1)
assert not torch.cuda.is_initialized()
delta = torch.zeros(1, 3, 32, 32)
delta[0, 0, 0, 0] = .125
ranked, ownership, all_records = {}, {}, []
calls = []
def black_box(x):
    assert not torch.is_grad_enabled()
    calls.append(len(x))
    return torch.stack([2 * x[:, 0, 0, 0].square() + .1 * x[:, 0, 0, 1], x[:, 0, 0, 1]], dim=1)
for owner, start, count in [(5, 0, 31), (7, 31, 30)]:
    x = torch.zeros(count, 3, 32, 32)
    x[:, 0, 0, 0] = torch.arange(start, start + count).float() / 128
    ids = [owner * 100000 + j for j in range(count)]
    ownership[owner] = ids
    # Deliberately unrelated labels cannot affect the known score or order.
    dataset = core.IndexedDataset(TensorDataset(x, torch.arange(count).remainder(10)), ids)
    loader = DataLoader(dataset, batch_size=11, shuffle=True, generator=torch.Generator().manual_seed(owner))
    ranked[owner], records = observe_and_rank(black_box, loader, delta, 'cpu')
    assert [i for i, _ in ranked[owner]] == list(reversed(ids))
    for row in records:
        values = row['x'][:, 0, 0, 0]
        # (2*(v+.125)^2)-(2*v^2) = .5*v+.03125, nonnegative on this domain.
        expected = .5 * values + .03125
        assert torch.equal(row['score_FP32'], expected)
        stream = io.BytesIO(); torch.save(row, stream); stream.seek(0)
        back = torch.load(stream, weights_only=True)
        assert torch.equal(back['source_ids'], row['source_ids']) and torch.equal(back['score_FP32'], row['score_FP32'])
    assert sorted(torch.cat([row['source_ids'] for row in records]).tolist()) == ids
    all_records.extend(records)
selection = core.select_requests(ranked, ownership, 9)
assert selection[5] == [] and selection[7] == list(reversed(ownership[7]))[:9]
assert len(all_records) == 6 and len(calls) == 12 and sum(calls) == 122
assert not torch.cuda.is_initialized()
write(ROOT / 'SSS_LOGGER_CPU2_RESULT.json', {'state': 'passed', 'CPU_only': True, 'samples': 61,
      'batches': 6, 'actual_forward_calls': 12, 'actual_forward_sample_evaluations': 122,
      'contracts': ['query_callable_only_two_forward_no_label_score', 'shuffled_stable_IDs_and_analytic_L2',
                    'partial_batch_query_receipt_roundtrip', 'logged_ranks_owned_global_top9'],
      'count': 4, 'source_hashes': read(ROOT / 'SSS_LOGGER_CPU2_FREEZE.json')['files'],
      'core_or_original_SSS_audits_repeated': False, 'real_victim_or_SSS_used': False})
print(json.dumps({'state': 'passed', 'CPU_only': True, 'logger_contracts': 4}))
