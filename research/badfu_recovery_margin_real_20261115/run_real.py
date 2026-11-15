"""Apply the frozen P06 solver to sealed endpoints using only authorized clean fits."""

import hashlib
import json
import math
import os
from pathlib import Path
import time

for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):
    os.environ[name] = '4'
os.environ['CUDA_VISIBLE_DEVICES'] = ''

import numpy as np
import torch
import torch.nn as nn
from scipy.optimize import linprog

import recovery_margin as guard
import timing as old

ROOT = Path(__file__).resolve().parent
NORMAL = ('normal193', 'normal228', 'normal850')
ARMS = ('none', 'anchor', 'nominal', 'bounded')
PATHS = ('balanced', 'client1_weighted')
HORIZON = 12
MARGIN = .1


def write(name, value):
    p = ROOT / name
    tmp = p.with_suffix('.tmp')
    with tmp.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')
    tmp.replace(p)


def select_data(cfg):
    rng = np.random.default_rng(61116)
    public = torch.load(old.check(cfg['public_data']), map_location='cpu', weights_only=True)
    retained = torch.load(old.check(cfg['retained_data']), map_location='cpu', weights_only=True)
    parts = old.read(old.check(cfg['partition']))['clean_cifar10_indices']
    removal = cfg['infected_normal_removal']
    deleted = old.read(old.check(removal))
    assert removal['format'] == 'local_positions' and removal['client'] == 1 and len(set(deleted)) == 850
    deleted = {parts[removal['client']][i] for i in deleted}
    labels = public['test_y']
    choices = np.stack([old.pick(rng, torch.where(labels == i)[0].numpy(), 320) for i in range(10)])
    public_ids = {k: np.sort(choices[:, a:b].ravel()) for k, (a, b) in {
        'fit': (0, 80), 'guard_pool': (80, 120), 'proxy': (120, 160), 'test': (160, 320)}.items()}
    assert len(set(np.concatenate(list(public_ids.values())))) == 3200
    draws = {k: old.pick(rng, sorted(set(parts[k]) - deleted), 416) for k in (1, 2, 3)}
    fit_ids = {k: v[:256] for k, v in draws.items()}
    client_ids = np.concatenate([v[256:] for v in draws.values()])
    assert not set(np.concatenate(list(draws.values()))) & deleted
    assert len(set(np.concatenate(list(draws.values())))) == 3 * 416
    member_pools = {'normal193': parts[4], 'normal228': sorted(set(range(50000)) - set(sum(parts[1:], [])))}
    assert {k: len(v) for k, v in member_pools.items()} == {'normal193': 9668, 'normal228': 11395}
    member_ids = {k: old.pick(rng, ids, 400) for k, ids in member_pools.items()}
    assert not set(np.concatenate(list(member_ids.values()))) & set(np.concatenate(list(draws.values())))
    plans = {name: [np.r_[old.pick(rng, range(256), first), old.pick(rng, range(256, 512), 32 - first)]
                    for _ in range(HORIZON)] for name, first in zip(PATHS, (16, 24))}
    extra = [old.pick(rng, range(512, 768), 32) for _ in range(HORIZON)]
    def raw_row(source, key, ids):
        return source[f'{key}_x'][ids], source[f'{key}_y'][ids].numpy()
    values = {k: raw_row(public, 'test', v) for k, v in public_ids.items()}
    values.update(retained=raw_row(retained, 'train', np.concatenate(list(fit_ids.values()))),
                  clients=raw_row(retained, 'train', client_ids))
    values.update({k: raw_row(retained, 'train', v) for k, v in member_ids.items()})
    receipts = {'public': {k: old.index_digest(v) for k, v in public_ids.items()},
                'retained': {str(k): old.index_digest(v) for k, v in fit_ids.items()},
                'client_eval': old.index_digest(client_ids), 'member_eval': {k: old.index_digest(v) for k, v in member_ids.items()},
                'scenario_batches': {k: old.index_digest(v) for k, v in plans.items()}, 'extra_batches': old.index_digest(extra),
                'separate_public_roles': True, 'train_overlap_known_deleted': 0}
    write('DATA_RECEIPT.json', receipts)
    return values, plans, extra, public_ids['test']


