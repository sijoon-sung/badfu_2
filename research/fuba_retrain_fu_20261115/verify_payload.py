"""Read-only hash guard for the remote review manifest or extracted local packet."""
import hashlib
import json
from pathlib import Path


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def verify(manifest_root,expected_manifest_sha256):
    root=Path(manifest_root).resolve();manifest=root/'MANIFEST.json'
    assert digest(manifest)==expected_manifest_sha256,'Manifest differs from external catalogue'
    info=json.loads(manifest.read_text(encoding='utf-8'))
    if (root/'after.pt').is_file():payload=root
    else:
        assert root.name=='delivery' and root.parent==Path(info['remote_root']).resolve()
        payload=root.parent
    for name,item in info['files'].items():
        p=(payload/name).resolve()
        assert p.is_relative_to(payload) and p.is_file(),name
        assert p.stat().st_size==item['bytes'] and digest(p)==item['sha256'],name
    return {'files':len(info['files']),'payload_root':str(payload),'state':'all_hashes_verified','model_loads':0}
