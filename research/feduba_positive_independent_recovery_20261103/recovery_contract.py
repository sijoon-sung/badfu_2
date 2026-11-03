import hashlib,importlib.metadata,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def checked(m):
    p=Path(m['path']);assert p.is_absolute() and sha(p)==m['sha256'],str(p)
    if 'bytes' in m:assert p.stat().st_size==m['bytes']
def source_check():
    p=read(ROOT/'PROFILE.json');assert ROOT==Path(p['execution_root']) and p['launch_enabled']
    assert list(sys.version_info[:3])==p['python_version']
    for name,version in p['package_versions'].items():assert importlib.metadata.version(name)==version
    for name,digest in read(ROOT/'SOURCE_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest,name
    b=read(ROOT/'INPUT_BINDING.json')
    for m in b['inputs'].values():checked(m)
    old=Path(p['original_root']);assert not (old/'PAIR_EVAL_VERIFIED.json').exists() and not (old/'COMPLETION.json').exists()
    return p,b
def require_recovery_publication():
    p,b=source_check();pub=read(ROOT/'RUN_PUBLICATION.json')
    assert pub['state']=='published_actual_independent_writer_recovery_before_queries'
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json') and pub['run_freeze_sha256']==sha(ROOT/'RUN_FREEZE.json')
    assert len(pub['commit'])==40
    for name,digest in read(ROOT/'RUN_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest,name
    assert read(ROOT/'SOURCE_REVIEW_RESULT.json')['state']=='passed_source_only_recovery_review'
    term=read(ROOT/'UPSTREAM_TERMINAL_CHECK.json');assert term['state']=='old_tasks_terminal_expected_exits_and_native0'
    return p,b
