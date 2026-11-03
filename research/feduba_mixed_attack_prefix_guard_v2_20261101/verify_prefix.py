"""Independent CPU audit of 4 committed rounds and six stored round-5 roles."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import json
import math
from pathlib import Path
import time
import traceback
from audit_common import ROOT, OLD, FOUNDATION, read, sha, once, progress, published_inputs


def main():
    profile, binding, preserved, original, selected_case, memory = published_inputs()
    once('AUDIT_ONCE.json', {'pid': os.getpid(), 'time_unix': time.time()})
    import torch
    from torch.utils.data import DataLoader
    import model_reference
    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    strict = model_reference.ResNet18().cpu().eval()
    checked_models = 0
    checked_files = {}

    def finite(value):
        if isinstance(value, torch.Tensor):
            assert value.device.type == 'cpu' and bool(torch.isfinite(value).all())
        elif isinstance(value, dict):
            for item in value.values(): finite(item)
        elif isinstance(value, (list, tuple)):
            for item in value: finite(item)

    def equal(a, b):
        if isinstance(a, torch.Tensor): return isinstance(b, torch.Tensor) and torch.equal(a, b)
        if isinstance(a, dict): return isinstance(b, dict) and a.keys() == b.keys() and all(equal(a[k], b[k]) for k in a)
        if isinstance(a, (list, tuple)): return isinstance(b, (list, tuple)) and len(a) == len(b) and all(equal(x, y) for x, y in zip(a, b))
        return a == b

    def load(meta, key=None, model=False):
        nonlocal checked_models
        path = Path(meta['path']); path = path if path.is_absolute() else OLD / path
        path = path.resolve()
        assert any(path.is_relative_to(Path(root).resolve()) for root in profile['allowed_tensor_roots'])
        assert sha(path) == meta['sha256'] and path.stat().st_size == meta['bytes'], str(path)
        value = torch.load(path, map_location='cpu', weights_only=True)
        finite(value)
        checked_files[str(path)] = meta['sha256']
        value = value if key is None else value[key]
        if model:
            strict.load_state_dict(value, strict=True); checked_models += 1
        return value

    p = read(OLD / 'FU_LAUNCH_PROFILE.json')
    manifest = read(OLD / 'fu/attack/MANIFEST.json')
    selection = read(OLD / 'SSS_RESULT.json')
    assert manifest['branch'] == 'attack' and manifest['case_id'] == profile['case_id']
    assert len(manifest['rounds']) == 4 and len(original['rounds']) == 20
    assert manifest['SSS_result_sha256'] == sha(OLD / 'SSS_RESULT.json')
    assert selection['trigger_binding_sha256'] == p['trigger_binding_sha256'] == sha(OLD / 'TRIGGER_SOURCE_BINDING.json')
    parts = read(FOUNDATION / 'CLEAN_SPLIT.json')['indices']
    assert sha(FOUNDATION / 'CLEAN_SPLIT.json') == read(OLD / 'CLEAN_FL_READY.json')['split_sha256']
    assert len(parts) == 20 and sorted(sum(parts, [])) == list(range(50000))
    selected = {int(k): v for k, v in selection['selected_by_owner'].items()}
    assert set(selected) == {5, 7} and sum(map(len, selected.values())) == 125
    for owner, ids in selected.items(): assert len(ids) == len(set(ids)) and set(ids).issubset(parts[owner])
    current = load(manifest['initial'], model=True)
    initial = load(original['fresh_initial'], p['history_global_payload_key'], model=True)
    assert equal(current, initial)
    incoming = manifest['initial']
    expected_events = {}
    roles = epochs = batches = 0
    role_metadata = []

    def check_role(meta, r, client, historical, old_meta):
        nonlocal roles, epochs, batches, checked_models
        value = load(meta)
        assert value['branch'] == 'attack' and value['round'] == r and value['client'] == client
        assert value['incoming_new_global'] == incoming and value['incoming_old_global'] == historical['incoming']
        assert value['original_local'] == old_meta[client]
        assert value['delta'] == selection['delta'] and value['SSS_result_sha256'] == manifest['SSS_result_sha256']
        indices, chosen = parts[client], selected.get(client, [])
        expected_batches = math.ceil(len(indices) / 128) * 5
        assert value['source_indices'] == indices and value['selected_source_ids'] == chosen
        assert len(indices) == 2500 and expected_batches == value['batches'] == 100
        seed = 42 + 500000 + r * 10000 + client * 100
        schedule = {'seed': seed, 'epochs': 5, 'batch_size': 128, 'expected_batches': 100,
                    'lr': .01 * (1 + math.cos(math.pi * (r - 1) / 20)) / 2}
        assert value['schedule'] == schedule
        strict.load_state_dict(value['model'], strict=True); checked_models += 1
        optimizer = value['optimizer']
        assert len(optimizer['param_groups']) == 1
        group = optimizer['param_groups'][0]
        assert group['lr'] == schedule['lr'] and group['momentum'] == .9 and group['weight_decay'] == 0
        assert group['dampening'] == 0 and not group['nesterov'] and not group['maximize']
        parameters = list(strict.parameters())
        assert len(group['params']) == len(parameters) and set(optimizer['state']) == set(group['params'])
        for ident, parameter in zip(group['params'], parameters):
            state = optimizer['state'][ident]
            assert set(state) == {'momentum_buffer'}
            assert state['momentum_buffer'].shape == parameter.shape and state['momentum_buffer'].dtype == parameter.dtype
        for key in current:
            if 'num_batches_tracked' in key:
                assert torch.equal(value['model'][key], current[key] + expected_batches)
        assert len(value['epochs']) == 5
        previous = None
        for e, local in enumerate(value['epochs'], 1):
            assert local['epoch'] == e and local['examples'] == 2500 and local['batches'] == 20
            assert local['cumulative_role_batches'] == e * 20 and math.isfinite(local['loss'])
            generator = torch.Generator().set_state(local['loader_rng_before_epoch'])
            order = torch.cat(list(DataLoader(torch.arange(2500), batch_size=128, shuffle=True,
                                             generator=generator, num_workers=0)))
            assert torch.equal(local['source_ids'], torch.tensor(indices)[order])
            assert torch.equal(local['loader_rng'], generator.get_state())
            assert len(local['rng']['torch_CUDA']) == len(local['rng_before_epoch']['torch_CUDA']) == 1
            if previous:
                assert equal(local['rng_before_epoch'], previous['rng'])
                assert torch.equal(local['loader_rng_before_epoch'], previous['loader_rng'])
            else:
                seeded = torch.Generator().manual_seed(seed).get_state()
                assert torch.equal(local['loader_rng_before_epoch'], seeded)
                assert torch.equal(local['rng_before_epoch']['torch_CPU'], seeded)
            expected_events[(r, client, e)] = {k: local[k] for k in ['examples', 'batches', 'cumulative_role_batches', 'loss']}
            previous = local; epochs += 1
        assert equal(value['rng'], previous['rng']) and torch.equal(value['loader_rng'], previous['loader_rng'])
        assert len(value['edge_batches']) == 2
        for edge, e, b, n in zip(value['edge_batches'], [1, 5], [1, 20], [128, 68]):
            assert edge['epoch'] == e and edge['batch'] == b
            assert edge['x'].shape == (n, 3, 32, 32) and edge['x'].dtype == torch.float32
            assert edge['labels'].shape == (n,) and edge['labels'].dtype == torch.int64
            assert bool(((edge['labels'] >= 0) & (edge['labels'] < 10)).all())
            recorded = value['epochs'][e-1]['source_ids']
            assert torch.equal(edge['source_ids'], recorded[:128] if e == 1 else recorded[-68:])
        roles += 1; batches += expected_batches
        role_metadata.append({'round': r, 'client': client, 'checkpoint': meta})
        progress({'state': 'auditing_saved_attack_prefix', 'pid': os.getpid(), 'roles': roles,
                  'epochs': epochs, 'batches': batches, 'last_round': r, 'last_client': client})
        return value['model']

    for row, historical in zip(manifest['rounds'], original['rounds']):
        r, clients = row['round'], row['clients']
        assert r == historical['round'] and clients == historical['clients'] and row['weights'] == [.1] * 10
        assert row['incoming_new_global'] == incoming and row['incoming_old_global'] == historical['incoming']
        old_global = load(historical['incoming'], p['history_global_payload_key'], model=True)
        old_meta = {item['client']: item['checkpoint'] for item in historical['roles']}
        trained_meta = {item['client']: item['checkpoint'] for item in row['trained_roles']}
        calibrated_meta = {item['client']: item for item in row['calibrated_roles']}
        assert list(trained_meta) == list(calibrated_meta) == clients
        reused = [c for c in clients if r == 1 and c not in [5, 7]]
        assert row['original_first_round_nonowners_reused'] == reused
        new_states = []
        for client in clients:
            trained = check_role(trained_meta[client], r, client, historical, old_meta)
            original_state = load(old_meta[client], p['history_role_payload_key'], model=True)
            effective = original_state if client in reused else trained
            detail = calibrated_meta[client]
            assert detail['effective_source'] == (old_meta[client] if client in reused else trained_meta[client])
            assert detail['effective_kind'] == ('original_first_round_nonowner' if client in reused else 'new_trained')
            expected = {}
            for key in current:
                old_difference = original_state[key] - old_global[key]
                new_difference = effective[key] - current[key]
                length = torch.linalg.vector_norm(old_difference.float().reshape(-1), ord=2)
                scale = torch.linalg.vector_norm(new_difference.float().reshape(-1), ord=2)
                direction = new_difference if float(scale) == 0 else new_difference / scale
                expected[key] = (current[key] + length * direction).to(current[key].dtype)
            calibrated = load(detail['checkpoint'], model=True)
            assert equal(calibrated, expected)
            new_states.append(calibrated)
        averaged = {}
        for key in current:
            value = torch.zeros_like(current[key])
            for state in new_states: value.add_(state[key])
            averaged[key] = new_states[-1][key].clone() if 'num_batches_tracked' in key else value / 10
        after = load(row['after'], model=True)
        assert equal(after, averaged) and row['actual_cumulative_batches'] == batches
        incoming, current = row['after'], after
    assert (roles, epochs, batches) == (40, 200, 4000)
    historical = original['rounds'][4]
    clients = historical['clients']
    saved_clients = {int(Path(n).stem.rsplit('client', 1)[1])
                     for n in preserved['all_original_prefix_files']
                     if n.startswith('fu/attack/trained/round05_client')}
    assert len(saved_clients) == 6 and set(clients[:6]) == saved_clients and clients[6] == 10
    old_meta = {item['client']: item['checkpoint'] for item in historical['roles']}
    partial = []
    for client in clients[:6]:
        relative = f'fu/attack/trained/round05_client{client:02d}.pt'
        anchor = preserved['all_original_prefix_files'][relative]
        meta = {'path': relative, 'sha256': anchor['sha256'], 'bytes': anchor['bytes'], 'payload_key': 'model'}
        check_role(meta, 5, client, historical, old_meta); partial.append({'client': client, 'checkpoint': meta})
    assert not (OLD / 'fu/attack/trained/round05_client10.pt').exists()
    assert (roles, epochs, batches) == (46, 230, 4600)
    events = [json.loads(line) for line in (OLD / 'fu/attack/events.jsonl').read_text(encoding='utf-8').splitlines()]
    locals_ = [v for v in events if v['kind'] == 'local_epoch']
    keys = [(v['round'], v['client'], v['epoch']) for v in locals_]
    unsaved = {(5, 10, e) for e in range(1, 6)}
    assert len(keys) == len(set(keys)) == 235 and set(keys) == set(expected_events) | unsaved
    for event in locals_:
        key = (event['round'], event['client'], event['epoch'])
        if key in expected_events:
            assert {k: event[k] for k in expected_events[key]} == expected_events[key]
        else:
            assert event['examples'] == 2500 and event['batches'] == 20 and event['cumulative_role_batches'] == event['epoch'] * 20
    commits = [v for v in events if v['kind'] == 'round_commit']
    assert len(commits) == 4 and [v['round'] for v in commits] == [1, 2, 3, 4]
    assert [v['actual_cumulative_batches'] for v in commits] == [1000, 2000, 3000, 4000]
    assert not torch.cuda.is_initialized()
    result = {'state': 'passed_new_CPU_attack_prefix46_audit', 'CPU_only': True, 'threads': 1,
              'committed_rounds': 4, 'committed_roles': 40, 'partial_round5_saved_roles': 6,
              'saved_roles': roles, 'saved_epochs': epochs, 'saved_batches': batches,
              'original_event_epochs': 235, 'uncommitted_unsaved_client10_epochs': 5,
              'uncommitted_unsaved_client10_batches': 100,
              'all_4R_calibration_and_aggregation_exact': True, 'all_saved_role_source_ID_optimizer_RNG_checked': True,
              'momentum_shapes_and_BN_counters_checked': True, 'edge_input_ID_shapes_checked': True,
              'raw_augmentation_independently_replayed': False, 'all_SGD_gradients_independently_recomputed': False,
              'forward_calls': 0, 'backward_calls': 0, 'optimizer_steps': 0, 'strict_model_loads': checked_models,
              'checked_tensor_file_hashes': checked_files, 'round4_incoming_for_resume': incoming,
              'partial_round5_role_metadata': partial, 'prefix_preserved_sha256': binding['external_files']['PREFIX_PRESERVED.json']['sha256'],
              'input_binding_sha256': profile['input_binding_sha256'], 'new_training_launched': False,
              'memory_guard_before_model_loads': memory,
              'GPU_resume_still_requires_separate_profile_freeze_publication': True,
              'overall_goal_complete': False, 'D08_D15_detection_validated': False}
    once('AUDIT_RESULT.json', result)
    progress({'state': result['state'], 'pid': os.getpid(), 'roles': roles, 'epochs': epochs, 'batches': batches})
    print(json.dumps({k: result[k] for k in ['state', 'saved_roles', 'saved_epochs', 'saved_batches', 'forward_calls']}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        once('AUDIT_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
