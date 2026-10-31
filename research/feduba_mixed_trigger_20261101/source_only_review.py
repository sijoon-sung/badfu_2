"""One AST/hash/closed-gate review, no prepare, no torch, model or fixture execution."""
import ast
import json
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode = True
from datetime import datetime, timezone
import binding_gate as gate


def main():
    p = gate.source_profile()
    files = list(gate.ROOT.glob('*.py'))
    for path in files: ast.parse(path.read_text(encoding='utf-8'))
    for name, meta in p['copied_sources'].items():
        assert gate.sha(gate.ROOT / name) == meta['sha256'] == gate.sha(meta['original_path'])
    teacher = Path(p['teacher_root'])
    assert gate.sha(teacher / 'FREEZE.json') == p['teacher_source_freeze_sha256']
    for name, digest in gate.read(teacher / 'FREEZE.json')['files'].items(): assert gate.sha(teacher / name) == digest
    assert gate.sha(teacher / 'PUBLICATION.json') == p['teacher_publication_sha256']
    # Reuse the completed original SGD contract as evidence; never execute it again.
    meta = p['inputs']['SGD_CPU_receipt']; gate.verify_meta(meta)
    receipt = gate.read(meta['path']); assert receipt['state'] == 'passed' and receipt['count'] == 4
    for name in ['core.py', 'stg_training.py']:
        assert receipt['source_hashes'][name] == gate.sha(gate.ROOT / name)
    for name in ['architecture', 'original_GPU_failure']: gate.verify_meta(p['inputs'][name])
    assert gate.read(p['inputs']['original_GPU_failure']['path'])['state'] == 'failed_preserved'
    assert not (Path(p['original_root']) / 'STG_VERIFIED.json').exists()
    assert not any((gate.ROOT / name).exists() for name in ['LAUNCH_PROFILE.json', 'RUN_FREEZE.json', 'RUN_PUBLICATION.json',
                   'PREPARE_ONCE.json', 'TRIGGER_ONCE.json', 'CONTROLLER_ONCE.json'])
    try:
        gate.run_profile()
        raise AssertionError('Source-only profile unexpectedly allowed run')
    except gate.Unlaunched: pass
    ps = "$tokens=$null;$errors=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('D:/FEDUBA_MIXED_TRIGGER_20261101/launch.ps1',[ref]$tokens,[ref]$errors);if($errors.Count){throw ($errors|Out-String)};Write-Output 'passed'"
    assert subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', ps], text=True, encoding='utf-8').strip() == 'passed'
    task = "if(Get-ScheduledTask -TaskName 'Codex-FedUBA-mixed-teacher-CPU-trigger100-20261101' -ErrorAction SilentlyContinue){throw 'Future task already exists; inspect, never duplicate'};Write-Output 'absent'"
    assert subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', task], text=True, encoding='utf-8').strip() == 'absent'
    query = "Get-CimInstance Win32_Process | Where-Object {$_.Name -in @('python.exe','pythonw.exe') -and $_.CommandLine -match 'FEDUBA_MIXED_SURROGATE_20261101'} | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', query], text=True, encoding='utf-8').strip()
    processes = json.loads(raw) if raw else []
    if isinstance(processes, dict): processes = [processes]
    assert 'torch' not in sys.modules
    result = {'state': 'passed_source_only_closed_launch_gate', 'utc': datetime.now(timezone.utc).isoformat(),
              'source_freeze_sha256': gate.sha(gate.ROOT / 'SOURCE_FREEZE.json'), 'Python_AST_files': len(files),
              'PowerShell_AST': 'passed', 'copied_helpers_exact': True, 'reused_completed_SGD_CPU4_not_reexecuted': True,
              'active_teacher13_source_hashes_unchanged': True, 'observed_teacher_processes': processes,
              'teacher_output_model_hashed_or_loaded': False, 'new_model_queries': 0, 'torch_imported': False,
              'new_fixture_or_training_executed': False, 'prepare_launch_executed': False,
              'actual_launch_profile_or_run_freeze_created': False, 'closed_run_gate_rejected_as_expected': True,
              'overall_goal_complete': False}
    gate.once('SOURCE_ONLY_REVIEW.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    try: main()
    except BaseException:
        import traceback
        gate.once('SOURCE_REVIEW_FAILURE.json', {'state': 'failed_preserved_source_only', 'traceback': traceback.format_exc()})
        raise