def embed(backbone, images):
    x = old.features(backbone, images).numpy().astype(np.float64)
    return np.column_stack((x, np.ones(len(x))))


def margin_matrix(head, x, y):
    logits = x @ head.T
    values = logits[np.arange(len(x)), y, None] - logits
    values[np.arange(len(x)), y] = np.inf
    return values.min(axis=1)


def choose_protected(base, pool_x, pool_y):
    margins = margin_matrix(base, pool_x, pool_y)
    eligible = [np.flatnonzero((pool_y == c) & (margins >= .35)) for c in range(10)]
    ids = np.concatenate([i[np.argsort(margins[i], kind='stable')[:12]] for i in eligible])
    return pool_x[ids], pool_y[ids], [len(i) for i in eligible]


def step(x, y, base, scale, radius):
    ridge = .05 * scale
    eta = .2 / (float(np.square(x).sum() / len(x)) + ridge)
    return guard.make_step(x, y, base, eta, ridge, radius)


def replay(head, schedule, extras):
    result = [head]
    actual_norms = []
    for spec, extra in zip(schedule, extras):
        nominal = guard.apply_step(result[-1], spec)
        state = guard.apply_step(result[-1], spec, extra)
        size = float(np.linalg.norm(state - nominal))
        assert size <= spec.radius + 1e-10
        actual_norms.append(size)
        result.append(state)
    return result, actual_norms


def maximum_correction(candidates, schedules, x, y):
    rows, rhs = [], []
    for path in schedules:
        for t, h in enumerate(guard._trajectory(candidates, path)):
            rows.append(-guard._margins(h, x, y).T)
            rhs.append(-np.repeat(guard.margin_radius(x, path[:t]) + MARGIN + 1e-7, h.shape[1] - 1))
    result = linprog(np.r_[1., np.zeros(len(candidates) - 1)], A_ub=np.concatenate(rows), b_ub=np.concatenate(rhs),
                     A_eq=[np.ones(len(candidates))], b_eq=[1.], bounds=[(0., 1.)] * len(candidates),
                     method='highs', options={'primal_feasibility_tolerance': 1e-9})
    if result.status == 2:
        return None
    if not result.success:
        raise RuntimeError(result.message)
    return float(1. - result.x[0])


def scores(heads, test, clients, member):
    def counts(logits, labels):
        return old.correct_counts(torch.from_numpy(logits), torch.from_numpy(labels))
    x, y = test
    cx, cy = clients
    out = []
    for head in heads:
        public = x @ head.T
        private = cx @ head.T
        row = {'public': counts(public, y), 'clients': {str(i + 1): counts(private[i*160:(i+1)*160], cy[i*160:(i+1)*160]) for i in range(3)}}
        out.append(row)
    if member is not None:
        mx, my = member
        out[-1]['audit'] = old.auc_by_class(torch.from_numpy(mx @ heads[-1].T), torch.from_numpy(public),
                                          torch.from_numpy(my), torch.from_numpy(y))
    return out


def compare(rows, baseline):
    def delta(a, b):
        assert a['n'] == b['n']
        return 100 * (a['correct'] - b['correct']) / b['n']
    overall, classes, clients = [], [], []
    for row, ref in zip(rows, baseline):
        overall.append(delta(row['public'], ref['public']))
        classes.append(min(100 * (a-b) / n for a,b,n in zip(row['public']['class_correct'],ref['public']['class_correct'],ref['public']['class_n'])))
        clients.append(min(delta(row['clients'][k], ref['clients'][k]) for k in ref['clients']))
    auc = None
    if 'audit' in rows[-1]:
        auc = abs(rows[-1]['audit']['macro_auc'] - .5) - abs(baseline[-1]['audit']['macro_auc'] - .5)
    return {'worst_overall_pp': min(overall), 'worst_class_pp': min(classes), 'worst_client_pp': min(clients), 'auc_distance_increase': auc,
            'passed': min(overall) >= -2 and min(classes) >= -5 and min(clients) >= -5 and (auc is None or auc <= .03)}


