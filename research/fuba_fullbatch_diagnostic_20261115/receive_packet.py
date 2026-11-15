"""Local full-archive transfer verification; no training or inference."""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import zipfile

ROOT=Path(__file__).resolve().parent


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def verify(payload,expected):
    manifest=payload/'REVIEW_MANIFEST.json';assert sha(manifest)==expected
    files=json.loads(manifest.read_text(encoding='utf-8'))['files']
    base=payload.resolve()
    for name,item in files.items():
        p=(base/name).resolve();assert p.is_relative_to(base) and p.is_file()
        assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'],name
    return files


def main():
    for name,digest in json.loads((ROOT/'LOCAL_TOOLS_FREEZE.json').read_text())['files'].items():
        assert sha(ROOT/name)==digest,name
    delivery=ROOT/'delivery';seal=json.loads((delivery/'SEAL.json').read_text())
    archive=delivery/'FUBA_FULLBATCH_DIAGNOSTIC_20261115.zip'
    assert sha(archive)==seal['archive_sha256'] and archive.stat().st_size==seal['archive_bytes']
    payload=delivery/'payload';assert not payload.exists()
    with zipfile.ZipFile(archive) as z:
        items=z.infolist();names=[x.filename for x in items];assert len(names)==len(set(names))
        raw=z.read('REVIEW_MANIFEST.json');assert hashlib.sha256(raw).hexdigest()==seal['manifest_sha256']
        files=json.loads(raw)['files'];assert set(names)==set(files)|{'REVIEW_MANIFEST.json'}
        payload.mkdir();base=payload.resolve()
        for item in items:
            p=(base/item.filename).resolve()
            assert p.is_relative_to(base) and not item.is_dir() and not stat.S_ISLNK(item.external_attr>>16)
            p.parent.mkdir(parents=True,exist_ok=True)
            with z.open(item) as a,p.open('xb') as b:shutil.copyfileobj(a,b)
    files=verify(payload,seal['manifest_sha256'])
    result={'state':'passed','files':len(files),'archive_sha256':seal['archive_sha256'],
            'manifest_sha256':seal['manifest_sha256'],'all_hashes_and_sizes_verified':True,
            'model_loads':0,'new_inference':0,'control_retraining':False}
    with (ROOT/'LOCAL_DELIVERY.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
