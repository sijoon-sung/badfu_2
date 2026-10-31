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
        for block in iter(lambda: stream.read(4 << 20), b''):
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


def guard(free_min=4000, used_max=6000):
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu,memory.free,memory.used',
                                   '--format=csv,noheader,nounits'], text=True).strip()
    util, free, used = map(lambda item: int(item.strip()), raw.split(','))
    assert util <= 5 and free >= free_min and used <= used_max, raw
    query = "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|mpiexec'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    rows = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', query], text=True))
    rows = [rows] if isinstance(rows, dict) else rows
    for row in rows or []:
        if row['ProcessId'] in [os.getpid(), os.getppid()]:
            continue
        text = (row.get('CommandLine') or '').lower()
        if any(token in text for token in ['mpiexec.exe', 'badfu_train.py', '/runner.py', '\\runner.py',
                                           'train_method_iba.py', 'independent_evaluate.py', 'gpu_probe.py',
                                           'clean_fl_runner.py', 'trigger_runner.py', 'fu_runner.py']):
            raise RuntimeError('Competing training/evaluation PID ' + str(row['ProcessId']))
    return {'utilization_pct': util, 'free_MiB': free, 'used_MiB': used,
            'free_min_MiB': free_min, 'used_max_MiB': used_max}


def freeze_check(name):
    for path, digest in read(ROOT / name)['files'].items():
        assert sha(ROOT / path) == digest, path
