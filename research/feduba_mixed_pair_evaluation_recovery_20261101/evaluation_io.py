"""Separate evaluation outputs, immutable original inputs, and shell-free strict metadata guard."""
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from native_processes import processes

ROOT = Path(__file__).resolve().parent
OLD = Path('D:/FEDUBA_MIXED_PAIR_20261101')
RECOVERY = Path('D:/FEDUBA_MIXED_ATTACK_RECOVERY_RUN_20261101')
FOUNDATION = Path('D:/FEDUBA_PAPER_IMPLEMENTATION_20261031')


def original_recovery():
    key = '_frozen_completed_attack_recovery_io'
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, RECOVERY / 'recovery_io.py')
        module = importlib.util.module_from_spec(spec); sys.modules[key] = module; spec.loader.exec_module(module)
    return sys.modules[key]


def aliases():
    frozen = original_recovery()
    paths = {n: frozen.input_path(RECOVERY / n) for n in frozen.OLD_INPUTS}
    paths.update({n: RECOVERY / n for n in ['FU_attack_RESULT.json', 'FU_attack_VERIFIED.json',
        'fu/attack/MANIFEST.json', 'RECOVERY_INPUT_BINDING.json']})
    return paths


def input_path(path):
    path = Path(path)
    if path.is_absolute() and path.is_relative_to(ROOT):
        return aliases().get(path.relative_to(ROOT).as_posix(), path)
    return path


def read(path): return json.loads(input_path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256(); buffer = bytearray(65536)
    with input_path(path).open('rb', buffering=0) as stream:
        while (n := stream.readinto(buffer)): h.update(memoryview(buffer)[:n])
    return h.hexdigest()


def tensor_path(meta):
    path = Path(meta['path']); path = (path if path.is_absolute() else OLD / path).resolve()
    assert any(path.is_relative_to(p.resolve()) for p in [ROOT, OLD, RECOVERY, FOUNDATION,
        Path('D:/FEDUBA_MIXED_TRIGGER_20261101'), Path('D:/CHECKPOINTS_FOR_REVIEW')]), str(path)
    return path


def writable(path):
    path = Path(path).resolve()
    assert path.is_relative_to(ROOT.resolve())
    assert path.relative_to(ROOT.resolve()).as_posix() not in aliases()
    return path


def write(path, value):
    path = writable(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False, ensure_ascii=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    for attempt in range(40):
        try: os.replace(temporary, path); return
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


def source_check():
    assert ROOT == Path('D:/FEDUBA_MIXED_PAIR_EVALUATION_RECOVERY_20261101')
    p = read(ROOT / 'SOURCE_PROFILE.json')
    assert p['launch_enabled'] is False and p['actual_input_binding'] is None
    assert list(sys.version_info[:3]) == p['python_version']
    for name, version in p['package_versions'].items(): assert importlib.metadata.version(name) == version, name
    for name, digest in read(ROOT / 'SOURCE_FREEZE.json')['files'].items(): assert sha(ROOT / name) == digest, name
    return p


def require_published_run():
    source = source_check()
    pub = read(ROOT / 'RUN_PUBLICATION.json')
    assert pub['state'] == 'published_actual_evaluation_only_nativeguard_recovery_before_execution'
    assert pub['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
    assert pub['run_freeze_sha256'] == sha(ROOT / 'RUN_FREEZE.json')
    for name, digest in read(ROOT / 'RUN_FREEZE.json')['files'].items(): assert sha(ROOT / name) == digest, name
    launch, binding = read(ROOT / 'LAUNCH_PROFILE.json'), read(ROOT / 'EVALUATION_INPUT_BINDING.json')
    assert launch['launch_enabled'] is True and launch['input_binding_sha256'] == sha(ROOT / 'EVALUATION_INPUT_BINDING.json')
    for meta in binding['receipts'].values():
        assert sha(meta['path']) == meta['sha256'] and Path(meta['path']).stat().st_size == meta['bytes']
    assert sha(RECOVERY / 'FU_attack_VERIFIED.json') == source['required_attack_verified_sha256']
    assert read(RECOVERY / 'FU_attack_VERIFIED.json')['state'] == 'passed'
    assert read(ROOT / 'METADATA_PROBE_RESULT.json')['state'] == 'passed_new_native_metadata_source_probe'
    assert read(ROOT / 'METADATA_PROBE_CIM_MATCH.json')['state'] == 'passed_native_self_PID_parent_commandline_match_external_CIM'
    return original_recovery().require_published_run()


def freeze_check(legacy_name=None):
    require_published_run()
    if legacy_name is not None:
        assert legacy_name == 'PAIR_EVAL_RUN_FREEZE.json'
        for name, digest in read(OLD / legacy_name)['files'].items(): assert sha(OLD / name) == digest, name


class ResourceBusy(RuntimeError): pass


def memory_guard():
    from native_memory import memory_information
    value = memory_information(); p = read(ROOT / 'SOURCE_PROFILE.json')['memory_guard']
    if value['availableBytes'] < p['available_min_bytes'] or value['commitLimit'] - value['committedBytes'] < p['commit_free_min_bytes']:
        raise ResourceBusy('Fixed RAM/commit headroom unavailable: ' + json.dumps(value))
    return value


def guard(free_min=4000, used_max=6000):
    memory = memory_guard()
    executable = read(ROOT / 'SOURCE_PROFILE.json')['nvidia_smi_path']
    raw = subprocess.check_output([executable, '--query-gpu=utilization.gpu,memory.free,memory.used',
                                   '--format=csv,noheader,nounits'], text=True).strip()
    util, free, used = [int(v.strip()) for v in raw.split(',')]
    if not (util <= 5 and free >= free_min and used <= used_max): raise ResourceBusy('Fixed GPU guard unavailable: ' + raw)
    rows = processes()
    peers = [r for r in rows if r['ProcessId'] not in [os.getpid(), os.getppid()]]
    if peers: raise ResourceBusy('Strict native peer-Python/mpiexec guard: ' + json.dumps(peers))
    return {'utilization_pct': util, 'free_MiB': free, 'used_MiB': used,
        'free_min_MiB': free_min, 'used_max_MiB': used_max, 'memory': memory,
        'other_python_or_mpiexec_processes': 0, 'competing_trainers': 0,
        'process_metadata_getter': 'Windows_Toolhelp32_no_shell_child', 'peers_guard_stricter_than_original_token_filter': True}
