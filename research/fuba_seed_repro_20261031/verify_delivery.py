"""Deliver one completed seed without changing its sealed packet or training run."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
from study_common import ROOT, read, sha, write, case_id


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--receipt', type=Path, required=True)
    p.add_argument('--archive', type=Path)
    p.add_argument('--source', type=Path)
    p.add_argument('--review-parent', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--local-cpu-check', action='store_true')
    args = p.parse_args()
    sys.dont_write_bytecode = True
    for name, digest in read(ROOT / 'DELIVERY_TOOLS_FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name
    assert args.seed in read(ROOT / 'PROFILE.json')['new_seeds']
    assert bool(args.archive) != bool(args.source)
    assert not args.output.exists(), 'Completed delivery receipt is preserved'
    receipt = read(args.receipt)
    assert receipt['case_id'] == case_id(args.seed)
    parent = args.review_parent.resolve()
    assert parent.name == 'CHECKPOINTS_FOR_REVIEW' and parent.is_dir()
    dest = parent / f'FUBA_seed_repro_MNIST_DBA_s{args.seed}_pre100_post_KD10'
    assert dest.resolve().parent == parent
    if args.archive:
        import zipfile
        assert sha(args.archive) == receipt['archive_sha256']
        assert args.archive.stat().st_size == receipt['archive_bytes']
        with zipfile.ZipFile(args.archive) as z:
            names = z.namelist()
            assert len(names) == len(set(names))
            for info in z.infolist():
                name = info.filename
                path = PurePosixPath(name)
                assert name and '\\' not in name and ':' not in name and not path.is_absolute()
                assert '..' not in path.parts and not stat.S_ISLNK(info.external_attr >> 16)
                assert (dest / name).resolve().is_relative_to(dest.resolve()), name
            if not dest.exists():
                dest.mkdir(exist_ok=False)
                z.extractall(dest)
    else:
        assert args.source.resolve() == Path(receipt['packet_root']).resolve()
        assert sha(args.source / 'DELIVERY_MANIFEST.json') == receipt['manifest_sha256']
        assert sha(args.source / 'DELIVERY_SEAL.json') == receipt['seal_sha256']
        if not dest.exists():
            shutil.copytree(args.source, dest)
    assert sha(dest / 'DELIVERY_MANIFEST.json') == receipt['manifest_sha256']
    assert sha(dest / 'DELIVERY_SEAL.json') == receipt['seal_sha256']
    manifest = read(dest / 'DELIVERY_MANIFEST.json')
    assert manifest['case_id'] == receipt['case_id']
    expected = set(manifest['files']) | {'DELIVERY_MANIFEST.json', 'DELIVERY_SEAL.json'}
    assert {f.relative_to(dest).as_posix() for f in dest.rglob('*') if f.is_file()} == expected
    for name, item in manifest['files'].items():
        target = (dest / name).resolve()
        assert target.is_relative_to(dest.resolve())
        assert sha(target) == item['sha256'] and target.stat().st_size == item['bytes'], name
    guard = load_module('delivered_seed_guard', dest / 'load_checkpoint.py')
    guard.verify(dest, receipt['manifest_sha256'])
    assert sha(dest / 'CPU_AUDIT_through0100.json') == receipt['full_CPU_audit_sha256']
    assert sha(dest / 'VERIFIED.json') == receipt['independent_verification_sha256']
    model_checks = []
    if args.local_cpu_check:
        import torch
        torch.set_num_threads(1)
        Net = load_module('delivered_seed_author_model', dest / 'author_model.py').Net
        model = Net().cpu().eval()
        sample = torch.stack([torch.zeros(1, 28, 28), torch.linspace(0, 1, 784).reshape(1, 28, 28)])

        def finite(value):
            if isinstance(value, torch.Tensor):
                assert value.device.type == 'cpu' and bool(torch.isfinite(value).all())
            elif isinstance(value, dict):
                for item in value.values():
                    finite(item)
            elif isinstance(value, (tuple, list)):
                for item in value:
                    finite(item)
            elif isinstance(value, float):
                assert math.isfinite(value)

        for name, keys in sorted(manifest['model_payloads'].items()):
            value = torch.load(dest / name, map_location='cpu', weights_only=True)
            finite(value)
            for key in keys:
                state = value
                if key != '$':
                    for part in key.split('/'):
                        state = state[int(part)] if isinstance(state, list) else state[part]
                model.load_state_dict(state, strict=True)
                with torch.inference_mode():
                    logits = model(sample)
                assert logits.shape == (2, 10) and bool(torch.isfinite(logits).all())
                model_checks.append({'path': name, 'payload_key': key, 'strict_CPU_finite_forward': True})
    for path in dest.rglob('*'):
        if path.is_file():
            path.chmod(path.stat().st_mode & ~stat.S_IWRITE)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, {'state': 'delivered_hash_verified', 'case_id': receipt['case_id'],
          'seed': args.seed, 'root': str(dest), 'manifest_sha256': receipt['manifest_sha256'],
          'seal_sha256': receipt['seal_sha256'], 'all_files_verified': len(expected),
          'copied_packet_readonly': True, 'full_raw_history_local': False,
          'remote_packet_CPU_payloads': len(read(dest / 'PACKET_CPU_CHECKS.json')['models']),
          'local_CPU_checks': model_checks, 'local_CPU_check_requested': args.local_cpu_check,
          'source_sha256': sha(Path(__file__)), 'numeric_run_modified': False})
    print(json.dumps({'state': 'delivered_hash_verified', 'case_id': receipt['case_id'],
                      'files': len(expected), 'local_CPU_payloads': len(model_checks)}))


if __name__ == '__main__':
    main()
