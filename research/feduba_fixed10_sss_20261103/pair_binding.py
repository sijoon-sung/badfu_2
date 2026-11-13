"""New fixed10 victim source/actual binding; model-free until the published SSS run."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
FOUNDATION=Path('D:/FEDUBA_FIXED10_FOUNDATION_20261103')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    return h.hexdigest()
def checked(meta):
    p=Path(meta['path']);p=p if p.is_absolute() else ROOT/p
    assert sha(p)==meta['sha256'],str(p)
    if 'bytes' in meta:assert p.stat().st_size==meta['bytes']
    return p
def source_profile():
    p=read(ROOT/'SOURCE_PROFILE.json')
    assert p['launch_enabled'] is False and ROOT==Path(p['execution_root'])
    assert FOUNDATION==Path(p['foundation_root'])
    assert list(sys.version_info[:3])==p['python_version']
    for n,v in p['package_versions'].items():assert importlib.metadata.version(n)==v
    for n,d in read(ROOT/'SOURCE_FREEZE.json')['files'].items():assert sha(ROOT/n)==d,n
    return p
def require_published_run():
    p=source_profile();pub=read(ROOT/'RUN_PUBLICATION.json')
    assert pub['state']=='published_actual_fixed10_newSSS_before_queries'
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json') and pub['run_freeze_sha256']==sha(ROOT/'RUN_FREEZE.json')
    for n,d in read(ROOT/'RUN_FREEZE.json')['files'].items():assert sha(ROOT/n)==d,n
    a=read(ROOT/'LAUNCH_PROFILE.json')
    assert a['launch_enabled'] is True and a['case_id']==p['normal_case_id'] and a['new_SSS_samples']==5000
    binding=read(ROOT/'FOUNDATION_INPUT_BINDING.json')
    for meta in binding['receipts'].values():checked(meta)
    checked(binding['pre']);checked(binding['split'])
    return p,a
def foundation_history():return read(FOUNDATION/'clean_fl/MANIFEST.json')
