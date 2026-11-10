"""Metadata-only guard for an existing remote normal deletion endpoint."""
import hashlib
import json
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8<<20), b''): h.update(block)
    return h.hexdigest()


def verify(root, expected_manifest_sha256=None):
    root = Path(root)
    assert sha(root/'GUARD_MANIFEST.json') == expected_manifest_sha256
    m = json.loads((root/'GUARD_MANIFEST.json').read_text(encoding='utf-8'))
    for name, info in m['files'].items():
        p = Path(info.get('path', root/name))
        assert p.stat().st_size == info['bytes'] and sha(p) == info['sha256'], name
    return m
