"""Read-only study snapshot with actual process identity; never launches jobs."""
import json
from pathlib import Path
import subprocess
import time
from study_common import ROOT


def maybe(path):
    for attempt in range(10):
        try:
            return json.loads(path.read_text(encoding='utf-8')) if path.exists() else None
        except (PermissionError, json.JSONDecodeError):
            time.sleep(.05)
    raise RuntimeError('Cannot read stable state: ' + str(path))


state = maybe(ROOT / 'STUDY_STATE.json')
snapshot = {'study': state, 'prepared': (ROOT / 'PREPARED.json').exists()}
if state and state.get('root'):
    active = Path(state['root'])
    snapshot['active'] = {n: maybe(active / n) for n in ['STATE.json', 'CONTROLLER_STATE.json', 'RESULT.json']}
    manifest = maybe(active / 'run/MANIFEST.json')
    snapshot['committed_rounds'] = len(manifest['rounds']) if manifest else 0
command = "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|mpiexec' -and $_.CommandLine -like '*FUBA_SEED_REPRO_20261031*'} | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
raw = subprocess.check_output(['powershell', '-NoProfile', '-Command', command], text=True).strip()
snapshot['actual_processes'] = json.loads(raw) if raw else []
snapshot['GPU'] = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu,memory.free,memory.used',
                                          '--format=csv,noheader,nounits'], text=True).strip()
print(json.dumps(snapshot, ensure_ascii=False, indent=2))
