"""Aggregate same-round contrasts from DISLAB counts, keeping stages explicit."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_bytes())


def main():
    a = read(ROOT / 'PANEL_stored_RESULT.json')
    assert a['state'] == 'passed' and a['endpoint_checks'] == 10 and len(a['rows']) == 30
    new_path = ROOT / 'PANEL_new_RESULT.json'
    b = read(new_path) if new_path.exists() else {'rows': []}
    all_rows = a['rows'] + b['rows']
    names = {'p00':'balanced_original', 'p01':'class2_all', 'p02':'normal125', 'p03':'minus_diagnostic',
             'p04':'plus_diagnostic', 'u00':'balanced_b','u01':'dark_a','u02':'dark_b'}
    probes = {}
    model_rounds = {}
    for row in all_rows:
        track = row['track']; r = row['round']
        assert (track,r) not in model_rounds
        model_rounds[track,r] = row
        for p in row['probes']:
            assert p['n'] == 900 and 0 <= p['witness'] <= p['stable'] <= 900
            probes.setdefault((r,p['probe'],p['arm']),{})[track] = p
    comparisons = []
    for (r,pid,arm), v in sorted(probes.items()):
        a0 = min(('p03','p04'),key=lambda t:v[t]['witness'])
        normals = [k for k in v if k not in ('p03','p04')]
        n0 = max(normals,key=lambda t:v[t]['witness'])
        large = [k for k in normals if k != 'p02']
        n1 = max(large,key=lambda t:v[t]['witness'])
        aw, nw, lw = v[a0]['witness'],v[n0]['witness'],v[n1]['witness']
        comparisons.append(dict(round=r, probe=pid, arm=arm, minimum_diagnostic=aw, minimum_diagnostic_track=a0,
           maximum_benign=nw, maximum_benign_track=n0, maximum_large_benign=lw, maximum_large_benign_track=n1,
           large_overlap=lw>=aw, large_gap=aw-lw, all_overlap=nw>=aw))
    margins = []
    for r in sorted({c['round'] for c in comparisons}):
        c = [c for c in comparisons if c['round']==r]
        worst=min(c,key=lambda p:p['large_gap'])
        margins.append(dict(round=r, probes=len(c), overlapping_large=sum(p['large_overlap'] for p in c),
          overlapping_any=sum(p['all_overlap'] for p in c), worst_large=worst))
    out = dict(interpretation='same_round_fixed_terminal_probes_retrospective',stored_rows=len(a['rows']),new_rows=len(b['rows']),
               rounds=margins,case_names=names,comparisons=comparisons)
    (ROOT/'SUMMARY.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
    print(json.dumps(dict(stored_rows=len(a['rows']),new_rows=len(b['rows']),rounds=margins),indent=2))


if __name__=='__main__':main()
