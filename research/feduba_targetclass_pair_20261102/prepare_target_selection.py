"""One new selection from existing audited scores; zero model queries or optimization."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import traceback
from pair_binding import ROOT, FOUNDATION, source_profile, read, sha, checked


def once(name, value):
    with (ROOT / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write('\n')


def main():
    p = source_profile(); pub = read(ROOT / 'SOURCE_PUBLICATION.json')
    assert pub['source_freeze_sha256'] == sha(ROOT / 'SOURCE_FREEZE.json')
    assert pub['state'] == 'published_targetclass_source_before_metadata_preparation'
    for v in p['inputs'].values(): checked(v)
    once('PREPARE_ONCE.json', {'pid': os.getpid(), 'model_loads': 0, 'queries': 0})
    import torch
    from torchvision.datasets import CIFAR10
    import core
    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    selected_case = json.loads(subprocess.check_output([sys.executable, '-B', p['catalog_root'] + '/select_case.py',
        p['normal_case_id'], '--purpose', 'diagnostic'], text=True, encoding='utf-8'))
    assert selected_case['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selected_case['server_inputs']['pre']['sha256'] == p['normal_pre_sha256']
    once('NORMAL_CASE_SELECTION.json', selected_case)
    original = read(p['inputs']['old_SSS_result']['path'])
    audit = read(p['inputs']['old_SSS_verified']['path'])
    assert audit['state'] == 'passed' and audit['SSS_result_sha256'] == sha(p['inputs']['old_SSS_result']['path'])
    assert original['delta']['sha256'] == p['required_delta_sha256']
    train = CIFAR10(read(ROOT / 'CLEAN_FL_PROFILE.json')['data_root'], train=True, download=False)
    labels = train.targets
    assert len(labels) == 50000
    parts = read(FOUNDATION / 'CLEAN_SPLIT.json')['indices']
    target_ranks, target_ownership, original_hist = {}, {}, [0] * 10
    for owner in [5, 7]:
        ranked = original['owner_ranks'][str(owner)]
        assert len(ranked) == 2500 and {i for i, score in ranked} == set(parts[owner])
        assert all(math.isfinite(score) for i, score in ranked)
        target_ranks[owner] = [(i, score) for i, score in ranked if labels[i] == 2]
        target_ownership[owner] = [i for i in parts[owner] if labels[i] == 2]
        for i in original['selected_by_owner'][str(owner)]: original_hist[labels[i]] += 1
    chosen = core.select_requests(target_ranks, target_ownership, 125)
    # Independent plain-Python global ordering; no new model inference or old SSS replay.
    candidates = [(float(s), int(i), owner) for owner in [5, 7] for i, s in target_ranks[owner]]
    independently_selected = sorted(candidates, key=lambda row: (-row[0], row[1]))[:125]
    independent = {owner: [i for score, i, who in independently_selected if who == owner] for owner in [5, 7]}
    assert independent == chosen and all(labels[i] == 2 for ids in chosen.values() for i in ids)
    selection = {'state': 'prepared_new_target_class_selection_from_existing_audited_SSS',
        'case_id': p['normal_case_id'], 'selection_scope': 'target_class2_only_global_top125_owner5_7',
        'pre_checkpoint': original['pre_checkpoint'], 'delta': original['delta'],
        'selected_by_owner': {str(k): v for k, v in chosen.items()}, 'request_budget': 125,
        'trigger_binding_sha256': sha(ROOT / 'TRIGGER_SOURCE_BINDING.json'),
        'old_SSS_result': p['inputs']['old_SSS_result'], 'new_model_queries': 0, 'new_SSS_query_claimed': False}
    once('SSS_RESULT.json', selection)
    once('SSS_VERIFIED.json', {'state': 'passed', 'audit_scope': 'new_target_filter_budget_order_and_ownership_only',
        'SSS_result_sha256': sha(ROOT / 'SSS_RESULT.json'), 'selected_by_owner': selection['selected_by_owner'],
        'trigger_binding_sha256': selection['trigger_binding_sha256'], 'new_model_queries': 0,
        'old_full_query_audit_reused': p['inputs']['old_SSS_verified']})
    original_history = read(p['foundation_history_manifest']['path'])
    benign_batches = sum(math.ceil((2500 - len(chosen.get(c, []))) / 128) * 5
                         for row in original_history['rounds'] for c in row['clients'])
    fu = copy.deepcopy(read(ROOT / 'FU_PROFILE.json')); fu['launch_enabled'] = True
    fu['history_manifest_sha256'] = p['foundation_history_manifest']['sha256']
    fu['trigger_binding_sha256'] = selection['trigger_binding_sha256']
    once('FU_LAUNCH_PROFILE.json', fu)
    ev = copy.deepcopy(read(ROOT / 'PAIR_EVAL_PROFILE.json')); ev['launch_enabled'] = True
    ev['trigger_binding_sha256'] = selection['trigger_binding_sha256']; once('PAIR_EVAL_LAUNCH_PROFILE.json', ev)
    once('PREPARATION_RESULT.json', {'state': 'prepared_actual_targetclass_selection_and_profiles',
        'source_freeze_sha256': sha(ROOT / 'SOURCE_FREEZE.json'), 'model_queries': 0,
        'old_selected_class_counts': original_hist, 'new_selected_class_counts': [0, 0, 125, 0, 0, 0, 0, 0, 0, 0],
        'eligible_target_counts_by_owner': {str(k): len(v) for k, v in target_ranks.items()},
        'selected_counts_by_owner': {str(k): len(v) for k, v in chosen.items()},
        'expected_benign_batches': benign_batches, 'expected_attack_batches': 20000,
        'CIFAR_MD5_checked': True, 'same_old_score_values_used': True,
        'old_global_top125_preserved': True, 'whole_goal_complete': False})
    once('LAUNCH_PROFILE.json', {'id': 'feduba.targetclass125.s42.pairedFU20.20261102',
        'launch_enabled': True, 'execution_root': str(ROOT), 'selected_IDs': 125,
        'selection_sha256': sha(ROOT / 'SSS_RESULT.json'), 'selection_audit_sha256': sha(ROOT / 'SSS_VERIFIED.json'),
        'preparation_sha256': sha(ROOT / 'PREPARATION_RESULT.json'), 'FU_benign_batches': benign_batches,
        'FU_attack_batches': 20000, 'each_FU_rounds': 20, 'each_FU_epochs': 1000,
        'primary_and_independent_each_calls': 474, 'primary_and_independent_each_sample_forwards': 60000,
        'retraining_original_foundation_or_STG': False, 'reuse_old_FU_after_models': False})
    files = dict(read(ROOT / 'SOURCE_FREEZE.json')['files'])
    for n in ['SOURCE_FREEZE.json', 'SSS_RESULT.json', 'SSS_VERIFIED.json', 'FU_LAUNCH_PROFILE.json',
              'PAIR_EVAL_LAUNCH_PROFILE.json', 'LAUNCH_PROFILE.json', 'PREPARATION_RESULT.json', 'NORMAL_CASE_SELECTION.json']:
        files[n] = sha(ROOT / n)
    for n in ['RUN_FREEZE.json', 'FU_RUN_FREEZE.json', 'PAIR_EVAL_RUN_FREEZE.json']:
        once(n, {'state': 'actual_targetclass_pair_frozen_before_training', 'files': files})
    print(json.dumps(read(ROOT / 'PREPARATION_RESULT.json')))


if __name__ == '__main__':
    try: main()
    except BaseException:
        once('PREPARE_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
