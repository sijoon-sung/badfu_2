"""Readonly packet guard. Verify this loader's external hash before importing it."""
import hashlib
import json
from pathlib import Path
import stat


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 << 20), b''): h.update(block)
    return h.hexdigest()


def verify(root, expected_manifest_sha256):
    root = Path(root).resolve()
    path = root / 'DELIVERY_MANIFEST.json'
    assert digest(path) == expected_manifest_sha256
    value = json.loads(path.read_text(encoding='utf-8'))
    expected = set(value['files']) | {'DELIVERY_MANIFEST.json', 'DELIVERY_SEAL.json'}
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    assert actual == expected
    for name, meta in value['files'].items():
        target = (root / name).resolve()
        assert target.is_relative_to(root) and not (root / name).is_symlink()
        assert target.stat().st_size == meta['bytes'] and digest(target) == meta['sha256'], name
    for name in expected:
        target = root / name
        assert bool(target.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY), name
    seal = json.loads((root / 'DELIVERY_SEAL.json').read_text(encoding='utf-8'))
    assert seal['manifest_sha256'] == expected_manifest_sha256
    assert seal['case_id'] == value['case_id'] and seal['payload_file_count'] == len(value['files'])
    return {'state': 'passed', 'verified_payload_files': len(value['files']), 'all_readonly': True}
