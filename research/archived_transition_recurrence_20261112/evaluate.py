"""Audit repeated condition-specific prediction on sealed original FL trajectories."""
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
D24 = Path('D:/BADFU_FC_PCA_MATCHED_CONTROL_20261112')
D27 = Path('D:/PCA_SUPPORT_EXPANSION_20261112/recovery')
WINDOWS = ((10, 11), (20, 21), (30, 31))


def prepare():
    import hashlib
    import importlib.util
    import json

    def sha(path):
        with Path(path).open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()

    freeze = json.loads((ROOT / 'FREEZE.json').read_bytes())
    publication = json.loads((ROOT / 'PUBLICATION.json').read_bytes())
    assert ROOT == Path(freeze['root']).resolve()
    assert publication['all_raw_blob_bytes_verified']
    assert publication['freeze_sha256'] == sha(ROOT / 'FREEZE.json')
    for name, expected in freeze['files'].items():
        assert sha(ROOT / name) == expected, name
    for name, expected in freeze['dependencies'].items():
        assert sha(name) == expected, name
    sys.path.insert(1, str(D24))
    from bindings import read, select

    spec = importlib.util.spec_from_file_location('frozen_d24', D24 / 'evaluate.py')
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    plan = read(D24 / 'PLAN.json')
    tasks = original.bind(plan)
    mappings = read(ROOT / 'PRE_HISTORIES.json')
    history_cache = {}
    for task in tasks:
        cfg = mappings[task['case']]
        cache_key = cfg['case'], cfg['key']
        if cache_key not in history_cache:
            entry = select(cfg['case'], 'global_history')['server_inputs'][cfg['key']]
            manifest = Path(entry['history_manifest'])
            assert sha(manifest) == cfg['manifest_sha256']
            stored = read(manifest)
            rows = stored if isinstance(stored, list) else stored['rounds']
            assert [row['round'] for row in rows] == list(range(1, 41))
            bound = {}
            for epoch in [n for pair in WINDOWS for n in pair] + [40]:
                item = rows[epoch - 1]
                path = (manifest.parent / item['path']).resolve()
                assert path.is_relative_to(manifest.parent.resolve())
                assert sha(path) == item['sha256']
                bound[epoch] = dict(path=str(path), sha256=item['sha256'],
                                    payload_key=entry['payload_key'])
            history_cache[cache_key] = entry, bound
        entry, bound = history_cache[cache_key]
        assert task['pre']['sha256'] == entry['sha256'], task['case']
        task['pre_history'] = bound
    assert len(history_cache) == 3
    assert plan['admission']['memory_gib'] == 6
    plan['admission']['memory_gib'] = 4
    return plan, tasks


