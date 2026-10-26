"""Exploratory feasibility check on existing FC arrays; no new training.

This is one explicit implementation of the attached proposal, not a
reproduction of FoolsGold, RLR, or DeepSight. No threshold is fitted.
"""
from pathlib import Path
import hashlib
import json
import math
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'research_20261018' / 'all_or_nothing'
ARRAYS = OLD / 'pure_layer4_arrays.npz'
CASES = OLD / 'pure_layer4_result.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(a, b, fraction):
    a, b = a.ravel(), b.ravel()
    energy = a*a + b*b
    size = max(1, math.ceil(len(a)*fraction))
    # Deterministic ties; coordinate selection does not inspect signs or labels.
    index = np.argsort(-energy, kind='stable')[:size]
    a, b, energy = a[index], b[index], energy[index]
    opposite = a*b < 0
    total_l1 = float(np.abs(a).sum()+np.abs(b).sum())
    cancelled_l1 = float((2*np.minimum(np.abs(a), np.abs(b))[opposite]).sum())
    score = cancelled_l1/total_l1
    assert np.isclose(cancelled_l1, total_l1-np.abs(a+b).sum(), rtol=1e-10, atol=1e-12)
    assert 0 <= score <= 1+1e-12
    return dict(selected_coordinates=size,
                opposite_coordinate_fraction=float(opposite.mean()),
                opposite_joint_energy_fraction=float(energy[opposite].sum()/energy.sum()),
                cancelled_l1_fraction=score,
                masked_cosine=float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b))))


def main():
    archive = np.load(ARRAYS)
    cases = [row['case'] for row in json.loads(CASES.read_text(encoding='utf-8'))['rows']]
    rows = []
    for case in cases:
        a = archive[case+'/fc/retained'].astype(np.float64)
        b = archive[case+'/fc/forget'].astype(np.float64)
        rows.append(dict(case=case, attack=case.startswith('attack'),
                         norm_ratio=float(np.linalg.norm(a)/np.linalg.norm(b)),
                         masks={str(f):measure(a,b,f) for f in (.05,.10,1.)}))
    summary = {}
    for f in (.05,.10,1.):
        values = {}
        for metric in ('opposite_coordinate_fraction','opposite_joint_energy_fraction',
                       'cancelled_l1_fraction','masked_cosine'):
            attack = [(r['case'],r['masks'][str(f)][metric]) for r in rows if r['attack']]
            control = [(r['case'],r['masks'][str(f)][metric]) for r in rows if not r['attack']]
            amin,amax = min(v for _,v in attack),max(v for _,v in attack)
            cmin,cmax = min(v for _,v in control),max(v for _,v in control)
            values[metric] = dict(attack_range=[amin,amax],control_range=[cmin,cmax],
                                  ranges_overlap=not(amin>cmax or cmin>amax),
                                  attack_min=min(attack,key=lambda x:x[1]),
                                  control_max=max(control,key=lambda x:x[1]))
        summary[str(f)] = values
    report = dict(scope='16 previously inspected requests; exploratory FC check only',
                  matrix='10x513 FC weight and bias; same one-point CE updates in both branches',
                  mask='largest ceil(fraction*N) entries of A_i^2+B_i^2; no sign/attack labels in selection',
                  cancelled_l1_fraction='sum(|A_i|+|B_i|-|A_i+B_i|) / sum(|A_i|+|B_i|) within mask',
                  fractions=[.05,.10,1.],source_sha256=digest(Path(__file__)),
                  input_sha256={str(p.relative_to(ROOT)):digest(p) for p in (ARRAYS,CASES)},
                  new_training_steps=0,new_images_loaded=0,threshold_fit=False,
                  limitations=['Not an exact reproduction of a cited defense.',
                               'Old Conv archive has channel summaries, not full coordinate arrays.',
                               'Client/round update histories are absent for these 16 requests.',
                               'All masks are reported; no best fraction is selected.'],
                  summary=summary,rows=rows)
    output=Path(__file__).with_name('coordinate_conflict_result.json')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__ == '__main__':
    main()
