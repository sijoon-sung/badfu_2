"""One declared full20R paired-FU branch, only after actual case/STG/SSS gates."""
import argparse
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
from runtime_common import ROOT, read, write, sha, save, guard, freeze_check


def checked(meta, payload_key):
    path = Path(meta['path']); path = path if path.is_absolute() else ROOT / path
    assert sha(path) == meta['sha256']
    value = torch.load(path, map_location='cpu', weights_only=True)
    return value if payload_key is None else value[payload_key]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--branch', choices=['benign', 'attack'], required=True)
    parser.add_argument('--catalog-root', type=Path, required=True)
    parser.add_argument('--case-id', required=True)
    args = parser.parse_args()
    freeze_check('FU_RUN_FREEZE.json')
    p = read(ROOT / 'FU_LAUNCH_PROFILE.json')
    assert p['launch_enabled'] and args.case_id == p['required_clean_case_id']
    assert read(ROOT / 'FU_ENGINE_CPU_RESULT.json')['state'] == 'passed'
    assert read(ROOT / 'FU_POLICY_CPU_RESULT.json')['state'] == 'passed'
    selection, audited = read(ROOT / 'SSS_RESULT.json'), read(ROOT / 'SSS_VERIFIED.json')
    assert audited['state'] == 'passed' and audited['SSS_result_sha256'] == sha(ROOT / 'SSS_RESULT.json')
    assert selection['case_id'] == args.case_id and selection['selected_by_owner'] == audited['selected_by_owner']
    selected_case = json.loads(subprocess.check_output([sys.executable, '-u', str(args.catalog_root / 'select_case.py'),
                    args.case_id, '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected_case['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selected_case['server_inputs']['pre']['sha256'] == selection['pre_checkpoint']['sha256']
    assert sha(ROOT / 'clean_fl/MANIFEST.json') == p['history_manifest_sha256']
    assert read(ROOT / 'CLEAN_FL_VERIFIED.json')['state'] == 'passed'
    original = read(ROOT / 'clean_fl/MANIFEST.json')
    assert len(original['rounds']) == 20
    if args.branch == 'attack':
        assert read(ROOT / 'FU_benign_VERIFIED.json')['state'] == 'passed'
    resources = guard(read(ROOT / 'GPU_PREFLIGHT_RESULT.json')['foundation_free_min_MiB'])
    with (ROOT / f'FU_{args.branch}_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid(), 'started_unix': time.time(), 'case_id': args.case_id, 'guard': resources}, stream)
    out = ROOT / 'fu' / args.branch; out.mkdir(parents=True, exist_ok=False)
    def event(**data):
        with (out / 'events.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
            stream.write(json.dumps({'time_unix': time.time(), **data}, allow_nan=False) + '\n'); stream.flush()
    write(out / 'CASE_SELECTION.json', selected_case)
    torch.set_num_threads(1); torch.backends.cudnn.benchmark = False
    parts = read(ROOT / 'CLEAN_SPLIT.json')['indices']
    assert sha(ROOT / 'CLEAN_SPLIT.json') == read(ROOT / 'CLEAN_FL_READY.json')['split_sha256']
    selected = owned_selection(parts, {int(k): v for k, v in selection['selected_by_owner'].items()}, [5, 7], 125)
    delta = checked(selection['delta'], selection['delta']['payload_key'])
    data_root = read(ROOT / 'CLEAN_FL_PROFILE.json')['data_root']
    train = CIFAR10(data_root, train=True, download=False, transform=transforms.Compose([
          transforms.RandomCrop(32, padding=4), transforms.RandomHorizontalFlip(),
          transforms.ToTensor(), transforms.Normalize((.5,) * 3, (.5,) * 3)]))
    new_global = checked(original['fresh_initial'], p['history_global_payload_key'])
    incoming = save(out / 'initial.pt', new_global); incoming['payload_key'] = None
    manifest = {'profile': p['id'], 'branch': args.branch, 'case_id': args.case_id,
                'SSS_result_sha256': sha(ROOT / 'SSS_RESULT.json'), 'initial': incoming,
                'original_history_manifest_sha256': p['history_manifest_sha256'], 'rounds': []}
    model = model_reference.ResNet18().cuda()
    total_batches = 0
    for record in original['rounds']:
        freeze_check('FU_RUN_FREEZE.json')
        r, clients = record['round'], record['clients']
        assert len(clients) == len(set(clients)) == 10
        old_global = checked(record['incoming'], p['history_global_payload_key'])
        old_metadata = {item['client']: item['checkpoint'] for item in record['roles']}
        assert set(old_metadata) == set(clients)
        old_states = {c: checked(old_metadata[c], p['history_role_payload_key']) for c in clients}
        trained, new_metadata, roles = {}, {}, []
        for client in clients:
            model.load_state_dict(new_global, strict=True)
            dataset = branch_dataset(train, parts[client], selected[client], delta, args.branch)
            indices = [i for i in parts[client] if args.branch == 'attack' or i not in set(selected[client])]
            schedule = local_schedule(r, client, len(dataset))
            def epoch_event(v):
                event(kind='local_epoch', branch=args.branch, round=r, client=client, **v)
                write(ROOT / f'FU_{args.branch}_STATE.json', {'state': 'training', 'pid': os.getpid(),
                      'round': r, 'rounds': r - 1, 'client': client, 'epoch': v['epoch'],
                      'cumulative_role_batches': v['cumulative_role_batches'], 'examples': v['examples'],
                      'updated_unix': time.time()})
            value = train_role(model, dataset, indices, schedule, 'cuda', epoch_event)
            value.update(branch=args.branch, round=r, client=client, incoming_new_global=incoming,
                         incoming_old_global=record['incoming'], original_local=old_metadata[client],
                         selected_source_ids=selected[client], delta=selection['delta'],
                         SSS_result_sha256=sha(ROOT / 'SSS_RESULT.json'))
            meta = save(out / 'trained' / f'round{r:02d}_client{client:02d}.pt', value)
            meta['payload_key'] = 'model'
            trained[client], new_metadata[client] = value['model'], meta
            total_batches += value['batches']
            roles.append({'client': client, 'checkpoint': meta, 'source_N': len(dataset), 'batches': value['batches']})
        after, effective, calibrated, reused = calibration_round(r, clients, [5, 7], old_states, trained, old_global, new_global)
        calibrated_records = []
        for client in clients:
            assert all(bool(torch.isfinite(v).all()) for v in calibrated[client].values())
            meta = save(out / 'calibrated' / f'round{r:02d}_client{client:02d}.pt', calibrated[client]); meta['payload_key'] = None
            calibrated_records.append({'client': client, 'checkpoint': meta,
                'effective_source': old_metadata[client] if client in reused else new_metadata[client],
                'effective_kind': 'original_first_round_nonowner' if client in reused else 'new_trained'})
        model.load_state_dict(after, strict=True)
        meta = save(out / 'rounds' / f'round{r:02d}.pt', after); meta['payload_key'] = None
        stored = checked(meta, None)
        assert all(torch.equal(stored[k], after[k]) for k in after)
        manifest['rounds'].append({'round': r, 'clients': clients, 'weights': [.1] * 10,
                'incoming_new_global': incoming, 'incoming_old_global': record['incoming'],
                'trained_roles': roles, 'calibrated_roles': calibrated_records,
                'original_first_round_nonowners_reused': reused, 'after': meta, 'actual_cumulative_batches': total_batches})
        write(out / 'MANIFEST.json', manifest)
        event(kind='round_commit', round=r, actual_cumulative_batches=total_batches, original_roles_reused=reused)
        write(ROOT / f'FU_{args.branch}_STATE.json', {'state': 'round_committed', 'pid': os.getpid(),
              'rounds': r, 'actual_cumulative_batches': total_batches, 'updated_unix': time.time()})
        new_global, incoming = after, meta
    final = save(out / 'after.pt', new_global); final['payload_key'] = None
    if args.branch == 'attack':
        assert total_batches == 20000
    result = {'state': 'completed_FU20', 'branch': args.branch, 'profile': p['id'], 'rounds': 20,
              'new_trained_roles': 200, 'actual_local_epochs': 1000, 'actual_batches': total_batches,
              'after': final, 'delta': selection['delta'], 'SSS_result_sha256': sha(ROOT / 'SSS_RESULT.json'),
              'history_manifest_sha256': sha(out / 'MANIFEST.json'), 'performance_not_yet_evaluated': True,
              'FedUBA_attack_completed': False}
    write(ROOT / f'FU_{args.branch}_RESULT.json', result)
    write(ROOT / f'FU_{args.branch}_STATE.json', {'state': 'completed_FU20', 'pid': os.getpid(), 'rounds': 20, 'updated_unix': time.time()})
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        # Branch argument is recorded even for a preflight failure; original outputs stay intact.
        branch = sys.argv[sys.argv.index('--branch') + 1] if '--branch' in sys.argv else 'unknown'
        write(ROOT / f'FU_{branch}_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
