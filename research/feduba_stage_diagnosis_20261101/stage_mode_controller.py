"""One new bounded CPU diagnosis then independent saved-logit arithmetic check."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import json
from pathlib import Path
import subprocess
import sys
import traceback
sys.dont_write_bytecode = True
from stage_mode_diagnosis import ROOT, write, read, frozen


def main():
    frozen()
    write(ROOT / 'CONTROLLER_ONCE.json', {'pid': os.getpid(), 'model_forward_call_budget': 8})
    for phase in ['run', 'verify']:
        with (ROOT / (phase + '.log')).open('xb') as log:
            child = subprocess.Popen([sys.executable, '-B', '-u', str(ROOT / 'stage_mode_diagnosis.py'), '--phase', phase],
                                     stdout=log, stderr=subprocess.STDOUT, cwd=ROOT, env=os.environ.copy())
            temp = ROOT / 'STATE.tmp'
            temp.write_text(json.dumps({'state': 'running', 'pid': os.getpid(), 'phase': phase, 'child_pid': child.pid}), encoding='utf-8')
            os.replace(temp, ROOT / 'STATE.json')
            assert child.wait() == 0, phase + ' failed; preserve prefix without retries'
    assert read(ROOT / 'VERIFIED.json')['state'] == 'passed_independent_logit_counts_and_CE'
    temp = ROOT / 'STATE.tmp'; temp.write_text(json.dumps({'state': 'completed_CPU8_diagnosis_verified',
          'pid': os.getpid(), 'overall_goal_complete': False}), encoding='utf-8'); os.replace(temp, ROOT / 'STATE.json')


if __name__ == '__main__':
    try: main()
    except BaseException:
        write(ROOT / 'CONTROLLER_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
