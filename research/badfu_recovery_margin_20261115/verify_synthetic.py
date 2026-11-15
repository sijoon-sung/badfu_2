"""Deterministic, benign fixtures for the recovery-margin solver."""

from fractions import Fraction
import json
import platform

import numpy as np
import scipy

from recovery_margin import apply_step, make_candidates, make_step, margin_radius, select_head


def binary_margin(head, feature):
    return float((head[0] - head[1]) @ feature)


def timing_comparison():
    base = np.array([[.8, .2], [0, 0]])
    aggressive = np.array([[-2, 3], [0, 0]])
    heads = np.stack((base, aggressive))
    label = [0]
    recovery = [[0, 1]]
    protected = [[1, 1]]
    proxy = [[0, 1]]
    nominal = make_step(recovery, label, base, .9, 0, 0)
    bounded = make_step(recovery, label, base, .9, 0, .1)

    def solve(replays):
        return select_head(heads, replays, protected, label, proxy, label, [0], .2)

    instant = solve([()])
    future = solve([(nominal,)])
    robust = solve([(nominal,), (bounded,)])
    assert instant is not None and future is not None and robust is not None
    instant_later = binary_margin(apply_step(instant.head, nominal), protected[0])
    assert instant.weights[1] == 1 and np.isclose(instant_later, -.8, atol=1e-10)
    nominal_limit = (Fraction('1.72') - Fraction('.2')) / Fraction('2.52')
    robust_limit = (Fraction('1.72') - Fraction('.2') - Fraction('.2')) / Fraction('2.52')
    assert abs(future.weights[1] - float(nominal_limit)) < 1e-6
    assert abs(robust.weights[1] - float(robust_limit)) < 1e-6
    assert robust.minimum_margins[1][-1] >= .2
    assert len(robust.minimum_margins) == 2 and all(len(m) == 2 for m in robust.minimum_margins)
    return {'anchor_only_candidate_weight': float(instant.weights[1]), 'anchor_only_later_margin': round(instant_later, 6),
            'full_nominal_candidate_weight': round(float(future.weights[1]), 6),
            'full_bounded_candidate_weight': round(float(robust.weights[1]), 6),
            'full_bounded_final_margin_lower': round(robust.minimum_margins[1][-1], 7)}


def affinity_and_transport():
    base = np.array([[.3, .8], [.4, -.1], [.5, .3]])
    other = base + [[.1, -.1], [.2, .2], [0, -.1]]
    first = make_step([[1, 1]], [0], base, .2, .1, .07)
    second = make_step([[1, 0]], [1], base, .4, .1, .03)
    assert not np.allclose(first.transition @ second.transition, second.transition @ first.transition)
    x = np.array([[1., 1.], [.4, -.7], [0., 1.]])
    mix = .25 * base + .75 * other

    def replay(head):
        return apply_step(apply_step(head, first), second)

    clean = replay(mix)
    np.testing.assert_allclose(clean, .25 * replay(base) + .75 * replay(other), atol=1e-12)
    # Use two fixed perturbations in this benign fixture, with the server cap.
    after_first = apply_step(mix, first, [[.2, .3], [.1, 0], [.05, .12]])
    affected = apply_step(after_first, second, [[.03, -.2], [-.3, .1], [.2, -.4]])
    score_error = x @ (affected - clean).T
    pairwise_error = np.abs(score_error[:, :, None] - score_error[:, None, :])
    bound = margin_radius(x, (first, second))
    expected = np.sqrt(2) * (.07 * np.linalg.norm(x @ second.transition.T, axis=1) + .03 * np.linalg.norm(x, axis=1))
    np.testing.assert_allclose(bound, expected, atol=1e-12, rtol=0)
    assert np.all(pairwise_error <= bound[:, None, None] + 1e-12)
    np.testing.assert_allclose(margin_radius(x, ()), 0, atol=0, rtol=0)

    nominal_scores, actual_scores = x @ clean.T, x @ affected.T
    def loss(logits):
        return np.logaddexp.reduce(logits, axis=1) - logits.diagonal()
    assert np.all(loss(actual_scores) <= loss(nominal_scores) + bound + 1e-12)
    return {'cross_time_affinity': True, 'noncommuting_step_order': True,
            'pairwise_margin_and_proxy_bound_checked': True}


