"""Future one-time SSS -> benign FU -> attack FU -> two full evaluations; code-only."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
import json
import subprocess
import sys
import time
import traceback
from runtime_common import ROOT, read, write, guard, freeze_check


def processes():
    query = "Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    rows = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', query], text=True))
    return [rows] if isinstance(rows, dict) else rows or []


def wait_idle(step):
    deadline = time.time() + 86400
    while True:
        freeze_check('PAIR_RUN_FREEZE.json')
        peers = [r for r in processes() if r['ProcessId'] not in [os.getpid(), os.getppid()] and
                 'feduba_paper_implementation_20261031' in (r.get('CommandLine') or '').lower() and
                 any(n in (r.get('CommandLine') or '').lower() for n in ['stg_controller.py', 'trigger_runner.py',
                     'verify_stg.py', 'sss_runner.py', 'verify_sss.py', 'fu_runner.py', 'verify_fu.py',
                     'evaluate_pair.py', 'verify_pair_evaluation.py', 'paired_controller.py'])]
        if peers:
            reason = 'Existing finite stage process still exits: ' + str([r['ProcessId'] for r in peers])
        else:
            try:
                guard(read(ROOT / 'GPU_PREFLIGHT_RESULT.json')['foundation_free_min_MiB'])
                return
            except (AssertionError, RuntimeError) as error:
                reason = str(error)
        write(ROOT / 'PAIR_CONTROLLER_STATE.json', {'state': 'waiting_for_resources_or_original_exit',
              'pid': os.getpid(), 'step': step, 'reason': reason, 'updated_unix': time.time()})
        if time.time() > deadline: raise RuntimeError('Fixed 24h resource wait exhausted; no automatic relaunch')
        time.sleep(15)


def run(name, log, p, gpu=False, branch=None):
    freeze_check('PAIR_RUN_FREEZE.json')
    if gpu: wait_idle(name)
    args = [sys.executable, '-u', str(ROOT / name)]
    if name in ['sss_runner.py', 'fu_runner.py', 'evaluate_pair.py', 'verify_pair_evaluation.py']:
        args += ['--catalog-root', p['catalog_root'], '--case-id', p['required_clean_case_id']]
    if branch: args += ['--branch', branch]
    env = os.environ.copy(); env['CUDA_VISIBLE_DEVICES'] = '0' if gpu else '-1'
    env['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    child = subprocess.Popen(args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    write(ROOT / 'PAIR_CONTROLLER_STATE.json', {'state': 'running', 'pid': os.getpid(), 'step': name,
          'branch': branch, 'child_pid': child.pid, 'updated_unix': time.time()})
    if child.wait(): raise RuntimeError(name + ' failed; preserved, no automatic repeat')


def main():
    freeze_check('PAIR_RUN_FREEZE.json')
    p = read(ROOT / 'PAIR_LAUNCH_PROFILE.json')
    assert p['launch_enabled'] and p['case_purpose'] == 'diagnostic'
    assert read(ROOT / 'STG_CONTROLLER_STATE.json')['state'] == 'completed_STG_verified_only'
    assert read(ROOT / 'STG_VERIFIED.json')['state'] == 'passed'
    assert read(ROOT / 'CLEAN_DELIVERY_COMPLETE.json')['state'] == 'normal_foundation_delivery_and_three_host_diagnostic_registration_complete'
    for n in ['SSS_LAUNCH_PROFILE.json', 'FU_LAUNCH_PROFILE.json', 'PAIR_EVAL_LAUNCH_PROFILE.json']:
        value = read(ROOT / n)
        assert value['launch_enabled'] and value['required_clean_case_id'] == p['required_clean_case_id']
    assert read(ROOT / 'PAIR_EVAL_CPU_RESULT.json')['state'] == 'passed'
    with (ROOT / 'PAIR_CONTROLLER_ONCE.json').open('x', encoding='utf-8') as stream:
        json.dump({'pid': os.getpid(), 'created_unix': time.time()}, stream)
    for name in ['SSS_ONCE.json', 'SSS_RESULT.json', 'FU_benign_ONCE.json', 'FU_attack_ONCE.json',
                 'PAIR_EVAL_ONCE.json', 'PAIR_EVAL_AUDIT_ONCE.json', 'PAIR_EVAL_RESULT.json']:
        assert not (ROOT / name).exists(), 'Existing finite artifact: ' + name
    with (ROOT / 'pair_console.log').open('x', encoding='utf-8', newline='\n', buffering=1) as log:
        run('sss_runner.py', log, p, gpu=True)
        run('verify_sss.py', log, p)
        for branch in ['benign', 'attack']:
            run('fu_runner.py', log, p, gpu=True, branch=branch)
            run('verify_fu.py', log, p, branch=branch)
        run('evaluate_pair.py', log, p, gpu=True)
        run('verify_pair_evaluation.py', log, p, gpu=True)
    assert read(ROOT / 'PAIR_EVAL_VERIFIED.json')['state'] == 'passed'
    write(ROOT / 'PAIR_CONTROLLER_STATE.json', {'state': 'completed_pair_evaluation_delivery_pending',
          'pid': os.getpid(), 'updated_unix': time.time(),
          'minimum_operational_gate_passed': read(ROOT / 'PAIR_EVAL_RESULT.json')['minimum_operational_gate']['passed'],
          'overall_goal_complete': False, 'remaining': ['readonly_delivery', 'catalogue_index_guards', 'detection_validation']})


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'PAIR_CONTROLLER_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
