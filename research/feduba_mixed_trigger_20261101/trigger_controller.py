"""Future one-shot CPU runner -> independent audit, no automatic later-stage launch."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import sys
sys.dont_write_bytecode = True
import subprocess
import traceback
import binding_gate as gate
from runtime_common import ROOT, read, write, sha


def main():
    gate.run_profile()
    publication = read(ROOT / 'RUN_PUBLICATION.json')
    assert publication['state'] == 'published_actual_mixed_teacher_trigger_profile_before_execution'
    assert publication['run_freeze_sha256'] == sha(ROOT / 'RUN_FREEZE.json')
    assert publication['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
    gate.once('CONTROLLER_ONCE.json', {'pid': os.getpid(), 'automatic_retries': 0})
    for phase, name in [('trigger', 'mixed_cpu_trigger.py'), ('audit', 'verify_mixed_cpu_trigger.py')]:
        gate.run_profile()
        with (ROOT / (phase + '.log')).open('xb') as stream:
            command = [sys.executable, '-B', '-u', str(ROOT / name)]
            child = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, env=os.environ.copy())
            write(ROOT / 'CONTROLLER_STATE.json', {'state': 'running', 'phase': phase, 'pid': os.getpid(),
                  'child_pid': child.pid, 'command': command})
            assert child.wait() == 0, phase + ' failed; preserve prefix without retry'
    assert read(ROOT / 'TRIGGER_VERIFIED.json')['state'] == 'passed_new_mixed_teacher_CPU_trigger100'
    completion = {'state': 'completed_new_mixed_teacher_CPU_trigger100_verified', 'pid': os.getpid(),
                  'result_sha256': sha(ROOT / 'TRIGGER_RESULT.json'), 'verified_sha256': sha(ROOT / 'TRIGGER_VERIFIED.json'),
                  'teacher': read(ROOT / 'TRIGGER_RESULT.json')['teacher'], 'delta': read(ROOT / 'TRIGGER_RESULT.json')['delta'],
                  'new_SSS_FU_evaluation_or_delivery_started': False, 'overall_goal_complete': False}
    gate.once('COMPLETION.json', completion); write(ROOT / 'CONTROLLER_STATE.json', completion)


if __name__ == '__main__':
    try: main()
    except BaseException:
        gate.once('CONTROLLER_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(),
            'traceback': traceback.format_exc(), 'previous_state': read(ROOT / 'CONTROLLER_STATE.json') if (ROOT / 'CONTROLLER_STATE.json').exists() else None})
        write(ROOT / 'CONTROLLER_STATE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'overall_goal_complete': False})
        raise
