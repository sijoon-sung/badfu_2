"""CPU-only resource entry; no GPU allowlist change or CUDA operation."""
import json,subprocess
from sourcepair_pilot import cpu_guard


def guard():
    cpu=cpu_guard()
    memory=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
        'Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory | Select-Object AvailableBytes,CommittedBytes,CommitLimit | ConvertTo-Json -Compress'],text=True))
    assert int(memory['AvailableBytes'])>=8*1024**3
    assert int(memory['CommitLimit'])-int(memory['CommittedBytes'])>=16*1024**3
    return {'CPU':cpu,'memory':memory,'device':'CPU_only_no_CUDA'}
