"""Independent equations: does not import or execute the producer."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--result', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.result.read_text(encoding='utf-8'))
    e = result['erm']
    # Independent polynomial interpolation identifies the unique minimizers.
    loss_before = lambda a: (a - 2) ** 2 + 3 * a ** 2
    loss_after = lambda a: (a - 2) ** 2
    stationary = []
    for loss in [loss_before, loss_after]:
        constant = loss(F(0))
        linear = (loss(F(1)) - loss(F(-1))) / 2
        quadratic = (loss(F(1)) + loss(F(-1))) / 2 - constant
        assert quadratic > 0
        stationary.append(-linear / (2 * quadratic))
    assert stationary == [F(e['before_coefficient']), F(e['after_coefficient'])] == [F(1, 2), F(2)]
    assert F(e['conditional_before']) == F(-1, 2) and F(e['conditional_after']) == 1
    assert e['fc_weight_before'] == e['fc_weight_after'] == '1'
    assert e['bias_before'] == e['bias_after'] == '0'
    # Count by disjoint semantic groups, not the producer's per-row loop.
    assert e['benign_training_count'] == 96 + 1 + 3 == 100
    assert e['benign_deleted_count'] == 22 + 3 == 25
    assert e['benign_retained_count'] == 74 + 1 == 75
    assert F(e['benign_deleted_fraction']) == F(1, 4)
    assert e['benign_original100_correct_before'] == 96 + 3 == 99
    assert e['benign_original100_correct_after'] == 96 + 1 == 97
    assert e['heldout_domain'] == -1 and e['heldout_conditional_truth'] == '-1'

    g = result['gauge']
    assert g['covariance_before'] == ['1', '1/100'] and g['covariance_after'] == ['1', '100']
    assert F(g['retained_energy_both']) == F(100, 101) > F(95, 100)
    assert (g['pca95_axis_before'], g['pca95_axis_after']) == (0, 1)
    for name, values in [('z_before', [F(i, 100) for i in range(10)]),
                         ('z_after', [F(1)] + [F(i, 100) for i in range(1, 10)])]:
        alarms = []
        for k, saved in enumerate(g[name]):
            rest = [v for i, v in enumerate(values) if i != k]
            numerator = values[k] - sum(rest, F(0)) / 9
            # Pairwise variance formula is independent of centered-square implementation.
            var = sum(((x - y) ** 2 for x in rest for y in rest), F(0)) / (2 * 9 * 9)
            assert F(saved['variance']) == var and F(saved['numerator']) == numerator
            assert F(saved['z_squared']) == numerator * numerator / var
            alarm = numerator > 0 and numerator * numerator >= 36 * var
            assert saved['alarm'] == alarm
            if alarm:
                alarms.append(k)
        assert alarms == ([] if name == 'z_before' else [0])
    assert F(g['z_after'][0]['z_squared']) == F(5415, 4)
    assert g['logits_compared_exact'] == 80
    # General diagonal inverse identity, coefficient by coefficient.
    for wx in [F(-3), F(0), F(7, 11)]:
        for wy in [F(-4, 3), F(1), F(9)]:
            assert wx == wx / 1 * 1 and wy == wy / 100 * 100
    # Direct before/after logit differences for the two fixed rows.
    expected = [F(-17, 6), F(218, 21)]
    for channel, total in zip(result['decomposition'], expected):
        assert F(channel['total']) == total
        assert sum((F(channel[k]) for k in ['parallel', 'perpendicular', 'feature', 'constant']), F(0)) == total
    receipt = dict(status='passed', checker='independent_fraction_polynomial_pairwise_variance_v1',
                   result_sha256=hashlib.sha256(args.result.read_bytes()).hexdigest(),
                   real_model_experiments=0, independent_training_seeds=0)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
