"""Test two fixed necessary-condition claims; exact algebra, no model training."""
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def encoded(value):
    if isinstance(value, F):
        return str(value)
    if isinstance(value, dict):
        return {k: encoded(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encoded(v) for v in value]
    return value

def gradient(points):
    # For w=(log(3),0), sigmoid(log(3)*u) is exactly 3/4 or 1/4.
    answer = [F(0), F(0)]
    for u, v, y in points:
        probability = F(3, 4) if u == 1 else F(1, 4)
        for j, x in enumerate((u, v)):
            answer[j] += (probability - y) * x / len(points)
    return answer

def check_benign_deletion():
    points = [(F(u), F(v, 10), int(u > 0)) for u in (-1, 1) for v in (-1, 1)]
    removed = (F(-1), F(1, 10), 0)
    retained = [p for p in points if p != removed]
    before, after = gradient(points), gradient(retained)
    assert before == [F(-1, 4), F(0)]
    assert after == [F(-1, 4), F(-1, 120)]
    # Population covariance and clean accuracy are checked independently.
    means = [sum(p[j] for p in points) / len(points) for j in range(2)]
    covariance = [[sum((p[i]-means[i])*(p[j]-means[j]) for p in points)/len(points)
                   for j in range(2)] for i in range(2)]
    assert covariance == [[F(1), F(0)], [F(0), F(1, 100)]]
    energy = covariance[0][0] / (covariance[0][0]+covariance[1][1])
    assert energy > F(95, 100)
    assert all(int(u > 0) == y for u, _, y in points)
    step_difference = [-(after[j]-before[j]) for j in range(2)]
    assert step_difference == [F(0), F(1, 120)]
    return dict(status='counterexample_to_exact_cancellation',
                clean_points=points, removed=removed, deleted_fraction=F(1, 4),
                clean_accuracy=F(1), covariance=covariance, top_axis_energy=energy,
                full_gradient=before, retained_gradient=after,
                one_step_retained_minus_full_for_lr1=step_difference,
                limit='Disproves exact-zero premise, not every possible tail-variance bound or detector.')

def check_in_span_transition():
    clean = [(F(-2), F(0), 0), (F(2), F(0), 1)]
    pre_bias, post_bias = F(0), F(3, 2)
    predict = lambda u, bias: int(u + bias > 0)
    assert all(predict(u, pre_bias) == y for u, _, y in clean)
    assert all(predict(u, post_bias) == y for u, _, y in clean)
    trigger_input = (F(-1), F(0))
    assert trigger_input[0] < 0  # Still class 0 under the declared semantic label.
    assert predict(trigger_input[0], pre_bias) == 0
    assert predict(trigger_input[0], post_bias) == 1
    assert trigger_input[1] == 0
    return dict(status='counterexample_to_necessary_off_span_geometry',
                clean_accuracy_pre=F(1), clean_accuracy_post=F(1),
                conditional_target_rate_pre=F(0), conditional_target_rate_post=F(1),
                clean_span_axis=[1, 0], triggered_point=trigger_input,
                perpendicular_trigger_component=F(0), weight_delta=[[0, 0]],
                bias_delta=post_bias-pre_bias,
                limit='Constructed functions only; no claim of a trained BadFU/FUBA/FedUBA mechanism or universal impossibility.')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='Verify committed output without overwriting it')
    args = ap.parse_args()
    plan = json.loads((HERE/'PLAN.json').read_text(encoding='utf-8'))
    for name, expected in plan['frozen_files'].items():
        assert digest(HERE/name) == expected, ('Frozen source mismatch', name)
    result = encoded(dict(hypothesis_id=plan['id'], arithmetic='fractions.Fraction',
        benign_deletion=check_benign_deletion(), in_span_transition=check_in_span_transition(),
        common_detector='unvalidated', real_model_training=False,
        scope='Two exact counterexamples to asserted geometric necessities, not attack-detection performance.'))
    path = HERE/'MATH_RESULTS.json'
    if args.check:
        assert json.loads(path.read_text(encoding='utf-8')) == result
    else:
        with path.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'state':'checked' if args.check else 'completed',
                      'necessary_geometric_claims':'counterexamples_found',
                      'common_detector':'unvalidated','training':False}))

if __name__ == '__main__':
    main()
