"""Replay the fixed PCA and measure per-image rescue under expanded clean support."""
import os
import sys
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
BASE = Path('D:/BADFU_FC_PCA_MATCHED_CONTROL_20261112')


def bind():
    import hashlib
    import importlib.util
    import json

    def digest(path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()

    def read(path):
        return json.loads(path.read_text(encoding='utf-8'))

    freeze = read(ROOT / 'FREEZE.json')
    publication = read(ROOT / 'PUBLICATION.json')
    assert publication['freeze_sha256'] == digest(ROOT / 'FREEZE.json')
    assert publication['all_raw_blob_bytes_verified']
    for name, expected in freeze['files'].items():
        assert digest(ROOT / name) == expected, name
    for name, expected in freeze['base_files'].items():
        assert digest(BASE / name) == expected, name
    assert ROOT == Path(freeze['root']).resolve()
    sys.path.insert(1, str(BASE))
    from bindings import read, write

    plan = read(BASE / 'PLAN.json')
    spec = importlib.util.spec_from_file_location('frozen_d24', BASE / 'evaluate.py')
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    return SimpleNamespace(plan=plan, tasks=original.bind(plan), read=read, write=write)


def run(bound):
    import numpy as np
    import torch
    from torch.nn.functional import linear

    from bindings import sha
    from probe_reference import tensor_sha
    from route_core import Endpoint, load_native, load_transform, settings

    read, write = bound.read, bound.write
    settings(bound.plan)
    d20 = Path(bound.plan['d20'])
    cfg = read(d20 / 'PROFILE.json')
    original = read(d20 / 'PUBLIC_SPLIT.json')
    panels = {'original': original['test'], **read(BASE / 'HOLDOUT_SPLITS.json')}
    prior = {(r['case'], r['round'], r['split'], r['arm']): r
             for r in read(BASE / 'RESULT.json')['rows']}
    selections = read(d20 / 'SELECTIONS.json')
    assert sha(cfg['raw_data']) == cfg['raw_sha256']
    raw = torch.load(cfg['raw_data'], map_location='cpu', weights_only=True)
    used = set(original['fit'] + original['calibration'] + sum(panels.values(), []))
    rng = np.random.default_rng(2026111227)
    extra = []
    panels.update(C=[], D=[])
    labels = raw['test_y'].tolist()
    for c in range(10):
        ids = [i for i, y in enumerate(labels) if y == c and i not in used]
        shuffled = rng.permutation(ids).tolist()
        extra.extend(shuffled[:32])
        panels['C'].extend(shuffled[32:132])
        panels['D'].extend(shuffled[132:232])
    fresh = extra + panels['C'] + panels['D']
    assert len(extra) == 320 and len(panels['C']) == len(panels['D']) == 1000
    assert len(set(fresh)) == 2320 and not used.intersection(fresh)
    write(ROOT / 'NEW_SPLITS.json', dict(extra_fit=extra, C=panels['C'], D=panels['D']))

    def images(ids):
        for idx in torch.tensor(ids).split(32):
            yield (raw['test_x'][idx].permute(0, 3, 1, 2).contiguous().float().cuda() / 255,
                   raw['test_y'][idx].long().cuda())

    def capture(model, x):
        pred = model(x).argmax(1)
        return model.feature, pred

    def fit_basis(features):
        mean = features.mean(0)
        _, singular, vh = torch.linalg.svd(features - mean, full_matrices=False)
        power = singular.square()
        rank = int(torch.searchsorted(power.cumsum(0), power.sum() * .95)) + 1
        assert 0 < rank < features.shape[1]
        bases = {'pca': vh[:rank].T.contiguous().float().cuda()}
        for i in range(1, 4):
            generator = torch.Generator(device='cpu').manual_seed(2026111200 + i)
            gaussian = torch.randn(features.shape[1], rank, dtype=torch.float64, generator=generator)
            bases[f'random_{i}'] = torch.linalg.qr(gaussian, mode='reduced').Q.float().cuda()
        return mean.float().cuda(), rank, bases

    def heads(pre, post, fitted):
        mean, _, bases = fitted
        delta = post.head.weight - pre.head.weight
        removed = {k: delta - (delta @ v) @ v.T for k, v in bases.items()}
        size = torch.linalg.vector_norm(removed['pca'])
        for key in ('random_1', 'random_2', 'random_3'):
            norm = torch.linalg.vector_norm(removed[key])
            assert norm > 0
            removed[key] *= size / norm
            assert torch.allclose(torch.linalg.vector_norm(removed[key]), size, rtol=1e-5, atol=1e-8)
        return {k: (post.head.weight - v, post.head.bias + v @ mean) for k, v in removed.items()}

    def measure(post, batches, target, small, wide):
        stats = dict(n=0, stable=0, native=0)
        for key in small:
            stats.update({key + '_320': 0, key + '_640': 0, key + '_both': 0})
        for x, z, y, before_x, before_z in batches:
            hx, ax = capture(post, x)
            hz, az = capture(post, z)
            stable = (before_x == y) & (ax == y)
            witness = stable & (before_z == y) & (az == target)
            stats['n'] += len(y)
            stats['stable'] += int(stable.sum())
            stats['native'] += int(witness.sum())
            for key in small:
                a = witness & (linear(hx, *small[key]).argmax(1) == y) & (linear(hz, *small[key]).argmax(1) == y)
                b = witness & (linear(hx, *wide[key]).argmax(1) == y) & (linear(hz, *wide[key]).argmax(1) == y)
                for suffix, mask in (('_320', a), ('_640', b), ('_both', a & b)):
                    stats[key + suffix] += int(mask.sum())
        assert stats['n'] == 900
        return stats

    started = time.monotonic()
    rows, matched = [], 0
    with torch.inference_mode():
        for task in bound.tasks:
            cid = task['case']
            pm, pd = load_native(task['pre'], 'badfu', 'cuda')
            qm, qd = load_native(task['post'], 'badfu', 'cuda')
            pre = Endpoint(pm, 'badfu')
            fit = torch.cat([capture(pre, x)[0] for x, _ in images(original['fit'])]).cpu().double()
            added = torch.cat([capture(pre, x)[0] for x, _ in images(extra)]).cpu().double()
            bases = fit_basis(fit), fit_basis(torch.cat([fit, added]))
            if task['history']:
                check, digest = load_native(task['history'][40], 'badfu', 'cpu')
                assert digest == qd, cid
                del check
            probes = []
            for selection in selections:
                if selection['case'] != cid:
                    continue
                meta = selection['chosen']
                assert sha(meta['payload']) == meta['payload_sha256']
                target = meta['target']
                transform = load_transform(meta['family'], cfg, meta['payload'], 'cuda')
                batches_by_panel = {}
                for name, ids in panels.items():
                    batches = []
                    for x, y in images(ids):
                        keep = y != target
                        if not keep.any():
                            continue
                        x, y = x[keep], y[keep]
                        z = transform(x, torch.full_like(y, target))
                        batches.append((x, z, y, capture(pre, x)[1], capture(pre, z)[1]))
                    batches_by_panel[name] = batches
                probes.append((selection['arm'], target, batches_by_panel))
                del transform
            assert len(probes) == 2
            for epoch in ([40, 10, 20, 30] if task['history'] else [40]):
                model, digest = (qm, qd) if epoch == 40 else load_native(task['history'][epoch], 'badfu', 'cuda')
                post = Endpoint(model, 'badfu')
                small, wide = (heads(pre, post, basis) for basis in bases)
                for arm, target, panel_batches in probes:
                    for name, batches in panel_batches.items():
                        if epoch != 40 and name == 'original':
                            continue
                        stats = measure(post, batches, target, small, wide)
                        rank320, rank640 = (b[1] for b in bases)
                        if (key := (cid, epoch, name, arm)) in prior:
                            old = prior[key]
                            assert (stats['n'], stats['stable'], stats['native'], stats['pca_320'], rank320) == (
                                old['n'], old['stable'], old['native'], old['pca'], old['pca_rank']), key
                            matched += 1
                        rows.append(dict(case=cid, round=epoch, split=name, arm=arm,
                                         rank320=rank320, rank640=rank640, **stats))
                assert tensor_sha(model.state_dict()) == digest
                post.close()
                del post, model
                write(ROOT / 'PROGRESS.json', dict(case=cid, round=epoch, rows=len(rows), d24_matched=matched))
            assert tensor_sha(pm.state_dict()) == pd
            pre.close()
            del pre, pm, qm, probes
            torch.cuda.empty_cache()
    assert matched == len(prior) == 96 and len(rows) == 180
    write(ROOT / 'RESULT.json', dict(rows=rows, seconds=time.monotonic() - started,
                                   d24_matched=matched, training_steps=0, new_probe_searches=0))


if __name__ == '__main__':
    try:
        (ROOT / 'ONCE').open('x').write(str(os.getpid()))
        bound = bind()
        from resource_guard import admit

        observations = admit(bound.plan)
        bound.write(ROOT / 'ADMISSION.json', observations)
        run(bound)
    except Exception:
        import json

        (ROOT / 'FAILURE.json').write_text(json.dumps(dict(traceback=traceback.format_exc())), encoding='utf-8')
        raise SystemExit(1)
