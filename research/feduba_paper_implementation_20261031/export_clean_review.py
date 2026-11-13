"""One finite CPU export of actual verified clean foundation; raw history is retained."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import traceback
import zipfile
import torch
sys.dont_write_bytecode = True
import model_reference
from runtime_common import ROOT, read, write, sha, freeze_check

PACKET = Path('D:/CHECKPOINTS_FOR_REVIEW/FedUBA_cleanFL20_s42_20261031')
CASE = 'feduba.paper.cifar10.cleanfl20.s42.20261031'


def main():
    freeze_check('CLEAN_EXPORT_FREEZE.json')
    assert read(ROOT / 'FOUNDATION_STATE.json')['state'] == 'completed_clean_FL_foundation_only'
    verified, result = read(ROOT / 'CLEAN_FL_VERIFIED.json'), read(ROOT / 'CLEAN_FL_RESULT.json')
    assert verified['state'] == 'passed' and verified['rounds'] == 20 and verified['roles'] == 200
    assert verified['actual_local_epoch_logs'] == 2000 and verified['actual_batches'] == 40000 and verified['independent_N'] == 10000
    assert verified['independent_clean_correct'] == result['evaluation']['clean_correct']
    with (ROOT / 'CLEAN_EXPORT_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid(), 'case_id': CASE}, stream)
    PACKET.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    manifest = read(ROOT / 'clean_fl/MANIFEST.json')
    ready = read(ROOT / 'CLEAN_FL_READY.json')
    assert len(manifest['rounds']) == 20
    last = manifest['rounds'][-1]['roles'][-1]
    payloads = {'run/before.pt': (result['before'], None), 'run/initial.pt': (ready['fresh_initial'], None),
                'run/last_role.pt': (last['checkpoint'], 'model')}
    for name, (meta, _) in payloads.items():
        source = ROOT / meta['path']
        assert sha(source) == meta['sha256']
        target = PACKET / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert sha(target) == meta['sha256']
    copies = ['CLEAN_FL_PROFILE.json','CLEAN_FL_PROTOCOL.txt','CLEAN_FL_FREEZE.json','CLEAN_FL_READY.json',
              'CLEAN_FL_RESULT.json','CLEAN_FL_VERIFIED.json','CLEAN_FL_STATE.json','CLEAN_FL_CONTROLLER_STATE.json',
              'FOUNDATION_STATE.json','FOUNDATION_ONCE.json','FOUNDATION_FREEZE.json','CLEAN_FL_STARTED.json',
              'CLEAN_SPLIT.json','clean_fl/MANIFEST.json','clean_fl/events.jsonl','clean_fl_console.log','foundation_console.log']
    for name in copies:
        target = PACKET / 'evidence' / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    for name in read(ROOT / 'FOUNDATION_FREEZE.json')['files']:
        target = PACKET / 'executed_code' / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    shutil.copyfile(ROOT / 'model_reference.py', PACKET / 'model_reference.py')
    shutil.copyfile(ROOT / 'review_loader.py', PACKET / 'load_checkpoint.py')
    for name in ['CLEAN_DELIVERY_PROTOCOL.txt', 'CLEAN_EXPORT_FREEZE.json', 'export_clean_review.py', 'review_loader.py']:
        target = PACKET / 'delivery_code' / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    checks = []
    for name, (meta, key) in payloads.items():
        value = torch.load(PACKET / name, map_location='cpu', weights_only=True)
        state = value if key is None else value[key]
        assert all(t.device.type == 'cpu' and bool(torch.isfinite(t).all()) for t in state.values())
        model = model_reference.ResNet18().cpu().eval(); model.load_state_dict(state, strict=True)
        with torch.inference_mode():
            output = model(torch.zeros(1, 3, 32, 32))
            assert output.shape == (1, 10) and bool(torch.isfinite(output).all())
        if key:
            assert value['epochs'] == 10 and value['batches'] == 200
            assert value['optimizer']['state'] and value['rng']['torch_CPU'].numel() and len(value['rng']['torch_CUDA']) == 1
            assert all(bool(torch.isfinite(v['momentum_buffer']).all()) for v in value['optimizer']['state'].values())
        checks.append({'file': name, 'sha256': meta['sha256'], 'payload_key': key, 'strict_CPU_finite_forward': True})
    assert not torch.cuda.is_initialized()
    write(PACKET / 'CPU_VERIFIED.json', {'state': 'passed', 'CPU_only': True, 'payloads': checks,
          'clean_correct': verified['independent_clean_correct'], 'CA_pct': verified['CA_pct'],
          'performance_source': 'original independent DISLAB10000 evaluation; this packet check is one-input forward only'})
    write(PACKET / 'DELIVERY_SCOPE.json', {'case_id': CASE, 'purpose': 'normal_clean_foundation_diagnostic_only',
          'actual_clean_rounds': 20, 'actual_original_roles': 200, 'packet_tensor_payloads': 3,
          'local_role_payloads': 1, 'last_role_client': last['client'],
          'last_role_original': last['checkpoint'], 'all_original_history_retained_at': str(ROOT / 'clean_fl'),
          'local_packet_includes_all200_role_tensors': False, 'all_epoch_logs_included': True,
          'actual_attack_or_post_unlearning_pair': False, 'default_BadFU_cases_changed': False})
    files = {p.relative_to(PACKET).as_posix(): {'sha256': sha(p), 'bytes': p.stat().st_size}
             for p in sorted(PACKET.rglob('*')) if p.is_file()}
    write(PACKET / 'DELIVERY_MANIFEST.json', {'case_id': CASE, 'files': files, 'payloads': checks})
    manifest_sha = sha(PACKET / 'DELIVERY_MANIFEST.json')
    write(PACKET / 'DELIVERY_SEAL.json', {'case_id': CASE, 'manifest_sha256': manifest_sha,
          'payload_file_count': len(files), 'kind': 'normal_foundation_not_FedUBA_attack_reproduction'})
    seal_sha = sha(PACKET / 'DELIVERY_SEAL.json')
    for path in PACKET.rglob('*'):
        if path.is_file(): path.chmod(0o444)
    spec = importlib.util.spec_from_file_location('new_clean_review_guard', PACKET / 'load_checkpoint.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    guard = module.verify(PACKET, manifest_sha)
    archive = ROOT / 'CLEAN_REVIEW_DELIVERY.zip'
    with archive.open('xb') as stream, zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as zipped:
        for path in sorted(PACKET.rglob('*')):
            if path.is_file(): zipped.write(path, path.relative_to(PACKET).as_posix())
    receipt = {'state': 'exported_verified_normal_review', 'case_id': CASE, 'packet_root': str(PACKET),
               'archive_path': str(archive), 'archive_sha256': sha(archive), 'archive_bytes': archive.stat().st_size,
               'manifest_sha256': manifest_sha, 'seal_sha256': seal_sha, 'payload_file_count': len(files),
               'packet_total_files': len(files) + 2, 'tensor_payload_count': 3, 'guard': guard,
               'pre': {'path': str(PACKET / 'run/before.pt'), 'sha256': result['before']['sha256'], 'payload_key': None},
               'local_delivery_complete': False, 'catalogue_registered': False, 'FedUBA_attack_completed': False}
    write(ROOT / 'CLEAN_REVIEW_DELIVERY_REMOTE.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'CLEAN_EXPORT_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
