"""One stdlib metadata preparation, only after the current trigger's verified exit."""
import os
from pathlib import Path
import subprocess
import sys
import traceback
sys.dont_write_bytecode = True
from pair_binding import ROOT, FOUNDATION, read, sha, checked, once, source_profile, trigger_ready


def main():
    source = source_profile()
    assert read(ROOT / 'SOURCE_ONLY_REVIEW.json')['state'] == 'passed_source_only_no_queries_or_prepare'
    publication = read(ROOT / 'SOURCE_PUBLICATION.json')
    assert publication['state'] == 'mixed_pair_source_published_before_actual_binding'
    assert publication['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
    assert publication['source_review_sha256'] == sha(ROOT / 'SOURCE_ONLY_REVIEW.json')
    for name in ['PREPARE_ONCE.json', 'PREPARE_FAILURE.json', 'TRIGGER_SOURCE_BINDING.json',
                 'PAIR_LAUNCH_PROFILE.json', 'PAIR_CONTROLLER_ONCE.json', 'SSS_ONCE.json', 'SSS_RESULT.json']:
        assert not (ROOT / name).exists(), name
    binding, terminal = trigger_ready(source)
    for meta in source['external_evidence'].values(): checked(meta)
    import json
    catalog_root = source['catalog_root']
    catalog = read(catalog_root + '/catalog.json')
    case = next(c for c in catalog['cases'] if c['id'] == source['normal_case_id'])
    assert case['allowed_purposes'] == ['diagnostic']
    assert Path(case['source_root']).resolve() == FOUNDATION.resolve()
    assert case['history_scope']['manifest_sha256'] == source['foundation_history_manifest']['sha256']
    assert Path(case['history_scope']['raw_root']).resolve() == FOUNDATION / 'clean_fl'
    assert case['history_scope']['role_payload_key'] == 'model' and case['history_scope']['global_payload_key'] is None
    selected = json.loads(subprocess.check_output([sys.executable, '-B', catalog_root + '/select_case.py',
               source['normal_case_id'], '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selected['server_inputs']['pre']['sha256'] == source['normal_pre_sha256']
    assert selected['server_inputs']['pre']['payload_key'] is None
    assert selected['checkpoint_guard']['manifest_sha256'] == source['normal_manifest_sha256']
    assert selected['checkpoint_guard']['seal_sha256'] == source['normal_seal_sha256']
    clean = read(ROOT / 'CLEAN_FL_VERIFIED.json')
    assert clean['state'] == 'passed' and clean['utility_gate'] and clean['rounds'] == 20 and clean['roles'] == 200
    checked(source['foundation_history_manifest'])
    original = read(source['foundation_history_manifest']['path'])
    assert len(original['rounds']) == 20 and sum(len(r['roles']) for r in original['rounds']) == 200
    for row in original['rounds']:
        for role in row['roles']:
            meta = role['checkpoint']; assert clean['history_hashes'][meta['path']] == meta['sha256']
    once('PREPARE_ONCE.json', {'pid': os.getpid(), 'model_loads': 0, 'model_forwards': 0})
    once('TRIGGER_SOURCE_BINDING.json', binding); once('TRIGGER_TERMINAL.json', terminal)
    once('NORMAL_SELECTION.json', selected)
    binding_sha = sha(ROOT / 'TRIGGER_SOURCE_BINDING.json')
    base = read(ROOT / 'FU_PROFILE.json')
    shared = {'launch_enabled': True, 'trigger_binding_sha256': binding_sha}
    sss = {**base, **shared, 'id': 'feduba.mixed_teacher.sss125.s42.20261101',
           'logger_CPU_result': 'SSS_LOGGER_CPU2_RESULT.json',
           'numeric_policy_sha256': sha(ROOT / 'SSS_NUMERIC_POLICY.json'), 'bound_delta': binding['delta']}
    fu = {**base, **shared, 'id': 'feduba.mixed_teacher.pairedFU20.s42.20261101',
          'history_manifest_sha256': source['foundation_history_manifest']['sha256'],
          'history_role_payload_key': 'model', 'history_global_payload_key': None}
    evaluation = {**read(ROOT / 'PAIR_EVAL_PROFILE.json'), **shared,
                  'id': 'feduba.mixed_teacher.paired_evaluation.s42.20261101',
                  'stage': 'actual_new_delta_three_models_after_both_FU_CPU_audits'}
    pair = {**shared, 'id': 'feduba.mixed_teacher.SSS125.pairedFU20.s42.20261101',
            'required_clean_case_id': source['normal_case_id'], 'case_purpose': 'diagnostic',
            'catalog_root': catalog_root, 'source_profile_sha256': sha(ROOT / 'SOURCE_PROFILE.json'),
            'history_manifest_sha256': source['foundation_history_manifest']['sha256'],
            'branch_order': ['SSS', 'SSS_CPU_audit', 'benignFU20', 'benign_CPU_audit',
                             'attackFU20', 'attack_CPU_audit', 'primary_full_eval', 'independent_full_eval'],
            'automatic_retries': 0, 'performance_gate_does_not_skip_a_branch': True,
            'delivery_required': True, 'overall_goal_complete': False}
    profiles = ['SSS_LAUNCH_PROFILE.json', 'FU_LAUNCH_PROFILE.json', 'PAIR_EVAL_LAUNCH_PROFILE.json', 'PAIR_LAUNCH_PROFILE.json']
    for name, value in zip(profiles, [sss, fu, evaluation, pair]): once(name, value)
    names = set(read(ROOT / 'SOURCE_FREEZE.json')['files']) | set(profiles) | {
        'SOURCE_FREEZE.json', 'SOURCE_ONLY_REVIEW.json', 'SOURCE_PUBLICATION.json',
        'TRIGGER_SOURCE_BINDING.json', 'TRIGGER_TERMINAL.json', 'NORMAL_SELECTION.json'}
    freezes = ['SSS_FREEZE.json', 'FU_RUN_FREEZE.json', 'PAIR_EVAL_RUN_FREEZE.json']
    for name in freezes: once(name, {'files': {n: sha(ROOT / n) for n in sorted(names)}})
    names.update(freezes)
    once('PAIR_RUN_FREEZE.json', {'files': {n: sha(ROOT / n) for n in sorted(names)}})
    once('PREPARE_RESULT.json', {'state': 'passed_metadata_binding_actual_profiles_not_started',
         'profiles_and_freezes_sha256': {n: sha(ROOT / n) for n in profiles + freezes + ['PAIR_RUN_FREEZE.json']},
         'trigger_binding_sha256': binding_sha, 'delta': binding['delta'], 'model_loads': 0, 'model_forwards': 0,
         'next_required': 'Publish these exact actual profiles/freezes to existing PR before any numerical execution'})
    assert 'torch' not in sys.modules


if __name__ == '__main__':
    try: main()
    except BaseException:
        once('PREPARE_FAILURE.json', {'state': 'failed_preserved_no_retry', 'traceback': traceback.format_exc()})
        raise
