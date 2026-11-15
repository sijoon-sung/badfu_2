"""Verify an externally anchored input snapshot without loading tensors."""
import hashlib
import json
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def verify(root, expected):
    root = Path(root).resolve()
    manifest = root / 'REVIEW_MANIFEST.json'
    assert sha(manifest) == expected
    files = json.loads(manifest.read_text(encoding='utf-8'))['files']
    for name, record in files.items():
        path = (root / name).resolve()
        assert path.is_relative_to(root) and path.is_file()
        assert path.stat().st_size == record['bytes'] and sha(path) == record['sha256'], name
    return files