def enforced_limit():
    center = np.array([[.2, -.1], [0, .3]])
    step = make_step([[.2, 1]], [1], center, .2, .1, .2)
    nominal = apply_step(center, step)
    applied = apply_step(center, step, [[1, 2], [3, 4]])
    assert np.isclose(np.linalg.norm(applied - nominal), .2, atol=1e-12, rtol=0)
    zero = make_step([[.2, 1]], [1], center, .2, .1, 0)
    np.testing.assert_allclose(apply_step(center, zero, [[1, 2], [3, 4]]), nominal, atol=0, rtol=0)
    assert not step.transition.flags.writeable
    return {'realized_extra_norm': .2, 'zero_budget': 'exact'}


def ridge_correction():
    center = np.array([[1., -1.], [0., 0.]])
    fit = np.array([[0., 1.], [-1., 0.]])
    fit_labels = [0, 1]
    candidates = make_candidates(center, fit, fit_labels, [.05, .2])
    for weight, strength in zip(candidates[1:], [.05, .2]):
        gradient = (weight @ fit.T - np.eye(2)[fit_labels].T) @ fit / len(fit) + strength * (weight - center)
        np.testing.assert_allclose(gradient, 0, rtol=0, atol=1e-12)
    retained = [[1., 0.], [-1., 0.]]
    labels = [0, 1]
    step = make_step([[1., 0.]], [0], center, .3, .05, .01)
    chosen = select_head(candidates, [(step,)], retained, labels, [[0, .8], [-.8, 0]], [0, 1], [0, 1], .3)
    unseen = [0, .9]
    assert chosen is not None and binary_margin(center, unseen) < 0 < binary_margin(apply_step(chosen.head, step), unseen)
    return {'ridge_normal_equation_residual_bounded': True, 'benign_held_out_fixture_restored': True}


def infeasible_and_invalid():
    heads = np.array([[[-1.], [0.]], [[-2.], [0.]]])
    result = select_head(heads, [()], [[1]], [0], [[1]], [0], [0], .1)
    assert result is None
    center = heads[0]
    for invalid_call in (lambda: make_step([[1]], [0], center, 2, 0, 0),
                         lambda: make_step([[1]], [0], center, .1, 0, -.1),
                         lambda: make_candidates(center, [[1]], [0], [0]),
                         lambda: select_head(heads, [()], [[1]], [2], [[1]], [0], [0], .1)):
        try:
            invalid_call()
        except ValueError:
            continue
        raise AssertionError('Accepted an invalid input')
    return {'no_head_on_infeasible_constraints': True, 'invalid_inputs_rejected': 4}


def uncovered_feature():
    first = np.array([[1., 1], [0, 0]])
    second = np.array([[1., -1], [0, 0]])
    for point in ([1, 0], [-1, 0]):
        np.testing.assert_array_equal(first @ point, second @ point)
    assert binary_margin(first, [0, 1]) > 0 > binary_margin(second, [0, 1])
    return {'identical_protected_scores_can_disagree_on_an_uncovered_feature': True}


def main():
    results = {'timing': timing_comparison(), 'transport': affinity_and_transport(), 'clipping': enforced_limit(),
               'ridge_generation': ridge_correction(), 'feasibility': infeasible_and_invalid(),
               'coverage_limit': uncovered_feature()}
    assert len(results) == 6
    print(json.dumps({'state': 'passed', 'checks': results, 'device': 'CPU', 'dtype': 'float64',
                      'real_checkpoints_loaded': 0, 'runtime': {'python': platform.python_version(),
                      'numpy': np.__version__, 'scipy': scipy.__version__}}, indent=2))


if __name__ == '__main__':
    main()
