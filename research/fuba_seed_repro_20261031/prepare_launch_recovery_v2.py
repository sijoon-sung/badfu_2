"""Preserve terminated attempt; copy only immutable inputs into a new attempt root."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
from study_common import ROOT, read, sha, write, once, verify_freeze

verify_freeze()
once('RECOVERY_PREPARE_V2_ONCE.json')
for name, digest in read(ROOT / 'RECOVERY_PREPARE_V2_FREEZE.json')['files'].items():
    assert sha(ROOT / name) == digest, name
old = ROOT / 'seeds/seed_5129832'
command = "Get-CimInstance Win32_Process -Filter 'ProcessId=11688 OR ProcessId=8400 OR ProcessId=15836' | Select-Object ProcessId | ConvertTo-Json -Compress"
assert not subprocess.check_output(['powershell', '-NoProfile', '-Command', command], text=True).strip()
task = "Get-ScheduledTask | Where-Object {$_.TaskName -eq 'Codex-FUBA-ten-seed-repro-20261031'} | Select-Object TaskName | ConvertTo-Json -Compress"
assert not subprocess.check_output(['powershell', '-NoProfile', '-Command', task], text=True).strip()
assert not (old / 'run/MANIFEST.json').exists() and not list((old / 'run').rglob('*.pt'))
events = [json.loads(line) for line in (old / 'run/events.jsonl').read_text(encoding='utf-8').splitlines()]
assert [(e['round'], e['client'], e['phase'], e['epoch']) for e in events] == [(1, 0, 'benign', i) for i in [1, 2, 3]]
incident = ROOT / 'incidents/first_launch_terminated'
incident.mkdir(parents=True, exist_ok=False)
old_files = {f.relative_to(old).as_posix(): {'sha256': sha(f), 'bytes': f.stat().st_size}
             for f in old.rglob('*') if f.is_file()}
for name in ['STUDY_STATE.json', 'STUDY_ONCE.json', 'study_console.log', 'seed_5129832_controller.py.log']:
    if (ROOT / name).exists():
        shutil.copyfile(ROOT / name, incident / name)
for name in ['STATE.json', 'CONTROLLER_STATE.json', 'CONTROLLER_ONCE.json', 'STARTED.json', 'console.log', 'run/events.jsonl']:
    dest = incident / 'attempt1' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(old / name, dest)
write(incident / 'ORIGINAL_FILES.json', {'root': str(old), 'files': old_files,
      'all_original_files_kept_in_place': True, 'complete_phases': 0, 'committed_rounds': 0})
new = ROOT / 'seeds/seed_5129832_recovery1'
new.mkdir(exist_ok=False)
immutable = list(read(old / 'FREEZE.json')['files']) + ['FREEZE.json', 'READY.json', 'author_model.py', 'initial.pt', 'SPLIT.json']
for name in immutable:
    shutil.copyfile(old / name, new / name)
    assert sha(new / name) == sha(old / name), name
prepared = copy.deepcopy(read(ROOT / 'PREPARED.json'))
assert prepared['seeds'][0]['seed'] == 5129832
prepared['seeds'][0]['root'] = str(new)
prepared['recovery'] = {'original_root': str(old), 'replacement_root': str(new),
                        'initial_SPLIT_READY_source_hashes_unchanged': True,
                        'completed_work_repeated': False, 'uncommitted_role_recomputed': True}
write(ROOT / 'PREPARED_RECOVERY.json', prepared)
write(ROOT / 'LAUNCH_RECOVERY_READY.json', {'state': 'passed', 'old_pids_absent': [11688, 8400, 15836],
      'old_task_absent': True, 'old_files': old_files, 'recovery_root': str(new),
      'PREPARED_RECOVERY_sha256': sha(ROOT / 'PREPARED_RECOVERY.json'),
      'termination_cause': 'unknown; scheduler operational logging was disabled',
      'old_input_hashes_identical': True, 'old_completed_phase_count': 0})
print(json.dumps({'state': 'passed', 'original_attempt_preserved': True, 'immutable_inputs_copied_exact': True}))