def run_case(name, cfg, constructor, data, plans, extra_plan, test_ids, open_archive):
    start = time.monotonic()
    print(f'{name} extracting fixed features', flush=True)
    entry = cfg['models'][name]
    model, _, _ = old.load_endpoint(entry, constructor)
    fc = model.model.fc
    base = np.column_stack((fc.weight.detach().numpy(), fc.bias.detach().numpy())).astype(np.float64)
    backbone = nn.Sequential(*list(model.model.children())[:-1], nn.Flatten(1)).eval()
    active = ('fit', 'guard_pool', 'proxy', 'test', 'retained', 'clients') + ((name,) if name in data else ())
    x = {k: (embed(backbone, data[k][0]), data[k][1]) for k in active}
    with torch.inference_mode():
        native = model(old.normalise(data['test'][0][:32])).numpy()
    cached = x['test'][0][:32] @ base.T
    np.testing.assert_allclose(cached, native, atol=4e-5, rtol=1e-5)
    assert np.array_equal(cached.argmax(1), native.argmax(1))
    fit_x, fit_y = x['fit']
    guard_x, guard_y, coverage = choose_protected(base, *x['guard_pool'])
    proxy_x, proxy_y = x['proxy']
    scale = float(np.square(fit_x).mean())
    candidates = guard.make_candidates(base, fit_x, fit_y, scale * np.array([.1, 1, 10, 100]))
    maximum_feature = max(np.linalg.norm(x['guard_pool'][0], axis=1).max(), np.linalg.norm(proxy_x, axis=1).max())
    epsilon = float(.1 / (HORIZON * math.sqrt(2) * maximum_feature))
    retained_x, retained_y = x['retained']
    schedules = [tuple(step(retained_x[i], retained_y[i], base, scale, epsilon) for i in plans[p]) for p in PATHS]
    nominal = [tuple(guard.RecoveryStep(s.transition, s.intercept, 0.) for s in path) for path in schedules]
    proposals = [guard.apply_step(base, step(retained_x[i], retained_y[i], base, scale, 0)) - base for i in extra_plan]
    proposed = [float(np.linalg.norm(p)) for p in proposals]
    arms = {'none': base}
    certificates = {}
    max_mass = None
    if min(coverage) >= 12:
        print(f'{name} solving identical candidate constraints', flush=True)
        for key, routes in zip(ARMS[1:], ([()], nominal, schedules)):
            chosen = guard.select_head(candidates, routes, guard_x, guard_y, proxy_x, proxy_y, proxy_y, MARGIN)
            if chosen is not None:
                arms[key] = chosen.head
                certificates[key] = {'weights': chosen.weights.tolist(), 'minima': chosen.minimum_margins,
                                     'worst_proxy_ce_upper': chosen.worst_proxy_loss_upper_bound}
        max_mass = maximum_correction(candidates, schedules, guard_x, guard_y)
    fit = {'input_sha256': entry['sha256'], 'coverage_pool_per_class': 40, 'eligible_by_class': coverage,
           'protected_by_class': [min(v, 12) for v in coverage], 'fit_ridge_scale': scale, 'epsilon': epsilon,
           'proposal_norm_by_step': proposed, 'candidate_count': 5, 'head_hashes': {k: hashlib.sha256(v.tobytes()).hexdigest() for k,v in arms.items()},
           'certificates': certificates, 'maximum_feasible_correction_mass': max_mass}
    write(f'{name}_FIT.json', fit)

    phases, realized, clean, deltas = {}, {}, {}, {}
    for key, head in arms.items():
        pairs = [replay(head, path, proposals) for path in schedules]
        phases[key] = [heads for heads, _ in pairs]
        realized[key] = {p: norms for p, (_, norms) in zip(PATHS, pairs)}
        clean[key] = {p: scores(heads, x['test'], x['clients'], x.get(name)) for p, heads in zip(PATHS, phases[key])}
        if key != 'none':
            deltas[key] = {p: compare(clean[key][p], clean['none'][p]) for p in PATHS}
    measured_margin = None
    active_correction = False
    if 'bounded' in arms:
        m = min(float(margin_matrix(h, guard_x, guard_y).min()) for heads in phases['bounded'] for h in heads)
        assert m >= MARGIN - 1e-9
        assert all(float(margin_matrix(h, guard_x, guard_y).min()) >= bound - 1e-9
                   for heads, row in zip(phases['bounded'], certificates['bounded']['minima']) for h,bound in zip(heads,row))
        measured_margin = m
        active_correction = sum(certificates['bounded']['weights'][1:]) >= .01 and not np.allclose(arms['bounded'], base, rtol=0, atol=1e-9)
    gate = active_correction and all(v['passed'] for v in deltas['bounded'].values())
    report = {'fit': fit, 'cap_clipped_steps_per_scenario': sum(int(v > epsilon) for v in proposed), 'realized_extra_norms': realized,
              'clean': clean, 'utility_deltas': deltas, 'protected_actual_min_margin': measured_margin,
              'nonzero_bounded_correction': active_correction, 'gate': gate}
    if open_archive:
        images, truth, target = old.read_archived_eval(cfg, test_ids, torch.from_numpy(x['test'][1]))
        bank = embed(backbone, images)
        truth = truth.numpy()
        archive = {}
        for key, routes in phases.items():
            archive[key] = {}
            for p, heads in zip(PATHS, routes):
                first, last = ((bank @ heads[i].T).argmax(1) for i in (0, -1))
                def count(indices):
                    return old.functional(torch.from_numpy(indices), torch.from_numpy(truth), target)
                archive[key][p] = {'anchor': count(first), 'final': count(last), 'reerror': int(((first == truth) & (last != truth)).sum()),
                                   'retained_correct': int(((first == truth) & (last == truth)).sum())}
        report['fixed_archive'] = archive
    assert old.sha(entry['path']) == entry['sha256'] and not torch.cuda.is_initialized()
    report['seconds'] = time.monotonic() - start
    write(f'{name}_RESULT.json', report)
    print(f'{name} complete gate={gate} seconds={report["seconds"]:.1f}', flush=True)
    return gate


