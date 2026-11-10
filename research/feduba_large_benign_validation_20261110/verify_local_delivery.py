"""Byte-only local receipt; no torch imports, payload loads or inference."""
import hashlib
import json
import argparse
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parent


def digest(stream):
    h = hashlib.sha256()
    size = 0
    while chunk := stream.read(8 * 1024 * 1024):
        h.update(chunk)
        size += len(chunk)
    return h.hexdigest(), size


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seal', default='REVIEW_SEAL.json')
    parser.add_argument('--manifest', default='REVIEW_MANIFEST.json')
    parser.add_argument('--receipt', default='LOCAL_DELIVERY_VERIFIED.json')
    args = parser.parse_args()
    out = ROOT / 'remote_results'
    seal = json.loads((out / args.seal).read_bytes())
    manifest_bytes = (out / args.manifest).read_bytes()
    manifest = json.loads(manifest_bytes)
    archive = out / seal['file']
    with archive.open('rb') as f:
        actual_sha, actual_size = digest(f)
    assert actual_sha == seal['sha256'] and actual_size == seal['bytes']
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist()) == len(set(z.namelist()))
        assert set(z.namelist()) == set(manifest['files']) | {'REVIEW_MANIFEST.json'}
        assert z.read('REVIEW_MANIFEST.json') == manifest_bytes
        for name, expected in manifest['files'].items():
            with z.open(name) as f:
                value, size = digest(f)
            assert value == expected['sha256'] and size == expected['bytes'], name
        checks = json.loads(z.read('STORAGE_CHECKS.json'))
        assert checks['model_forward_calls'] == checks['GPU_calls'] == 0
        typed = checks['checks']
        assert len(typed) == manifest['typed_payloads'] == seal['typed_payloads']
        assert {v['path'] for v in typed} == {n for n in manifest['files'] if n.endswith('.pt')}
        assert all(v['strict_cpu_load'] and v['finite'] for v in typed)
        for v in typed:
            assert v['sha256'] == manifest['files'][v['path']]['sha256']
    assert len(manifest['files']) == seal['files']
    receipt = dict(state='passed', archive=str(archive.resolve()),
                   sha256=actual_sha, bytes=actual_size, files=seal['files'],
                   all_manifest_bytes_verified=True, typed_payloads=len(typed),
                   DISLAB_strict_CPU_finite_checks_bound=True,
                   local_torch_loads=0, local_model_forward_calls=0,
                   packet_scope=manifest['scope'])
    (ROOT / args.receipt).write_bytes(
        (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({k: v for k, v in receipt.items() if k != 'packet_scope'}))


if __name__ == '__main__':
    main()
