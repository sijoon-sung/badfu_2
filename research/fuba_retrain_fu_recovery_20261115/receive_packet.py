"""Local stdlib-only archive/manifest verification after authenticated transfer."""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import zipfile
from verify_payload import verify


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    root=Path(__file__).resolve().parent;delivery=root/'delivery'
    seal=json.loads((delivery/'SEAL.json').read_text());archive=delivery/'FUBA_RETRAIN_FU_RECOVERY_20261115.zip'
    assert archive.stat().st_size==seal['archive_bytes'] and digest(archive)==seal['archive_sha256']
    payload=delivery/'payload';assert not payload.exists()
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist();names=[i.filename for i in entries];assert len(names)==len(set(names))
        raw=z.read('REVIEW_MANIFEST.json');assert hashlib.sha256(raw).hexdigest()==seal['manifest_sha256']
        manifest=json.loads(raw);assert set(names)==set(manifest['files'])|{'REVIEW_MANIFEST.json'}
        payload.mkdir();base=payload.resolve()
        for item in entries:
            target=(base/item.filename).resolve()
            assert target.is_relative_to(base) and not stat.S_ISLNK(item.external_attr>>16)
            assert not item.is_dir() and not target.exists()
            target.parent.mkdir(parents=True,exist_ok=True)
            with z.open(item) as src,target.open('xb') as dst:shutil.copyfileobj(src,dst)
    proof=verify(payload,seal['manifest_sha256'])
    assert digest(root/'verify_payload.py')==digest(payload/'verify_payload.py')
    result={'state':'passed','archive_sha256':seal['archive_sha256'],'manifest_sha256':seal['manifest_sha256'],
            'files':proof['files'],'all_sizes_and_hashes_verified':True,'payload_root':str(payload),
            'torch_loads':0,'local_catalogue_pending':True,'full_paper_reproduced':False}
    with (root/'LOCAL_DELIVERY.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
