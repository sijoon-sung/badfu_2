"""Exclusive DISLAB-only experiment I/O and unchanged native resource guards."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parent


def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''): digest.update(chunk)
    return digest.hexdigest()


def write(name, value, exclusive=True):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x' if exclusive else 'w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def meta(path):
    path = Path(path)
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


def check(meta_value):
    path = Path(meta_value['path'])
    assert sha(path) == meta_value['sha256'], str(path)
    if 'bytes' in meta_value: assert path.stat().st_size == meta_value['bytes']
    return path


def profile(published=True):
    p = read(ROOT / 'PROFILE.json')
    assert ROOT == Path(p['execution_root']) and p['launch_enabled'] is True
    assert list(sys.version_info[:3]) == [3, 12, 10]
    for name, digest in read(ROOT / 'SOURCE_FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name
    if published:
        pub = read(ROOT / 'PUBLICATION.json')
        assert pub['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
        assert pub['profile_sha256'] == sha(ROOT / 'PROFILE.json')
        assert pub['state'] == 'published_actual_profile_before_execution'
    for v in p['inputs'].values(): check(v)
    return p


def resource_guard():
    from native_memory import memory_information
    from native_processes import processes
    p = read(ROOT / 'PROFILE.json')
    memory = memory_information()
    raw = subprocess.check_output([p['nvidia_smi_path'], '--query-gpu=utilization.gpu,memory.free,memory.used',
                                   '--format=csv,noheader,nounits'], text=True).strip()
    util, free, used = [int(x.strip()) for x in raw.split(',')]
    rows = processes()
    peers = [r for r in rows if r['ProcessId'] not in [os.getpid(), os.getppid()] and
             any(t in r['CommandLine'].lower() for t in p['known_training_process_tokens'])]
    assert not peers, 'Competing trainer identified; no process will be stopped'
    assert memory['availableBytes'] >= 8 * 2**30
    assert memory['commitLimit'] - memory['committedBytes'] >= 16 * 2**30
    assert util <= 5 and free >= 4000 and used <= 6000, raw
    assert shutil.disk_usage(ROOT).free >= 2 * 2**30
    return {'utc': time.time(), 'memory': memory, 'GPU': {'util': util, 'free': free, 'used': used},
            'competing_trainers': 0, 'CPU_threads': 2, 'CUDA_VISIBLE_DEVICES': '-1'}


def cpu_copy(value):
    import torch
    if isinstance(value, torch.Tensor): return value.detach().cpu().clone()
    if isinstance(value, dict): return {k: cpu_copy(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return type(value)(cpu_copy(v) for v in value)
    return value


def save(name, value):
    import torch
    path = ROOT / name; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        torch.save(cpu_copy(value), stream); stream.flush(); os.fsync(stream.fileno())
    return meta(path)


def numeric_policy():
    import torch
    torch.set_num_threads(2); torch.backends.mkldnn.enabled = True
    torch.set_float32_matmul_precision('highest')
    assert os.environ['CUDA_VISIBLE_DEVICES'] == '-1' and not torch.cuda.is_initialized()
    assert str(torch.__version__) == '2.7.1+cu118'
    return {'threads': torch.get_num_threads(), 'MKLDNN': torch.backends.mkldnn.enabled,
            'torch': str(torch.__version__), 'CUDA_initialized': torch.cuda.is_initialized(), 'dtype': 'FP32'}
