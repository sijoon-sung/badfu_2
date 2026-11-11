"""Read-only functional audit on frozen baseline witnesses; no fitting."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
CAT = Path('D:/TRAJECTORY_CATALOG_20261023')
ROOTS = {'d20': Path('D:/BLIND_ROUTE_DETECTOR_V2_20261110'),
         'n00': Path('D:/FEDUBA_LARGE_BENIGN_VALIDATION_20261110/detector/n00'),
         'n01': Path('D:/FEDUBA_LARGE_BENIGN_VALIDATION_20261110/detector/n01')}


def read(path):
    return json.loads(Path(path).read_bytes())


def write(name, value):
    p = ROOT / name
    t = p.with_suffix('.tmp')
    t.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    t.replace(p)


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def identity(meta):
    return (os.path.normcase(os.path.normpath(meta['path'])), meta['sha256'], meta['payload_key'])


def preflight():
    freeze = read(ROOT / 'FREEZE.json')
    for name, digest in freeze['files'].items():
        assert sha(ROOT / name) == digest, name
    assert read(ROOT / 'PUBLICATION.json')['freeze_sha256'] == sha(ROOT / 'FREEZE.json')
    catalogue = read(ROOT / 'CATALOG_SELECTIONS.json')
    selected = {}
    bound = []
    for name, folder in ROOTS.items():
        for file, digest in freeze['references'][name].items():
            assert sha(folder / file) == digest, (name, file)
        cfg = read(folder / 'PROFILE.json')
        selection_digest = sha(folder / 'SELECTIONS.json')
        result = read(folder / 'RESULT.json')
        verified = read(folder / 'VERIFIED.json')
        assert verified['all_counts_exact'] and verified['primary_sha256'] == sha(folder / 'RESULT.json')
        assert read(folder / 'SELECTION_SEAL.json')['sha256'] == result['selection_sha256'] == selection_digest
        split = read(folder / 'PUBLIC_SPLIT.json')
        assert len(set(split['test'])) == 1000
        assert not (set(split['test']) & (set(split['fit']) | set(split['calibration'])))
        for case in read(folder / 'INPUTS.json')['cases']:
            cid = case['id']
            entry = catalogue[cid]
            key = (entry['case_id'], entry['purpose'])
            if key not in selected:
                command = [sys.executable, str(CAT / 'select_case.py'), key[0], '--purpose', key[1]]
                selected[key] = json.loads(subprocess.check_output(command, encoding='utf-8'))
            for endpoint in ('pre', 'post'):
                evidence = selected[key]['server_inputs'][entry[endpoint]]
                assert identity(evidence) == identity(case[endpoint]), (cid, endpoint)
            chosen, = [v['chosen'] for v in read(folder / 'SELECTIONS.json') if v['case'] == cid and v['arm'] == 'baseline']
            expected, = [v for v in result['results'] if v['case'] == cid and v['arm'] == 'baseline']
            assert chosen['family'] == expected['family'] and chosen['target'] == expected['target']
            assert sha(chosen['payload']) == chosen['payload_sha256'], cid
            bound.append((case, chosen, expected, cfg, split['test']))
    assert len(bound) == len(catalogue) == 12
    write('PREFLIGHT.json', dict(state='passed', bindings=catalogue, cases=[v[0]['id'] for v in bound]))
    return bound


def main():
    bound = preflight()
    if '--preflight' in sys.argv:
        return
    (ROOT / 'ONCE').open('x').write(str(os.getpid()))
    from resource_guard import admit
    admission = dict(bound[0][3], admission=dict(memory_gib=6, disk_gib=2, gpu_free_mib=4096, gpu_util_max=10, wait_seconds=120))
    obs = admit(admission)
    write('ADMISSION.json', [dict(v, competitors=[dict(pid=p['ProcessId'], name=p['Name']) for p in v['competitors']]) for v in obs])
    import torch
    from probe_reference import tensor_sha
    from route_core import Endpoint, four_routes, load_native, load_transform, settings
    settings(admission)
    cfg = bound[0][3]
    assert sha(cfg['raw_data']) == cfg['raw_sha256']
    raw = torch.load(cfg['raw_data'], map_location='cpu', weights_only=True)
    rows = []
    started = time.monotonic()
    with torch.inference_mode():
        for case, chosen, expected, cfg, test in bound:
            loaded = [load_native(case[k], case['architecture'], 'cuda') for k in ('pre', 'post')]
            pre, post = [Endpoint(m, case['architecture']) for m, _ in loaded]
            t = chosen['target']
            transform = load_transform(chosen['family'], cfg, chosen['payload'], 'cuda')
            classes = {c: [0] * 6 for c in range(10) if c != t}
            matrix = [[0] * 3 for _ in range(3)]
            for ids in torch.tensor(test).split(32):
                y = raw['test_y'][ids].long().cuda()
                x = raw['test_x'][ids].permute(0, 3, 1, 2).contiguous().float().cuda() / 255
                keep = y != t
                y, x = y[keep], x[keep]
                if not len(y):
                    continue
                p0, p01, p10, p1 = [z.argmax(1) for z in four_routes(pre, post, x)]
                z0, z01, z10, z1 = [z.argmax(1) for z in four_routes(pre, post, transform(x, torch.full_like(y, t)))]
                stable = (p0 == y) & (p1 == y)
                w = stable & (z0 == y) & (z1 == t)
                b = (z01 == y) & (z10 == t)
                c = (p01 == y) & (p10 == y)
                for label, counters in classes.items():
                    take = y == label
                    for i, mask in enumerate((take, take & stable, take & w, take & w & b, take & w & c, take & w & b & c)):
                        counters[i] += int(mask.sum())
                for i, mask0 in enumerate((z01 == y, z01 == t, (z01 != y) & (z01 != t))):
                    for j, mask1 in enumerate((z10 == y, z10 == t, (z10 != y) & (z10 != t))):
                        matrix[i][j] += int((w & mask0 & mask1).sum())
            n, stable, w, b, c, bc = map(sum, zip(*classes.values()))
            assert (n, w, stable) == (expected['n'], expected['witness'], expected['stable']), case['id']
            assert all(classes[r['source']][::2][:2] == [r['n'], r['witness']] for r in expected['source_counts']), case['id']
            assert sum(map(sum, matrix)) == w and matrix[0][1] == b
            assert 0 <= bc <= min(b, c) <= w <= stable <= n
            for model, digest in loaded:
                assert tensor_sha(model.state_dict()) == digest
            for k in ('pre', 'post'):
                assert sha(case[k]['path']) == case[k]['sha256']
            rows.append(dict(case=case['id'], n=n, stable=stable, witness=w, body=b, clean_compatible=c,
                             strict_body=bc, matrix=matrix, source_counts=classes))
            print(case['id'], n, stable, w, b, c, bc, flush=True)
            pre.close(); post.close()
            del pre, post, transform, loaded, model
            torch.cuda.empty_cache()
    write('RESULT.json', dict(state='complete', columns=['n','stable','witness','body','clean_compatible','strict_body'],
                              matrix_axis=['source_y','target_t','other'], native_counts_exact=True,
                              all_model_hashes_preserved=True, training_steps=0, selections_changed=0,
                              torch=torch.__version__, cuda=torch.version.cuda, seconds=time.monotonic()-started, rows=rows))


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        # Preserve traceback without exposing raw unrelated process arguments.
        lines = traceback.format_exc().splitlines()
        if 'Admission failed' in lines[-1]:
            lines[-1] = 'Admission failed; GPU inference was not started.'
        write('FAILURE.json', dict(traceback='\n'.join(lines)))
        raise SystemExit(1)
