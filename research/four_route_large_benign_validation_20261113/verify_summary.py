"""Independently reconstruct the stored comparison from count records."""
import argparse
import json
from itertools import product
from pathlib import Path

SEEDS = (20261020, 20261023)
ROUNDS = (1, 2, 3, 10, 20, 30, 40)
METHODS = {'baseline': ('w', 91), 'route': ('b', 75)}
GROUPS = {'scores': tuple(f'c{i:02}' for i in range(6)),
          'normal_origin_scores': tuple(f'c{i:02}' for i in range(4))}


def check(folder, complete):
    def read(name):
        return json.loads((folder / name).read_bytes())

    scores = read('SCORES.json')
    comparisons = read('COMPARISON.json')
    for row in scores:
        counts = {(p['arm'], p['owner']): (p['w'], p['b']) for p in row['counts']}
        assert set(counts) == set(product(METHODS, GROUPS['scores']))
        assert all(0 <= b <= w <= 900 for w, b in counts.values())
        for key, owners in GROUPS.items():
            for method, (event, _) in METHODS.items():
                assert row[key][method] == max(counts[method, o][event == 'b'] for o in owners)
    for epoch, studies in comparisons.items():
        group = [r for r in scores if r['round'] == int(epoch)]
        normal = [r for r in group if not r['attack']]
        attacks = [r for r in group if r['attack']]
        assert len(normal) == 4 and len(attacks) == 2
        assert sorted(r['seed'] for r in normal) == sorted(SEEDS * 2)
        assert sorted(r['seed'] for r in attacks) == list(SEEDS)
        for key, outputs in studies.items():
            for method, (_, fixed) in METHODS.items():
                def values(rows):
                    return [r[key][method] for r in rows]

                neg, pos = values(normal), values(attacks)
                assert outputs['fixed'][method] == [sum(n > fixed for n in neg), sum(a > fixed for a in pos)]
                for budget, expected in enumerate(outputs['descriptive_same_alarm_budget'][method]):
                    cutoff = sorted(neg, reverse=True)[budget]
                    assert expected == sum(a > cutoff for a in pos)
                for split in outputs['seed_holdout']:
                    seed = split['calibration_seed']
                    threshold = max(values(r for r in normal if r['seed'] == seed))
                    held = values(r for r in normal if r['seed'] != seed)
                    assert split['methods'][method] == {
                        'threshold': threshold,
                        'held_normal': sum(v > threshold for v in held),
                        'attack': sum(v > threshold for v in pos),
                    }
    if complete:
        assert set(map(int, comparisons)) == set(ROUNDS) and len(scores) == 42
        state = read('STATE.json')
        assert state['stage'] == 'complete' and state['normal_rounds'] == 160
    return comparisons


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    parser.add_argument('--complete', action='store_true')
    args = parser.parse_args()
    result = check(args.folder, args.complete)
    print(json.dumps(result, indent=2))
