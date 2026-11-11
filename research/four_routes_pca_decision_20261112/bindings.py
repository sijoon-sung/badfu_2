"""Common metadata and catalogue mutations for this new validation only."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from checkpoint_guard import sha,verify

ROOT=Path(__file__).resolve().parent
FOUNDATION=Path('D:/FEDUBA_FIXED10_FOUNDATION_20261103')
CAT=Path('D:/TRAJECTORY_CATALOG_20261023')


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))


def write(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='\n') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    for attempt in range(40):
        try:
            os.replace(tmp,p);break
        except PermissionError:
            if attempt==39:raise
            time.sleep(.05)


def checked(meta):
    assert sha(meta['path'])==meta['sha256'],meta['path']
    if 'bytes' in meta:assert Path(meta['path']).stat().st_size==meta['bytes']


def absolute(value):
    if isinstance(value,dict):
        result={k:absolute(v) for k,v in value.items()}
        if 'path' in result and 'sha256' in result:
            p=Path(result['path'])
            assert not p.is_absolute() and p.parts[0] in ('clean_fl','private_assets')
            p=(FOUNDATION/p).resolve();assert p.is_relative_to(FOUNDATION.resolve());result['path']=str(p)
        return result
    if isinstance(value,list):return [absolute(v) for v in value]
    return value


def make_guard(name,case_id,files):
    root=ROOT/'guards'/name;root.mkdir(parents=True,exist_ok=False)
    loader=ROOT/'checkpoint_guard.py'
    files={**files,loader.name:dict(path=str(loader),sha256=sha(loader),bytes=loader.stat().st_size)}
    write(root/'GUARD_MANIFEST.json',dict(case_id=case_id,files=files))
    digest=sha(root/'GUARD_MANIFEST.json');write(root/'GUARD_SEAL.json',dict(manifest_sha256=digest))
    verify(root,digest)
    return dict(manifest_path=str(root/'GUARD_MANIFEST.json'),manifest_sha256=digest,
                seal_path=str(root/'GUARD_SEAL.json'),seal_sha256=sha(root/'GUARD_SEAL.json'),loader_path=str(loader))


def append_case(entry,name):
    original=(CAT/'catalog.json').read_bytes();before=json.loads(original)
    assert all(c['id']!=entry['id'] for c in before['cases'])
    after=json.loads(original);after['cases'].append(entry)
    audit=CAT/'audit'/('DELETION_ROUND_'+name+'_20261111.json')
    assert not audit.exists()
    write(audit,dict(previous_catalog_sha256=sha(CAT/'catalog.json'),entry=entry,
                     old_cases_and_defaults_preserved=True,new_default=False))
    after.setdefault('supplemental_audits',[]).append(dict(path='audit/'+audit.name,sha256=sha(audit)))
    assert after['cases'][:-1]==before['cases']
    for k in before:
        if k not in ('cases','supplemental_audits'):assert after[k]==before[k]
    assert (CAT/'catalog.json').read_bytes()==original,'Catalogue changed concurrently'
    write(CAT/'catalog.json',after)
    write(ROOT/('CATALOG_'+name+'.json'),dict(before_sha256=__import__('hashlib').sha256(original).hexdigest(),
                                           after_sha256=sha(CAT/'catalog.json'),old_cases=len(before['cases']),new_cases=len(after['cases']),
                                           old_cases_and_defaults_preserved=True,new_case_id=entry['id']))


def select(case_id,purpose):
    result=subprocess.run([sys.executable,str(CAT/'select_case.py'),case_id,'--purpose',purpose],
                          capture_output=True,encoding='utf-8',check=True)
    return json.loads(result.stdout)


def require_publication():
    pub=read(ROOT/'RUN_PUBLICATION.json')
    assert pub['all_raw_blob_bytes_verified']
    for name,digest in read(ROOT/'RUN_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest,name
    return read(ROOT/'PROFILE.json')
