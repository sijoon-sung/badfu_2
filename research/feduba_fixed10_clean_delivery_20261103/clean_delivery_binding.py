"""New normal packet source/actual binding; no model reads here."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(65536),b''):h.update(b)
    return h.hexdigest()
def source_profile():
    p=read(ROOT/'SOURCE_PROFILE.json')
    assert p['launch_enabled'] is False and ROOT==Path(p['execution_root'])
    assert list(sys.version_info[:3])==p['python_version']
    for n,v in p['package_versions'].items():assert importlib.metadata.version(n)==v
    for n,d in read(ROOT/'SOURCE_FREEZE.json')['files'].items():assert sha(ROOT/n)==d,n
    return p
def require_published_run():
    p=source_profile();pub=read(ROOT/'RUN_PUBLICATION.json')
    assert pub['state']=='published_actual_fixed10_clean_review_before_export'
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json') and pub['run_freeze_sha256']==sha(ROOT/'RUN_FREEZE.json')
    for n,d in read(ROOT/'RUN_FREEZE.json')['files'].items():assert sha(ROOT/n)==d,n
    a=read(ROOT/'LAUNCH_PROFILE.json')
    assert a['launch_enabled'] is True and a['case_id']==p['normal_case_id'] and a['CPU_zero1_calls']==3
    return p,a
