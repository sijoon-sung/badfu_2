"""One local verified extraction/CPU check; original export receipt stays unchanged."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import traceback
import zipfile
sys.dont_write_bytecode = True
import torch
from runtime_common import ROOT, read, write, sha, freeze_check

DEST = Path('C:/Users/sijoo/Documents/ChatGPT/badFU/CHECKPOINTS_FOR_REVIEW/FedUBA_cleanFL20_s42_20261031')


def import_checked(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def main():
    freeze_check('CLEAN_RECEIVE_FREEZE.json')
    assert not (ROOT / 'CLEAN_REVIEW_LOCAL_COMPLETE.json').exists()
    receipt = read(ROOT / 'CLEAN_REVIEW_DELIVERY_REMOTE.json')
    archive = ROOT / 'CLEAN_REVIEW_DELIVERY.zip'
    assert receipt['state'] == 'exported_verified_normal_review'
    assert archive.stat().st_size == receipt['archive_bytes'] and sha(archive) == receipt['archive_sha256']
    dest = DEST.resolve()
    assert dest.parent == Path('C:/Users/sijoo/Documents/ChatGPT/badFU/CHECKPOINTS_FOR_REVIEW').resolve()
    dest.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as zipped:
        for item in zipped.infolist():
            target = (dest / item.filename).resolve()
            assert target.is_relative_to(dest) and not item.is_dir()
            target.parent.mkdir(parents=True, exist_ok=True)
            with zipped.open(item) as source, target.open('xb') as output:
                shutil.copyfileobj(source, output)
    assert sha(dest / 'DELIVERY_MANIFEST.json') == receipt['manifest_sha256']
    assert sha(dest / 'DELIVERY_SEAL.json') == receipt['seal_sha256']
    manifest = read(dest / 'DELIVERY_MANIFEST.json')
    assert manifest['case_id'] == receipt['case_id'] and len(manifest['files']) == receipt['payload_file_count']
    for name, meta in manifest['files'].items():
        path = (dest / name).resolve()
        assert path.is_relative_to(dest) and sha(path) == meta['sha256'] and path.stat().st_size == meta['bytes']
    for path in dest.rglob('*'):
        if path.is_file(): path.chmod(0o444)
    loader = import_checked(dest / 'load_checkpoint.py', 'local_clean_delivery_guard')
    guard = loader.verify(dest, receipt['manifest_sha256'])
    architecture = import_checked(dest / 'model_reference.py', 'local_clean_model_reference')
    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    checks = []
    for meta in manifest['payloads']:
        value = torch.load(dest / meta['file'], map_location='cpu', weights_only=True)
        state = value if meta['payload_key'] is None else value[meta['payload_key']]
        assert all(v.device.type == 'cpu' and bool(torch.isfinite(v).all()) for v in state.values())
        model = architecture.ResNet18().cpu().eval(); model.load_state_dict(state, strict=True)
        with torch.inference_mode():
            output = model(torch.zeros(1, 3, 32, 32))
            assert output.shape == (1, 10) and bool(torch.isfinite(output).all())
        if meta['payload_key']:
            assert value['optimizer']['state'] and len(value['rng']['torch_CUDA']) == 1 and value['rng']['torch_CPU'].numel()
            assert all(bool(torch.isfinite(v['momentum_buffer']).all()) for v in value['optimizer']['state'].values())
        checks.append({'file': meta['file'], 'sha256': meta['sha256'], 'payload_key': meta['payload_key'], 'strict_CPU_finite_forward': True})
    assert len(checks) == receipt['tensor_payload_count'] and not torch.cuda.is_initialized()
    # All verification evidence is outside the sealed packet; source export flags remain historical.
    local = {'state': 'local_delivery_complete', 'case_id': receipt['case_id'], 'packet_root': str(dest),
             'archive_sha256': receipt['archive_sha256'], 'archive_bytes': receipt['archive_bytes'],
             'manifest_sha256': receipt['manifest_sha256'], 'seal_sha256': receipt['seal_sha256'],
             'packet_total_files': receipt['packet_total_files'], 'payload_file_count': len(manifest['files']),
             'guard': guard, 'CPU_only': True, 'payload_checks': checks,
             'local_delivery_complete': True, 'catalogue_registered': False, 'FedUBA_attack_completed': False,
             'original_export_receipt_modified': False}
    write(ROOT / 'CLEAN_REVIEW_LOCAL_COMPLETE.json', local)
    print(json.dumps(local))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'CLEAN_REVIEW_LOCAL_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
