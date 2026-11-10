"""Externally anchored references; metadata guards never load tensors."""
import hashlib
import json
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8<<20),b''):h.update(block)
    return h.hexdigest()


def verify(root, expected_manifest_sha256=None):
    root=Path(root)
    assert sha(root/'GUARD_MANIFEST.json')==expected_manifest_sha256
    seal=json.loads((root/'GUARD_SEAL.json').read_text(encoding='utf-8'))
    assert seal['manifest_sha256']==expected_manifest_sha256
    metadata=json.loads((root/'GUARD_MANIFEST.json').read_text(encoding='utf-8'))
    for name,item in metadata['files'].items():
        path=Path(item.get('path',root/name))
        assert path.stat().st_size==item['bytes'] and sha(path)==item['sha256'],name
    return metadata
