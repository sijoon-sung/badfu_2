"""Read-only DISLAB admission. Never stops other work."""
import ctypes
import hashlib
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
    command = "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw|mpiexec)\\.exe$' } | Select-Object ProcessId,Name,CommandLine,@{Name='Created';Expression={$_.CreationDate.ToUniversalTime().ToString('o')}}) | ConvertTo-Json -Compress"
    output = subprocess.check_output(['powershell', '-NoProfile', '-NonInteractive', '-Command', command], text=True)
    processes = json.loads(output) if output.strip() else []
    if isinstance(processes, dict): processes = [processes]
    # Main controller and its isolated per-case search children share this root.
    study_root = Path('D:/FEDUBA_DELETION_ROUND_REPEATS_20261111').resolve()
    assert Path(__file__).resolve().is_relative_to(study_root)
    own_root = str(study_root).replace('\\', '/').lower()
    compute = subprocess.check_output(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader,nounits'], text=True)
    compute_pids = {int(line.strip()) for line in compute.splitlines() if line.strip().isdigit()}
    ignored_services = []
    competitors = []
    service_identities = json.loads((Path(__file__).resolve().parent/'SHARED_SERVICE_IDENTITIES.json').read_text())
    for p in processes:
        command_line = (p.get('CommandLine') or '').replace('\\', '/').lower()
        if own_root in command_line: continue
        # Observed resident CPU gateway, not a trainer. Require exact command
        # and absence from NVIDIA compute PID inventory, never kill it.
        gateway = '"c:/users/dislab/appdata/local/hermes/tools/python-3.14.7+20260901-win32-x64/python.exe" -m hermes_cli.main gateway run'
        if command_line == gateway and p['ProcessId'] not in compute_pids:
            ignored_services.append(dict(pid=p['ProcessId'], identity='observed hermes CPU gateway', nvidia_compute=False))
        elif any(hashlib.sha256(command_line.encode()).hexdigest() == s['command_sha256'] for s in service_identities):
            ignored_services.append(dict(pid=p['ProcessId'], identity='explicitly admitted shared external workload',
                                         created=p['Created'], command_sha256=hashlib.sha256(command_line.encode()).hexdigest(),
                                         nvidia_compute=p['ProcessId'] in compute_pids, shared_gpu=True))
        else: competitors.append(p)
    return dict(memory_gib=m.available/2**30, disk_gib=shutil.disk_usage('D:/').free/2**30,
                gpu_free_mib=free, gpu_util=utilization, competitors=competitors, ignored_services=ignored_services)


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
