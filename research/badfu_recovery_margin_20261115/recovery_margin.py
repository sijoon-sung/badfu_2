"""Reference solver for post-deletion head correction with finite recovery guarantees."""

from dataclasses import dataclass
from itertools import chain
import math

import numpy as np
from scipy.optimize import linprog


def _finite(values, dims):
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != dims or not values.size or not np.isfinite(values).all():
        raise ValueError(f'Expected a finite, nonempty {dims}-dimensional array')
    return values


def _labeled(x, y, classes, dimension):
    x, y = _finite(x, 2), np.asarray(y)
    if (x.shape[1] != dimension or y.shape != (len(x),) or y.dtype.kind not in 'iu'
            or np.any(y < 0) or np.any(y >= classes)):
        raise ValueError('Features and integer class labels must agree with the head')
    return x, y.astype(np.intp)


def _loss_terms(x, y, center):
    classes, dimension = center.shape
    x, y = _labeled(x, y, classes, dimension)
    return x.T @ x / len(x), np.eye(classes)[y].T @ x / len(x)


@dataclass(frozen=True)
class RecoveryStep:
    transition: np.ndarray
    intercept: np.ndarray
    radius: float

    def __post_init__(self):
        transition = _finite(self.transition, 2).copy()
        intercept = _finite(self.intercept, 2).copy()
        dimension = intercept.shape[1]
        if transition.shape != (dimension, dimension) or not math.isfinite(self.radius) or self.radius < 0:
            raise ValueError('Invalid transition shape or residual radius')
        transition.setflags(write=False)
        intercept.setflags(write=False)
        object.__setattr__(self, 'transition', transition)
        object.__setattr__(self, 'intercept', intercept)


def make_step(x, y, center, learning_rate, ridge, radius):
    """Create a step from authorized retained features and a fixed post-deletion center."""
    center = _finite(center, 2)
    if not all(map(math.isfinite, (learning_rate, ridge))) or learning_rate <= 0 or ridge < 0:
        raise ValueError('The learning rate must be positive and ridge nonnegative')
    gram, cross = _loss_terms(x, y, center)
    identity = np.eye(center.shape[1])
    hessian = gram + ridge * identity
    if learning_rate * np.linalg.eigvalsh(hessian)[-1] > 1.0:
        raise ValueError('The step exceeds the declared contraction regime')
    return RecoveryStep(identity - learning_rate * hessian, learning_rate * (cross + ridge * center), radius)


def make_candidates(center, clean_x, clean_y, strengths):
    """Include the post-deletion head and ridge heads fit to an authorized correction pool."""
    center = _finite(center, 2)
    gram, cross = _loss_terms(clean_x, clean_y, center)
    identity = np.eye(center.shape[1])
    heads = [center]
    for strength in strengths:
        if not math.isfinite(strength) or strength <= 0:
            raise ValueError('Candidate ridge strengths must be positive and finite')
        heads.append(np.linalg.solve(gram + strength * identity, (cross + strength * center).T).T)
    return _finite(np.stack(heads), 3)


def apply_step(head, step, proposed_extra=None):
    """Apply the declared server step and clip the aggregate extra update to its radius."""
    head = _finite(head, 2)
    if head.shape != step.intercept.shape:
        raise ValueError('Recovery step and head have different shapes')
    next_head = head @ step.transition + step.intercept
    if proposed_extra is not None:
        extra = _finite(proposed_extra, 2)
        if extra.shape != head.shape:
            raise ValueError('Extra update and head have different shapes')
        length = np.linalg.norm(extra)
        if not math.isfinite(length):
            raise ValueError('The extra update norm is not finite')
        next_head += extra * min(1.0, step.radius / length) if length > 0 else extra
    return _finite(next_head, 2)


def margin_radius(x, prefix):
    """Bound the loss of any pairwise class margin after the specified steps."""
    x = _finite(x, 2)
    transported = x.T
    bound = np.zeros(len(x))
    for step in reversed(prefix):
        bound += step.radius * np.linalg.norm(transported, axis=0)
        transported = step.transition @ transported
    bound *= math.sqrt(2.0)
    return _finite(bound, 1)


def _trajectory(heads, replay):
    yield heads
    for step in replay:
        heads = heads @ step.transition + step.intercept
        yield heads


