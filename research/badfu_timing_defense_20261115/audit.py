"""Check the archived counts and apply the frozen decision rules without model access."""

from fractions import Fraction
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARMS = ('none', 'early', 'late', 'split')
NORMAL = ('normal193', 'normal228', 'normal850')
FURTHER = ('infected_normal', 'attack23', 'attack20')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def pct_delta(count, base, n):
    return Fraction(100 * (count - base), n)


def check_public(row):
    assert row['class_n'] == [160] * 10 and row['n'] == 1600
    assert sum(row['class_correct']) == row['correct']
    assert all(0 <= hits <= total for hits, total in zip(row['class_correct'], row['class_n']))


def check_case(key, row, expected):
    assert row['fit']['source'] == expected['sha256']
    assert row['fit']['actual_recovery_steps'] == 48
    assert row['fit']['actual_repair_steps'] == dict(none=0, early=48, late=48, split=48)
    assert tuple(row['arms']) == ARMS and tuple(row['fit']['model_hashes']) == ARMS
    check_public(row['clean_original'])
    for arm in row['arms'].values():
        check_public(arm['public_anchor'])
        check_public(arm['public_final'])
        assert set(arm['by_client']) == {'1', '2', '3'}
        assert all(0 <= c['correct'] <= c['n'] == 160 for c in arm['by_client'].values())
        if key in NORMAL[:2]:
            aud = arm['deletion_audit']
            assert aud['member_n'] == 400 and 1 <= aud['classes'] <= 10 and 0 <= aud['macro_auc'] <= 1
        if key in FURTHER:
            for check in arm['archive'].values():
                assert sum(check[k] for k in ('original_correct', 'target', 'other_wrong')) == check['n'] == 1440
            trace = arm['transitions']
            assert sum(trace[k] for k in ('rescued_still_correct', 'rescued_regressed_target', 'rescued_regressed_other')) == trace['anchor_rescued']


def audit_gate(row, reported=None):
    control = row['arms']['none']
    base = control['public_final']
    values = {}
    for key in ('late', 'split'):
        arm = row['arms'][key]
        item = arm['public_final']
        overall = pct_delta(item['correct'], base['correct'], 1600)
        worst_class = min(pct_delta(a, b, 160) for a, b in zip(item['class_correct'], base['class_correct']))
        worst_client = min(pct_delta(a['correct'], control['by_client'][k]['correct'], 160) for k, a in arm['by_client'].items())
        distance = None
        if 'deletion_audit' in arm:
            distance = abs(arm['deletion_audit']['macro_auc'] - .5) - abs(control['deletion_audit']['macro_auc'] - .5)
        passed = overall >= -2 and worst_class >= -5 and worst_client >= -5 and (distance is None or distance <= .03)
        audit = {'delta_clean_pp': float(overall), 'worst_class_pp': float(worst_class), 'worst_client_pp': float(worst_client),
                 'added_auc_distance': distance, 'passed': passed}
        if reported:
            assert audit == reported[key]
        values[key] = audit
    return values


def largest_class_losses(row):
    baseline = row['arms']['none']['public_final']['class_correct']
    out = {}
    for key in ('late', 'split'):
        after = row['arms'][key]['public_final']['class_correct']
        loss = min(a - b for a, b in zip(after, baseline))
        out[key] = [{'class': cls, 'before': b, 'after': a, 'n': 160}
                    for cls, (a, b) in enumerate(zip(after, baseline)) if a - b == loss]
    return out


def attack_comparison(row):
    phases = {k: v['archive'] for k, v in row['arms'].items()}
    a, b = phases['late'], phases['split']
    immediate = pct_delta(a['anchor']['original_correct'], phases['none']['anchor']['original_correct'], 1440)
    regression = pct_delta(a['anchor']['original_correct'], a['tail12']['original_correct'], 1440)
    improvement = pct_delta(b['tail12']['original_correct'], a['tail12']['original_correct'], 1440)
    gate = audit_gate(row)
    return {'late_initial_recovery_pp': float(immediate), 'late_regression_pp': float(regression),
            'split_advantage_pp': float(improvement), 'start': row['archive_original'],
            'archive': phases, 'utility': gate, 'criteria_met': immediate >= 5 and regression >= 2 and improvement >= 2
            and all(v['passed'] for v in gate.values())}


def main():
    out = ROOT / 'receipts'
    inputs = read(ROOT / 'INPUTS.json')
    terminal = read(out / 'TERMINAL.json')
    assert terminal['state'] in ('complete', 'normal_gate_failed')
    assert set(terminal['gates']) == set(NORMAL)
    names = NORMAL + FURTHER if terminal['state'] == 'complete' else NORMAL
    results = {name: read(out / f'{name}_RESULT.json') for name in names}
    for name, fields in results.items():
        check_case(name, fields, inputs['models'][name])
    gates = {name: audit_gate(results[name], terminal['gates'][name]) for name in NORMAL}
    passed = all(v['passed'] for group in gates.values() for v in group.values())
    assert passed == terminal['attack_evaluation'] == (terminal['state'] == 'complete')
    if passed:
        comparisons = {name: attack_comparison(results[name]) for name in FURTHER}
        supported = all(comparisons[name]['criteria_met'] for name in ('attack23', 'attack20'))
        verdict = 'supported_under_fixed_profile' if supported else 'not_supported_under_fixed_profile'
    else:
        assert not any((out / f'{name}_RESULT.json').exists() for name in FURTHER)
        comparisons = {}
        verdict = 'stopped_at_benign_utility_or_deletion_gate'
    clean = {name: {arm: row['public_final']['correct'] for arm, row in fields['arms'].items()} for name, fields in results.items()}
    summary = {'decision': verdict, 'case_count': len(results), 'clean_final_out_of_1600': clean,
               'case_seconds': {name: fields['seconds'] for name, fields in results.items()},
               'normal_gates': gates, 'largest_class_losses': {name: largest_class_losses(results[name]) for name in NORMAL},
               'fixed_archive_evaluation': comparisons}
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
