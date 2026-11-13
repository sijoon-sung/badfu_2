"""Read-only process identity diagnosis; never reads credentials or calls a service."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def main():
    script="@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe'} | Select-Object ProcessId,CommandLine,@{Name='Created';Expression={$_.CreationDate.ToUniversalTime().ToString('o')}})|ConvertTo-Json -Compress"
    rows=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',script],text=True))
    if isinstance(rows,dict):rows=[rows]
    raw=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True)
    gpu_pids={int(line.strip()) for line in raw.splitlines() if line.strip().isdigit()}
    identities=[];owned=[]
    for row in rows:
        command=(row.get('CommandLine') or '').replace('\\','/').lower()
        if 'research_code/live_api_service.py run ' in command:
            assert row['ProcessId'] not in gpu_pids,'Observed service uses GPU; no CPU exception'
            identities.append(dict(pid=row['ProcessId'],created=row['Created'],
                command_sha256=hashlib.sha256(command.encode()).hexdigest(),require_no_nvidia_compute=True,
                identity='Observed non-NVIDIA live API collection process; raw command retained only in original private failure log'))
        if str(ROOT).replace('\\','/').lower() in command and row['ProcessId']!=os.getpid():owned.append(row['ProcessId'])
    assert len(identities)==2 and not owned
    assert not (ROOT/'fu').exists() and not (ROOT/'STATE.json').exists()
    result=dict(identities=identities,all_absent_from_NVIDIA=True,owned_scientific_processes=owned,
                original_FU_tensor_load_or_training=False,credentials_read=False,service_contacted=False,processes_stopped=False)
    (ROOT/'CPU_SERVICE_IDENTITIES.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
