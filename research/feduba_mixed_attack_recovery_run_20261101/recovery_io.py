"""Explicit old/new metadata routing and closed recovery publication gates."""
import base64
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
OLD = Path('D:/FEDUBA_MIXED_PAIR_20261101')
FOUNDATION = Path('D:/FEDUBA_PAPER_IMPLEMENTATION_20261031')
CPU = Path('D:/FEDUBA_MIXED_ATTACK_PREFIX_GUARD_V2_20261101')
OPS = Path('D:/FEDUBA_MIXED_PAIR_MEMORY_RECOVERY_20261101')
OLD_INPUTS = frozenset(['CLEAN_FL_PROFILE.json', 'CLEAN_FL_READY.json', 'CLEAN_FL_RESULT.json',
    'CLEAN_FL_VERIFIED.json', 'CLEAN_DELIVERY_COMPLETE.json', 'GPU_PREFLIGHT_RESULT.json',
    'FU_PROFILE.json', 'FU_LAUNCH_PROFILE.json', 'FU_ENGINE_CPU_RESULT.json', 'FU_POLICY_CPU_RESULT.json',
    'PAIR_EVAL_PROFILE.json', 'PAIR_EVAL_LAUNCH_PROFILE.json', 'PAIR_EVAL_CPU_RESULT.json',
    'SSS_RESULT.json', 'SSS_VERIFIED.json', 'TRIGGER_SOURCE_BINDING.json',
    'FU_benign_RESULT.json', 'FU_benign_VERIFIED.json', 'fu/benign/MANIFEST.json'])


def input_path(path):
    path = Path(path)
    if path.is_absolute() and path.is_relative_to(ROOT):
        name = path.relative_to(ROOT).as_posix()
        if name in OLD_INPUTS: return OLD / name
    return path


def tensor_path(meta):
    path = Path(meta['path'])
    path = path if path.is_absolute() else OLD / path
    path = path.resolve()
    assert any(path.is_relative_to(p.resolve()) for p in [ROOT, OLD, FOUNDATION,
        Path('D:/FEDUBA_MIXED_TRIGGER_20261101'), Path('D:/CHECKPOINTS_FOR_REVIEW')]), str(path)
    return path


def read(path):
    return json.loads(input_path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256(); buffer = bytearray(65536)
    with input_path(path).open('rb', buffering=0) as stream:
        while (n := stream.readinto(buffer)): h.update(memoryview(buffer)[:n])
    return h.hexdigest()


def writable(path):
    path = Path(path).resolve()
    assert path.is_relative_to(ROOT.resolve())
    assert path.relative_to(ROOT.resolve()).as_posix() not in OLD_INPUTS
    return path


def write(path, value):
    path = writable(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False, ensure_ascii=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    for attempt in range(40):
        try:
            os.replace(temporary, path); return
        except PermissionError:
            if attempt == 39: raise
            time.sleep(.05)


def once(name, value):
    path = writable(ROOT / name)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False, ensure_ascii=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def save(path, value):
    import torch
    from runtime_common import cpu
    path = writable(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        torch.save(cpu(value), stream); stream.flush(); os.fsync(stream.fileno())
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


def ps_json(query):
    query = "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';" + query
    encoded = base64.b64encode(query.encode('utf-16le')).decode()
    run = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded],
                         text=True, encoding='utf-8', capture_output=True, timeout=30)
    if run.returncode or not run.stdout.strip():
        raise RuntimeError('Metadata process query failed: ' + json.dumps({'exit': run.returncode,
            'stdout_characters': len(run.stdout), 'stderr_preview': run.stderr[:2000]}))
    assert len(run.stdout) < 100000
    return json.loads(run.stdout)


def processes():
    return ps_json("$v=@(Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe' OR Name='mpiexec.exe'\" | Select-Object ProcessId,ParentProcessId,CommandLine);ConvertTo-Json -InputObject $v -Depth 3 -Compress")


def original_module():
    name = '_frozen_original_mixed_pair_binding'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, OLD / 'pair_binding.py')
        module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return sys.modules[name]


