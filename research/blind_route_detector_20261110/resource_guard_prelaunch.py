"""Read-only DISLAB admission. Never stops other work."""
import ctypes
import json
import shutil
import subprocess
import time
from pathlib import Path


def inspect():
    class Memory(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)]+[(k, ctypes.c_ulonglong) for k in
                   ('total', 'available', 'total_page', 'available_page', 'total_virtual', 'available_virtual', 'extended')]
    m = Memory(); m.length = ctypes.sizeof(m)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu,memory.free', '--format=csv,noheader,nounits'], text=True)
    utilization, free = map(int, gpu.strip().splitlines()[0].split(','))
    command = "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw|mpiexec)\\.exe$' } | Select-Object ProcessId,Name,CommandLine) | ConvertTo-Json -Compress"
    output = subprocess.check_output(['powershell', '-NoProfile', '-NonInteractive', '-Command', command], text=True)
    processes = json.loads(output) if output.strip() else []
    if isinstance(processes, dict): processes = [processes]
    own_root = str(Path(__file__).resolve().parent).replace('\\', '/').lower()
    competitors = [p for p in processes if own_root not in (p.get('CommandLine') or '').replace('\\', '/').lower()]
    return dict(memory_gib=m.available/2**30, disk_gib=shutil.disk_usage('D:/').free/2**30,
                gpu_free_mib=free, gpu_util=utilization, competitors=competitors)


def admit(cfg):
    a = cfg['admission']; started = time.monotonic(); observations = []
    while True:
        row = inspect(); observations.append(row)
        ok = (row['memory_gib'] >= a['memory_gib'] and row['disk_gib'] >= a['disk_gib'] and
              row['gpu_free_mib'] >= a['gpu_free_mib'] and row['gpu_util'] <= a['gpu_util_max'] and not row['competitors'])
        if ok: return observations
        if time.monotonic()-started >= a['wait_seconds']:
            raise RuntimeError('Admission failed without starting GPU search: '+json.dumps(row))
        time.sleep(10)
