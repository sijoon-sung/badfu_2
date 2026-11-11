"""Verify a received review packet by bytes, without opening model payloads."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent


def check(stream):
    digest=hashlib.sha256(); n=0
    while b:=stream.read(8*1024*1024):
        digest.update(b);n+=len(b)
    return dict(sha256=digest.hexdigest(),bytes=n)


def main():
    seal=json.loads((ROOT/'ROUND_REVIEW_SEAL.json').read_bytes())
    data=(ROOT/'ROUND_REVIEW_MANIFEST.json').read_bytes();manifest=json.loads(data)
    assert hashlib.sha256(data).hexdigest()==seal['manifest_sha256']
    archive=ROOT/seal['file']
    with archive.open('rb') as f: assert check(f)=={k:seal[k] for k in ('sha256','bytes')}
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist())==len(manifest['files'])+1
        assert set(z.namelist())==set(manifest['files'])|{'ROUND_REVIEW_MANIFEST.json'}
        assert z.read('ROUND_REVIEW_MANIFEST.json')==data
        for n,meta in manifest['files'].items():
            with z.open(n) as f:assert check(f)==meta,n
    assert seal['model_payloads']==sum(n.endswith('.pt') for n in manifest['files'])==13
    receipt=dict(state='passed',sha256=seal['sha256'],bytes=seal['bytes'],files=len(manifest['files']),model_payloads=13,
                 all_manifest_bytes_verified=True,local_tensor_loads=0,local_model_forwards=0)
    (ROOT/'LOCAL_ROUND_REVIEW_VERIFIED.json').write_bytes((json.dumps(receipt,indent=2)+'\n').encode())
    print(json.dumps(receipt))


if __name__=='__main__':main()