def source_check():
    assert ROOT == Path('D:/FEDUBA_MIXED_ATTACK_RECOVERY_RUN_20261101')
    profile = read(ROOT / 'SOURCE_PROFILE.json')
    assert profile['launch_enabled'] is False and profile['actual_input_binding'] is None
    assert list(sys.version_info[:3]) == profile['python_version']
    for name, version in profile['package_versions'].items():
        assert importlib.metadata.version(name) == version, name
    for name, digest in read(ROOT / 'SOURCE_FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name
    return profile


def require_published_run():
    source = source_check()
    if not (ROOT / 'LAUNCH_PROFILE.json').exists():
        raise Unlaunched('Closed recovery source: actual launch profile absent')
    p = read(ROOT / 'LAUNCH_PROFILE.json')
    assert p['launch_enabled'] is True
    publication = read(ROOT / 'RUN_PUBLICATION.json')
    assert publication['state'] == 'published_actual_attack_recovery154_and_pair_evaluation_before_execution'
    assert publication['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
    assert publication['run_freeze_sha256'] == sha(ROOT / 'RUN_FREEZE.json')
    for name, digest in read(ROOT / 'RUN_FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name
    binding = read(ROOT / 'RECOVERY_INPUT_BINDING.json')
    assert p['input_binding_sha256'] == sha(ROOT / 'RECOVERY_INPUT_BINDING.json')
    for meta in binding['receipts'].values():
        assert sha(meta['path']) == meta['sha256'] and Path(meta['path']).stat().st_size == meta['bytes']
    assert binding['CPU_result_sha256'] == source['required_CPU_prefix_result_sha256']
    assert binding['prefix_preserved_sha256'] == source['required_prefix_preserved_sha256']
    assert read(CPU / 'AUDIT_RESULT.json')['state'] == 'passed_new_CPU_attack_prefix46_audit'
    assert binding['CPU_task_last_result'] == 0
    assert read(ROOT / 'TERMINAL_OBSERVATION.json')['CPU_task']['lastResult'] == 0
    original = original_module()
    original.require_published_run()
    # These canonical values are historical inputs, not modified recovery profiles.
    return original.source_profile(), read(OLD / 'PAIR_LAUNCH_PROFILE.json')


def freeze_check(legacy_name=None):
    require_published_run()
    if legacy_name is not None:
        assert legacy_name in ['FU_RUN_FREEZE.json', 'PAIR_EVAL_RUN_FREEZE.json']
        for name, digest in read(OLD / legacy_name)['files'].items():
            assert sha(OLD / name) == digest, name


class Unlaunched(RuntimeError): pass
class ResourceBusy(RuntimeError): pass


def memory_guard():
    from native_memory import memory_information
    value = memory_information(); p = read(ROOT / 'SOURCE_PROFILE.json')['memory_guard']
    if value['availableBytes'] < p['available_min_bytes'] or value['commitLimit'] - value['committedBytes'] < p['commit_free_min_bytes']:
        raise ResourceBusy('Fixed RAM/commit headroom unavailable: ' + json.dumps(value))
    return value


def guard(free_min=4000, used_max=6000):
    memory = memory_guard()
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu,memory.free,memory.used',
                                   '--format=csv,noheader,nounits'], text=True).strip()
    util, free, used = [int(item.strip()) for item in raw.split(',')]
    if not (util <= 5 and free >= free_min and used <= used_max):
        raise ResourceBusy('Fixed GPU guard unavailable: ' + raw)
    rows = processes()
    tokens = ['mpiexec.exe', 'badfu_train.py', '/runner.py', '\\runner.py', 'train_method_iba.py',
        'independent_evaluate.py', 'gpu_probe.py', 'clean_fl_runner.py', 'trigger_runner.py',
        'fu_runner.py', 'resume_attack.py', 'verify_fu.py', 'verify_prefix.py', 'evaluate_pair.py', 'verify_pair_evaluation.py']
    for row in rows:
        if row['ProcessId'] in [os.getpid(), os.getppid()]: continue
        command = (row.get('CommandLine') or '').lower()
        if any(token in command for token in tokens):
            raise ResourceBusy('Competing numerical process ' + str(row['ProcessId']))
    return {'utilization_pct': util, 'free_MiB': free, 'used_MiB': used,
            'free_min_MiB': free_min, 'used_max_MiB': used_max, 'memory': memory,
            'competing_trainers': 0}
