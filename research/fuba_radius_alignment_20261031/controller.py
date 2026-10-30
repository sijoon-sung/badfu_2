import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path(__file__).resolve().parent
with (root / 'CONTROLLER_ONCE.json').open('x', encoding='utf-8') as f:
    json.dump({'pid': os.getpid(), 'time_unix': time.time()}, f)
with (root / 'console.log').open('x', encoding='utf-8') as f:
    child = subprocess.Popen([sys.executable, '-u', str(root / 'runner.py')], cwd=root, stdout=f,
                             stderr=subprocess.STDOUT,
                             env=dict(os.environ, CUDA_VISIBLE_DEVICES='0', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1'))
    (root / 'CONTROLLER_STATE.json').write_text(json.dumps({'state': 'running', 'pid': os.getpid(), 'child_pid': child.pid}), encoding='utf-8')
    code = child.wait()
    (root / 'CONTROLLER_STATE.json').write_text(json.dumps({'state': 'complete_verified' if code == 0 else 'failed', 'exit': code, 'pid': os.getpid()}), encoding='utf-8')
    sys.exit(code)
