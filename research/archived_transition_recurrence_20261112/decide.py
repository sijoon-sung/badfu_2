"""Compare sealed behavioral counts with a normal-only calibration."""
import json
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
METHODS = ('native', 'pca', 'recur', 'recur_pca')


def assess(rows, field):
    counts = []
    for row in rows:
        events = row['classes']
        n = sum(events['native'])
        if n < 20:
            continue
        wins = sum(events[field])
        assert 0 <= wins <= n <= 900
        denominator = 900 if field == 'native' else n
        score = Fraction(wins, denominator) if sum(x > 0 for x in events[field]) >= 2 else Fraction(0)
        counts.append(score)
    return max(counts, default=None)


def main():
    result = json.loads((ROOT / 'RESULT.json').read_bytes())
    assert result['d27_rows_matched'] == 180 and len(result['rows']) == 248
    pairs = {}
    for row in result['rows']:
        key = (row['case'], row['probe_owner'], row['round'], row['split'])
        pairs.setdefault(key, []).append(row)
    assert all({r['arm'] for r in rows} == {'baseline', 'route'} and len(rows) == 2 for rows in pairs.values())
    decisions = {}
    for name in METHODS:
        ref = [assess(pairs[cid, cid, 40, 'original'], name) for cid in ('c02', 'c03')]
        assert all(v is not None for v in ref)
        limit = max(ref)
        rows = []
        for (cid, owner, epoch, split), data in sorted(pairs.items()):
            score = assess(data, name)
            rows.append(dict(case=cid, owner=owner, round=epoch, split=split,
                             score=None if score is None else str(score),
                             alert=None if score is None else score > limit))
        endpoint = {(r['case'], r['owner'], r['split']): r['alert']
                    for r in rows if r['round'] == 40 and r['split'] != 'original'}
        own_pass = all(endpoint[c, c, s] is expected for s in 'ABCD'
                       for c, expected in [('c00', False), ('c01', False), ('c04', True), ('c05', True)])
        same_probe_pass = all(endpoint['c03', 'c05', s] is False and endpoint['c05', 'c05', s] is True for s in 'ABCD')
        decisions[name] = dict(calibration=str(limit), own_pass=own_pass,
                               same_probe_pass=same_probe_pass, rows=rows)
    (ROOT / 'DECISION.json').write_text(json.dumps(decisions, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
