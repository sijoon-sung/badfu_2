"""One recovery controller; never starts completed SSS, benign FU, or CPU46 jobs."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
import subprocess
import sys
import time
import traceback
from recovery_io import ROOT, OLD, read, write, once, require_published_run, guard, memory_guard, processes, ResourceBusy


def wait_resources(step, gpu):
    deadline = time.time() + 86400
    while True:
        require_published_run()
        try:
            if gpu:
                value = guard(4000)
            else:
                value = {'memory': memory_guard()}
                peers = [r for r in processes() if r['ProcessId'] not in [os.getpid(), os.getppid()] and
                    any(root in (r.get('CommandLine') or '').lower() for root in
                        ['feduba_mixed_pair_20261101', 'feduba_mixed_attack_recovery_run_20261101']) and
                    any(name in (r.get('CommandLine') or '').lower() for name in
                        ['fu_runner.py', 'resume_attack.py', 'verify_fu.py', 'evaluate_pair.py', 'verify_pair_evaluation.py'])]
                if peers: raise ResourceBusy('Existing relevant numerical process ' + str([r['ProcessId'] for r in peers]))
            return value
        except ResourceBusy as error:
            write(ROOT / 'RECOVERY_CONTROLLER_STATE.json', {'state': 'waiting_for_fixed_resources',
                'pid': os.getpid(), 'step': step, 'reason': str(error), 'updated_unix': time.time()})
            if time.time() > deadline: raise RuntimeError('Fixed 24h resource wait exhausted; no retry')
            time.sleep(15)


def run(name, log, profile, gpu, branch=False):
    resources = wait_resources(name, gpu)
    args = [sys.executable, '-B', '-u', str(ROOT / name)]
    if name in ['resume_attack.py', 'evaluate_pair.py', 'verify_pair_evaluation.py']:
        args += ['--catalog-root', profile['catalog_root'], '--case-id', profile['case_id']]
    if branch: args += ['--branch', 'attack']
    env = os.environ.copy(); env['CUDA_VISIBLE_DEVICES'] = '0' if gpu else '-1'
    env['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    child = subprocess.Popen(args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    write(ROOT / 'RECOVERY_CONTROLLER_STATE.json', {'state': 'running', 'pid': os.getpid(),
          'step': name, 'child_pid': child.pid, 'resources': resources, 'updated_unix': time.time()})
    if child.wait(): raise RuntimeError(name + ' failed; preserved; no automatic repeat')


def main():
    require_published_run()
    profile = read(ROOT / 'LAUNCH_PROFILE.json')
    once('RECOVERY_CONTROLLER_ONCE.json', {'pid': os.getpid(), 'started_unix': time.time()})
    for n in ['RECOVERY_ATTACK_ONCE.json', 'FU_attack_RESULT.json', 'FU_attack_AUDIT_ONCE.json',
              'PAIR_EVAL_ONCE.json', 'PAIR_EVAL_AUDIT_ONCE.json', 'PAIR_EVAL_RESULT.json']:
        assert not (ROOT / n).exists(), n
    with (ROOT / 'recovery_console.log').open('x', encoding='utf-8', newline='\n', buffering=1) as log:
        run('resume_attack.py', log, profile, True)
        run('verify_fu.py', log, profile, False, branch=True)
        assert read(ROOT / 'FU_attack_VERIFIED.json')['state'] == 'passed'
        run('evaluate_pair.py', log, profile, True)
        run('verify_pair_evaluation.py', log, profile, True)
    assert read(ROOT / 'PAIR_EVAL_VERIFIED.json')['state'] == 'passed'
    completion = {'state': 'completed_recovered_attack_and_independent_pair_evaluation_delivery_pending',
        'pid': os.getpid(), 'reused_original_roles': 46, 'executed_here_roles': 154,
        'minimum_operational_gate_passed': read(ROOT / 'PAIR_EVAL_RESULT.json')['minimum_operational_gate']['passed'],
        'overall_goal_complete': False, 'remaining': ['readonly_delivery', 'catalogue_index_guards', 'detection_validation']}
    write(ROOT / 'COMPLETION.json', completion)
    write(ROOT / 'RECOVERY_CONTROLLER_STATE.json', completion)


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'RECOVERY_CONTROLLER_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
