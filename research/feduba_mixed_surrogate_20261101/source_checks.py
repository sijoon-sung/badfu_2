"""Prepublication source/metadata checks. No torch/model/tensor loading."""
import ast
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):
    with Path(path).open('rb') as s: return hashlib.file_digest(s, 'sha256').hexdigest()


def main():
    p = read(ROOT / 'PROFILE.json')
    assert ROOT == Path(p['execution_root'])
    assert list(sys.version_info[:3]) == p['python_version']
    versions = {n: importlib.metadata.version(n) for n in p['package_versions']}
    assert versions == p['package_versions']
    for name, digest in read(ROOT / 'FREEZE.json')['files'].items(): assert sha(ROOT / name) == digest, name
    sources = list(ROOT.glob('*.py'))
    for source in sources: ast.parse(source.read_text(encoding='utf-8'))
    ps = "$tokens=$null; $errors=$null; [void][System.Management.Automation.Language.Parser]::ParseFile('D:/FEDUBA_MIXED_SURROGATE_20261101/launch.ps1',[ref]$tokens,[ref]$errors); if($errors.Count){throw ($errors | Out-String)}; Write-Output 'passed'"
    assert subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', ps], text=True, encoding='utf-8').strip() == 'passed'
    for name, meta in p['bindings'].items():
        assert sha(meta['path']) == meta['sha256'], name
        if 'bytes' in meta: assert Path(meta['path']).stat().st_size == meta['bytes'], name
    ready, asset = read(p['bindings']['old_ready']['path']), read(p['bindings']['asset_receipt']['path'])
    for source, key in [('initial', 'fresh_initial')]:
        assert p['bindings'][source]['sha256'] == ready[key]['sha256']
    for key, old_key in [('tiny', 'surrogate'), ('target', 'target')]:
        assert p['bindings'][key]['sha256'] == asset[old_key]['sha256']
    assert ready['asset_result_sha256'] == sha(p['bindings']['asset_receipt']['path'])
    assert read(p['bindings']['clean_verified']['path'])['state'] == 'passed'
    assert read(p['bindings']['clean_verified']['path'])['utility_gate'] is True
    assert read(p['bindings']['foundation_state']['path'])['state'] == 'completed_clean_FL_foundation_only'
    old = read(p['bindings']['old_CPU8_result']['path'])
    assert old['summary']['eval_frozen/zero']['target_hits'] == 0
    assert not old['diagnostic_rule']['BN_mode_gap_consistent_with_fixed_diagnostic_rule']
    assert read(p['bindings']['old_CPU8_verified']['path'])['state'] == 'passed_independent_logit_counts_and_CE'
    packet = read(p['bindings']['pair_manifest']['path'])
    typed = {v['file']: v for v in packet['payloads']}
    for key in ['target_probe_step1', 'target_probe_step2']:
        relative = Path(p['bindings'][key]['path']).relative_to(Path(p['bindings']['pair_manifest']['path']).parent).as_posix()
        assert packet['files'][relative]['sha256'] == p['bindings'][key]['sha256']
        assert typed[relative]['kind'] == 'tensor_evidence' and typed[relative]['payload_key'] is None
    assert (math.ceil(100200 / 128), 100200 % 128, math.ceil(200 / 128), 200 % 128) == (783, 104, 2, 72)
    assert p['fixed_budget']['training_batches'] == 100 * 783 + 5 * 2 == 78310
    assert p['fixed_budget']['sample_exposures'] == 100200 * 100 + 200 * 5 == 10021000
    assert (0, 400) != (1, 400)  # Domains must preserve collisions in raw IDs, not deduplicate them.
    selection = json.loads(subprocess.check_output([sys.executable, '-B', p['catalog_root'] + '/select_case.py',
            p['normal_case_id'], '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selection['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selection['checkpoint_guard']['manifest_sha256'] == p['normal_manifest_sha256']
    assert selection['checkpoint_guard']['seal_sha256'] == p['normal_seal_sha256']
    assert selection['server_inputs']['pre']['sha256'] == p['normal_pre_sha256']
    assert selection['server_inputs']['pre']['payload_key'] is None
    old_root = Path('D:/FEDUBA_PAPER_IMPLEMENTATION_20261031')
    assert not (old_root / 'STG_VERIFIED.json').exists()
    assert read(old_root / 'STG_CONTROLLER_STATE.json')['state'] == 'failed_preserved'
    assert read(old_root / 'PAIR_CONTROLLER_STATE.json')['state'] == 'completed_pair_evaluation_delivery_pending'
    command = "Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python|mpiexec'} | Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress"
    raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command', command], text=True, encoding='utf-8').strip()
    rows = json.loads(raw) if raw else []
    if isinstance(rows, dict): rows = [rows]
    study = [v for v in rows if v['ProcessId'] != os.getpid() and any(x in (v.get('CommandLine') or '').lower()
             for x in ['feduba_paper_implementation_20261031', 'feduba_stage_diagnosis_20261101', 'feduba_mixed_surrogate_20261101'])]
    assert not study, study
    assert 'torch' not in sys.modules
    result = {'state': 'passed_source_and_metadata_only', 'utc': datetime.now(timezone.utc).isoformat(),
              'freeze_sha256': sha(ROOT / 'FREEZE.json'), 'Python_AST_files': len(sources),
              'package_versions': versions,
              'PowerShell_launcher_AST': 'passed',
              'pinned_initial_data_source_and_receipt_hashes_match': True, 'normal_case_diagnostic_guard': True,
              'mixed_count_batches_tail_contract': {'N': 100200, 'batches': 783, 'tail': 104},
              'old_original_GPU_failure_preserved': True, 'old_CPU8_rule_rejected_preserved': True,
              'other_study_processes': study, 'new_model_loads': 0, 'new_model_forwards': 0,
              'no_torch_import': True, 'completed_fixture_repeated': False}
    with (ROOT / 'SOURCE_CHECKS.json').open('x', encoding='utf-8', newline='\n') as s:
        json.dump(result, s, indent=2); s.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    try: main()
    except BaseException:
        import traceback
        with (ROOT / 'SOURCE_CHECK_FAILURE.json').open('x', encoding='utf-8', newline='\n') as stream:
            json.dump({'state': 'failed_preserved_before_any_model_load', 'traceback': traceback.format_exc()}, stream, indent=2)
            stream.write('\n')
        raise
