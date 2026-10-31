"""Read-only compact state/process/manifest inventory of both independent stages."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import json
import subprocess
import time
from runtime_common import ROOT


def optional(name):
    for _ in range(20):
        try:
            return json.loads((ROOT / name).read_text(encoding='utf-8')) if (ROOT / name).exists() else None
        except (PermissionError, json.JSONDecodeError):
            time.sleep(.05)
    raise RuntimeError(name)


names = ['FOUNDATION_STATE.json', 'CLEAN_FL_STATE.json', 'CLEAN_FL_CONTROLLER_STATE.json', 'CLEAN_FL_RESULT.json',
         'CLEAN_FL_FAILURE.json', 'ASSET_CPU2_STATE.json', 'STG_READY.json', 'STG_CONTROLLER_STATE.json',
         'STG_STATE.json', 'STG_RESULT.json', 'STG_FAILURE.json', 'STG_AUDIT_STATE.json', 'STG_AUDIT_FAILURE.json']
values = {name: optional(name) for name in names}
if values['STG_READY.json']:
    values['STG_READY.json'].pop('source_hashes', None)
    values['STG_READY.json'].pop('target_external_original_IDs', None)
for name in ['CLEAN_FL_VERIFIED.json', 'STG_VERIFIED.json']:
    value = optional(name)
    if value:
        values[name] = {k: v for k, v in value.items() if k != 'history_hashes'}
for folder in ['clean_fl', 'stg']:
    value = optional(folder + '/MANIFEST.json')
    if value:
        rows = value.get('rounds', value.get('epochs'))
        values[folder + '_manifest'] = {'committed': len(rows), 'last_record': rows[-1] if rows else None}
query = "Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*FEDUBA_PAPER_IMPLEMENTATION_20261031*'} | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
raw = subprocess.check_output(['powershell', '-NoProfile', '-Command', query], text=True).strip()
values['actual_processes'] = json.loads(raw) if raw else []
values['GPU'] = subprocess.check_output(['nvidia-smi', '--query-gpu=utilization.gpu,memory.free,memory.used', '--format=csv,noheader,nounits'], text=True).strip()
print(json.dumps(values, ensure_ascii=False, indent=2))
