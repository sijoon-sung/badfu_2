import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False, ensure_ascii=False); stream.write('\n')
        stream.flush(); os.fsync(stream.fileno())
    for attempt in range(40):
        try:
            os.replace(tmp, path); return
        except PermissionError:
            if attempt == 39:
                raise
            time.sleep(.05)


def cpu(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {key: cpu(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return type(value)(cpu(item) for item in value)
    return value


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists(), path
    with path.open('xb') as stream:
        torch.save(cpu(value), stream); stream.flush(); os.fsync(stream.fileno())
    return {'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path), 'bytes': path.stat().st_size}


def seed(value):
    random.seed(value); np.random.seed(value); torch.manual_seed(value); torch.cuda.manual_seed_all(value)


def rng():
    a = np.random.get_state()
    return {'python': random.getstate(), 'numpy': (a[0], a[1].tolist(), int(a[2]), int(a[3]), float(a[4])),
            'torch_CPU': torch.get_rng_state(), 'torch_CUDA': torch.cuda.get_rng_state_all()}


class ResourceBusy(RuntimeError): pass

def guard(free_min=4000, used_max=6000):
    from native_memory import memory_information
    from native_processes import processes
    memory=memory_information()
    if memory['availableBytes'] < 8*2**30 or memory['commitLimit']-memory['committedBytes'] < 16*2**30:
        raise ResourceBusy('Fixed RAM/commit guard unavailable')
    raw=subprocess.check_output(['C:/Windows/System32/nvidia-smi.exe','--query-gpu=utilization.gpu,memory.free,memory.used','--format=csv,noheader,nounits'],text=True).strip()
    util,free,used=[int(v.strip()) for v in raw.split(',')]
    if not(util<=5 and free>=free_min and used<=used_max): raise ResourceBusy('Fixed GPU guard unavailable: '+raw)
    p=read(ROOT/'SOURCE_PROFILE.json')
    peers=[r for r in processes() if r['ProcessId'] not in [os.getpid(),os.getppid()] and any(t in r['CommandLine'].lower() for t in p['known_training_process_tokens'])]
    if peers: raise ResourceBusy('Competing trainer identified; no process will be stopped')
    return {'utilization_pct':util,'free_MiB':free,'used_MiB':used,'memory':memory,'competing_trainers':0}


def freeze_check(name):
    for path, digest in read(ROOT / name)['files'].items():
        assert sha(ROOT / path) == digest, path
