"""Verify archived pairs and evaluate a one-shot SVD head edit on DISLAB CPU."""

import json
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
NORMAL = ('normal193', 'normal228')
ATTACK = ('attack23', 'attack20')
CASES = NORMAL + ATTACK
GRID = sorted(((k, a) for k in (1, 2, 4) for a in (.25, .5, 1.)), key=lambda v: (v[0] * v[1], v[1], v[0]), reverse=True)

import run_real as p07
import numpy as np
import torch
from PIL import Image


def lock(path, digest):
    return p07.old.check({'path': str(path), 'sha256': digest})


def read(path):
    return p07.old.read(path)


def verify_pairs(cfg):
    print('checking archived request provenance and same-image pairs', flush=True)
    source = p07.old.check(cfg['evaluation_only']['reader'])
    helper = source.parent
    base = helper.parents[1]
    plain = base / 'upstream/data_prepare/record/badnet_original'
    archive_meta = read(lock(helper / 'paper_input_alignment.json', '7b588dcff8517ea4e3c001873d015a9e82a320ff9b13927281e522374d6f6457'))
    paper_run = helper / 'runs/badfu_paper32_plain_s20261020'
    lock(helper / 'paper_reproduction.py', '1c25fb6ce1fef44382176633761a7d25487832bebe0fd3593b1d0cbe941f7883')
    protocol = read(lock(paper_run / 'protocol.json', 'e1d0b0dbbdb21bc8ee507afe847de9aa6b5a398bdf8a74b547501148584c20e0'))
    paper_manifest = read(lock(paper_run / 'poison_only/trajectory/manifest.json', 'a8dd29c3a972cdd1c8bb9914e8cdbbdcb09537217f639abab283980a7e3e1ef2'))
    assert protocol['seed'] == 20261020 and protocol['batch_size'] == 32 and protocol['rounds'] == 40
    assert paper_manifest['metadata']['phase'] == 'poison_only'
    assert len(paper_manifest['rounds']) == 40 and sum(paper_manifest['metadata']['counts']) == 49150
    final = paper_manifest['rounds'][-1]
    assert final['path'] == Path(cfg['models']['attack20']['path']).name and final['sha256'] == cfg['models']['attack20']['sha256']

    original = torch.load(p07.old.check(cfg['retained_data']), map_location='cpu', weights_only=True)
    split = read(p07.old.check(cfg['partition']))
    parts = split['clean_cifar10_indices']
    cover_ids = split['cover_cifar10_indices']
    poison_ids = split['poison_cifar10_indices']
    assert len(set(cover_ids)) == 850 and not set(cover_ids) & set(poison_ids)
    ids = {'attack23': sorted(cover_ids), 'normal193': sorted(parts[4]),
           'normal228': sorted(parts[0] + cover_ids + poison_ids)}
    history = Path('D:/MULTISEED_ACTUAL_FU_20261022/badfu/seed_20261023')
    phases = {'attack23': ('attack_FU', 'd4891b555318678b90dd15ba6ff249051bc6cc3069c30f3c0819381b08e192bf', 850),
              'normal193': ('normal_big4_FU', 'fd4a1805525363d2fcfbdc62c1b84c024127e997ffa8bae3c31a9c4857c776b9', 9668),
              'normal228': ('normal_largest0_FU', '6a8558ff20094db9125bc40e505134be7acf0211b4147b2729493fe9baccbd21', 11395)}
    for case, (phase, digest, n) in phases.items():
        info = read(lock(history / phase / 'COMPLETE.json', digest))
        assert info['checkpoint_sha256'] == cfg['models'][case]['sha256'] and info['phase'] == phase
        assert len(ids[case]) == len(set(ids[case])) == info['audit']['removed_n'] == n
        assert p07.old.index_digest(ids[case]) == info['audit']['removed_indices_sha256']

    assert archive_meta['plain_original_labels_preserved'] and archive_meta['sample_indices_match_active_partition']
    record = torch.load(p07.old.check(cfg['evaluation_only']['record']), map_location='cpu', weights_only=False)
    request = record['bd_train']['cv_data_container']['data_dict']
    index_order, requested, requested_y = [], [], []
    file_hashes = archive_meta['plain_cover_file_sha256']
    for i, row in request.items():
        full = str(row['path']).replace('\\', '/').split('/')
        relative = '/'.join(full[full.index('cv_train_dataset'):])
        path = lock(plain / relative, file_hashes[relative])
        with Image.open(path) as im:
            requested.append(np.asarray(im.convert('RGB')).copy())
        index_order.append(int(i))
        requested_y.append(int(row['other_info'][0]))
    assert index_order == cover_ids and len(requested) == len(file_hashes) == 850
    del record
    request_x = torch.from_numpy(np.stack(requested))
    reference = original['train_x'][index_order]
    assert reference.shape == request_x.shape == (850, 32, 32, 3)
    assert original['train_y'][index_order].tolist() == requested_y
    equal = (request_x == reference).all(dim=-1).flatten(1).sum(dim=1)
    assert bool(((equal >= 512) & (equal < 1024)).all())
    proof = {'attack23': {'source_identity_pairs': 850, 'original_label_matches': 850, 'nonidentical_pairs': 850,
                          'index_sha256': p07.old.index_digest(ids['attack23'])},
             'attack20': {'source_identity_pairs': 850, 'original_label_matches': 850, 'nonidentical_pairs': 850,
                          'index_sha256': p07.old.index_digest(sorted(index_order))}}
    for name in NORMAL:
        clean_request = original['train_x'][ids[name]]
        clean_refs = torch.index_select(original['train_x'], 0, torch.tensor(ids[name]))
        assert torch.equal(clean_request, clean_refs)
        proof[name] = {'source_identity_pairs': len(ids[name]), 'original_label_matches': len(ids[name]), 'nonidentical_pairs': 0,
                       'index_sha256': p07.old.index_digest(ids[name]), 'exact_pixel_matches': len(ids[name])}
    p07.write('PAIRS.json', proof)
    print(f'pair audit complete: {[(name, row["source_identity_pairs"]) for name, row in proof.items()]}', flush=True)
    return request_x, reference, {name: original['train_x'][ids[name][:32]] for name in NORMAL}