def main():
    freeze = old.read(ROOT / 'FREEZE.json')
    for name, digest in freeze.items():
        assert old.sha(ROOT / name) == digest
    start = ROOT / 'STARTED.json'
    with start.open('x', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'runner_hash': old.sha(__file__)}, f)
    import sys
    import scipy
    import torchvision
    assert (torch.__version__, torchvision.__version__, np.__version__, scipy.__version__) == ('2.7.1+cu118', '0.22.1+cu118', '1.26.4', '1.15.3')
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(61116)
    cfg = old.read(ROOT / 'INPUTS.json')
    snapshot = old.check(cfg['snapshot']['manifest']).parent
    old.check(cfg['snapshot']['seal'])
    old.check(cfg['snapshot']['loader'])
    sys.path.insert(0, str(snapshot))
    import load_confirmed as sealed
    sealed.verify(snapshot, cfg['snapshot']['manifest']['sha256'])
    ctor = sealed.model_class(snapshot)
    data, plans, extras, ids = select_data(cfg)
    gates = {name: run_case(name, cfg, ctor, data, plans, extras, ids, False) for name in NORMAL}
    attack_evaluation = all(gates.values())
    if attack_evaluation:
        for name in ('infected_normal', 'attack23', 'attack20'):
            run_case(name, cfg, ctor, data, plans, extras, ids, True)
    write('TERMINAL.json', {'state': 'complete' if attack_evaluation else 'normal_gate_failed', 'normal_gates': gates,
                            'attack_evaluation': attack_evaluation, 'runtime_cpu': 'torch2.7.1/numpy1.26.4/scipy1.15.3'})


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        write('FAILURE.json', {'type': type(exc).__name__, 'message': str(exc)})
        raise
