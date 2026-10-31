import json
import os
import subprocess
import sys
import time
import traceback
from runtime_common import ROOT, read, write, freeze_check

sys.dont_write_bytecode = True
os.environ.update(PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='0')
freeze_check('CLEAN_FL_FREEZE.json')
with (ROOT / 'CLEAN_FL_CONTROLLER_ONCE.json').open('x', encoding='utf-8') as f:
    json.dump({'pid': os.getpid(), 'created_unix': time.time()}, f)
with (ROOT / 'clean_fl_console.log').open('x', encoding='utf-8', newline='\n', buffering=1) as log:
    try:
        for name in ['clean_fl_runner.py', 'verify_clean_fl.py']:
            child = subprocess.Popen([sys.executable, '-u', str(ROOT / name)], cwd=ROOT,
                                     stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy())
            write(ROOT / 'CLEAN_FL_CONTROLLER_STATE.json', {'state': 'running', 'pid': os.getpid(),
                  'child_pid': child.pid, 'step': name, 'updated_unix': time.time()})
            if child.wait():
                raise RuntimeError(name + ' failed; preserve original state and do not duplicate')
        write(ROOT / 'CLEAN_FL_CONTROLLER_STATE.json', {'state': 'complete_clean_FL_verified',
              'pid': os.getpid(), 'updated_unix': time.time(), 'overall_goal_complete': False})
    except BaseException:
        write(ROOT / 'CLEAN_FL_CONTROLLER_STATE.json', {'state': 'failed_preserved', 'pid': os.getpid(),
              'updated_unix': time.time(), 'traceback': traceback.format_exc()})
        raise
