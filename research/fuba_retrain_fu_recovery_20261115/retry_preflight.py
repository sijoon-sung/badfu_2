"""Retry only a failed pre-CUDA resource check; actual training source is unchanged."""
import json
import os
import subprocess
import time
import traceback
from run import ROOT,read,sha,write,train


def main():
    for name,digest in read(ROOT/'ATTEMPT2_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    assert not (ROOT/'STARTED.json').exists() and not (ROOT/'STATE.json').exists()
    prior=read(ROOT/'FAILURE_train.json')['traceback']
    assert 'resources=ops.guard()' in prior and 'assert util <= 5 and free >= 2500' in prior
    write('ATTEMPT2_STARTED.json',{'pid':os.getpid(),'time':time.time(),'scope':'resource-only retry before any new training'})
    stable=0
    for index in range(600):
        util,free,used=[int(v.strip()) for v in subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu,memory.free,memory.used','--format=csv,noheader,nounits'],text=True).split(',')]
        stable=stable+1 if util<=5 and free>=2500 else 0
        with (ROOT/'attempt2_resources.jsonl').open('a') as f:
            f.write(json.dumps({'time':time.time(),'util_pct':util,'free_MiB':free,'used_MiB':used,'consecutive_idle_samples':stable})+'\n')
        if stable>=15:break
        time.sleep(1)
    else:raise RuntimeError('No stable GPU resource window; no training started')
    train()  # The original source performs its unchanged resource guards again.


if __name__=='__main__':
    try:main()
    except Exception:
        write('FAILURE_ATTEMPT2.json',{'traceback':traceback.format_exc()});raise