def audit(plan, tasks):
    import torch
    from torch.nn.functional import linear

    from bindings import read, sha, write
    from probe_reference import tensor_sha
    from route_core import Endpoint, load_native, load_transform, settings

    settings(plan)
    d20 = Path(plan['d20'])
    cfg = read(d20 / 'PROFILE.json')
    split = read(d20 / 'PUBLIC_SPLIT.json')
    holdout = read(D27 / 'NEW_SPLITS.json')
    panels = {'original': split['test'], **read(D24 / 'HOLDOUT_SPLITS.json'),
              'C': holdout['C'], 'D': holdout['D']}
    assert len(set(sum(panels.values(), []))) == 5000
    assert not set(sum(panels.values(), [])).intersection(split['fit'] + split['calibration'])
    assert sha(cfg['raw_data']) == cfg['raw_sha256']
    raw = torch.load(cfg['raw_data'], map_location='cpu', weights_only=True)
    probes = read(d20 / 'SELECTIONS.json')
    prior = {(r['case'], r['round'], r['split'], r['arm']): r
             for r in read(D27 / 'RESULT.json')['rows']}

    def batches(indices):
        for idx in torch.tensor(indices).split(32):
            yield (raw['test_x'][idx].permute(0, 3, 1, 2).contiguous().float().cuda() / 255,
                   raw['test_y'][idx].long().cuda())

    def captures(model, x):
        labels = model(x).argmax(1)
        return model.feature, labels

    def build_inputs(task, pre):
        cid = task['case']
        permitted = {cid}
        if cid in ('c03', 'c05'):
            permitted = {'c03', 'c05'}
        payloads = {}
        for row in probes:
            if row['case'] not in permitted:
                continue
            chosen = row['chosen']
            target = chosen['target']
            assert sha(chosen['payload']) == chosen['payload_sha256']
            transform = load_transform(chosen['family'], cfg, chosen['payload'], 'cuda')
            for split_name, ids in panels.items():
                rows = []
                for x, y in batches(ids):
                    keep = y != target
                    if not keep.any():
                        continue
                    x, y = x[keep], y[keep]
                    z = transform(x, torch.full_like(y, target))
                    native_pre = (pre(x).argmax(1) == y) & (pre(z).argmax(1) == y)
                    rows.append((x, z, y, native_pre))
                payloads[row['case'], row['arm'], split_name] = target, rows
        assert len(payloads) == len(permitted) * 10
        return payloads

    def history_masks(task, payloads):
        result = {}
        for epoch in [n for pair in WINDOWS for n in pair]:
            model, digest = load_native(task['pre_history'][epoch], 'badfu', 'cuda')
            endpoint = Endpoint(model, 'badfu', capture=False)
            for key, (target, rows) in payloads.items():
                result[key, epoch] = [
                    (endpoint(x).argmax(1) == y) & (endpoint(z).argmax(1) == target)
                    for x, z, y, _ in rows
                ]
            assert tensor_sha(model.state_dict()) == digest
            del endpoint, model
        return result

    def pca_axes(pre):
        fit = torch.cat([captures(pre, x)[0] for x, _ in batches(split['fit'])]).cpu().double()
        mean = fit.mean(0)
        _, singular, vh = torch.linalg.svd(fit - mean, full_matrices=False)
        power = singular.square()
        rank = int(torch.searchsorted(power.cumsum(0), power.sum() * .95)) + 1
        return mean.float().cuda(), vh[:rank].T.contiguous().float().cuda(), rank

    def observe(pre, post, basis, payload, masks):
        target, rows = payload
        mean, axes, _ = basis
        delta = post.head.weight - pre.head.weight
        residual = delta - (delta @ axes) @ axes.T
        w = post.head.weight - residual
        b = post.head.bias + residual @ mean
        names = ('native', 'pca', 'recur', 'recur_pca', 'early', 'late_20', 'late_30')
        tallies = {name: torch.zeros(10, dtype=torch.int64, device='cuda') for name in names}
        size = 0
        for i, (x, z, y, before) in enumerate(rows):
            hx, pred_x = captures(post, x)
            hz, pred_z = captures(post, z)
            witness = before & (pred_x == y) & (pred_z == target)
            r10, r20, r30 = (masks[lo][i] & masks[hi][i] for lo, hi in WINDOWS)
            pca = (linear(hx, w, b).argmax(1) == y) & (linear(hz, w, b).argmax(1) == y)
            recur = r20 | r30
            for name, mask in zip(names, (witness, pca, recur, recur & pca, r10, r20, r30)):
                tallies[name] += torch.bincount(y[witness & mask], minlength=10)
            size += len(y)
        assert size == 900
        return {k: v.tolist() for k, v in tallies.items()}

    started = time.monotonic()
    output, matches = [], 0
    with torch.inference_mode():
        for task in tasks:
            cid = task['case']
            pm, pd = load_native(task['pre'], 'badfu', 'cuda')
            last, last_digest = load_native(task['pre_history'][40], 'badfu', 'cpu')
            assert pd == last_digest, cid
            del last
            pre = Endpoint(pm, 'badfu')
            basis = pca_axes(pre)
            payloads = build_inputs(task, pre)
            archived = history_masks(task, payloads)
            for epoch in ([40, 10, 20, 30] if task['history'] else [40]):
                binding = task['post'] if epoch == 40 else task['history'][epoch]
                model, digest = load_native(binding, 'badfu', 'cuda')
                if epoch == 40 and task['history']:
                    stored, stored_digest = load_native(task['history'][40], 'badfu', 'cpu')
                    assert digest == stored_digest, cid
                    del stored
                post = Endpoint(model, 'badfu')
                for key, payload in payloads.items():
                    owner, arm, panel = key
                    if epoch != 40 and panel == 'original':
                        continue
                    counts = observe(pre, post, basis, payload, {n: archived[key, n] for lo, hi in WINDOWS for n in (lo, hi)})
                    if owner == cid:
                        baseline = prior[cid, epoch, panel, arm]
                        assert (sum(counts['native']), sum(counts['pca']), basis[-1]) == (
                            baseline['native'], baseline['pca_320'], baseline['rank320']), (cid, epoch, panel, arm)
                        matches += 1
                    output.append(dict(case=cid, probe_owner=owner, arm=arm, round=epoch,
                                       split=panel, classes=counts))
                assert tensor_sha(model.state_dict()) == digest
                post.close()
                del post, model
                write(ROOT / 'PROGRESS.json', dict(case=cid, round=epoch, rows=len(output), prior_matches=matches))
            assert tensor_sha(pm.state_dict()) == pd
            pre.close()
            del pre, pm, payloads, archived
            torch.cuda.empty_cache()
    assert matches == len(prior) == 180 and len(output) == 248
    write(ROOT / 'RESULT.json', dict(rows=output, d27_rows_matched=matches, seconds=time.monotonic() - started,
                                   training_steps=0, new_probe_searches=0))


if __name__ == '__main__':
    try:
        (ROOT / 'ONCE').open('x').write(str(os.getpid()))
        plan, tasks = prepare()
        from bindings import write
        from resource_guard import admit

        observations = admit(plan)
        write(ROOT / 'ADMISSION.json', observations)
        audit(plan, tasks)
    except Exception:
        import json

        (ROOT / 'FAILURE.json').write_text(json.dumps(dict(traceback=traceback.format_exc())), encoding='utf-8')
        raise SystemExit(1)
