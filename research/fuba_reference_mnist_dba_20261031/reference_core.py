"""FUBA Algorithms 1/2, fixed DBA data and a network without BN buffers."""
from dataclasses import dataclass
import copy
import torch
from torch import nn


@dataclass(frozen=True)
class Settings:
    epochs: int = 50
    batch: int = 64
    lr: float = .001
    consistency: float = 2.
    mixture: float = .25
    target: int = 8


PATCHES = ((0, 2, 0, 5), (4, 6, 7, 12), (4, 6, 0, 5), (0, 2, 7, 12))


def stamp(images, role):
    result = images.clone()
    for y0, y1, x0, x1 in PATCHES if role == 4 else [PATCHES[role]]:
        result[:, :, y0:y1, x0:x1] = 1
    return result


def weights(anchor, benign):
    a, b = dict(anchor.named_parameters()), dict(benign.named_parameters())
    assert a.keys() == b.keys()
    diff = {k: (a[k].detach() - b[k].detach()).abs() for k in a}
    low = min(float(v.min()) for v in diff.values())
    high = max(float(v.max()) for v in diff.values())
    return {k: torch.ones_like(v) if high == low else 1 - (v - low) / (high - low)
            for k, v in diff.items()}


def state(model):
    return {k: v.detach().clone() for k, v in model.state_dict().items()}


def affine(incoming, other, scale):
    result = copy.deepcopy(incoming)
    left, right = incoming.state_dict(), other.state_dict()
    assert left.keys() == right.keys()
    assert all(v.is_floating_point() for v in left.values()), 'This reference is for the no-buffer Net'
    result.load_state_dict({k: left[k] + scale * (right[k] - left[k]) for k in left}, strict=True)
    return result


def expected(upload, representative, mixture=.25):
    result = copy.deepcopy(upload)
    a, b = upload.state_dict(), representative.state_dict()
    result.load_state_dict({k: mixture * a[k] + (1 - mixture) * b[k] for k in a}, strict=True)
    return result


def learn(model, x, y, settings, *, phase_seed, phase, gradient_weights=None, reference=None, log=None):
    literal = gradient_weights is not None or reference is not None
    optimizer = (torch.optim.SGD(model.parameters(), lr=settings.lr, foreach=True) if literal
                 else torch.optim.Adam(model.parameters(), lr=settings.lr, foreach=True))
    model.train()
    ref = torch.nn.utils.parameters_to_vector(reference.parameters()).detach() if reference is not None else None
    device = x.device
    generator = torch.Generator(device=device).manual_seed(phase_seed)
    batches = 0
    for epoch in range(settings.epochs):
        order = torch.randperm(len(y), generator=generator, device=device)
        total = torch.zeros((), device=device)
        finite = torch.ones((), dtype=torch.bool, device=device)
        for idx in order.split(settings.batch):
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.cross_entropy(model(x[idx]), y[idx])
            if ref is not None:
                vector = torch.nn.utils.parameters_to_vector(model.parameters())
                loss = loss + settings.consistency * (vector - ref).square().sum()
            finite.logical_and_(torch.isfinite(loss.detach()))
            loss.backward()
            if gradient_weights is not None:
                with torch.no_grad():
                    for name, parameter in model.named_parameters():
                        parameter.grad.mul_(gradient_weights[name])
            optimizer.step()
            total.add_(loss.detach() * len(idx))
            batches += 1
        state_finite = torch.stack([torch.isfinite(v).all() for v in model.state_dict().values()]).all()
        if not bool(finite & state_finite):
            raise FloatingPointError('Nonfinite epoch; role is not submitted')
        if log:
            log(phase=phase, epoch=epoch + 1, epochs=settings.epochs, batches=batches,
                examples=len(y), loss=float(total) / len(y), optimizer=type(optimizer).__name__)
    return model, optimizer, generator.get_state(), batches


def embed(incoming, clean_x, clean_y, poisoned_x, poisoned_y, settings, *, seed, log, capture):
    a, opt, rng, n = learn(copy.deepcopy(incoming), poisoned_x, poisoned_y, settings,
                          phase_seed=seed + 1, phase='backdoor_anchor', log=log)
    capture(1, a, opt, rng, n)
    b, opt, rng, n = learn(copy.deepcopy(a), clean_x, clean_y, settings,
                          phase_seed=seed + 2, phase='benign_anchor', log=log)
    capture(2, b, opt, rng, n)
    w = weights(a, b)
    del a, b
    result, opt, rng, n = learn(copy.deepcopy(incoming), poisoned_x, poisoned_y, settings,
                               phase_seed=seed + 3, phase='embedding', gradient_weights=w, log=log)
    capture(3, result, opt, rng, n)
    return result


def attacker(incoming, clean_x, clean_y, poison_x, poison_y, settings, *, seed, log, capture, score):
    embedded = embed(incoming, clean_x, clean_y, poison_x, poison_y, settings, seed=seed, log=log, capture=capture)
    rep, opt, rng, n = learn(copy.deepcopy(incoming), clean_x, clean_y, settings,
                             phase_seed=seed + 4, phase='representative', log=log)
    capture(4, rep, opt, rng, n)
    scores = []
    for point in range(11):
        gamma = point / 10
        candidate = expected(affine(incoming, embedded, gamma), rep, settings.mixture)
        scores.append({'gamma': gamma, **score(candidate)})
    passed = [s['gamma'] for s in scores if s['ASR_pct'] < 10]
    gamma = max(passed) if passed else 0.
    return affine(incoming, embedded, gamma), {'gamma': gamma, 'scores': scores,
                                               'constraint_met': bool(passed), 'grid_complete': True}


def defender(incoming, clean_x, clean_y, poison_x, poison_y, settings, *, seed, log, capture):
    ref = embed(incoming, clean_x, clean_y, poison_x, poison_y, settings, seed=seed, log=log, capture=capture)
    recovered, opt, rng, n = learn(copy.deepcopy(ref), clean_x, clean_y, settings,
                                   phase_seed=seed + 4, phase='recovery', reference=ref, log=log)
    capture(4, recovered, opt, rng, n)
    result = copy.deepcopy(incoming)
    g, a, b = incoming.state_dict(), recovered.state_dict(), ref.state_dict()
    result.load_state_dict({k: g[k] + a[k] - b[k] for k in g}, strict=True)
    return result, {'reference': 'unscaled_embedding', 'objective': 'clean_CE_plus_2_squared_L2'}
