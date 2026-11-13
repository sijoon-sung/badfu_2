"""Compare source-class coverage at a fixed count of observed transitions."""
import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

SOURCES = {
    'd15': ('D:/PAIRED_PROBE_VALIDATION_20261023/RESULT_SCALARS.json',
            'c74866c89e9af31bc326a626f3befb00791e63ec0d61ed4524661b6164b1e8af'),
    'd29': ('D:/LOW_RECURRENCE_CONFIRMATION_20261112/RESULT.json',
            '017a000309fc8ce31b96ec0779854215b88756435ee78c66529b277279fe2114'),
    'd22_stored': ('D:/FEDUBA_DELETION_ROUND_REPEATS_20261111/PANEL_stored_RESULT.json',
                   '5723a806b027e03fbdc8c6d520d0a2e5efbd8a3e898d095cb6b01c7ae425ad4c'),
    'd22_new': ('D:/FEDUBA_DELETION_ROUND_REPEATS_20261111/PANEL_new_RESULT.json',
                '0dde1ab6a0d3a3e8393454aa8ec1201d8382b044c29e41047516c73865fea1d0'),
}


def coverage(counts):
    total = sum(counts)
    assert len(counts) in (9, 10) and all(0 <= n <= 100 for n in counts)
    assert 20 <= total <= 900
    denom = math.comb(total, 20)
    return Fraction(sum(denom - math.comb(total - n, 20) for n in counts), denom)


def match(normal, attack):
    n, a = sum(normal), sum(attack)
    return min(n, a) >= 20 and 10 * abs(n - a) <= max(50, n, a)


def compare(key, normal, attack):
    n, a = coverage(normal), coverage(attack)
    return dict(key=key, normal_total=sum(normal), attack_total=sum(attack),
                normal_coverage=round(float(n), 6), attack_coverage=round(float(a), 6),
                supports=a > n, normal_counts=normal, attack_counts=attack)


def run():
    data = {}
    for key, (name, digest) in SOURCES.items():
        payload = Path(name).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == digest, key
        data[key] = json.loads(payload)
    assert coverage([20] + [0]*8) == 1 and coverage([10, 10] + [0]*7) == 2
    d15 = {row['pair']: row['primary_public'] for row in data['d15']['records']
           if row['objective'] == 'paired'}
    n = [x['witness'] for x in d15['q12']['source_counts']]
    a = [x['witness'] for x in d15['q10']['source_counts']]
    assert (sum(n), sum(a)) == (72, 63)
    d29 = [r for r in data['d29']['rows'] if r['case'] == r['probe_owner']]
    eligible_d29 = []
    for normal in (r for r in d29 if r['case'] in ('c00', 'c01')):
        for attack in (r for r in d29 if r['case'] in ('c04', 'c05')):
            keys = ('round', 'split', 'arm')
            if any(normal[k] != attack[k] for k in keys):
                continue
            n29, a29 = normal['classes']['native'], attack['classes']['native']
            if match(n29, a29):
                key = [normal['case'], attack['case'], *(normal[k] for k in keys)]
                eligible_d29.append(compare(key, n29, a29))
    rows = data['d22_stored']['rows'] + data['d22_new']['rows']
    assert len(rows) == 42
    groups = {}
    for row in rows:
        for probe in row['probes']:
            counts = probe['witness_by_class']
            assert sum(counts) == probe['witness'] and probe['n'] == 900
            assert counts[probe['target']] == 0
            key = (row['round'], probe['probe'], probe['arm'], probe['target'])
            tracks = groups.setdefault(key, {})
            assert row['track'] not in tracks
            tracks[row['track']] = counts
    eligible_d22 = []
    for key, tracks in sorted(groups.items()):
        for normal in sorted(set(tracks) - {'p02', 'p03', 'p04'}):
            for attack in ('p03', 'p04'):
                if match(tracks[normal], tracks[attack]):
                    eligible_d22.append(compare([normal, attack, *key], tracks[normal], tracks[attack]))
    return dict(d15=compare(['q12', 'q10'], n, a), d29=eligible_d29, d22=eligible_d22)


if __name__ == '__main__':
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == sys.argv[1]
    print(json.dumps(run(), separators=(',', ':')))
