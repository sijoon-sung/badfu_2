"""Once stdlib-only actual recovery binding; no model loads or numerical imports."""
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
from recovery_io import ROOT, OLD, CPU, OPS, FOUNDATION, OLD_INPUTS, read, sha, once, source_check, processes, ps_json, original_module, tensor_path


def meta(path):
    path = Path(path)
    return {'path': str(path), 'sha256': sha(path), 'bytes': path.stat().st_size}


def main():
    p = source_check()
    publication = read(ROOT / 'SOURCE_PUBLICATION.json')
    assert publication['state'] == 'published_closed_recovery_source_before_metadata_prepare'
    assert publication['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
    assert not (ROOT / 'LAUNCH_PROFILE.json').exists()
    once('PREPARE_ONCE.json', {'pid': os.getpid(), 'model_loads': 0, 'model_forwards': 0})
    original = original_module(); original.require_published_run()
    assert sha(OLD / 'SOURCE_FREEZE.json') == p['required_original_source_freeze_sha256']
    assert sha(OLD / 'PAIR_RUN_FREEZE.json') == p['required_original_pair_run_freeze_sha256']
    assert sha(CPU / 'AUDIT_RESULT.json') == p['required_CPU_prefix_result_sha256']
    assert sha(OPS / 'PREFIX_PRESERVED.json') == p['required_prefix_preserved_sha256']
    audit, prefix = read(CPU / 'AUDIT_RESULT.json'), read(OPS / 'PREFIX_PRESERVED.json')
    assert audit['state'] == 'passed_new_CPU_attack_prefix46_audit'
    assert (audit['saved_roles'], audit['saved_epochs'], audit['saved_batches'], audit['forward_calls']) == (46, 230, 4600, 0)
    for name, anchor in prefix['all_original_prefix_files'].items():
        path = (OLD / name).resolve(); assert path.is_relative_to(OLD.resolve())
        assert sha(path) == anchor['sha256'] and path.stat().st_size == anchor['bytes'], name
    relevant = [r for r in processes() if r['ProcessId'] not in [os.getpid(), os.getppid()] and
        any(root in (r.get('CommandLine') or '').lower() for root in ['feduba_mixed_pair_20261101',
            'feduba_mixed_attack_prefix_guard_v2_20261101', 'feduba_mixed_attack_resume_20261101',
            'feduba_mixed_pair_memory_recovery_20261101'])]
    assert not relevant, [r['ProcessId'] for r in relevant]
    terminal = ps_json("$c=Get-ScheduledTask -TaskName 'Codex-FedUBA-mixed-attack-prefix46-CPU-audit-guard-v2-20261101';$ci=Get-ScheduledTaskInfo -InputObject $c;$o=Get-ScheduledTask -TaskName 'Codex-FedUBA-mixed-trigger-SSS-pairedFU20-20261101';$oi=Get-ScheduledTaskInfo -InputObject $o;[pscustomobject]@{CPU_task=@{state=[string]$c.State;lastResult=[long]$ci.LastTaskResult};original_task=@{state=[string]$o.State;lastResult=[long]$oi.LastTaskResult};utc=(Get-Date).ToUniversalTime().ToString('o')} | ConvertTo-Json -Depth 3 -Compress")
    assert terminal['CPU_task']['state'] == terminal['original_task']['state'] == 'Ready'
    assert terminal['CPU_task']['lastResult'] == 0 and terminal['original_task']['lastResult'] == 1
    terminal['relevant_original_processes'] = []
    once('TERMINAL_OBSERVATION.json', terminal)
    selected = json.loads(subprocess.check_output([sys.executable, '-B', str(Path(p['catalog_root']) / 'select_case.py'),
               p['case_id'], '--purpose', 'diagnostic'], text=True, encoding='utf-8', timeout=60))
    assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    selection = read(OLD / 'SSS_RESULT.json')
    assert selected['server_inputs']['pre']['sha256'] == selection['pre_checkpoint']['sha256']
    assert read(OLD / 'FU_benign_VERIFIED.json')['state'] == 'passed'
    case_guard = {'state': selected['guard_state'], 'case_id': p['case_id'], 'purpose': 'diagnostic',
                  'catalog_root': p['catalog_root'], 'server_inputs_pre': selected['server_inputs']['pre']}
    once('CASE_GUARD.json', case_guard)
    for m in [audit['round4_incoming_for_resume'], *[v['checkpoint'] for v in audit['partial_round5_role_metadata']],
              selection['delta'], read(OLD / 'FU_benign_RESULT.json')['after']]:
        path = tensor_path(m); assert sha(path) == m['sha256'] and path.stat().st_size == m['bytes']
    assert not (OLD / 'fu/attack/trained/round05_client10.pt').exists()
    canonical = read(OLD / 'CLEAN_FL_PROFILE.json')
    ready = read(OLD / 'CLEAN_FL_READY.json')
    data_files = {}
    for name, digest in ready['data_files_sha256'].items():
        path = Path(canonical['data_root']) / 'cifar-10-batches-py' / name
        value = meta(path); assert value['sha256'] == digest, name; data_files[name] = value
    once('DATA_CHECKS.json', {'state': 'passed_existing_CIFAR_file_hashes_metadata_only', 'files': data_files,
          'model_loads': 0, 'model_forwards': 0, 'new_dataset_generated': False})
    receipts = {'CPU_RESULT': meta(CPU / 'AUDIT_RESULT.json'), 'CPU_SOURCE_FREEZE': meta(CPU / 'CPU_AUDIT_FREEZE.json'),
        'CPU_PUBLICATION': meta(CPU / 'CPU_AUDIT_PUBLICATION.json'), 'PREFIX_PRESERVED': meta(OPS / 'PREFIX_PRESERVED.json'),
        'OPS_RESULT': meta(OPS / 'OPS_RESULT.json'), 'ORIGINAL_SOURCE_FREEZE': meta(OLD / 'SOURCE_FREEZE.json'),
        'ORIGINAL_RUN_FREEZE': meta(OLD / 'PAIR_RUN_FREEZE.json'), 'ORIGINAL_PUBLICATION': meta(OLD / 'PAIR_PUBLICATION.json'),
        'ORIGINAL_ATTACK_FAILURE': meta(OLD / 'FU_attack_FAILURE.json'),
        'ORIGINAL_CONTROLLER_FAILURE': meta(OLD / 'PAIR_CONTROLLER_FAILURE.json'),
        'ORIGINAL_ATTACK_MANIFEST': meta(OLD / 'fu/attack/MANIFEST.json'),
        'ORIGINAL_ATTACK_EVENTS': meta(OLD / 'fu/attack/events.jsonl'),
        'FOUNDATION_MANIFEST': meta(FOUNDATION / 'clean_fl/MANIFEST.json'),
        'CLEAN_SPLIT': meta(FOUNDATION / 'CLEAN_SPLIT.json'),
        'TERMINAL_OBSERVATION': meta(ROOT / 'TERMINAL_OBSERVATION.json'),
        'CASE_GUARD': meta(ROOT / 'CASE_GUARD.json'), 'DATA_CHECKS': meta(ROOT / 'DATA_CHECKS.json')}
    for name in sorted(OLD_INPUTS):
        receipts['CANONICAL:' + name] = meta(OLD / name)
    binding = {'state': 'prepared_actual_recovery_input_binding_metadata_only', 'receipts': receipts,
        'CPU_result_sha256': sha(CPU / 'AUDIT_RESULT.json'), 'CPU_task_last_result': 0,
        'prefix_preserved_sha256': sha(OPS / 'PREFIX_PRESERVED.json'),
        'round4_incoming_for_resume': audit['round4_incoming_for_resume'],
        'partial_round5_role_metadata': audit['partial_round5_role_metadata'],
        'delta': selection['delta'], 'benign_after': read(OLD / 'FU_benign_RESULT.json')['after'],
        'pre': selected['server_inputs']['pre'], 'original_files_modified': False,
        'model_loads': 0, 'model_forwards': 0}
    once('RECOVERY_INPUT_BINDING.json', binding)
    actual = {'id': p['id'] + '.actual', 'launch_enabled': True, 'source_profile_sha256': sha(ROOT / 'SOURCE_PROFILE.json'),
        'input_binding_sha256': sha(ROOT / 'RECOVERY_INPUT_BINDING.json'), 'CPU_result_sha256': binding['CPU_result_sha256'],
        'original_attack_manifest_sha256': receipts['ORIGINAL_ATTACK_MANIFEST']['sha256'],
        'catalog_root': p['catalog_root'], 'case_id': p['case_id'], 'case_purpose': 'diagnostic',
        'reused_roles': 46, 'new_roles': 154, 'new_epochs': 770, 'new_batches': 15400,
        'effective_roles': 200, 'effective_epochs': 1000, 'effective_batches': 20000,
        'original_failed_unsaved_batches': 100, 'physical_batches_including_failure': 20100}
    once('LAUNCH_PROFILE.json', actual)
    names = set(read(ROOT / 'SOURCE_FREEZE.json')['files']) | {'SOURCE_FREEZE.json', 'SOURCE_PUBLICATION.json',
        'RECOVERY_INPUT_BINDING.json', 'LAUNCH_PROFILE.json', 'TERMINAL_OBSERVATION.json', 'CASE_GUARD.json', 'DATA_CHECKS.json'}
    once('RUN_FREEZE.json', {'state': 'frozen_actual_recovery154_and_independent_pair_evaluation',
          'files': {name: sha(ROOT / name) for name in sorted(names)}})
    assert 'torch' not in sys.modules
    once('PREPARE_RESULT.json', {'state': 'passed_actual_recovery_metadata_preparation', 'model_loads': 0,
          'model_forwards': 0, 'new_dataset_or_initial_generated': False, 'actual_profile_before_execution': True,
          'source_freeze_sha256': sha(ROOT / 'SOURCE_FREEZE.json'), 'run_freeze_sha256': sha(ROOT / 'RUN_FREEZE.json')})
    print(json.dumps({'state': 'passed_actual_recovery_metadata_preparation', 'model_loads': 0, 'model_forwards': 0}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        once('PREPARE_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
