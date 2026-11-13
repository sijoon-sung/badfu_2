"""One finite resource-wait -> fixture -> fresh clean-FL -> audit pipeline."""
import json
import os
import subprocess
import sys
import time
import traceback
from runtime_common import ROOT, write, freeze_check, guard

os.environ.update(PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='0')
freeze_check('FOUNDATION_FREEZE.json')
with (ROOT / 'FOUNDATION_ONCE.json').open('x', encoding='utf-8') as stream:
    json.dump({'pid': os.getpid(), 'created_unix': time.time()}, stream)
deadline = time.time() + 86400
with (ROOT / 'foundation_console.log').open('x', encoding='utf-8', newline='\n', buffering=1) as log:
    try:
        assert not any((ROOT / name).exists() for name in [
            'GPU_PREFLIGHT_ONCE.json', 'CLEAN_FL_READY.json', 'CLEAN_FL_CONTROLLER_ONCE.json'])
        while True:
            freeze_check('FOUNDATION_FREEZE.json')
            try:
                resource = guard()
                break
            except (AssertionError, RuntimeError) as error:
                write(ROOT / 'FOUNDATION_STATE.json', {'state': 'waiting_for_resources',
                      'pid': os.getpid(), 'reason': str(error), 'deadline_unix': deadline,
                      'updated_unix': time.time(), 'other_apps_stopped': False})
                if time.time() >= deadline:
                    raise RuntimeError('Finite 24h resource deadline expired; no experiment launched') from error
                time.sleep(30)
        for name in ['gpu_probe.py', 'prepare_clean_fl.py', 'clean_fl_controller.py']:
            env = os.environ.copy()
            if name == 'prepare_clean_fl.py':
                env['CUDA_VISIBLE_DEVICES'] = ''
            child = subprocess.Popen([sys.executable, '-u', str(ROOT / name)], cwd=ROOT,
                                     stdout=log, stderr=subprocess.STDOUT, env=env)
            write(ROOT / 'FOUNDATION_STATE.json', {'state': 'running', 'pid': os.getpid(),
                  'step': name, 'child_pid': child.pid, 'updated_unix': time.time()})
            if child.wait():
                raise RuntimeError(name + ' failed; original state preserved, no automatic rerun')
        write(ROOT / 'FOUNDATION_STATE.json', {'state': 'completed_clean_FL_foundation_only',
              'pid': os.getpid(), 'updated_unix': time.time(), 'overall_FedUBA_goal_complete': False,
              'remaining': ['STG', 'SSS', 'BEA_and_benign_FU', 'evaluation', 'delivery']})
    except BaseException:
        write(ROOT / 'FOUNDATION_STATE.json', {'state': 'failed_preserved', 'pid': os.getpid(),
              'updated_unix': time.time(), 'traceback': traceback.format_exc()})
        raise
