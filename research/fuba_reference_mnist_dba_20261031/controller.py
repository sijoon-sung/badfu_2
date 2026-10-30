import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

root = Path(__file__).resolve().parent
with (root / 'CONTROLLER_ONCE.json').open('x', encoding='utf-8') as f:
    json.dump({'pid': os.getpid(), 'time_unix': time.time()}, f)


def state(**value):
    (root / 'CONTROLLER_STATE.json').write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


with (root / 'console.log').open('x', encoding='utf-8', buffering=1) as log:
    try:
        for name in ['runner.py', 'verify.py']:
            child = subprocess.Popen([sys.executable, '-u', str(root / name)], cwd=root, stdout=log, stderr=subprocess.STDOUT,
                                     env=dict(os.environ, CUDA_VISIBLE_DEVICES='0', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1'))
            state(state='running', pid=os.getpid(), child_pid=child.pid, step=name)
            if child.wait():
                raise RuntimeError(name + ' failed')
        state(state='complete_verified', pid=os.getpid())
    except BaseException:
        state(state='failed', pid=os.getpid(), traceback=traceback.format_exc())
        raise
