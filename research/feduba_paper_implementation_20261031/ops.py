"""Read-only live FedUBA stage inventory; no launch/resume or training."""
import json
import subprocess
import time
from runtime_common import ROOT


def read_optional(name):
    path = ROOT / name
    for _ in range(10):
        try:
            return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
        except (PermissionError, json.JSONDecodeError):
            time.sleep(.05)
    raise RuntimeError('Cannot read stable state: ' + name)


snapshot = {name: read_optional(name) for name in ['PREVIOUS_QUEUE_STOPPED.json', 'CORE_CPU_RESULT.json',
            'FOUNDATION_ONCE.json', 'FOUNDATION_STATE.json',
            'GPU_PREFLIGHT_RESULT.json', 'GPU_PREFLIGHT_FAILURE.json', 'CLEAN_FL_READY.json',
            'CLEAN_FL_STATE.json', 'CLEAN_FL_CONTROLLER_STATE.json', 'CLEAN_FL_RESULT.json', 'CLEAN_FL_VERIFIED.json']}
# Keep CPU/source receipts compact; immutable full hashes stay in their files.
for name in ['CORE_CPU_RESULT.json', 'CLEAN_FL_READY.json', 'PREVIOUS_QUEUE_STOPPED.json']:
    if snapshot[name]:
        snapshot[name] = {k: v for k, v in snapshot[name].items() if k not in ['source_hashes', 'previous_state']}
manifest = read_optional('clean_fl/MANIFEST.json')
snapshot['committed_clean_rounds'] = len(manifest['rounds']) if manifest else 0
query = "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|mpiexec' -and $_.CommandLine -like '*FEDUBA_PAPER_IMPLEMENTATION_20261031*'} | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
raw = subprocess.check_output(['powershell', '-NoProfile', '-Command', query], text=True).strip()
snapshot['actual_processes'] = json.loads(raw) if raw else []
snapshot['GPU'] = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu,memory.free,memory.used', '--format=csv,noheader,nounits'], text=True).strip()
print(json.dumps(snapshot, ensure_ascii=False, indent=2))
