"""One new CPU trigger100 branch and its independent CPU verification, no retries."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
import json
import subprocess
import sys
import time
import traceback
from runtime_common import ROOT, write, freeze_check

freeze_check('STG_CPU_TRIGGER_FREEZE.json')
with (ROOT / 'STG_CPU_TRIGGER_CONTROLLER_ONCE.json').open('x', encoding='utf-8') as f:
    json.dump({'pid': os.getpid(), 'time_unix': time.time()}, f)
try:
    with (ROOT / 'cpu_trigger_recovery.log').open('x', encoding='utf-8', newline='\n', buffering=1) as log:
        for name in ['cpu_trigger_recovery.py', 'verify_cpu_trigger_recovery.py']:
            child = subprocess.Popen([sys.executable, '-u', str(ROOT / name)], cwd=ROOT,
                                     env=os.environ.copy(), stdout=log, stderr=subprocess.STDOUT)
            write(ROOT / 'STG_CPU_TRIGGER_CONTROLLER_STATE.json', {'state': 'running', 'pid': os.getpid(),
                  'step': name, 'child_pid': child.pid, 'time_unix': time.time()})
            if child.wait(): raise RuntimeError(name + ' failed; preserve, no retry')
    write(ROOT / 'STG_CPU_TRIGGER_CONTROLLER_STATE.json', {'state': 'completed_CPU_trigger100_verified',
          'pid': os.getpid(), 'time_unix': time.time(), 'original_STG_CPU_GPU_audit_remains_failed': True,
          'overall_goal_complete': False})
except BaseException:
    write(ROOT / 'STG_CPU_TRIGGER_CONTROLLER_FAILURE.json', {'pid': os.getpid(), 'traceback': traceback.format_exc()})
    raise
