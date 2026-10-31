"""One CPU metadata-only binding of completed STG to the already declared paired study."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import torch
from runtime_common import ROOT, read, sha, freeze_check, write
from trigger_binding import verified_cpu_trigger


def create(name, value):
    with (ROOT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog-root', type=Path, required=True)
    parser.add_argument('--prepublished-code-commit', required=True)
    args = parser.parse_args()
    freeze_check('PAIR_PREPARE_FREEZE.json')
    for name in ['STG_FREEZE.json', 'SSS_SOURCE_FREEZE.json', 'FU_SOURCE_FREEZE.json', 'PAIR_EVAL_SOURCE_FREEZE.json']:
        freeze_check(name)
    assert not torch.cuda.is_initialized()
    binding_sha = sha(ROOT / 'STG_CPU_SOURCE_BINDING.json')
    binding, stg, audit = verified_cpu_trigger(binding_sha)
    clean = read(ROOT / 'CLEAN_FL_VERIFIED.json')
    assert clean['state'] == 'passed' and clean['utility_gate'] and clean['roles'] == 200 and clean['rounds'] == 20
    assert read(ROOT / 'CLEAN_DELIVERY_COMPLETE.json')['state'] == 'normal_foundation_delivery_and_three_host_diagnostic_registration_complete'
    for name in ['SSS_LOGGER_CPU2_RESULT.json', 'FU_ENGINE_CPU_RESULT.json', 'FU_POLICY_CPU_RESULT.json', 'PAIR_EVAL_CPU_RESULT.json']:
        assert read(ROOT / name)['state'] == 'passed'
    query = "Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe'} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    rows = json.loads(subprocess.check_output(['powershell', '-NoProfile', '-Command', query], text=True))
    rows = [rows] if isinstance(rows, dict) else rows or []
    workers = ['stg_controller.py', 'trigger_runner.py', 'verify_stg.py', 'paired_controller.py',
               'sss_runner.py', 'verify_sss.py', 'fu_runner.py', 'verify_fu.py', 'evaluate_pair.py', 'verify_pair_evaluation.py',
               'cpu_trigger_controller.py', 'cpu_trigger_recovery.py', 'verify_cpu_trigger_recovery.py']
    assert not any('feduba_paper_implementation_20261031' in (r.get('CommandLine') or '').lower() and
                   any(n in (r.get('CommandLine') or '').lower() for n in workers) for r in rows)
    base = read(ROOT / 'FU_PROFILE.json')
    case_id = base['required_clean_case_id']
    catalogue = read(args.catalog_root / 'catalog.json')
    case = next(c for c in catalogue['cases'] if c['id'] == case_id)
    assert case['allowed_purposes'] == ['diagnostic']
    selected = json.loads(subprocess.check_output([sys.executable, '-u', str(args.catalog_root / 'select_case.py'),
                          case_id, '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selected['server_inputs']['pre']['sha256'] == read(ROOT / 'CLEAN_FL_RESULT.json')['before']['sha256']
    assert selected['server_inputs']['pre']['payload_key'] is None and Path(selected['source_root']).resolve() == ROOT
    history = read(ROOT / 'clean_fl/MANIFEST.json'); history_sha = sha(ROOT / 'clean_fl/MANIFEST.json')
    assert case['history_scope']['manifest_sha256'] == history_sha
    assert Path(case['history_scope']['raw_root']).resolve() == ROOT / 'clean_fl'
    assert len(history['rounds']) == 20 and sum(len(row['roles']) for row in history['rounds']) == 200
    for row in history['rounds']:
        for role in row['roles']:
            meta = role['checkpoint']
            assert clean['history_hashes'][meta['path']] == meta['sha256']
    profiles = ['SSS_LAUNCH_PROFILE.json', 'FU_LAUNCH_PROFILE.json', 'PAIR_EVAL_LAUNCH_PROFILE.json', 'PAIR_LAUNCH_PROFILE.json']
    freezes = ['SSS_FREEZE.json', 'FU_RUN_FREEZE.json', 'PAIR_EVAL_RUN_FREEZE.json', 'PAIR_RUN_FREEZE.json']
    for n in profiles + freezes + ['PAIR_PREPARE_ONCE.json', 'PAIR_PREPARE_RESULT.json', 'PAIR_CONTROLLER_ONCE.json',
                                  'SSS_ONCE.json', 'SSS_RESULT.json', 'FU_benign_ONCE.json', 'FU_attack_ONCE.json']:
        assert not (ROOT / n).exists(), n
    create('PAIR_PREPARE_ONCE.json', {'pid': os.getpid(), 'created_unix': time.time(),
           'prepublished_code_commit': args.prepublished_code_commit, 'case_id': case_id})
    sss = {**base, 'id': 'feduba.paper.cifar10.sss.s42.20261031', 'launch_enabled': True,
           'logger_CPU_result': 'SSS_LOGGER_CPU2_RESULT.json', 'numeric_policy_sha256': sha(ROOT / 'SSS_NUMERIC_POLICY.json'),
           'trigger_binding_sha256': binding_sha, 'bound_delta': stg['delta']}
    fu = {**base, 'launch_enabled': True, 'history_manifest_sha256': history_sha,
          'history_role_payload_key': 'model', 'history_global_payload_key': None, 'trigger_binding_sha256': binding_sha}
    evaluation = {**read(ROOT / 'PAIR_EVAL_PROFILE.json'), 'launch_enabled': True,
                  'stage': 'actual_fixed_pre_benignFU_attackFU_evaluation_after_both_CPU_audits', 'trigger_binding_sha256': binding_sha}
    pair = {'id': 'feduba.paper.cifar10.paired20.s42.20261031', 'related_cards': base['related_cards'],
            'launch_enabled': True, 'required_clean_case_id': case_id, 'case_purpose': 'diagnostic',
            'catalog_root': args.catalog_root.as_posix(), 'history_manifest_sha256': history_sha,
            'trigger_binding_sha256': binding_sha, 'trigger_source_kind': binding['kind'],
            'delta': stg['delta'], 'branch_order': ['SSS', 'SSS_CPU_audit', 'benign_FU20', 'benign_CPU_audit',
                         'attack_FU20', 'attack_CPU_audit', 'primary_evaluation', 'independent_full_evaluation'],
            'resource_wait_max_hours_per_GPU_stage': 24, 'automatic_retries': 0,
            'performance_gate_is_a_stopping_rule_between_branches': False, 'delivery_still_required': True,
            'detection_success_implied': False}
    for name, value in zip(profiles, [sss, fu, evaluation, pair]): create(name, value)
    common = ['PAIR_LAUNCH_PROTOCOL.txt', 'CPU_BINDING_LAUNCH_PROTOCOL.txt', 'CLEAN_FL_PROFILE.json', 'CLEAN_FL_READY.json',
              'CLEAN_FL_VERIFIED.json', 'CLEAN_DELIVERY_COMPLETE.json', 'STG_LAUNCH_PROFILE.json', 'STG_RESULT.json',
              'STG_AUDIT_FAILURE.json', 'trigger_binding.py', 'STG_CPU_SOURCE_BINDING.json', 'STG_CPU_TRIGGER_RESULT.json',
              'STG_CPU_TRIGGER_VERIFIED.json', 'STG_CPU_TRIGGER_CONTROLLER_STATE.json', 'STG_CPU_TRIGGER_FREEZE.json']
    groups = [('SSS_SOURCE_FREEZE.json', 'SSS_LAUNCH_PROFILE.json', ['SSS_NUMERIC_POLICY.json']),
              ('FU_SOURCE_FREEZE.json', 'FU_LAUNCH_PROFILE.json', ['SSS_FREEZE.json']),
              ('PAIR_EVAL_SOURCE_FREEZE.json', 'PAIR_EVAL_LAUNCH_PROFILE.json', ['PAIR_EVAL_CPU_RESULT.json', 'FU_LAUNCH_PROFILE.json', 'FU_RUN_FREEZE.json'])]
    union = set(common + ['paired_controller.py', 'PAIR_LAUNCH_PROFILE.json', 'launch_pair.ps1', 'prepare_pair_profiles.py'])
    for freeze_name, (source, profile, extra) in zip(freezes[:3], groups):
        names = set(read(ROOT / source)['files']) | set(common + [source, profile] + extra)
        create(freeze_name, {'stage': 'actual_paired_stage_after_completed_STG_audit',
               'files': {n: sha(ROOT / n) for n in sorted(names)}})
        union.update(names); union.add(freeze_name)
    create('PAIR_RUN_FREEZE.json', {'stage': 'actual_sequential_SSS_two_FU20_and_two_full_evaluations',
            'files': {n: sha(ROOT / n) for n in sorted(union)}})
    create('PAIR_PREPARE_RESULT.json', {'state': 'passed_profiles_prepared_not_started', 'case_id': case_id,
           'case_selection': selected, 'history_manifest_sha256': history_sha,
           'delta': stg['delta'], 'trigger_binding_sha256': binding_sha,
           'CPU_trigger_verified_sha256': sha(ROOT / 'STG_CPU_TRIGGER_VERIFIED.json'),
           'profiles_and_freezes_sha256': {n: sha(ROOT / n) for n in profiles + freezes},
           'real_SSS_FU_or_pair_evaluation_executed': False,
           'next_required': 'Publish exact profiles/freezes to PR then record PAIR_PUBLICATION and launch once'})
    print(json.dumps({'state': 'passed_profiles_prepared_not_started', 'case_id': case_id}))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        write(ROOT / 'PAIR_PREPARE_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