def edit_head(base, mean, directions, rank, alpha):
    if rank == 0:
        return base.copy()
    v = directions[:, :rank]
    removed = alpha * ((base[:, :-1] @ v) @ v.T)
    head = base.copy()
    head[:, :-1] -= removed
    head[:, -1] += removed @ mean
    return head


def proxy_pass(counts, baseline):
    """2pp overall and 5pp per class on a 400-image, 40/class proxy."""
    return all(
        obs['correct'] - before['correct'] >= -8
        and min(a-b for a, b in zip(obs['class_correct'], before['class_correct'], strict=True)) >= -2
        for path, frames in counts.items() for obs, before in zip(frames, baseline[path], strict=True)
    )


def run_case(name, cfg, constructor, data, plans, extras_plan, ids, request, reference, clean_pairs):
    begin = time.monotonic()
    print(f'{name}: extracting fixed features', flush=True)
    entry = cfg['models'][name]
    model, _, _ = p07.old.load_endpoint(entry, constructor)
    fc = model.model.fc
    base = np.column_stack((fc.weight.detach().numpy(), fc.bias.detach().numpy())).astype(np.float64)
    backbone = torch.nn.Sequential(*list(model.model.children())[:-1], torch.nn.Flatten(1)).eval()
    needs = ('fit', 'guard_pool', 'proxy', 'retained', 'test', 'clients')
    x = {k: p07.embed(backbone, data[k][0]) for k in needs}
    with torch.inference_mode():
        native = model(p07.old.normalise(data['test'][0][:32])).numpy()
    np.testing.assert_allclose(x['test'][:32] @ base.T, native, atol=4e-5, rtol=1e-5)
    assert np.array_equal((x['test'][:32] @ base.T).argmax(1), native.argmax(1))
    mean = x['fit'][:, :-1].mean(axis=0)
    if name in NORMAL:
        samples = clean_pairs[name]
        z = p07.embed(backbone, samples)
        assert np.array_equal(z, p07.embed(backbone, samples.clone()))
        directions, singular = None, np.zeros(0)
    else:
        residual = (p07.embed(backbone, request) - p07.embed(backbone, reference))[:, :-1]
        assert residual.shape == (850, 512) and np.isfinite(residual).all()
        _, singular, vt = np.linalg.svd(residual, full_matrices=False)
        assert np.isfinite(singular).all() and singular[3] > 1e-10
        directions = vt[:4].T
        np.testing.assert_allclose(directions.T @ directions, np.eye(4), atol=1e-10, rtol=0)
    rng = np.random.default_rng(61119)
    random_basis = np.linalg.qr(rng.normal(size=(512, 4)), mode='reduced')[0]

    scale = float(np.square(x['fit']).mean())
    maximum = max(np.linalg.norm(x['guard_pool'], axis=1).max(), np.linalg.norm(x['proxy'], axis=1).max())
    radius = float(.1 / (p07.HORIZON * math.sqrt(2) * maximum))
    retained_x, retained_y = x['retained'], data['retained'][1]
    specs = {path: [p07.step(retained_x[i], retained_y[i], base, scale, radius) for i in batches]
             for path, batches in plans.items()}
    extra = [p07.guard.apply_step(base, p07.step(retained_x[i], retained_y[i], base, scale, 0.)) - base
             for i in extras_plan]
    proposal_norms = [float(np.linalg.norm(e)) for e in extra]

    def replay(head):
        return {key: p07.replay(head, path, extra) for key, path in specs.items()}

    def counts(heads, k):
        return [p07.old.correct_counts(torch.from_numpy(x[k] @ h.T), torch.from_numpy(data[k][1])) for h in heads]

    def proxy(results):
        return {path: counts(heads, 'proxy') for path, (heads, _) in results.items()}

    baseline = replay(base)
    normal_proxy = proxy(baseline)

    def choose(basis):
        for rank, alpha in GRID:
            h = edit_head(base, mean, basis, rank, alpha)
            states = replay(h)
            if proxy_pass(proxy(states), normal_proxy):
                return rank, alpha, states
        return 0, 0., baseline

    if directions is None:
        chosen = (0, 0., baseline)
        sham = choose(random_basis)
    else:
        chosen = choose(directions)
        k, alpha, _ = chosen
        sham = (k, alpha, replay(edit_head(base, mean, random_basis, k, alpha)))
        if k:
            verify = (x['proxy'][:, :-1] - mean) @ directions[:, :k]
            transformed = x['proxy'][:, :-1] - alpha * verify @ directions[:, :k].T
            expected = transformed @ base[:, :-1].T + base[:, -1]
            actual = x['proxy'] @ chosen[2]['balanced'][0][0].T
            np.testing.assert_allclose(actual, expected, atol=1e-10, rtol=0)
    arms = {'none': (0, 0., baseline), 'svd': chosen, 'random': sham}
    fit = {'model_sha256': entry['sha256'], 'exact_zero_residual': directions is None, 'numerical_rank_checked': int(directions is not None) * 4,
           'epsilon': radius, 'proposals_clipped': sum(v > radius for v in proposal_norms),
           'policies': {a: {'rank': k, 'alpha': alpha, 'proxy_pass': proxy_pass(proxy(states), normal_proxy),
                            'head_sha256': p07.hashlib.sha256(states['balanced'][0][0].tobytes()).hexdigest()}
                        for a, (k, alpha, states) in arms.items()}}
    p07.write(f'{name}_FIT.json', fit)
    print(f'{name}: policies fixed before opening archived evaluation', flush=True)

    imgs, truth, target = p07.old.read_archived_eval(cfg, ids, torch.from_numpy(data['test'][1]))
    evaluation_x = p07.embed(backbone, imgs)
    actual = {}
    for arm, (_, _, runs) in arms.items():
        actual[arm] = {}
        for path, (heads, norms) in runs.items():
            clean = p07.scores(heads, (x['test'], data['test'][1]), (x['clients'], data['clients'][1]), None)
            before, after = [(evaluation_x @ heads[i].T).argmax(1) for i in (0, -1)]
            def score(pred):
                return p07.old.functional(torch.from_numpy(pred), truth, target)
            actual[arm][path] = {'clean': clean, 'archive': {'immediate': score(before), 'final': score(after)},
                                 'reerror': int(((before == truth.numpy()) & (after != truth.numpy())).sum()),
                                 'extra_max': max(norms)}
    if name in NORMAL:
        assert actual['none'] == actual['svd']
    assert p07.old.sha(entry['path']) == entry['sha256'] and not torch.cuda.is_initialized()
    results = {'fit': fit, 'paths': actual, 'seconds': time.monotonic() - begin}
    p07.write(f'{name}_RESULT.json', results)
    print(f'{name}: complete in {results["seconds"]:.1f}s', flush=True)
    return results


