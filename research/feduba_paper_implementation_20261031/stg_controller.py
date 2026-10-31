"""One CPU prepare -> bounded prerequisite/resource wait -> full STG -> CPU audit."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
import json
import subprocess
import sys
import time
import traceback
from runtime_common import ROOT, read, write, guard, freeze_check


def run(name, log, gpu=False):
    env = os.environ.copy(); env['CUDA_VISIBLE_DEVICES'] = '0' if gpu else '-1'
    child = subprocess.Popen([sys.executable, '-u', str(ROOT / name)], cwd=ROOT,
                             env=env, stdout=log, stderr=subprocess.STDOUT)
    write(ROOT / 'STG_CONTROLLER_STATE.json', {'state': 'running', 'pid': os.getpid(),
          'step': name, 'child_pid': child.pid, 'updated_unix': time.time()})
    if child.wait():
        raise RuntimeError(name + ' failed; preserve, no automatic repeat')


def prerequisites():
    state = read(ROOT / 'FOUNDATION_STATE.json')
    if state['state'] == 'failed_preserved':
        raise ValueError('Original foundation failed; preserve and diagnose original, never duplicate')
    if state['state'] != 'completed_clean_FL_foundation_only':
        return False, 'original foundation still active'
    value = read(ROOT / 'CLEAN_FL_VERIFIED.json')
    if not value['utility_gate']:
        raise ValueError('Completed clean-FL utility80 gate failed; no STG launch')
    assert value['state'] == 'passed' and value['rounds'] == 20 and value['roles'] == 200
    query = "Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    rows = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', query], text=True))
    rows = [rows] if isinstance(rows, dict) else rows
    for row in rows or []:
        cmd = (row.get('CommandLine') or '').replace('\\', '/').lower()
        if 'feduba_paper_implementation_20261031' in cmd and any(name in cmd for name in [
            'foundation_controller.py', 'clean_fl_controller.py', 'clean_fl_runner.py', 'verify_clean_fl.py', 'gpu_probe.py']):
            return False, 'original finite foundation process still exits: ' + str(row['ProcessId'])
    return True, 'foundation verified and original processes absent'


freeze_check('STG_FREEZE.json')
with (ROOT / 'STG_CONTROLLER_ONCE.json').open('x', encoding='utf-8') as stream:
    json.dump({'pid': os.getpid(), 'created_unix': time.time()}, stream)
with (ROOT / 'stg_console.log').open('x', encoding='utf-8', newline='\n', buffering=1) as log:
    try:
        assert not any((ROOT / n).exists() for n in ['STG_READY.json', 'STG_STARTED.json', 'STG_AUDIT_ONCE.json'])
        run('prepare_stg.py', log)
        deadline = time.time() + 86400
        while True:
            freeze_check('STG_FREEZE.json')
            okay, reason = prerequisites()
            if okay:
                try:
                    guard(read(ROOT / 'GPU_PREFLIGHT_RESULT.json')['foundation_free_min_MiB'])
                    break
                except (AssertionError, RuntimeError) as error:
                    reason = str(error)
            write(ROOT / 'STG_CONTROLLER_STATE.json', {'state': 'waiting_for_foundation_or_resources',
                  'pid': os.getpid(), 'reason': reason, 'deadline_unix': deadline, 'updated_unix': time.time()})
            if time.time() >= deadline:
                raise RuntimeError('24h prerequisite/resource deadline expired without STG training')
            time.sleep(30)
        run('trigger_runner.py', log, gpu=True)
        run('verify_stg.py', log)
        write(ROOT / 'STG_CONTROLLER_STATE.json', {'state': 'completed_STG_verified_only',
              'pid': os.getpid(), 'overall_goal_complete': False, 'updated_unix': time.time()})
    except BaseException:
        write(ROOT / 'STG_CONTROLLER_STATE.json', {'state': 'failed_preserved', 'pid': os.getpid(),
              'traceback': traceback.format_exc(), 'updated_unix': time.time()})
        raise
