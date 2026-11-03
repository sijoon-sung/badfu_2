"""Metadata/source-only preflight. No torch import, model load, or model forward."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
from stage_mode_diagnosis import ROOT, frozen, sha, read, write

p = frozen()
assert 'torch' not in sys.modules
for name in ['stage_mode_diagnosis.py', 'stage_mode_controller.py', 'source_checks.py']:
    ast.parse((ROOT / name).read_text(encoding='utf-8'))
for binding in [p['architecture'], p['upstream_trigger_source'], p['paper']]:
    assert sha(binding['path']) == binding['sha256']
packet = Path(p['packet_root'])
assert sha(packet / 'DELIVERY_MANIFEST.json') == p['packet_manifest_sha256']
assert sha(packet / 'DELIVERY_SEAL.json') == p['packet_seal_sha256']
m = read(packet / 'DELIVERY_MANIFEST.json')
names = [p['model_file'], p['delta_file'], *p['step_files']]
for name in names:
    meta = m['files'][name]; path = packet / name
    assert sha(path) == meta['sha256'] and path.stat().st_size == meta['bytes']
assert m['files'][p['model_file']]['sha256'] == p['model_sha256']
assert m['files'][p['delta_file']]['sha256'] == p['delta_sha256']
old = Path('D:/FEDUBA_PAPER_IMPLEMENTATION_20261031')
terminal = {}
for name in ['PAIR_CONTROLLER_STATE.json', 'PAIR_EVAL_VERIFIED.json', 'FU_benign_VERIFIED.json', 'FU_attack_VERIFIED.json', 'STG_CPU_TRIGGER_CONTROLLER_STATE.json']:
    v = read(old / name); terminal[name] = {'sha256': sha(old / name), 'state': v['state']}
assert terminal['PAIR_CONTROLLER_STATE.json']['state'] == 'completed_pair_evaluation_delivery_pending'
assert all(terminal[name]['state'] == 'passed' for name in ['PAIR_EVAL_VERIFIED.json', 'FU_benign_VERIFIED.json', 'FU_attack_VERIFIED.json'])
assert terminal['STG_CPU_TRIGGER_CONTROLLER_STATE.json']['state'] == 'completed_CPU_trigger100_verified'
command = "Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('python.exe','pythonw.exe') -and $_.CommandLine -match 'FEDUBA_PAPER_IMPLEMENTATION_20261031' } | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', command], text=True, encoding='utf-8').strip()
processes = json.loads(raw) if raw else []
if isinstance(processes, dict): processes = [processes]
assert processes == [], processes
for branch in ['benign', 'attack']:
    v = read(old / 'fu' / branch / 'MANIFEST.json')
    assert len(v['rounds']) == 20
assert not (old / 'STG_VERIFIED.json').exists()
assert read(old / 'STG_CONTROLLER_STATE.json')['state'] == 'failed_preserved'
assert 'torch' not in sys.modules
write(ROOT / 'SOURCE_CHECKS.json', {'state': 'passed_source_and_metadata_only_before_CPU8',
    'utc': datetime.now(timezone.utc).isoformat(), 'freeze_sha256': sha(ROOT / 'FREEZE.json'),
    'python_AST_files': 3, 'new_model_loads': 0, 'new_model_forwards': 0,
    'old_research_processes': processes, 'old_terminal_metadata': terminal,
    'source_and_packet_bindings_match': True, 'original_GPU_STG_failure_preserved': True,
    'source_only_no_torch_import': True, 'completed_finite_jobs_repeated': False})
print('SOURCE_CHECKS passed; zero model loads/forwards')
