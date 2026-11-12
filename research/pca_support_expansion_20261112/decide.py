"""Apply the published acceptance conditions to the sealed evaluation output."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
source = json.loads((root / 'RESULT.json').read_bytes())
methods = ['pca_320', 'pca_640', 'pca_both'] + [f'random_{i}_both' for i in range(1, 4)]
table = {}
assert source['d24_matched'] == 96 and len(source['rows']) == 180
for row in source['rows']:
    assert row['n'] == 900
    for method in ('pca', 'random_1', 'random_2', 'random_3'):
        assert 0 <= row[method + '_both'] <= min(row[method + '_320'], row[method + '_640'])
        assert max(row[method + '_320'], row[method + '_640']) <= row['native']
    key = (row['split'], row['round'], row['case'])
    if key not in table:
        table[key] = {}
    assert row['arm'] not in table[key]
    table[key][row['arm']] = row
assert all(set(a) == {'baseline', 'route'} for a in table.values())
counts = {key: {method: max(r[method] for r in arms.values()) for method in methods}
          for key, arms in table.items()}
summary = {}
for method in methods:
    summary[method] = {}
    for split in 'ABCD':
        terminal = [counts[split, 40, f'c{i:02d}'][method] for i in range(6)]
        summary[method][split] = dict(
            counts=terminal, normal_alerts=sum(v > 5 for v in terminal[:4]),
            attack_alerts=sum(v > 5 for v in terminal[4:]))
accept = {method: all(r['normal_alerts'] == 0 and r['attack_alerts'] == 2 for r in panels.values())
          for method, panels in summary.items()}
mid = [dict(split=split, round=epoch, case=cid, **values)
       for (split, epoch, cid), values in counts.items() if epoch != 40]
out = dict(fixed_threshold_exclusive=5, original_rows_exact=96,
           terminal=summary, all_terminal_conditions=accept, intermediate=mid)
(root / 'DECISION.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(dict(terminal=summary, all_terminal_conditions=accept), indent=2))
