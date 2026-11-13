"""New exact, model-free constructions; no upstream jobs or models are run."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import platform
import sys

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def score(a, row):
    return row['u'] + a * row['v']


def optimum(rows):
    numerator = sum((r['v'] * (r['y'] - r['u']) for r in rows), F(0))
    denominator = sum((r['v'] ** 2 for r in rows), F(0))
    assert denominator > 0
    return numerator / denominator


def fixture():
    rows = [dict(id=i, u=F(1 if i % 2 else -1), v=F(0), d=0,
                 y=F(1 if i % 2 else -1)) for i in range(96)]
    rows.append(dict(id=96, u=F(-1), v=F(1), d=1, y=F(1)))
    rows += [dict(id=i, u=F(-1), v=F(1), d=-(i - 95), y=F(-1))
             for i in range(97, 100)]
    return rows


def z_details(values):
    result = []
    for k, value in enumerate(values):
        others = values[:k] + values[k + 1:]
        mean = sum(others, F(0)) / len(others)
        var = sum(((x - mean) ** 2 for x in others), F(0)) / len(others)
        assert var > 0
        numerator = value - mean
        result.append(dict(row=k, numerator=str(numerator), variance=str(var),
                           z_squared=str(numerator ** 2 / var),
                           alarm=numerator > 0 and numerator ** 2 >= 36 * var))
    return result


def dot(left, right):
    return sum((x * y for x, y in zip(left, right)), F(0))


def derive():
    rows = fixture()
    deleted = set(range(22)) | {97, 98, 99}
    retained = [r for r in rows if r['id'] not in deleted]
    for r in rows:
        truth = r['u'] if r['v'] == 0 else F(1 if r['d'] > 0 else -1)
        assert r['y'] == truth
    a0, a1 = optimum(rows), optimum(retained)
    assert (a0, a1) == (F(1, 2), F(2))
    correct = lambda a: sum((score(a, r) > 0) == (r['y'] > 0) for r in rows)
    # The malicious-label version has the same represented least-squares objective.
    poison = dict(u=F(-1), v=F(1), y=F(1))
    camouflage = dict(u=F(-1), v=F(1), y=F(-1))
    assert optimum([poison] + [camouflage] * 3) == a0
    assert optimum([poison]) == a1
    erm = dict(before_coefficient=str(a0), after_coefficient=str(a1),
               conditional_before=str(-1 + a0), conditional_after=str(-1 + a1),
               original_before='-1', original_after='-1',
               fc_weight_before='1', fc_weight_after='1', bias_before='0', bias_after='0',
               dominant_clean_logits_identical=True,
               attack_construction='P1+C3 same represented input, conflicting role labels',
               benign_training_count=len(rows), benign_deleted_count=len(deleted),
               benign_deleted_fraction=str(F(len(deleted), len(rows))),
               benign_retained_count=len(retained), all_benign_labels_semantically_correct=True,
               benign_original100_correct_before=correct(a0),
               benign_original100_correct_after=correct(a1),
               heldout_domain=-1, heldout_conditional_truth='-1')

    # Exact PCA: both diagonal covariances have distinct eigenvalues.
    clean = [(F(x), F(y, 10)) for x in [-1, 1] for y in [-1, 1]]
    clean_new = [(x, 100 * y) for x, y in clean]
    covariance = lambda data: [sum((p[j] ** 2 for p in data), F(0)) / 4 for j in [0, 1]]
    assert sum((x * y for x, y in clean), F(0)) == 0
    assert sum((x * y for x, y in clean_new), F(0)) == 0
    old_cov, new_cov = covariance(clean), covariance(clean_new)
    assert old_cov == [F(1), F(1, 100)] and new_cov == [F(1), F(100)]
    delta = [(F(1), F(0))] + [(F(i, 100), F(i, 100)) for i in range(1, 10)]
    w0 = [(F(i, 17), F(i * i + 1, 31)) for i in range(10)]
    w1 = [tuple(x + y for x, y in zip(a, b)) for a, b in zip(w0, delta)]
    comparisons = 0
    for weights in [w0, w1]:
        transformed = [(x, y / 100) for x, y in weights]
        for h, hp in zip(clean, clean_new):
            for w, wp in zip(weights, transformed):
                assert dot(w, h) == dot(wp, hp)
                comparisons += 1
    old_z = z_details([abs(d[1]) for d in delta])
    new_z = z_details([abs(d[0]) for d in delta])
    assert [x['row'] for x in old_z if x['alarm']] == []
    assert [x['row'] for x in new_z if x['alarm']] == [0]
    gauge = dict(transform_diagonal=['1', '100'], covariance_before=list(map(str, old_cov)),
                 covariance_after=list(map(str, new_cov)), pca95_axis_before=0,
                 pca95_axis_after=1, retained_energy_both=str(F(100, 101)),
                 logits_compared_exact=comparisons,
                 all_input_identity='(W A^-1)(A h)+b = W h+b',
                 z_before=old_z, z_after=new_z)

    # Fixed rational example checks the exact end-to-end decomposition.
    mu = (F(1, 3), F(-2, 5))
    h0, h1 = (F(2), F(1)), (F(3), F(4))
    weight0, weight1 = [(F(1), F(2)), (F(-1), F(3))], [(F(3), F(-2)), (F(2), F(1))]
    bias0, bias1 = (F(1, 2), F(-2, 3)), (F(2, 3), F(5, 7))
    channels = []
    for w0r, w1r, b0, b1 in zip(weight0, weight1, bias0, bias1):
        dw = tuple(x - y for x, y in zip(w1r, w0r))
        parallel = dw[0] * (h0[0] - mu[0])
        perpendicular = dw[1] * (h0[1] - mu[1])
        feature = dot(w1r, tuple(x - y for x, y in zip(h1, h0)))
        constant = dot(dw, mu) + b1 - b0
        actual = dot(w1r, h1) + b1 - dot(w0r, h0) - b0
        assert parallel + perpendicular + feature + constant == actual
        channels.append(dict(parallel=str(parallel), perpendicular=str(perpendicular),
                             feature=str(feature), constant=str(constant), total=str(actual)))
    return dict(schema='exact_mechanism_constructions_v1', arithmetic='fractions.Fraction',
                erm=erm, gauge=gauge, decomposition=channels,
                real_model_experiments=0, clinical_or_operational_detection_claim=False,
                independent_training_seeds=0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    freeze = json.loads((HERE / 'FREEZE.json').read_text(encoding='utf-8'))
    for name, digest in freeze['files'].items():
        assert sha(HERE / name) == digest, name
    publication = json.loads((HERE / 'PUBLICATION.json').read_text(encoding='utf-8'))
    assert publication['source_commit'] and publication['freeze_sha256'] == sha(HERE / 'FREEZE.json')
    args.output.mkdir(parents=True, exist_ok=False)
    write_new(args.output / 'ONCE.json', dict(host=platform.node(), python=sys.version,
               source_freeze_sha256=sha(HERE / 'FREEZE.json'), publication=publication))
    result = derive()
    write_new(args.output / 'RESULT.json', result)
    print(json.dumps(dict(status='passed', result_sha256=sha(args.output / 'RESULT.json'),
                          erm=result['erm'], gauge_alarm_before=[], gauge_alarm_after=[0]),
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
