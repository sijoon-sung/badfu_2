"""Report frozen case contrasts exactly from receipts; does not load models."""
from fractions import Fraction
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESEARCH = ROOT.parent
D20 = RESEARCH / 'blind_route_detector_v2_20261110' / 'remote_results'
D21 = RESEARCH / 'feduba_large_benign_validation_20261110' / 'remote_results'
GROUPS = {
    'BadFU': (('c04', 'c05'), ('c00', 'c01', 'c02', 'c03')),
    'FedUBA_large': (('c08', 'c09'), ('n00', 'n01')),
    'FedUBA_all': (('c08', 'c09'), ('c07', 'n00', 'n01')),
}


def read(path):
    return json.loads(path.read_bytes())


def describe(gap):
    return dict(exact=str(gap), percentage_points=100 * float(gap))


def margin(values, attack, normal):
    return min(values[c] for c in attack) - max(values[c] for c in normal)


def main():
    primary = [read(p / 'RESULT.json') for p in (D20, D21 / 'detector_n00', D21 / 'detector_n01')]
    baseline = {}
    route = {}
    for result in primary:
        for row in result['results']:
            (baseline if row['arm'] == 'baseline' else route)[row['case']] = Fraction(row['witness'], row['n'])
    comparisons = {}
    for name, (attack, normal) in GROUPS.items():
        g0 = margin(baseline, attack, normal)
        g1 = margin(route, attack, normal)
        comparisons[name] = dict(baseline=describe(g0), four_routes=describe(g1), change=describe(g1 - g0))
    result = read(ROOT / 'RESULT.json')
    assert result['native_counts_exact'] and result['training_steps'] == 0
    rows = result['rows']
    assert len(rows) == len(baseline) == len(route) == 12
    strict = {}
    for row in rows:
        cid = row['case']
        assert Fraction(row['witness'], row['n']) == baseline[cid]
        assert 0 <= row['strict_body'] <= min(row['body'], row['clean_compatible']) <= row['witness']
        if row['witness']:
            strict[cid] = Fraction(row['strict_body'], row['witness'])
    audit = {}
    for name in ('BadFU', 'FedUBA_all'):
        attack, normal = GROUPS[name]
        if any(c not in strict for c in attack + normal):
            audit[name] = dict(verdict='not_evaluable')
        else:
            weakest = min(attack, key=strict.get)
            largest = max(normal, key=strict.get)
            gap = strict[weakest] - strict[largest]
            audit[name] = dict(verdict='separated_in_fixed_cases' if gap > 0 else 'not_separated',
                               weakest_attack=weakest, highest_normal=largest, gap=describe(gap))
    output = dict(search_gap=comparisons, body_audit=audit, fuba='descriptive_only_no_matched_control',
                  strict_body_percent={c: 100 * float(v) for c, v in strict.items()})
    (ROOT / 'SUMMARY.json').write_bytes((json.dumps(output, indent=2) + '\n').encode())
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
