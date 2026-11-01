"""Fresh guarded CUDA entry; unrelated service arguments are never serialized."""
import json,subprocess,time
from sourcepair_pilot import cpu_guard


def guard():
    cpu=cpu_guard()
    memory=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
        'Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory | Select-Object AvailableBytes,CommittedBytes,CommitLimit | ConvertTo-Json -Compress'],text=True))
    assert int(memory['AvailableBytes'])>=8*1024**3
    assert int(memory['CommitLimit'])-int(memory['CommittedBytes'])>=16*1024**3
    inventory=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
        'Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in @(13000,31756,37492)} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress'],text=True))
    if isinstance(inventory,dict):inventory=[inventory]
    inv={int(v['ProcessId']):v['CommandLine'] for v in inventory}
    assert 'llama-server' in inv.get(13000,'')
    assert 'server.py --port 8767' in inv.get(31756,'')
    assert 'advanced_prediction_service.py' in inv.get(37492,'') and '--port 8769' in inv[37492]
    samples=[]
    for _ in range(3):
        row=subprocess.check_output(['nvidia-smi','--query-gpu=memory.total,memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip()
        total,used,free,util=map(int,row.split(','));assert total==10240 and free>=4096 and util<=5
        pids=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True).splitlines()
        assert {int(v.strip()) for v in pids if v.strip()}<=set(inv),'competing GPU compute process'
        samples.append({'total_MiB':total,'used_MiB':used,'free_MiB':free,'utilization_pct':util});time.sleep(1)
    return {'CPU':cpu,'memory':memory,'GPU':samples,'existing_services':{
        13000:'LMStudio llama-server; arguments omitted',31756:'prediction service port8767',37492:'advanced prediction service port8769'}}
