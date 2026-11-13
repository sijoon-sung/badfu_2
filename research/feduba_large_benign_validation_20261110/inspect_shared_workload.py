"""Observe an external workload, without assuming it is CPU-only or reading data."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    command="@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe'} | Select-Object ProcessId,CommandLine,@{Name='Created';Expression={$_.CreationDate.ToUniversalTime().ToString('o')}})|ConvertTo-Json -Compress"
    rows=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',command],text=True))
    if isinstance(rows,dict):rows=[rows]
    raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True)
    gpu_pids={int(line.strip()) for line in raw.splitlines() if line.strip().isdigit()}
    found=[];owned=[]
    for row in rows:
        value=(row.get('CommandLine') or '').replace('\\','/').lower()
        if 'research_code/live_api_service.py run ' in value:
            found.append(dict(pid=row['ProcessId'],created=row['Created'],command_sha256=hashlib.sha256(value.encode()).hexdigest(),
                nvidia_compute=row['ProcessId'] in gpu_pids,identity='Observed live API external workload; GPU sharing explicit, training status not certified'))
        if str(ROOT).replace('\\','/').lower() in value and row['ProcessId']!=os.getpid():owned.append(row['ProcessId'])
    assert not owned and not (ROOT/'fu').exists() and not (ROOT/'STATE.json').exists()
    assert len(found) in (0,2)
    result=dict(identities=found,CPU_only_hypothesis_rejected=any(x['nvidia_compute'] for x in found),
                own_tensor_loads=0,own_training_started=False,credentials_read=False,service_contacted=False,processes_stopped=False)
    (ROOT/'SHARED_WORKLOAD_OBSERVATION.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
