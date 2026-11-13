"""Compare already sealed defensive probes at several actual FU checkpoints."""
import argparse
import json
import os
import traceback
from pathlib import Path
from bindings import ROOT, read, write, sha, select, require_publication


def main(stage):
    cfg = require_publication()
    (ROOT / ('PANEL_' + stage + '_ONCE')).open('x').write(str(os.getpid()))
    from resource_guard import admit
    admission = admit(cfg)
    write(ROOT / ('PANEL_' + stage + '_ADMISSION.json'), [dict(x, competitors=[dict(pid=p['ProcessId'], name=p['Name']) for p in x['competitors']]) for x in admission])
    import torch
    from route_core import load_native, load_transform, settings
    from probe_reference import tensor_sha
    settings(cfg)
    design = read(ROOT / 'DESIGN.json')
    binding = read(ROOT / ('PANEL_' + stage + '_BINDING.json'))
    declared = select(binding['case_id'], 'diagnostic')['server_inputs']
    assert declared == binding['server_inputs']
    pcfg = read(Path(design['probes'][0]['root']) / 'PROFILE.json')
    assert sha(pcfg['raw_data']) == pcfg['raw_sha256']
    raw = torch.load(pcfg['raw_data'], map_location='cpu', weights_only=True)
    test = read(Path(design['probes'][0]['root']) / 'PUBLIC_SPLIT.json')['test']
    with torch.inference_mode():
        pre, pre_digest = load_native(declared['pre'], 'feduba', 'cuda')
        batches = []
        for ids in torch.tensor(test).split(32):
            y = raw['test_y'][ids].long().cuda()
            x = raw['test_x'][ids].permute(0, 3, 1, 2).contiguous().float().cuda() / 255
            batches.append((ids, x, y))
        y_all = torch.cat([b[2] for b in batches])
        def pred(model, x): return model(((x - .5) / .5).contiguous()).argmax(1)
        dark_ids = set()
        ordered = raw['test_x'][test].reshape(len(test), -1).sum(1, dtype=torch.int64).tolist()
        y_cpu = y_all.tolist()
        for c in range(10):
            pos = [i for i, y in enumerate(y_cpu) if y == c]
            assert len(pos) == 100
            dark_ids.update(test[i] for i in sorted(pos, key=lambda i: (ordered[i], test[i]))[:40])
        dark_mask = torch.tensor([i in dark_ids for i in test], device='cuda')
        probes = []
        for ref in design['probes']:
            folder = Path(ref['root'])
            for n, d in ref['hashes'].items(): assert sha(folder / n) == d, (ref['id'], n)
            assert read(folder / 'PUBLIC_SPLIT.json')['test'] == test
            cfg_probe = read(folder / 'PROFILE.json')
            assert cfg_probe['raw_sha256'] == pcfg['raw_sha256']
            base = read(folder / 'RESULT.json')
            seal = read(folder / 'SELECTION_SEAL.json')
            assert sha(folder / 'SELECTIONS.json') == base['selection_sha256'] == seal['sha256']
            for arm in ('baseline', 'route'):
                chosen, = [s['chosen'] for s in read(folder / 'SELECTIONS.json') if s['case'] == ref['id'] and s['arm'] == arm]
                expected, = [s for s in base['results'] if s['case'] == ref['id'] and s['arm'] == arm]
                assert sha(chosen['payload']) == chosen['payload_sha256']
                t = chosen['target']; transform = load_transform(chosen['family'], cfg_probe, chosen['payload'], 'cuda')
                items = []
                for ids, x, y in batches:
                    mask = y != t
                    if not mask.any(): continue
                    y, x = y[mask], x[mask]
                    z = transform(x, torch.full_like(y, t))
                    items.append((ids[mask.cpu()], x, z, y, pred(pre, x), pred(pre, z)))
                probes.append((ref['id'], arm, t, expected, items))
                del transform
        rows = []; stable_endpoint_checks = 0
        for track in binding['tracks']:
            branch = track['opaque']; prior = {}
            for r in track['rounds']:
                key = f'{branch}_r{r:02d}'
                post, digest = load_native(declared[key], 'feduba', 'cuda')
                p1s = [pred(post, b[1]) for b in batches]
                clean = torch.cat(p1s) == y_all
                clean_by_class = [int(clean[y_all == c].sum()) for c in range(10)]
                clean_row = dict(n=len(test), correct=int(clean.sum()), by_class=clean_by_class,
                                 dark_n=int(dark_mask.sum()), dark_correct=int((clean & dark_mask).sum()),
                                 other_n=int((~dark_mask).sum()), other_correct=int((clean & ~dark_mask).sum()))
                probe_rows = []
                for pid, arm, t, expected, items in probes:
                    hits = set(); n = stable_count = 0; counts = [0] * 10
                    for ids, x, z, y, p0, z0 in items:
                        ids = ids.tolist()
                        stable = (p0 == y) & (pred(post, x) == y)
                        w = stable & (z0 == y) & (pred(post, z) == t)
                        hits.update(i for i, on in zip(ids, w.tolist()) if on)
                        for c, on in zip(y.tolist(), w.tolist()): counts[c] += int(on)
                        n += len(ids); stable_count += int(stable.sum())
                    assert n == 900 and len(hits) == sum(counts)
                    if r == 20 and pid == track.get('source_case'):
                        assert (n, len(hits), stable_count) == (expected['n'], expected['witness'], expected['stable'])
                        assert all(counts[e['source']] == e['witness'] for e in expected['source_counts'])
                        stable_endpoint_checks += 1
                    old = prior.get((pid, arm)); prior[pid, arm] = hits
                    probe_rows.append(dict(probe=pid, arm=arm, target=t, n=n, stable=stable_count, witness=len(hits),
                                           witness_by_class=counts, dark_witness=len(hits & dark_ids),
                                           kept=None if old is None else len(hits & old),
                                           gained=None if old is None else len(hits - old), lost=None if old is None else len(old - hits)))
                assert tensor_sha(post.state_dict()) == digest
                rows.append(dict(track=branch, round=r, post_sha256=declared[key]['sha256'], clean=clean_row, probes=probe_rows))
                write(ROOT / ('PANEL_' + stage + '_PROGRESS.json'), dict(track=branch, round=r, rows=len(rows)))
                del post
                torch.cuda.empty_cache()
        assert tensor_sha(pre.state_dict()) == pre_digest
        assert stable_endpoint_checks == (10 if stage == 'stored' else 0)
    write(ROOT / ('PANEL_' + stage + '_RESULT.json'), dict(state='passed', rows=rows, endpoint_checks=stable_endpoint_checks,
          training_steps=0, selection_changes=0, interpretation='retrospective_frozen_terminal_probe_panel'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('stage', choices=['stored', 'new']); a = p.parse_args()
    try: main(a.stage)
    except BaseException:
        trace = traceback.format_exc().splitlines()
        if 'Admission failed' in trace[-1]: trace[-1] = 'Resource admission failed before CUDA inference.'
        write(ROOT / ('PANEL_' + a.stage + '_FAILURE.json'), dict(traceback='\n'.join(trace)))
        raise SystemExit(1)
