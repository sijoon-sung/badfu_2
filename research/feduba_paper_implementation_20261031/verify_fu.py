"""Independent full branch CPU state/optimizer/RNG/ID/history/calibration audit."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import argparse
import json
import math
import traceback
import torch
from torch.utils.data import DataLoader
import model_reference
from runtime_common import ROOT, read, write, sha, freeze_check


def load(meta, key=None):
    from pathlib import Path
    path = Path(meta['path']); path = path if path.is_absolute() else ROOT / path
    assert sha(path) == meta['sha256']
    value = torch.load(path, map_location='cpu', weights_only=True)
    return value if key is None else value[key]


def finite(value):
    if isinstance(value, torch.Tensor):
        assert value.device.type == 'cpu' and bool(torch.isfinite(value).all())
    elif isinstance(value, dict):
        for item in value.values(): finite(item)
    elif isinstance(value, (list, tuple)):
        for item in value: finite(item)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--branch', choices=['benign', 'attack'], required=True)
    branch = parser.parse_args().branch
    freeze_check('FU_RUN_FREEZE.json')
    with (ROOT / f'FU_{branch}_AUDIT_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid()}, stream)
    torch.set_num_threads(1)  # Same declared CPU reduction order; no core helper is called.
    assert not torch.cuda.is_initialized()
    p, result = read(ROOT / 'FU_LAUNCH_PROFILE.json'), read(ROOT / f'FU_{branch}_RESULT.json')
    assert result['state'] == 'completed_FU20' and result['branch'] == branch
    out = ROOT / 'fu' / branch
    assert sha(out / 'MANIFEST.json') == result['history_manifest_sha256']
    assert sha(ROOT / 'clean_fl/MANIFEST.json') == p['history_manifest_sha256']
    manifest, original = read(out / 'MANIFEST.json'), read(ROOT / 'clean_fl/MANIFEST.json')
    assert len(manifest['rounds']) == len(original['rounds']) == 20
    assert manifest['SSS_result_sha256'] == sha(ROOT / 'SSS_RESULT.json')
    parts = read(ROOT / 'CLEAN_SPLIT.json')['indices']
    selected = {int(k): v for k, v in read(ROOT / 'SSS_RESULT.json')['selected_by_owner'].items()}
    assert set(selected) == {5, 7} and sum(map(len, selected.values())) == 125
    for owner, ids in selected.items():
        assert len(set(ids)) == len(ids) and set(ids).issubset(set(parts[owner]))
    current = load(manifest['initial'])
    initial = load(original['fresh_initial'], p['history_global_payload_key'])
    assert all(torch.equal(current[k], initial[k]) for k in current)
    incoming = manifest['initial']
    batches = roles = epochs = 0; expected_event_keys = set(); hashes = {}; reused_records = []
    model = model_reference.ResNet18().cpu().eval()
    for row, historical in zip(manifest['rounds'], original['rounds']):
        r, clients = row['round'], row['clients']
        assert r == historical['round'] and clients == historical['clients'] and row['weights'] == [.1] * 10
        assert row['incoming_new_global'] == incoming and row['incoming_old_global'] == historical['incoming']
        old_global = load(historical['incoming'], p['history_global_payload_key'])
        old_meta = {v['client']: v['checkpoint'] for v in historical['roles']}
        trained_meta = {v['client']: v['checkpoint'] for v in row['trained_roles']}
        calibrated_meta = {v['client']: v for v in row['calibrated_roles']}
        assert list(trained_meta) == list(calibrated_meta) == clients
        reused = [c for c in clients if r == 1 and c not in [5, 7]]
        assert row['original_first_round_nonowners_reused'] == reused
        if reused: reused_records.append({'round': r, 'clients': reused})
        new_states = []
        for client in clients:
            meta = trained_meta[client]
            value = load(meta); finite(value)
            assert value['branch'] == branch and value['round'] == r and value['client'] == client
            assert value['incoming_new_global'] == incoming and value['incoming_old_global'] == historical['incoming']
            assert value['original_local'] == old_meta[client]
            chosen = selected.get(client, [])
            indices = [i for i in parts[client] if branch == 'attack' or i not in set(chosen)]
            expected_batches = math.ceil(len(indices) / 128) * 5
            assert value['source_indices'] == indices and value['selected_source_ids'] == chosen
            assert value['batches'] == expected_batches and len(value['epochs']) == 5
            seed_value = 42 + 500000 + r * 10000 + client * 100
            assert value['schedule']['seed'] == seed_value
            group = value['optimizer']['param_groups'][0]
            assert group['momentum'] == .9 and group['weight_decay'] == 0
            assert group['lr'] == .01 * (1 + math.cos(math.pi * (r - 1) / 20)) / 2
            assert value['optimizer']['state'] and len(value['optimizer']['param_groups']) == 1
            model.load_state_dict(value['model'], strict=True)
            previous = None
            for e, local in enumerate(value['epochs'], 1):
                assert local['epoch'] == e and local['examples'] == len(indices)
                assert local['batches'] == math.ceil(len(indices) / 128)
                assert local['cumulative_role_batches'] == e * local['batches']
                assert math.isfinite(local['loss'])
                generator = torch.Generator().set_state(local['loader_rng_before_epoch'])
                order = torch.cat(list(DataLoader(torch.arange(len(indices)), batch_size=128, shuffle=True,
                                                 generator=generator, num_workers=0)))
                assert torch.equal(local['source_ids'], torch.tensor(indices)[order])
                assert torch.equal(local['loader_rng'], generator.get_state())
                assert len(local['rng']['torch_CUDA']) == len(local['rng_before_epoch']['torch_CUDA']) == 1
                if previous:
                    assert torch.equal(local['loader_rng_before_epoch'], previous['loader_rng'])
                    assert torch.equal(local['rng_before_epoch']['torch_CPU'], previous['rng']['torch_CPU'])
                    assert all(torch.equal(a, b) for a, b in zip(local['rng_before_epoch']['torch_CUDA'], previous['rng']['torch_CUDA']))
                else:
                    seeded = torch.Generator().manual_seed(seed_value).get_state()
                    assert torch.equal(local['loader_rng_before_epoch'], seeded)
                    assert torch.equal(local['rng_before_epoch']['torch_CPU'], seeded)
                expected_event_keys.add((r, client, e)); previous = local; epochs += 1
            assert [v['epoch'] for v in value['edge_batches']] == [1, 5]
            assert torch.equal(value['rng']['torch_CPU'], previous['rng']['torch_CPU'])
            original_state = load(old_meta[client], p['history_role_payload_key'])
            effective = original_state if client in reused else value['model']
            detail = calibrated_meta[client]
            assert detail['effective_source'] == (old_meta[client] if client in reused else meta)
            assert detail['effective_kind'] == ('original_first_round_nonowner' if client in reused else 'new_trained')
            expected_state = {}
            for key in current:
                old_difference = original_state[key] - old_global[key]
                new_difference = effective[key] - current[key]
                length = torch.linalg.vector_norm(old_difference.float().reshape(-1), ord=2)
                scale = torch.linalg.vector_norm(new_difference.float().reshape(-1), ord=2)
                direction = new_difference if float(scale) == 0 else new_difference / scale
                expected_state[key] = (current[key] + length * direction).to(current[key].dtype)
            saved_calibrated = load(detail['checkpoint'])
            assert all(torch.equal(saved_calibrated[k], expected_state[k]) for k in current)
            new_states.append(saved_calibrated)
            batches += expected_batches; roles += 1
            hashes[meta['path']] = meta['sha256']; hashes[detail['checkpoint']['path']] = detail['checkpoint']['sha256']
        averaged = {}
        for key in current:
            value = torch.zeros_like(current[key])
            for state in new_states: value.add_(state[key])
            averaged[key] = new_states[-1][key].clone() if 'num_batches_tracked' in key else value / 10
        after = load(row['after'])
        assert all(torch.equal(after[k], averaged[k]) for k in current)
        assert row['actual_cumulative_batches'] == batches
        incoming, current = row['after'], after
        hashes[incoming['path']] = incoming['sha256']
        write(ROOT / f'FU_{branch}_AUDIT_STATE.json', {'state': 'auditing', 'pid': os.getpid(),
              'rounds': r, 'checked_roles': roles, 'actual_epochs': epochs, 'actual_batches': batches})
    assert roles == result['new_trained_roles'] == 200 and epochs == result['actual_local_epochs'] == 1000
    assert batches == result['actual_batches']
    final = load(result['after'])
    assert all(torch.equal(final[k], current[k]) for k in current)
    events = [json.loads(line) for line in (out / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
    observed = [(v['round'], v['client'], v['epoch']) for v in events if v['kind'] == 'local_epoch']
    assert len(observed) == len(set(observed)) == 1000 and set(observed) == expected_event_keys
    assert len([v for v in events if v['kind'] == 'round_commit']) == 20
    assert not torch.cuda.is_initialized()
    write(ROOT / f'FU_{branch}_VERIFIED.json', {'state': 'passed', 'CPU_only': True, 'branch': branch,
          'rounds': 20, 'new_trained_roles': roles, 'actual_local_epochs': epochs, 'actual_batches': batches,
          'all_role_source_ID_permutations_optimizer_RNG_checked': True,
          'independent_all_effective_source_calibration_and_aggregation_exact': True,
          'original_first_round_submissions_reused': reused_records, 'history_hashes': hashes,
          'after': result['after'], 'performance_not_yet_evaluated': True,
          'all_local_SGD_gradients_independently_recomputed': False, 'FedUBA_attack_completed': False})
    print(json.dumps({'state': 'passed', 'branch': branch, 'roles': roles, 'actual_epochs': epochs, 'actual_batches': batches}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        import sys
        branch = sys.argv[sys.argv.index('--branch') + 1] if '--branch' in sys.argv else 'unknown'
        write(ROOT / f'FU_{branch}_AUDIT_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