def summary_for(name, result):
    fit, actual = result['fit'], result['paths']
    base = actual['none']
    stages = {'immediate': ('balanced', 'immediate', 0), 'balanced': ('balanced', 'final', -1),
              'client1_weighted': ('client1_weighted', 'final', -1)}
    points = {s: {a: {'archive': paths[p]['archive'][phase], 'clean': paths[p]['clean'][t]['public']['correct']}
                  for a, paths in actual.items()} for s, (p, phase, t) in stages.items()}
    for arm in actual:
        assert actual[arm]['balanced']['archive']['immediate'] == actual[arm]['client1_weighted']['archive']['immediate']
    gates = {arm: {p: p07.compare(paths[p]['clean'], base[p]['clean']) for p in p07.PATHS}
             for arm, paths in actual.items()}
    gains = {}
    for s, row in points.items():
        a, b = row['svd']['archive'], row['none']['archive']
        assert a['n'] == b['n'] == 1440
        gains[s] = {'asr_drop_pp': 100 * (b['target'] - a['target']) / 1440,
                    'original_gain_pp': 100 * (a['original_correct'] - b['original_correct']) / 1440}
    passed = all(v['passed'] for v in gates['svd'].values())
    if name in ATTACK:
        passed = passed and all(gains[p]['asr_drop_pp'] >= 5 and gains[p]['original_gain_pp'] >= 5 for p in p07.PATHS)
    return {'policies': fit['policies'], 'gates': gates, 'counts': points, 'gains': gains, 'passed': passed,
            'seconds': result['seconds']}


