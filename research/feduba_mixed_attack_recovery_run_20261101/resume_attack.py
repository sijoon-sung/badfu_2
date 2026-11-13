"""Continue the same mixed attack: reference 46 stored roles, compute only 154."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import torch
from torchvision import transforms
from torchvision.datasets import CIFAR10
import model_reference
from fu_core import owned_selection, branch_dataset, calibration_round, local_schedule
from fu_training import train_role
from pair_binding import foundation_history, require_published_run
from recovery_io import ROOT, OLD, CPU, FOUNDATION, read, write, once, sha, save, guard, freeze_check, tensor_path


def checked(meta, payload_key=None):
    path = tensor_path(meta)
    assert sha(path) == meta['sha256'] and path.stat().st_size == meta['bytes']
    value = torch.load(path, map_location='cpu', weights_only=True)
    return value if payload_key is None else value[payload_key]


def main():
    require_published_run(); freeze_check('FU_RUN_FREEZE.json')
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog-root', type=Path, required=True)
    parser.add_argument('--case-id', required=True)
    args = parser.parse_args()
    launch = read(ROOT / 'LAUNCH_PROFILE.json')
    p = read(ROOT / 'FU_LAUNCH_PROFILE.json')
    assert args.case_id == p['required_clean_case_id'] == launch['case_id']
    assert read(ROOT / 'FU_ENGINE_CPU_RESULT.json')['state'] == 'passed'
    assert read(ROOT / 'FU_POLICY_CPU_RESULT.json')['state'] == 'passed'
    audit = read(CPU / 'AUDIT_RESULT.json')
    assert audit['state'] == 'passed_new_CPU_attack_prefix46_audit'
    assert (audit['saved_roles'], audit['saved_epochs'], audit['saved_batches']) == (46, 230, 4600)
    assert sha(CPU / 'AUDIT_RESULT.json') == launch['CPU_result_sha256']
    selection, sss_audit = read(ROOT / 'SSS_RESULT.json'), read(ROOT / 'SSS_VERIFIED.json')
    assert sss_audit['state'] == 'passed' and sss_audit['SSS_result_sha256'] == sha(ROOT / 'SSS_RESULT.json')
    assert selection['trigger_binding_sha256'] == sss_audit['trigger_binding_sha256'] == p['trigger_binding_sha256']
    assert sha(ROOT / 'TRIGGER_SOURCE_BINDING.json') == p['trigger_binding_sha256']
    assert read(ROOT / 'FU_benign_VERIFIED.json')['state'] == 'passed'
    selected_case = json.loads(subprocess.check_output([sys.executable, '-B', str(args.catalog_root / 'select_case.py'),
                    args.case_id, '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected_case['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selected_case['server_inputs']['pre']['sha256'] == selection['pre_checkpoint']['sha256']
    original = foundation_history()
    failed = read(OLD / 'fu/attack/MANIFEST.json')
    assert sha(OLD / 'fu/attack/MANIFEST.json') == launch['original_attack_manifest_sha256']
    assert len(failed['rounds']) == 4 and len(original['rounds']) == 20
    assert failed['rounds'][-1]['after'] == audit['round4_incoming_for_resume']
    partial = audit['partial_round5_role_metadata']
    assert [v['client'] for v in partial] == original['rounds'][4]['clients'][:6]
    partial_meta = {v['client']: v['checkpoint'] for v in partial}
    assert original['rounds'][4]['clients'][6] == 10
    assert not (OLD / 'fu/attack/trained/round05_client10.pt').exists()
    resources = guard(4000)
    once('RECOVERY_ATTACK_ONCE.json', {'pid': os.getpid(), 'started_unix': time.time(),
          'case_id': args.case_id, 'guard': resources, 'reused_roles': 46, 'new_roles': 154})
    out = ROOT / 'fu/attack'; out.mkdir(parents=True, exist_ok=False)
    write(out / 'CASE_SELECTION.json', selected_case)
    kept, excluded, kept_epochs, kept_commits = [], [], 0, 0
    source_events = OLD / 'fu/attack/events.jsonl'
    for line in source_events.read_bytes().splitlines(keepends=True):
        v = json.loads(line)
        keep = (v['kind'] == 'round_commit' and v['round'] <= 4) or (v['kind'] == 'local_epoch' and
            (v['round'] <= 4 or (v['round'] == 5 and v['client'] in partial_meta)))
        if keep:
            kept.append(line)
            kept_epochs += int(v['kind'] == 'local_epoch'); kept_commits += int(v['kind'] == 'round_commit')
        else:
            assert v['kind'] == 'local_epoch' and v['round'] == 5 and v['client'] == 10
            excluded.append(v)
    assert (kept_epochs, kept_commits, len(excluded)) == (230, 4, 5)
    assert [v['epoch'] for v in excluded] == [1, 2, 3, 4, 5]
    with (out / 'events.jsonl').open('xb') as stream:
        for line in kept: stream.write(line)
        stream.flush(); os.fsync(stream.fileno())
    origins = {'original_events_path': str(source_events), 'original_events_sha256': sha(source_events),
               'reused_epoch_events': 230, 'reused_round_commits': 4, 'excluded_unsaved_role_events': excluded,
               'excluded_events_are_preserved_in_original_raw': True, 'original_files_modified': False}
    write(ROOT / 'private_inputs/EVENT_ORIGINS.json', origins)

    def event(**data):
        with (out / 'events.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps({'time_unix': time.time(), **data}, allow_nan=False) + '\n'); stream.flush()

    torch.set_num_threads(1); torch.backends.cudnn.benchmark = False
    parts = read(FOUNDATION / 'CLEAN_SPLIT.json')['indices']
    assert sha(FOUNDATION / 'CLEAN_SPLIT.json') == read(ROOT / 'CLEAN_FL_READY.json')['split_sha256']
    selected = owned_selection(parts, {int(k): v for k, v in selection['selected_by_owner'].items()}, [5, 7], 125)
    delta = checked(selection['delta'], selection['delta']['payload_key'])
    data_root = read(ROOT / 'CLEAN_FL_PROFILE.json')['data_root']
    train = CIFAR10(data_root, train=True, download=False, transform=transforms.Compose([
        transforms.RandomCrop(32, padding=4), transforms.RandomHorizontalFlip(),
        transforms.ToTensor(), transforms.Normalize((.5,) * 3, (.5,) * 3)]))
    new_global = checked(audit['round4_incoming_for_resume'])
    incoming = audit['round4_incoming_for_resume']
    manifest = {'profile': launch['id'], 'branch': 'attack', 'case_id': args.case_id,
        'SSS_result_sha256': sha(ROOT / 'SSS_RESULT.json'), 'initial': copy.deepcopy(failed['initial']),
        'original_history_manifest_sha256': p['history_manifest_sha256'], 'rounds': copy.deepcopy(failed['rounds']),
        'recovery_source': {'original_manifest_path': str(OLD / 'fu/attack/MANIFEST.json'),
            'original_manifest_sha256': launch['original_attack_manifest_sha256'],
            'CPU_result_sha256': launch['CPU_result_sha256'], 'reused_roles': 46,
            'new_roles_expected': 154, 'original_unsaved_physical_batches': 100}}
    write(out / 'MANIFEST.json', manifest)
    model = model_reference.ResNet18().cuda()
    write(ROOT / 'TRAIN_RUNTIME_OBSERVATION.json', {'torch_version': str(torch.__version__),
          'device': torch.cuda.get_device_name(0), 'CPU_threads': torch.get_num_threads(),
          'matmul_TF32': torch.backends.cuda.matmul.allow_tf32,
          'cudnn_TF32': torch.backends.cudnn.allow_tf32,
          'cudnn_benchmark': torch.backends.cudnn.benchmark,
          'cudnn_deterministic': torch.backends.cudnn.deterministic,
          'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
          'float32_matmul_precision': torch.get_float32_matmul_precision(),
          'AMP_used': False, 'old_unrecorded_getters_or_unsaved_role_bit_identity_certified': False})
    total_batches, executed_roles, executed_batches, reused_roles = 4000, 0, 0, 40
    for record in original['rounds'][4:]:
        freeze_check('FU_RUN_FREEZE.json')
        r, clients = record['round'], record['clients']
        assert len(clients) == len(set(clients)) == 10
        old_global = checked(record['incoming'], p['history_global_payload_key'])
        old_metadata = {item['client']: item['checkpoint'] for item in record['roles']}
        assert set(old_metadata) == set(clients)
        old_states = {c: checked(old_metadata[c], p['history_role_payload_key']) for c in clients}
        trained, new_metadata, roles = {}, {}, []
        for client in clients:
            if r == 5 and client in partial_meta:
                meta = partial_meta[client]; value = checked(meta)
                assert value['incoming_new_global'] == incoming and value['incoming_old_global'] == record['incoming']
                assert value['round'] == 5 and value['client'] == client and value['branch'] == 'attack'
                assert value['source_indices'] == parts[client] and value['selected_source_ids'] == selected[client]
                assert value['schedule'] == local_schedule(r, client, 2500) and value['batches'] == 100
                assert value['delta'] == selection['delta'] and value['SSS_result_sha256'] == sha(ROOT / 'SSS_RESULT.json')
                reused_roles += 1; origin = 'reused_original_saved_round5_role'
            else:
                model.load_state_dict(new_global, strict=True)
                dataset = branch_dataset(train, parts[client], selected[client], delta, 'attack')
                indices = list(parts[client]); schedule = local_schedule(r, client, len(dataset))

                def epoch_event(v):
                    event(kind='local_epoch', branch='attack', round=r, client=client, **v)
                    write(ROOT / 'FU_attack_STATE.json', {'state': 'training_recovery', 'pid': os.getpid(),
                          'round': r, 'rounds': r - 1, 'client': client, 'epoch': v['epoch'],
                          'cumulative_role_batches': v['cumulative_role_batches'], 'examples': v['examples'],
                          'executed_here_roles_completed': executed_roles,
                          'executed_here_batches_before_role': executed_batches, 'updated_unix': time.time()})

                value = train_role(model, dataset, indices, schedule, 'cuda', epoch_event)
                value.update(branch='attack', round=r, client=client, incoming_new_global=incoming,
                    incoming_old_global=record['incoming'], original_local=old_metadata[client],
                    selected_source_ids=selected[client], delta=selection['delta'],
                    SSS_result_sha256=sha(ROOT / 'SSS_RESULT.json'))
                meta = save(out / 'trained' / f'round{r:02d}_client{client:02d}.pt', value)
                meta['payload_key'] = 'model'
                executed_roles += 1; executed_batches += value['batches']; origin = 'new_recovery_training'
            trained[client], new_metadata[client] = value['model'], meta
            total_batches += value['batches']
            roles.append({'client': client, 'checkpoint': meta, 'source_N': 2500, 'batches': value['batches'], 'origin': origin})
        after, effective, calibrated, reused = calibration_round(r, clients, [5, 7], old_states, trained, old_global, new_global)
        assert not reused
        calibrated_records = []
        for client in clients:
            assert all(bool(torch.isfinite(v).all()) for v in calibrated[client].values())
            meta = save(out / 'calibrated' / f'round{r:02d}_client{client:02d}.pt', calibrated[client]); meta['payload_key'] = None
            calibrated_records.append({'client': client, 'checkpoint': meta,
                'effective_source': new_metadata[client], 'effective_kind': 'new_trained'})
        model.load_state_dict(after, strict=True)
        meta = save(out / 'rounds' / f'round{r:02d}.pt', after); meta['payload_key'] = None
        stored = checked(meta)
        assert all(torch.equal(stored[k], after[k]) for k in after)
        manifest['rounds'].append({'round': r, 'clients': clients, 'weights': [.1] * 10,
            'incoming_new_global': incoming, 'incoming_old_global': record['incoming'],
            'trained_roles': roles, 'calibrated_roles': calibrated_records,
            'original_first_round_nonowners_reused': [], 'after': meta, 'actual_cumulative_batches': total_batches})
        write(out / 'MANIFEST.json', manifest)
        event(kind='round_commit', round=r, actual_cumulative_batches=total_batches, original_roles_reused=[])
        write(ROOT / 'FU_attack_STATE.json', {'state': 'round_committed', 'pid': os.getpid(), 'rounds': r,
              'effective_cumulative_batches': total_batches, 'executed_here_roles': executed_roles,
              'executed_here_batches': executed_batches, 'updated_unix': time.time()})
        new_global, incoming = after, meta
    assert (reused_roles, executed_roles, executed_batches, total_batches) == (46, 154, 15400, 20000)
    final = save(out / 'after.pt', new_global); final['payload_key'] = None
    result = {'state': 'completed_FU20', 'branch': 'attack', 'profile': launch['id'], 'rounds': 20,
        'new_trained_roles': 200, 'actual_local_epochs': 1000, 'actual_batches': total_batches,
        'legacy_count_fields_describe_effective_saved_history': True,
        'reused_original_roles': 46, 'executed_here_roles': 154, 'executed_here_epochs': 770,
        'executed_here_batches': 15400, 'original_failed_unsaved_epochs': 5, 'original_failed_unsaved_batches': 100,
        'total_physical_epochs_including_original_failure': 1005, 'total_physical_batches_including_original_failure': 20100,
        'after': final, 'delta': selection['delta'], 'SSS_result_sha256': sha(ROOT / 'SSS_RESULT.json'),
        'history_manifest_sha256': sha(out / 'MANIFEST.json'), 'performance_not_yet_evaluated': True,
        'trigger_binding_sha256': p['trigger_binding_sha256'], 'FedUBA_attack_completed': False,
        'recovery_input_binding_sha256': sha(ROOT / 'RECOVERY_INPUT_BINDING.json'),
        'CPU_prefix_result_sha256': launch['CPU_result_sha256'],
        'event_origins_sha256': sha(ROOT / 'private_inputs/EVENT_ORIGINS.json')}
    write(ROOT / 'FU_attack_RESULT.json', result)
    write(ROOT / 'FU_attack_STATE.json', {'state': 'completed_FU20_recovery', 'pid': os.getpid(), 'rounds': 20,
          'executed_here_roles': 154, 'executed_here_batches': 15400, 'updated_unix': time.time()})
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'FU_attack_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