def _margins(heads, x, y):
    logits = x @ heads.swapaxes(-1, -2)
    rivals = np.arange(heads.shape[-2]) != y[:, None]
    return (logits[:, np.arange(len(y)), y, None] - logits)[:, rivals]


def _proxy_loss_bounds(heads, x, y, groups, radius):
    logits = x @ heads.swapaxes(-1, -2)
    relative = logits - logits[:, np.arange(len(y)), y, None]
    top = relative.max(axis=-1, keepdims=True)
    losses = np.log(np.exp(relative - top).sum(axis=-1)) + top[..., 0] + radius
    return np.stack([losses[:, groups == group].mean(axis=1) for group in np.unique(groups)])


@dataclass(frozen=True)
class Correction:
    head: np.ndarray
    weights: np.ndarray
    worst_proxy_loss_upper_bound: float
    minimum_margins: tuple[tuple[float, ...], ...]


def select_head(candidates, replays, protected_x, protected_y, proxy_x, proxy_y, proxy_groups, margin):
    """Select one mixture for all declared scenarios and stages, or return None if infeasible."""
    candidates = _finite(candidates, 3)
    k, classes, dimension = candidates.shape
    protected_x, protected_y = _labeled(protected_x, protected_y, classes, dimension)
    proxy_x, proxy_y = _labeled(proxy_x, proxy_y, classes, dimension)
    groups = np.asarray(proxy_groups)
    replays = tuple(tuple(replay) for replay in replays)
    if classes < 2 or groups.shape != (len(proxy_x),) or groups.dtype.kind not in 'iu' or not replays:
        raise ValueError('Provide two or more classes, proxy group IDs and a replay scenario')
    if not math.isfinite(margin) or margin <= 0:
        raise ValueError('The certified margin must be positive and finite')
    if any(step.intercept.shape != (classes, dimension) for step in chain.from_iterable(replays)):
        raise ValueError('Replay dimensions must match the candidate heads')

    rows, limits, proxy_bounds = [], [], []
    # A positive fixed reserve is followed by a separate check on the returned head.
    reserve = 1e-7
    for replay in replays:
        for t, states in enumerate(_trajectory(candidates, replay)):
            radius = margin_radius(protected_x, replay[:t])
            margins = _margins(states, protected_x, protected_y).T
            rows.append(np.column_stack((-margins, np.zeros(len(margins)))))
            limits.append(-np.repeat(radius + margin + reserve, classes - 1))
            loss = _proxy_loss_bounds(states, proxy_x, proxy_y, groups, margin_radius(proxy_x, replay[:t]))
            proxy_bounds.append(loss)
            rows.append(np.column_stack((loss, -np.ones(len(loss)))))
            limits.append(np.zeros(len(loss)))

    result = linprog(np.r_[np.zeros(k), 1.0], A_ub=np.concatenate(rows), b_ub=np.concatenate(limits),
                     A_eq=[np.r_[np.ones(k), 0.0]], b_eq=[1.0], bounds=[(0, 1)] * k + [(0, None)],
                     method='highs', options={'primal_feasibility_tolerance': 1e-9})
    if result.status == 2:
        return None
    if not result.success:
        raise RuntimeError(f'Head selection failed: {result.message}')
    weights = _finite(result.x[:k], 1)
    if np.any(weights < 0) or not np.isclose(weights.sum(), 1, atol=1e-9, rtol=0):
        raise RuntimeError('Solver returned invalid mixture weights')
    weights = weights / weights.sum()
    head = np.einsum('i,icd->cd', weights, candidates)
    certified = []
    for replay in replays:
        minima = []
        for t, state in enumerate(_trajectory(head[None, :, :], replay)):
            r = np.repeat(margin_radius(protected_x, replay[:t]), classes - 1)
            lower = _margins(state, protected_x, protected_y)[0] - r
            if not np.isfinite(lower).all() or np.any(lower < margin):
                raise RuntimeError('Replayed mixture failed its numeric margin check')
            minima.append(float(lower.min()))
        certified.append(tuple(minima))
    upper_bound = float((np.concatenate(proxy_bounds) @ weights).max())
    head.setflags(write=False)
    weights.setflags(write=False)
    return Correction(head, weights, upper_bound, tuple(certified))