def main():
    import scipy
    import torchvision
    for f, digest in read(ROOT / 'FREEZE.json').items():
        lock(ROOT / f, digest)
    with (ROOT / 'STARTED.json').open('x', encoding='utf-8') as f:
        json.dump({'pid': os.getpid(), 'runner_sha256': p07.old.sha(__file__)}, f)
    assert (torch.__version__, torchvision.__version__, np.__version__, scipy.__version__) == ('2.7.1+cu118', '0.22.1+cu118', '1.26.4', '1.15.3')
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(61116)
    cfg = read(ROOT / 'INPUTS.json')
    snap = cfg['snapshot']
    storage = p07.old.check(snap['manifest']).parent
    p07.old.check(snap['seal'])
    p07.old.check(snap['loader'])
    sys.path.insert(0, str(storage))
    import load_confirmed as sealed
    sealed.verify(storage, snap['manifest']['sha256'])
    constructor = sealed.model_class(storage)
    request, reference, normal_checks = verify_pairs(cfg)
    data, plans, extras, ids = p07.select_data(cfg)
    summaries = {}
    for case in CASES:
        result = run_case(case, cfg, constructor, data, plans, extras, ids, request, reference, normal_checks)
        summaries[case] = summary_for(case, result)
        p07.write(f'{case}_SUMMARY.json', summaries[case])
        print(f'{case}: {summaries[case]["gains"]}', flush=True)
    p07.write('SUMMARY.json', {'state': 'complete', 'cases': summaries, 'passed': all(v['passed'] for v in summaries.values())})


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        with (ROOT / 'FAILURE.json').open('x', encoding='utf-8') as f:
            json.dump({'error': type(exc).__name__, 'message': str(exc)}, f)
        raise
