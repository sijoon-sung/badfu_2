"""Exclusive teacher-only task: train once, CPU audit, four CPU probes, logit audit."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='0', PYTHONDONTWRITEBYTECODE='1')
import json
import subprocess
import sys
import time
import traceback
sys.dont_write_bytecode = True
from mixed_common import ROOT, read, write, sha, once, frozen, check_bindings, gpu_guard, ResourceBusy


def main():
    p = frozen(); check_bindings(p)
    publication = read(ROOT / 'PUBLICATION.json')
    assert publication['state'] == 'published_before_mixed_teacher_training'
    assert publication['freeze_sha256'] == sha(ROOT / 'FREEZE.json')
    assert publication['source_checks_sha256'] == sha(ROOT / 'SOURCE_CHECKS.json')
    assert read(ROOT / 'SOURCE_CHECKS.json')['state'] == 'passed_source_and_metadata_only'
    once('CONTROLLER_ONCE.json', {'pid': os.getpid(), 'profile': p['id'], 'automatic_retries': 0})
    with (ROOT / 'domain_contract.log').open('xb') as stream:
        command = [sys.executable, '-B', '-u', str(ROOT / 'domain_contract.py')]
        child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, env=os.environ.copy())
        write(ROOT / 'CONTROLLER_STATE.json', {'state': 'running', 'phase': 'CPU_domain_contract',
              'pid': os.getpid(), 'child_pid': child.pid, 'command': command, 'updated_unix': time.time()})
        assert child.wait() == 0, 'new domain contract failed; preserve without retry'
    assert read(ROOT / 'DOMAIN_CONTRACT_RESULT.json')['state'] == 'passed'
    while True:
        frozen()
        try:
            resources = gpu_guard(p); break
        except ResourceBusy as exc:
            write(ROOT / 'CONTROLLER_STATE.json', {'state': 'waiting_resource_guard_no_trainer_started',
                  'pid': os.getpid(), 'reason': str(exc), 'updated_unix': time.time()})
            time.sleep(30)
    phases = [('training', 'mixed_teacher_runner.py', []), ('CPU_audit', 'verify_mixed_teacher.py', []),
              ('CPU_endpoint', 'teacher_endpoint.py', ['--phase', 'run']),
              ('CPU_logit_audit', 'teacher_endpoint.py', ['--phase', 'verify'])]
    for phase, script, extra in phases:
        frozen()
        with (ROOT / (phase + '.log')).open('xb') as stream:
            command = [sys.executable, '-B', '-u', str(ROOT / script), *extra]
            child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, env=os.environ.copy())
            write(ROOT / 'CONTROLLER_STATE.json', {'state': 'running', 'phase': phase, 'pid': os.getpid(),
                  'child_pid': child.pid, 'command': command, 'initial_guard': resources, 'updated_unix': time.time()})
            code = child.wait()
            assert code == 0, phase + ' exit ' + str(code) + '; preserve without retry'
    assert read(ROOT / 'TRAIN_VERIFIED.json')['state'] == read(ROOT / 'ENDPOINT_VERIFIED.json')['state'] == 'passed'
    result = {'state': 'completed_teacher_only_CPU_verified_endpoint_recorded', 'pid': os.getpid(),
              'training_result_sha256': sha(ROOT / 'TRAIN_RESULT.json'), 'training_audit_sha256': sha(ROOT / 'TRAIN_VERIFIED.json'),
              'endpoint_result_sha256': sha(ROOT / 'ENDPOINT_RESULT.json'), 'endpoint_audit_sha256': sha(ROOT / 'ENDPOINT_VERIFIED.json'),
              'minimal_functional_condition_passed': read(ROOT / 'ENDPOINT_RESULT.json')['minimal_functional_condition_passed'],
              'automatic_trigger_SSS_FU_or_next_training': False, 'overall_goal_complete': False}
    once('COMPLETION.json', result); write(ROOT / 'CONTROLLER_STATE.json', result)


if __name__ == '__main__':
    try: main()
    except BaseException:
        failure = {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc(),
                   'last_controller_state': read(ROOT / 'CONTROLLER_STATE.json') if (ROOT / 'CONTROLLER_STATE.json').exists() else None}
        once('CONTROLLER_FAILURE.json', failure)
        write(ROOT / 'CONTROLLER_STATE.json', {'state': 'failed_preserved', 'pid': os.getpid(),
              'failure_file': 'CONTROLLER_FAILURE.json', 'overall_goal_complete': False})
        raise
