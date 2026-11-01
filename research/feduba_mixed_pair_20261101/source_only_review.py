"""One stdlib source/receipt review, zero torch/model/fixture/prepare executions."""
import ast
from datetime import datetime, timezone
import subprocess
import sys
sys.dont_write_bytecode = True
from pair_binding import ROOT, FOUNDATION, read, sha, checked, once, source_profile, require_published_run, Unlaunched


def main():
    p = source_profile()
    files = sorted(ROOT.glob('*.py'))
    for path in files: ast.parse(path.read_text(encoding='utf-8'))
    copies = read(ROOT / 'COPY_PROVENANCE.json')
    for name, meta in copies['exact_copies'].items():
        assert sha(ROOT / name) == meta['sha256'] == sha(meta['original_path']), name
    for name, meta in copies['adapted_entrypoints'].items():
        assert sha(ROOT / name) == meta['adapted_sha256'], name
        assert sha(meta['original_path']) == meta['original_sha256'], name
    reused = {
        'SSS_LOGGER_CPU2_RESULT.json': ['core.py', 'sss_logging.py', 'runtime_common.py', 'FU_PROFILE.json'],
        'FU_ENGINE_CPU_RESULT.json': ['core.py', 'fu_core.py', 'fu_training.py', 'runtime_common.py', 'FU_PROFILE.json'],
        'FU_POLICY_CPU_RESULT.json': ['core.py', 'fu_core.py', 'runtime_common.py', 'FU_PROFILE.json'],
        'PAIR_EVAL_CPU_RESULT.json': ['pair_eval_core.py', 'runtime_common.py', 'FU_PROFILE.json', 'PAIR_EVAL_PROFILE.json']}
    for name, sources in reused.items():
        receipt = read(ROOT / name); assert receipt['state'] == 'passed'
        for filename in sources: assert receipt['source_hashes'][filename] == sha(ROOT / filename), filename
    for meta in p['external_evidence'].values(): checked(meta)
    checked(p['foundation_history_manifest']); checked(p['old_GPU_failure'])
    assert read(p['old_GPU_failure']['path'])['state'] == 'failed_preserved'
    assert not (FOUNDATION / 'STG_VERIFIED.json').exists()
    trigger = ROOT.__class__(p['trigger_root'])
    for name, digest in p['trigger_predeclared_files'].items(): assert sha(trigger / name) == digest
    for name, digest in read(trigger / 'SOURCE_FREEZE.json')['files'].items(): assert sha(trigger / name) == digest
    forbidden = ['PREPARE_ONCE.json', 'PREPARE_RESULT.json', 'TRIGGER_SOURCE_BINDING.json',
                 'PAIR_LAUNCH_PROFILE.json', 'PAIR_RUN_FREEZE.json', 'PAIR_PUBLICATION.json',
                 'PAIR_CONTROLLER_ONCE.json', 'SSS_ONCE.json', 'SSS_RESULT.json']
    assert all(not (ROOT / name).exists() for name in forbidden)
    try:
        require_published_run()
        raise AssertionError('Source-only pair unexpectedly allowed a numerical entrypoint')
    except Unlaunched: pass
    ps = "$tokens=$null;$errors=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('D:/FEDUBA_MIXED_PAIR_20261101/launch_pair.ps1',[ref]$tokens,[ref]$errors);if($errors.Count){throw ($errors|Out-String)};Write-Output 'passed'"
    assert subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', ps], text=True, encoding='utf-8', timeout=20).strip() == 'passed'
    ps = "if(Get-ScheduledTask -TaskName 'Codex-FedUBA-mixed-trigger-SSS-pairedFU20-20261101' -ErrorAction SilentlyContinue){throw 'Future exact task already exists'};Write-Output 'absent'"
    assert subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', ps], text=True, encoding='utf-8', timeout=20).strip() == 'absent'
    assert 'torch' not in sys.modules
    once('SOURCE_ONLY_REVIEW.json', {'state': 'passed_source_only_no_queries_or_prepare',
         'utc': datetime.now(timezone.utc).isoformat(), 'source_freeze_sha256': sha(ROOT / 'SOURCE_FREEZE.json'),
         'Python_AST_files': len(files), 'PowerShell_AST': 'passed',
         'seven_helpers_and_canonical_profiles_exact_copies': True,
         'completed_fixture_receipts_reused_not_reexecuted': list(reused),
         'current_trigger15_and_predeclared_profiles_unchanged': True,
         'new_model_queries': 0, 'torch_imports': 0, 'prepare_calls': 0,
         'trigger_output_model_or_delta_hash_reads': 0, 'new_fixtures': 0,
         'closed_numerical_gate_rejected_as_expected': True, 'future_exact_task': 'absent',
         'actual_launch_profiles_created': False, 'overall_goal_complete': False})


if __name__ == '__main__':
    try: main()
    except BaseException:
        import traceback
        once('SOURCE_REVIEW_FAILURE.json', {'state': 'failed_preserved_source_only', 'traceback': traceback.format_exc()})
        raise
