"""Apply the prepublished low-recurrence threshold to new image panels only."""
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(name):
    return json.loads((ROOT / name).read_bytes())


def scores(rows):
    events = [{k: sum(v) for k, v in row['classes'].items()} for row in rows]
    assert all(0 <= e['recur_opportunity'] <= min(e['opportunity'], e['recur']) <= e['native'] <= 900 for e in events)
    if min(e['native'] for e in events) < 20:
        return None
    return dict(
        recur=max(Fraction(e['recur'], e['native']) for e in events),
        native=max(Fraction(e['native'], 900) for e in events),
        pca=max(Fraction(e['pca'], e['native']) for e in events),
        opportunity=max(Fraction(e['recur_opportunity'], e['opportunity'])
                        for e in events if e['opportunity'] > 0),
        min_native=min(e['native'] for e in events),
        min_opportunity=min(e['opportunity'] for e in events),
    )


def main():
    freeze = read('CALIBRATION.json')
    limits = {key: Fraction(val) for key, val in freeze['cutoffs'].items()}
    assert limits['recur'] > 0
    data = read('RESULT.json')
    assert len(data['rows']) == 116
    pairs = {}
    for row in data['rows']:
        key = row['case'], row['probe_owner'], row['round'], row['split']
        pairs.setdefault(key, []).append(row)
    out = []
    for (cid, owner, epoch, split), rows in sorted(pairs.items()):
        assert len(rows) == 2 and {r['arm'] for r in rows} == {'baseline', 'route'}
        value = scores(rows)
        alert = None if value is None else dict(
            recur=value['recur'] < limits['recur'],
            native=value['native'] > limits['native'],
            pca=value['pca'] > limits['pca'],
        )
        out.append(dict(case=cid, owner=owner, round=epoch, split=split, alert=alert,
                        scores=None if value is None else {k: str(v) for k, v in value.items()}))
    endpoints = {(r['case'], r['owner'], r['split']): r['alert'] for r in out if r['round'] == 40}
    pass_method = {}
    for method in limits:
        own_checks = [(endpoints[c, c, s], i >= 4) for s in 'EF' for i in range(6) for c in [f'c{i:02}']]
        cross = [endpoints['c03', 'c05', s] for s in 'EF']
        pass_method[method] = all(a is not None and a[method] is expected for a, expected in own_checks) and all(
            a is not None and not a[method] for a in cross)
    decision = dict(cutoffs=freeze['cutoffs'], meets_fixed_conditions=pass_method, rows=out)
    (ROOT / 'DECISION.json').write_text(json.dumps(decision, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(pass_method)


if __name__ == '__main__':
    main()
