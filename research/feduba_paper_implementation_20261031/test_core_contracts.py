"""Finite new CPU contracts, independent analytic observables and original FU oracle."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import torch
from torch.utils.data import DataLoader, TensorDataset
import core
import model_reference

os.environ['CUDA_VISIBLE_DEVICES'] = ''
ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_function(path, name, globals_):
    text = Path(path).read_text(encoding='utf-8')
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(path), 'exec'), globals_)
    return globals_[name]


def main():
    assert not (ROOT / 'CORE_CPU_RESULT.json').exists(), 'Finite contracts already completed'
    for name, digest in json.loads((ROOT / 'CORE_FREEZE.json').read_text())['files'].items():
        assert sha(ROOT / name) == digest, name
    torch.set_num_threads(1)
    torch.manual_seed(20261031)
    passed = []
    x = torch.zeros(64, 1, 2, 2)
    x[:, 0, 0, 0] = torch.arange(64) / 64
    y, ids = torch.arange(64) % 10, list(range(900000, 900064))
    indexed = core.IndexedDataset(TensorDataset(x, y), ids)
    loader = DataLoader(indexed, batch_size=7, shuffle=True, generator=torch.Generator().manual_seed(409))
    query = lambda t: torch.stack([t[:, 0, 0, 0] ** 2, t[:, 0, 1, 1]], dim=1)
    delta = torch.zeros(1, 1, 2, 2); delta[0, 0, 0, 0] = .125
    ranked = core.sensitivity_rank(query, loader, delta, 'cpu')
    expected = list(reversed(ids))
    assert [i for i, _ in ranked] == expected
    for i, score in ranked:
        z = (i - 900000) / 64
        assert abs(score - (2 * z * .125 + .125 ** 2)) < 1e-7
    passed.append('64_shuffled_global_ID_ranks_and_analytic_logit_scores')
    ownership = {5: ids[:32], 7: ids[32:]}
    owner_ranked = {owner: [(i, score) for i, score in ranked if i in own] for owner, own in ownership.items()}
    chosen = core.select_requests(owner_ranked, ownership, 7)
    assert sorted(sum(chosen.values(), [])) == sorted(expected[:7])
    assert sum(map(len, chosen.values())) == 7
    try:
        core.RequestDataset(indexed, [1], delta, True)
        raise AssertionError('Foreign ID accepted')
    except AssertionError as error:
        assert str(error) != 'Foreign ID accepted'
    passed.append('exact_budget_and_foreign_ID_rejection')
    request = core.RequestDataset(indexed, expected[:7], delta, True)
    retained = core.RetainedDataset(indexed, expected[:7])
    assert len(request) == 64 and len(retained) == 57
    for j in range(64):
        xx, yy = request[j]
        wanted = (x[j] - delta[0]).clamp(-1, 1) if ids[j] in expected[:7] else x[j]
        assert torch.equal(xx, wanted) and torch.equal(yy, y[j])
    assert torch.equal(core.add_trigger(x, delta), (x + delta).clamp(-1, 1))
    assert torch.equal(core.add_trigger(torch.ones_like(x), delta, clip=False), torch.ones_like(x) + delta)
    raw = lambda value: (value + 1) / 2
    assert float((raw(request[63][0]) - raw(x[63])).abs().max()) == .125 / 2
    passed.append('BEA_minus_eval_plus_label_preservation_clip_coordinates_benign_removal')
    upstream = ROOT / 'upstream'
    ns = {'torch': torch, 'copy': copy}
    oracle_avg = source_function(upstream / 'Fed_train.py', 'fedavg', ns)
    ns['fedavg'] = oracle_avg
    oracle_step = source_function(upstream / 'Fed_Unlearn_attack.py', 'unlearning_step_once', ns)
    class Mini(torch.nn.Module):
        def __init__(self, values, count):
            super().__init__(); self.weight = torch.nn.Parameter(torch.tensor(values, dtype=torch.float32))
            self.register_buffer('num_batches_tracked', torch.tensor(count))
    og, ng = Mini([0, 0], 0), Mini([1, 1], 2)
    old = [Mini([3, 4], 5), Mini([-4, 3], 7)]
    new = [Mini([7, 9], 3), Mini([-7, 7], 5)]
    result, clients = core.fed_eraser_step([m.state_dict() for m in old], [m.state_dict() for m in new], og.state_dict(), ng.state_dict())
    oracle, oracle_clients = oracle_step(old, new, og, ng, SimpleNamespace(aggregation_method='fedavg'))
    assert torch.equal(result['weight'], torch.tensor([.5, 4.5]))
    for key in result:
        assert torch.equal(result[key], oracle.state_dict()[key]), key
    for a, b in zip(clients, oracle_clients):
        assert all(torch.equal(a[k], b.state_dict()[k]) for k in a)
    zero, _ = core.fed_eraser_step([old[0].state_dict()], [ng.state_dict()], og.state_dict(), ng.state_dict())
    assert all(torch.equal(zero[k], ng.state_dict()[k]) for k in zero)
    passed.append('original_FedEraser_AST_exact_and_independent_3_4_5_geometry_zero_direction_BN_cast')
    for constructor, classes in [(model_reference.ResNet18, 10), (model_reference.ResNet18_201, 201)]:
        model = constructor().cpu().eval()
        with torch.no_grad():
            output = model(torch.zeros(2, 3, 32, 32))
        assert output.shape == (2, classes) and bool(torch.isfinite(output).all())
    passed.append('recovered_direct_source_ResNet10_201_strict_CPU_output_shapes')
    model = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(12, 3)).eval()
    for p in model.parameters():
        p.requires_grad_(False)
    old_model = {k: v.clone() for k, v in model.state_dict().items()}
    trigger = torch.zeros(1, 3, 2, 2, requires_grad=True)
    opt = torch.optim.RAdam([trigger], lr=.1)
    loss = core.trigger_step(model, torch.full((4, 3, 2, 2), .4), torch.tensor([2] * 4), trigger, opt, 32 / 255)
    assert torch.count_nonzero(trigger) > 0 and opt.state
    assert all(torch.equal(old_model[k], v) for k, v in model.state_dict().items())
    passed.append('real_projected_STG_RAdam_step_finite_optimizer_and_frozen_surrogate')
    report = {'state': 'passed', 'CPU_only': True, 'contracts': passed, 'count': len(passed),
              'source_hashes': json.loads((ROOT / 'CORE_FREEZE.json').read_text())['files'],
              'corrected_SSS_sample_N': 64, 'shuffled_rank_matches': 64,
              'original_R03_audit_rerun': False, 'real_FL_FU_trained': False,
              'FedUBA_performance_reproduced': False, 'D08_D15_unresolved': True}
    with (ROOT / 'CORE_CPU_RESULT.json').open('x', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, indent=2); f.write('\n')
    print(json.dumps({'state': 'passed', 'contracts': len(passed), 'CPU_only': True}))


if __name__ == '__main__':
    main()
