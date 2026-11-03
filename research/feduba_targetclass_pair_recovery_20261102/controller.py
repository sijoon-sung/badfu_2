"""Create both real FU20 checkpoints, audit both, then evaluate independently."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback
from pair_binding import require_published_run
from runtime_common import ROOT, read, write, sha, guard, ResourceBusy


def once(name, value):
    with (ROOT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def wait_guard(step):
    started = time.monotonic()
    while True:
        try:
            value = guard(); assert shutil.disk_usage(ROOT).free >= 80 * 2**30
            return value
        except ResourceBusy as error:
            elapsed = time.monotonic() - started
            write(ROOT / 'CONTROLLER_STATE.json', {'state': 'waiting_fixed_resources', 'pid': os.getpid(),
                'step': step, 'elapsed_seconds': elapsed, 'reason': str(error)})
            assert elapsed < 86400, 'Fixed24h resource wait exhausted'
            time.sleep(15)


def main():
    source, launch = require_published_run()
    once('CONTROLLER_ONCE.json', {'pid': os.getpid(), 'started_unix': time.time(),
          'run_publication_sha256': sha(ROOT / 'RUN_PUBLICATION.json')})
    shared = ['--catalog-root', source['catalog_root'], '--case-id', source['normal_case_id']]
    tasks = [
        ('fu_runner.py', ['--branch', 'benign', *shared], '0'),
        ('verify_fu.py', ['--branch', 'benign'], '-1'),
        ('fu_runner.py', ['--branch', 'attack', *shared], '0'),
        ('verify_fu.py', ['--branch', 'attack'], '-1'),
        ('evaluate_pair.py', shared, '0'),
        ('verify_pair_evaluation.py', shared, '0'),
        ('export_checkpoint_review.py', [], '-1')]
    for name, args, device in tasks:
        require_published_run(); resources = wait_guard(name + ' ' + ' '.join(args))
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=device)
        with (ROOT / ('console_' + name.replace('.py', '') + '_' + str(tasks.index((name, args, device))) + '.log')).open('x', encoding='utf-8') as stream:
            child = subprocess.Popen([sys.executable, '-B', '-u', str(ROOT / name), *args], cwd=ROOT,
                                     env=env, stdout=stream, stderr=subprocess.STDOUT)
            write(ROOT / 'CONTROLLER_STATE.json', {'state': 'running', 'pid': os.getpid(), 'child': child.pid,
                'step': name, 'arguments': args, 'guard': resources, 'CUDA_VISIBLE_DEVICES': device})
            code = child.wait()
        assert code == 0, name + ' exit=' + str(code)
    once('COMPLETION.json', {'state': 'completed_targetclass_pair_with_actual_checkpoints_independent_evaluation_and_remote_review',
        'evaluation_sha256': sha(ROOT / 'PAIR_EVAL_RESULT.json'),
        'independent_evaluation_sha256': sha(ROOT / 'PAIR_EVAL_VERIFIED.json'),
        'remote_review_sha256': sha(ROOT / 'REMOTE_CHECKPOINT_REVIEW.json'),
        'operational_gate': read(ROOT / 'PAIR_EVAL_RESULT.json')['minimum_operational_gate'],
        'local_delivery_complete': False, 'overall_goal_complete': False})
    write(ROOT / 'CONTROLLER_STATE.json', {'state': 'completed', 'pid': os.getpid(), 'exit_code': 0})


if __name__ == '__main__':
    try: main()
    except BaseException:
        once('CONTROLLER_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
