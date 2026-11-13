"""Separate target-class pair binding; original runs and kernels stay immutable."""
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
FOUNDATION = Path('D:/FEDUBA_PAPER_IMPLEMENTATION_20261031')


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''): h.update(block)
    return h.hexdigest()


def checked(meta):
    path = Path(meta['path']); assert sha(path) == meta['sha256'], str(path)
    if 'bytes' in meta: assert path.stat().st_size == meta['bytes']


def source_profile():
    p = read(ROOT / 'SOURCE_PROFILE.json')
    assert p['launch_enabled'] is False and ROOT == Path(p['execution_root'])
    for n, digest in read(ROOT / 'SOURCE_FREEZE.json')['files'].items(): assert sha(ROOT / n) == digest, n
    assert list(sys.version_info[:3]) == p['python_version']
    for n, version in p['package_versions'].items(): assert importlib.metadata.version(n) == version
    return p


def require_published_run():
    p = source_profile()
    pub = read(ROOT / 'RUN_PUBLICATION.json')
    assert pub['state'] == 'published_actual_targetclass_pair_before_training'
    assert pub['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
    assert pub['run_freeze_sha256'] == sha(ROOT / 'RUN_FREEZE.json')
    for n, digest in read(ROOT / 'RUN_FREEZE.json')['files'].items(): assert sha(ROOT / n) == digest, n
    launch = read(ROOT / 'LAUNCH_PROFILE.json')
    assert launch['launch_enabled'] is True and launch['selected_IDs'] == 125
    assert launch['selection_sha256'] == sha(ROOT / 'SSS_RESULT.json')
    assert launch['selection_audit_sha256'] == sha(ROOT / 'SSS_VERIFIED.json')
    assert read(ROOT / 'SSS_RESULT.json')['selection_scope'] == 'target_class2_only_global_top125_owner5_7'
    assert read(ROOT / 'SSS_RESULT.json')['selected_by_owner'] == read(ROOT / 'SSS_VERIFIED.json')['selected_by_owner']
    return p, launch


def foundation_history():
    p = source_profile(); meta = p['foundation_history_manifest']; checked(meta)
    original = read(meta['path']); assert len(original['rounds']) == 20
    def absolute(value):
        if isinstance(value, dict):
            out = {key: absolute(item) for key, item in value.items()}
            if 'path' in out and 'sha256' in out:
                relative = Path(out['path'])
                assert not relative.is_absolute() and relative.parts[0] in ['clean_fl', 'private_assets']
                resolved = (FOUNDATION / relative).resolve()
                assert resolved.is_relative_to(FOUNDATION.resolve())
                out['path'] = str(resolved)
            return out
        if isinstance(value, list): return [absolute(item) for item in value]
        return value
    return absolute(copy.deepcopy(original))
