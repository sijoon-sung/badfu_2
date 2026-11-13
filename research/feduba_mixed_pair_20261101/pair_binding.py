"""Explicit input roots and closed metadata gates for the new mixed-teacher pair."""
import copy
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def once(name, value):
    with (ROOT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def checked(meta):
    path = Path(meta['path'])
    assert sha(path) == meta['sha256'], str(path)
    if 'bytes' in meta: assert path.stat().st_size == meta['bytes'], str(path)


FOUNDATION = Path('D:/FEDUBA_PAPER_IMPLEMENTATION_20261031')


def source_profile():
    for name, digest in read(ROOT / 'SOURCE_FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name
    p = read(ROOT / 'SOURCE_PROFILE.json')
    assert p['launch_enabled'] is False and p['trigger_binding'] is None
    assert ROOT == Path(p['execution_root']) and FOUNDATION == Path(p['foundation_root'])
    assert list(sys.version_info[:3]) == p['python_version']
    for name, version in p['package_versions'].items():
        assert importlib.metadata.version(name) == version, name
    return p


class Unlaunched(RuntimeError): pass


def require_published_run():
    source = source_profile()
    if not (ROOT / 'PAIR_LAUNCH_PROFILE.json').exists():
        raise Unlaunched('Closed source-only pair: no actual trigger binding or profiles')
    publication = read(ROOT / 'PAIR_PUBLICATION.json')
    assert publication['state'] == 'published_actual_mixed_trigger_paired_profiles_before_execution'
    assert publication['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
    assert set(publication['profiles_and_freezes_sha256']) == {
        'SSS_LAUNCH_PROFILE.json', 'FU_LAUNCH_PROFILE.json', 'PAIR_EVAL_LAUNCH_PROFILE.json',
        'PAIR_LAUNCH_PROFILE.json', 'SSS_FREEZE.json', 'FU_RUN_FREEZE.json',
        'PAIR_EVAL_RUN_FREEZE.json', 'PAIR_RUN_FREEZE.json'}
    for name, digest in publication['profiles_and_freezes_sha256'].items():
        assert sha(ROOT / name) == digest, name
    for name, digest in read(ROOT / 'PAIR_RUN_FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name
    p = read(ROOT / 'PAIR_LAUNCH_PROFILE.json')
    assert p['launch_enabled'] is True and p['case_purpose'] == 'diagnostic'
    assert p['source_profile_sha256'] == sha(ROOT / 'SOURCE_PROFILE.json')
    for actual, template in [('SSS_LAUNCH_PROFILE.json', 'FU_PROFILE.json'),
                             ('FU_LAUNCH_PROFILE.json', 'FU_PROFILE.json'),
                             ('PAIR_EVAL_LAUNCH_PROFILE.json', 'PAIR_EVAL_PROFILE.json')]:
        profile, fixed = read(ROOT / actual), read(ROOT / template)
        assert profile['launch_enabled'] is True
        for key, value in fixed.items():
            if key not in ['id', 'launch_enabled', 'stage']: assert profile[key] == value, (actual, key)
        assert profile['trigger_binding_sha256'] == p['trigger_binding_sha256']
    return source, p


def foundation_history():
    """Read the original manifest; resolve its raw relative metadata explicitly.

    No history tensors or directories are copied or linked into this experiment.
    The raw document and its digest remain those of the original completed run.
    """
    p = read(ROOT / 'SOURCE_PROFILE.json')
    meta = p['foundation_history_manifest']; checked(meta)
    original = read(meta['path'])
    assert len(original['rounds']) == 20
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


def trigger_ready(source):
    """Metadata/model hashing only after the current trigger has actually exited."""
    root = Path(source['trigger_root'])
    for name, digest in source['trigger_predeclared_files'].items():
        assert sha(root / name) == digest, name
    for name, digest in read(root / 'SOURCE_FREEZE.json')['files'].items():
        assert sha(root / name) == digest, name
    for name in ['CONTROLLER_FAILURE.json', 'TRIGGER_FAILURE.json', 'AUDIT_FAILURE.json']:
        assert not (root / name).exists(), name
    result, audit, completion = (read(root / name) for name in
                                ['TRIGGER_RESULT.json', 'TRIGGER_VERIFIED.json', 'COMPLETION.json'])
    assert result['state'] == 'completed_CPU_mixed_teacher_trigger100'
    assert audit['state'] == 'passed_new_mixed_teacher_CPU_trigger100'
    assert completion['state'] == 'completed_new_mixed_teacher_CPU_trigger100_verified'
    assert read(root / 'CONTROLLER_STATE.json') == completion
    assert result['new_epochs'] == audit['epochs'] == 100
    assert result['actual_batches'] == audit['batches'] == 200
    assert result['sample_exposures'] == audit['sample_exposures'] == 20000
    assert audit['result_sha256'] == completion['result_sha256'] == sha(root / 'TRIGGER_RESULT.json')
    assert completion['verified_sha256'] == sha(root / 'TRIGGER_VERIFIED.json')
    assert result['teacher'] == audit['teacher'] == completion['teacher']
    assert result['teacher']['sha256'] == source['required_mixed_teacher_sha256']
    assert result['delta'] == audit['delta'] == completion['delta']
    assert result['delta']['payload_key'] is None
    assert result['manifest_sha256'] == sha(root / 'MANIFEST.json')
    assert len(audit['history_hashes']) == 300 and audit['all200_projection_algebra_checked']
    replay = audit['fixed_independent_gradient_replays']
    assert [(v['epoch'], v['batch']) for v in replay] == [(1, 1), (100, 2)]
    assert all(v['augmentation_exact'] and v['atol'] == 2e-5 and v['rtol'] == 1e-3 for v in replay)
    query = "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object {$_.CommandLine -match 'FEDUBA_MIXED_TRIGGER_20261101'} | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', query], text=True, encoding='utf-8').strip()
    processes = json.loads(raw) if raw else []
    if isinstance(processes, dict): processes = [processes]
    assert processes == [], processes
    query = "Get-ScheduledTaskInfo -TaskName 'Codex-FedUBA-mixed-teacher-CPU-trigger100-20261101' | Select-Object LastTaskResult | ConvertTo-Json -Compress"
    info = json.loads(subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', query], text=True, encoding='utf-8'))
    assert info['LastTaskResult'] == 0
    delta = dict(result['delta']); relative = Path(delta['path'])
    assert not relative.is_absolute() and relative.as_posix() == 'private_run/delta.pt'
    delta['path'] = str((root / relative).resolve()); delta['payload_key'] = None
    checked(delta)  # First new-delta hash here is after verified completion and actual exit.
    files = ['TRIGGER_RESULT.json', 'TRIGGER_VERIFIED.json', 'COMPLETION.json', 'CONTROLLER_STATE.json',
             'MANIFEST.json', 'SOURCE_FREEZE.json', 'LAUNCH_PROFILE.json', 'RUN_FREEZE.json', 'RUN_PUBLICATION.json']
    receipts = {n: {'path': str(root / n), 'sha256': sha(root / n), 'bytes': (root / n).stat().st_size} for n in files}
    binding = {'kind': 'new_mixed105_teacher_verified_CPU_trigger100', 'teacher': result['teacher'],
               'delta': delta, 'original_delta_metadata': result['delta'], 'receipts': receipts,
               'old_GPU_failure': source['old_GPU_failure'], 'old_pair_performance_failure_preserved': True}
    terminal = {'state': 'verified_new_mixed_trigger_completed_actual_processes_exited',
                'utc': datetime.now(timezone.utc).isoformat(), 'trigger_processes': [], 'task_last_result': 0}
    return binding, terminal
