"""Once-only dependency wait; no CUDA context before the competing job exits."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'stage05'


def write(obj):
    temp=OUT/'WAIT_STATE.json.tmp';temp.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf8')
    os.replace(temp,OUT/'WAIT_STATE.json')


def main():
    os.chdir(ROOT)
    freeze=json.loads((ROOT/'STAGE05_WAIT_FREEZE.json').read_text(encoding='utf8'))
    for name,h in freeze['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
    with (OUT/'WAIT_STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time()},f)
    log=(ROOT/'stage05_delete_stdout.log').open('x',encoding='utf8',buffering=1)
    err=(ROOT/'stage05_delete_stderr.log').open('x',encoding='utf8',buffering=1)
    start=time.monotonic()
    while time.monotonic()-start<4*60*60:
        assert not (OUT/'DELETE_STARTED.json').exists() and not (OUT/'DELETE_COMPLETED.json').exists(),'already started'
        script="Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|mpiexec'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
        raw=subprocess.check_output(['powershell','-NoProfile','-Command',script],text=True).strip()
        rows=json.loads(raw) if raw else []
        if isinstance(rows,dict):rows=[rows]
        blocked=[p['ProcessId'] for p in rows if p['ProcessId']!=os.getpid() and any(x in (p.get('CommandLine') or '') for x in ['FEDUBA_PAPER_IMPLEMENTATION_20261031','FUBA_SEED_REPRO_20261031','mpiexec'])]
        gpu=subprocess.check_output(['nvidia-smi','--query-gpu=utilization.gpu,memory.free,memory.used','--format=csv,noheader,nounits'],text=True).strip()
        util,free,used=map(int,gpu.splitlines()[0].split(','))
        if not blocked and free>=3072 and util<=10:
            write({'state':'invoking_once','pid':os.getpid(),'time':time.time(),'GPU':gpu})
            run=subprocess.run([sys.executable,'-u',str(ROOT/'stage05_delete.py')],stdout=log,stderr=err,cwd=ROOT)
            write({'state':'completed' if run.returncode==0 else 'failed_preserved_no_retry',
                   'pid':os.getpid(),'time':time.time(),'exit_code':run.returncode});return
        write({'state':'waiting_for_competing_job','pid':os.getpid(),'time':time.time(),
               'competing_PIDs':blocked,'GPU':gpu,'seconds_waited':time.monotonic()-start})
        time.sleep(30)
    write({'state':'resource_wait_expired','pid':os.getpid(),'time':time.time(),'inference_started':False})


if __name__=='__main__':
    try:main()
    except BaseException:
        write({'state':'controller_failure_preserved','pid':os.getpid(),'time':time.time(),'traceback':traceback.format_exc()});raise
