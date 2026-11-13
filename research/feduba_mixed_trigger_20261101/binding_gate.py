"""Stdlib-only gates: code-only profile cannot launch; completed teacher is explicit."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parent


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def once(name, value):
    with (ROOT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n')


def source_profile():
    for name, digest in read(ROOT / 'SOURCE_FREEZE.json')['files'].items(): assert sha(ROOT / name) == digest, name
    p = read(ROOT / 'SOURCE_PROFILE.json')
    assert p['launch_enabled'] is False and p['teacher_binding'] is None
    assert ROOT == Path(p['execution_root']) and list(sys.version_info[:3]) == p['python_version']
    for name, version in p['package_versions'].items(): assert importlib.metadata.version(name) == version, name
    return p


def verify_meta(meta):
    path = Path(meta['path']); assert sha(path) == meta['sha256'], meta['path']
    if 'bytes' in meta: assert path.stat().st_size == meta['bytes']


def teacher_ready(p):
    root = Path(p['teacher_root'])
    assert sha(root / 'FREEZE.json') == p['teacher_source_freeze_sha256']
    for name, digest in read(root / 'FREEZE.json')['files'].items(): assert sha(root / name) == digest, name
    assert sha(root / 'PUBLICATION.json') == p['teacher_publication_sha256']
    required = ['TRAIN_RESULT.json', 'TRAIN_VERIFIED.json', 'ENDPOINT_RESULT.json', 'ENDPOINT_VERIFIED.json', 'COMPLETION.json']
    values = {name: read(root / name) for name in required}
    result, audit = values['TRAIN_RESULT.json'], values['TRAIN_VERIFIED.json']
    endpoint, endpoint_audit, completion = (values[n] for n in required[2:])
    assert result['state'] == 'completed_mixed100_warmup5_teacher_only'
    assert result['model_epochs'] == audit['model_epochs'] == 105 and result['actual_batches'] == audit['batches'] == 78310
    assert audit['state'] == endpoint_audit['state'] == 'passed'
    assert audit['train_result_sha256'] == sha(root / 'TRAIN_RESULT.json')
    assert audit['manifest_sha256'] == result['manifest_sha256'] == sha(root / 'MANIFEST.json')
    assert endpoint['teacher_audit_sha256'] == sha(root / 'TRAIN_VERIFIED.json')
    assert endpoint_audit['endpoint_result_sha256'] == sha(root / 'ENDPOINT_RESULT.json')
    assert completion['state'] == 'completed_teacher_only_CPU_verified_endpoint_recorded'
    for key, name in [('training_result_sha256', 'TRAIN_RESULT.json'), ('training_audit_sha256', 'TRAIN_VERIFIED.json'),
                      ('endpoint_result_sha256', 'ENDPOINT_RESULT.json'), ('endpoint_audit_sha256', 'ENDPOINT_VERIFIED.json')]:
        assert completion[key] == sha(root / name)
    assert endpoint['minimal_functional_condition_passed'] is endpoint_audit['minimal_functional_condition_passed'] is completion['minimal_functional_condition_passed'] is True
    fixed = result['fixed_teacher']
    assert audit['fixed_teacher'] == endpoint['fixed_teacher'] == fixed
    assert fixed['payload_key'] is None and fixed['path'] == 'private_run/fixed_teacher201.pt'
    model_path = (root / fixed['path']).resolve(); assert model_path.is_relative_to(root.resolve())
    for name in ['CONTROLLER_FAILURE.json', 'TRAIN_FAILURE.json', 'AUDIT_FAILURE.json', 'ENDPOINT_FAILURE_run.json', 'ENDPOINT_FAILURE_verify.json']:
        assert not (root / name).exists(), name
    # Actual command lines are authoritative; historical numeric PIDs are not.
    command = "Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('python.exe','pythonw.exe') -and $_.CommandLine -match 'FEDUBA_MIXED_SURROGATE_20261101'} | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', command], text=True, encoding='utf-8').strip()
    processes = json.loads(raw) if raw else []
    if isinstance(processes, dict): processes = [processes]
    assert processes == [], processes
    task = "Get-ScheduledTaskInfo -TaskName 'Codex-FedUBA-mixed-surrogate100-warmup5-20261101' | Select-Object LastTaskResult | ConvertTo-Json -Compress"
    info = json.loads(subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', task], text=True, encoding='utf-8'))
    assert info['LastTaskResult'] == 0
    # Hash the bare teacher only after completion and actual termination, never a live prefix.
    teacher = {'path': str(model_path), 'sha256': fixed['sha256'], 'bytes': fixed['bytes'], 'payload_key': None, 'classes': 201}
    verify_meta(teacher)
    bindings = {n: {'path': str(root / n), 'sha256': sha(root / n), 'bytes': (root / n).stat().st_size} for n in required}
    bindings['teacher'] = teacher
    terminal = {'state': 'teacher_completed_verified_endpoint_minimal_condition_passed_and_actual_processes_exited',
                'utc': datetime.now(timezone.utc).isoformat(), 'teacher_processes': processes, 'task_last_result': 0,
                'teacher_source_freeze_sha256': p['teacher_source_freeze_sha256']}
    return bindings, terminal


def select_normal(p):
    value = json.loads(subprocess.check_output([sys.executable, '-B', p['catalog_root'] + '/select_case.py',
                       p['normal_case_id'], '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert value['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert value['checkpoint_guard']['manifest_sha256'] == p['normal_manifest_sha256']
    assert value['checkpoint_guard']['seal_sha256'] == p['normal_seal_sha256']
    assert value['server_inputs']['pre']['sha256'] == p['normal_pre_sha256'] and value['server_inputs']['pre']['payload_key'] is None
    return value


class Unlaunched(RuntimeError): pass


def run_profile():
    source = source_profile()
    if not (ROOT / 'LAUNCH_PROFILE.json').exists(): raise Unlaunched('Source-only profile: no actual teacher binding or launch profile')
    freeze = read(ROOT / 'RUN_FREEZE.json')
    assert freeze['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
    assert freeze['launch_profile_sha256'] == sha(ROOT / 'LAUNCH_PROFILE.json')
    assert freeze['teacher_terminal_sha256'] == sha(ROOT / 'TEACHER_TERMINAL.json')
    p = read(ROOT / 'LAUNCH_PROFILE.json')
    assert p['launch_enabled'] is True and p['execution_root'] == str(ROOT).replace('\\', '/')
    assert p['source_profile_sha256'] == sha(ROOT / 'SOURCE_PROFILE.json')
    assert p['constants'] == source['constants']
    assert p['teacher_bindings']['teacher']['payload_key'] is None and p['teacher_bindings']['teacher']['classes'] == 201
    return source, p
