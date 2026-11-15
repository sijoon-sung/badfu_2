"""Export the new comparison after both complete numerical audits; originals stay put."""
import argparse
import json
from pathlib import Path
import shutil
import time
import zipfile
from run import ROOT, setup, read, write, sha, check, begin, load


def main():
    import torch
    p = setup()
    import model_reference
    assert read(ROOT / 'CONTROLLER.json')['state'] == 'completed'
    result = read(ROOT / 'RESULT.json')
    assert result['state'] == 'completed_comparison'
    assert read(ROOT / 'CURVE_RESULT.json')['state'] == 'passed_integrity'
    assert all(read(ROOT / ('AUDIT_' + b + '.json'))['state'] == 'passed' for b in ['benign', 'attack'])
    begin('export')
    out = ROOT / 'delivery'
    out.mkdir(exist_ok=False)
    evidence = ['PROFILE.json', 'PROTOCOL.txt', 'SCOPE.json', 'SOURCE_FREEZE.json', 'PREPARED.json',
                'TRAINED_benign.json', 'TRAINED_attack.json', 'AUDIT_benign.json', 'AUDIT_attack.json',
                'EVAL_primary.json', 'EVAL_independent.json', 'RESULT.json', 'CONTROLLER.json',
                'CURVE_PROTOCOL.txt', 'CURVE_FREEZE.json', 'CURVE_RESULT.json', 'FU_CURVES.png', 'PAPER_TARGETS.json']
    for name in evidence:
        shutil.copy2(ROOT / name, out / name)
    for branch in ['benign', 'attack']:
        shutil.copy2(ROOT / 'fu' / branch / 'epochs.jsonl', out / (branch + '_epochs.jsonl'))
    (out / 'source').mkdir()
    for name in ['run.py', 'verify.py', 'selection.py', 'test_selection.py', 'export_result.py', 'curve.py']:
        shutil.copy2(ROOT / name, out / 'source' / name)
    (out / 'source/kernels').mkdir()
    for name in p['external_sources']:
        shutil.copy2(Path(p['kernel_root']) / name, out / 'source/kernels' / name)
    model = model_reference.ResNet18().cpu().eval()
    cpu_checks = {}
    for name, metrics in result['metrics'].items():
        source = check(metrics['checkpoint'], ROOT)
        target = out / (name + '.pt')
        shutil.copy2(source, target)
        assert sha(target) == metrics['checkpoint']['sha256']
        state = torch.load(target, map_location='cpu', weights_only=True)
        model.load_state_dict(state, strict=True)
        with torch.inference_mode():
            logits = model(torch.zeros(1, 3, 32, 32))
        assert bool(torch.isfinite(logits).all())
        cpu_checks[name] = {'SHA256': sha(target), 'payload_key': None, 'strict_CPU_load': True,
                            'finite_zero_input_forward': True, 'performance_evaluation': False}
    delta = read(ROOT / 'private/SELECTION.json')['delta']
    shutil.copy2(check(delta), out / 'delta.pt')
    assert sha(out / 'delta.pt') == delta['sha256']
    write(out / 'PACKET_SCOPE.json', {'models': cpu_checks, 'delta_SHA256': delta['sha256'],
          'complete_local_epoch_logs': 2000, 'full_raw_400_role_optimizer_RNG_history': str(ROOT / 'fu'),
          'full_raw_history_in_this_packet': False, 'individual_SSS_IDs_and_queries_in_this_packet': False,
          'registered_as_default_input': False, 'full_paper_reproduced': False,
          'FU_semantics': result['FU_semantics'], 'time': time.time()})
    files = {file.relative_to(out).as_posix(): {'sha256': sha(file), 'bytes': file.stat().st_size}
             for file in sorted(out.rglob('*')) if file.is_file()}
    write(out / 'MANIFEST.json', files)
    seal = {'manifest_sha256': sha(out / 'MANIFEST.json'), 'files': len(files)}
    write(ROOT / 'DELIVERY_SEAL.json', seal)
    archive = ROOT / 'DELIVERY.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for file in sorted(out.rglob('*')):
            if file.is_file():
                z.write(file, file.relative_to(out).as_posix())
    # New packet verification, not a re-run of any former export/audit.
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        import hashlib
        for name, meta in files.items():
            assert hashlib.sha256(z.read(name)).hexdigest() == meta['sha256']
    write(ROOT / 'DELIVERY.json', {'state': 'completed', 'archive': {'path': str(archive), 'sha256': sha(archive),
          'bytes': archive.stat().st_size}, 'seal': seal, 'CPU_checks': cpu_checks, 'scope': 'three_endpoints_delta_epoch_logs_sources_receipts'})


if __name__ == '__main__':
    main()
