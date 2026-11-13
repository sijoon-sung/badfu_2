import hashlib
from storage_retry import replace_with_retry
import importlib.util
import json
import os
from pathlib import Path
import random
import sys
import time
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    replace_with_retry(tmp, path)


def cpu(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {k: cpu(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return type(value)(cpu(v) for v in value)
    return value


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists(), path
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('xb') as f:
        torch.save(cpu(value), f)
        f.flush()
        os.fsync(f.fileno())
    replace_with_retry(tmp, path)
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha(path), 'bytes': path.stat().st_size}


def load_model_class():
    spec = importlib.util.spec_from_file_location('paper_mnist_model', ROOT / 'author_model.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.Net


def rng():
    n = np.random.get_state()
    return {'python': random.getstate(), 'numpy': (n[0], n[1].tolist(), int(n[2]), int(n[3]), float(n[4])),
            'torch_CPU': torch.get_rng_state(), 'torch_CUDA': torch.cuda.get_rng_state_all()}


def seed(value):
    random.seed(value)
    np.random.seed(value)
    torch.manual_seed(value)
    torch.cuda.manual_seed_all(value)


def exact(a, b):
    assert a.keys() == b.keys() and all(torch.equal(a[k], b[k]) for k in a)


def guard():
    import subprocess
    raw = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu,memory.free,memory.used',
                                   '--format=csv,noheader,nounits'], text=True).strip()
    util, free, used = [int(v.strip()) for v in raw.split(',')]
    assert util <= 5 and free >= 7000 and used <= 2048, raw
    command = "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|mpiexec'} | Select-Object ProcessId,CommandLine | ConvertTo-Json"
    rows = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', command], text=True))
    if isinstance(rows, dict):
        rows = [rows]
    for row in rows or []:
        if row['ProcessId'] in [os.getpid(), os.getppid()]:
            continue
        cmd = (row.get('CommandLine') or '').lower()
        if any(t in cmd for t in ['mpiexec.exe', 'badfu_train.py', 'train_method_iba.py',
                                 '/runner.py', '\\runner.py', 'independent_evaluate.py']):
            raise RuntimeError('Competing training PID ' + str(row['ProcessId']))
    return {'utilization_pct': util, 'free_MiB': free, 'used_MiB': used}
