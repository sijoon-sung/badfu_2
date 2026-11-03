"""Metadata-only binding; pre and benign are reused evidence, never re-inferred."""
import hashlib,importlib.metadata,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):h.update(block)
    return h.hexdigest()
def checked(m):
    path=Path(m['path']);assert path.is_absolute() and sha(path)==m['sha256'],str(path)
    if 'bytes' in m:assert path.stat().st_size==m['bytes']
def source_profile():
    p=read(ROOT/'SOURCE_PROFILE.json');assert not p['launch_enabled'] and ROOT==Path(p['execution_root'])
    for n,d in read(ROOT/'SOURCE_FREEZE.json')['files'].items():assert sha(ROOT/n)==d,n
    assert list(sys.version_info[:3])==p['python_version']
    for n,v in p['package_versions'].items():assert importlib.metadata.version(n)==v
    return p
def require_published_run():
    p=source_profile();pub=read(ROOT/'RUN_PUBLICATION.json')
    assert pub['state']=='published_actual_positive_new_attack_eval_review_before_queries'
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json') and pub['run_freeze_sha256']==sha(ROOT/'EVAL_RUN_FREEZE.json')
    for n,d in read(ROOT/'EVAL_RUN_FREEZE.json')['files'].items():assert sha(ROOT/n)==d,n
    binding=read(ROOT/'INPUT_BINDING.json')
    for m in binding['receipts'].values():checked(m)
    for m in binding['source_models'].values():checked(m)
    assert binding['new_models_inference']==['attack'] and binding['pre_benign_evidence_reused_not_reinferred']
    return p,read(ROOT/'EVAL_LAUNCH_PROFILE.json')
