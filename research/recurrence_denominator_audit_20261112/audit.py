"""Check whether D29's endpoint decisions need request-specific history counts."""
import hashlib
import json
from pathlib import Path
from statistics import median_low

ROOT = Path(__file__).resolve().parent
SOURCES = {
    'd28': 'D:/ARCHIVED_TRANSITION_RECURRENCE_20261112/RESULT.json',
    'd29': 'D:/LOW_RECURRENCE_CONFIRMATION_20261112/RESULT.json',
}


def load(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def counts(row):
    w = sum(row['classes']['native'])
    r = sum(row['classes']['recur'])
    assert 0 <= r <= w <= 900
    return dict(arm=row['arm'], w=w, r=r)


def main():
    (ROOT / 'ONCE').open('x').close()
    freeze = load(ROOT / 'FREEZE.json')
    publication = load(ROOT / 'PUBLICATION.json')
    assert publication['all_raw_blob_bytes_verified'] and publication['freeze_sha256'] == sha(ROOT / 'FREEZE.json')
    for name, digest in freeze['files'].items():
        assert sha(ROOT / name) == digest
    for path, digest in freeze['dependencies'].items():
        assert sha(path) == digest
    data = {k: load(v) for k, v in SOURCES.items()}
    d28, d29 = data['d28']['rows'], data['d29']['rows']
    assert len(d28) == 248 and len(d29) == 116
    decision = load(ROOT / 'D29_DECISIONS.json')
    assert decision['cutoffs']['recur'] == '1/13'
    calibration = [counts(row)['r'] for row in d28
                   if row['case'] in ('c02', 'c03') and row['case'] == row['probe_owner'] and row['round'] == 40]
    assert len(calibration) == 20
    k = median_low(calibration)
    sealed = {(r['case'], r['owner'], r['split']): r['alert']['recur']
              for r in decision['rows']}
    grouped = {}
    for row in d29:
        if row['round'] == 40:
            grouped.setdefault((row['case'], row['probe_owner'], row['split']), []).append(counts(row))
    output = []
    for key, probes in sorted(grouped.items()):
        cid, owner, split = key
        assert len(probes) == 2 and {p['arm'] for p in probes} == {'baseline', 'route'}
        assert all(p['w'] >= max(20, k) for p in probes)
        actual = all(p['r'] * 13 < p['w'] for p in probes)
        control = all(k * 13 < p['w'] for p in probes)
        assert actual is sealed[key]
        output.append(dict(case=cid, probe_owner=owner, split=split, probes=probes, actual=actual,
                           fixed_numerator=control, min_w=min(p['w'] for p in probes),
                           max_w=max(p['w'] for p in probes)))
    assert len(output) == 16
    labels = {'normal': {'c00', 'c01', 'c02', 'c03'}, 'attack': {'c04', 'c05'}, 'large_normal': {'c00', 'c01'}}
    ranges = {}
    for name, cases in labels.items():
        rows = [r for r in output if r['case'] in cases and r['case'] == r['probe_owner']]
        ranges[name] = {key: [min(vals), max(vals)] for key, vals in (
            ('w', [p['w'] for r in rows for p in r['probes']]),
            ('r', [p['r'] for r in rows for p in r['probes']]),
            ('max_w', [r['max_w'] for r in rows]),
            ('min_w', [r['min_w'] for r in rows]),
        )}
    result = dict(calibration=sorted(calibration), median_low=k, implied_min_w_strict=13*k,
                  all_endpoint_decisions_reproduced=True,
                  fixed_numerator_changes=sum(r['actual'] != r['fixed_numerator'] for r in output),
                  ranges=ranges, endpoints=output)
    (ROOT / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
