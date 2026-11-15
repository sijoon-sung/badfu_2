"""One evaluation subprocess with durable output; no retries or training."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
from run import ROOT, frozen, sha, write


def main():
    frozen()
    assert ROOT == Path('D:/FUBA_PUBLIC_IBA_EVALUATION_20261115')
    assert not (ROOT / 'EVALUATION_STARTED.json').exists()
    write('EXECUTION_STARTED.json', {'pid': os.getpid(), 'time': time.time(), 'automatic_retry': False})
    stable = 0
    with (ROOT / 'resource_wait.jsonl').open('x') as log:
        for _ in range(300):
            util, free = [int(v.strip()) for v in subprocess.check_output(['nvidia-smi',
                '--query-gpu=utilization.gpu,memory.free', '--format=csv,noheader,nounits'], text=True).split(',')]
            stable = stable + 1 if util <= 5 and free >= 2500 else 0
            log.write(json.dumps({'time': time.time(), 'util': util, 'free_MiB': free, 'stable': stable}) + '\n')
            log.flush()
            if stable >= 15:
                break
            time.sleep(1)
        else:
            raise RuntimeError('Resource window absent; no automatic retry')
    with (ROOT / 'evaluation.log').open('x', encoding='utf-8') as log:
        run = subprocess.run([sys.executable, '-u', '-B', str(ROOT / 'run.py'), 'evaluate'],
                             stdout=log, stderr=subprocess.STDOUT)
    write('EXECUTION_RESULT.json', {'exit_code': run.returncode, 'log_sha256': sha(ROOT / 'evaluation.log'),
                                  'time': time.time()})
    if run.returncode:
        raise SystemExit(run.returncode)


if __name__ == '__main__':
    main()
