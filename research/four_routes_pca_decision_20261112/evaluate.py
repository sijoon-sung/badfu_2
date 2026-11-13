"""Read-only replay of sealed probes with feature and head PCA interventions."""
import os
from pathlib import Path
import time
import traceback

from bindings import ROOT, read, select, sha, write


def identity(meta):
    return os.path.normcase(os.path.normpath(meta['path'])), meta['sha256'], meta['payload_key']


def preflight(plan):
    freeze = read(ROOT/'FREEZE.json')
    receipt = read(ROOT/'PUBLICATION.json')
    assert receipt['all_raw_blob_bytes_verified'] and receipt['freeze_sha256'] == sha(ROOT/'FREEZE.json')
    for name, digest in freeze['files'].items():
        assert sha(ROOT/name) == digest, name
    for name, digest in plan['reference_files'].items():
        assert sha(name) == digest, name
    tasks = []
    for path in plan['panel_bindings']:
        b = read(path)
        actual = select(b['case_id'], 'diagnostic')['server_inputs']
        assert actual == b['server_inputs']
        for track in b['tracks']:
            for r in track['rounds']:
                t = track['opaque']
                tasks.append(dict(group='feduba', track=t, round=r, pre=actual['pre'], post=actual[f'{t}_r{r:02d}']))
    assert len(tasks) == 42
    source = read(Path(plan['d20'])/'INPUTS.json')
    choices = read(plan['badfu_catalogue_selection'])
    selected = {}
    for b in source['cases']:
        t = b['id']
        if t not in choices:
            continue
        c = choices[t]
        key = (c['case_id'], c['purpose'])
        if key not in selected:
            selected[key] = select(*key)['server_inputs']
        for endpoint in ('pre', 'post'):
            assert identity(b[endpoint]) == identity(selected[key][c[endpoint]])
        tasks.append(dict(group='badfu', track=t, round=None, pre=b['pre'], post=b['post']))
    assert len(tasks) == 48
    order = {'p00':0,'p01':0,'p02':0,'p03':1,'p04':1,'u00':1,'u01':1,'u02':1,
             'c00':2,'c01':2,'c02':2,'c03':2,'c04':3,'c05':3}
    return sorted(tasks, key=lambda t: order[t['track']])


def probe_specs(root, ids):
    root = Path(root)
    cfg = read(root/'PROFILE.json')
    selected = read(root/'SELECTIONS.json')
    assert sha(root/'SELECTIONS.json') == read(root/'SELECTION_SEAL.json')['sha256']
    return [(s['case'], s['arm'], s['chosen'], cfg) for s in selected if s['case'] in ids]


def run(plan, tasks):
    import torch
    from torch.nn import functional as F
    from probe_reference import tensor_sha
    from route_core import Endpoint, load_native, load_transform, settings

    settings(plan)
    cfg = read(Path(plan['d20'])/'PROFILE.json')
    assert sha(cfg['raw_data']) == cfg['raw_sha256']
    raw = torch.load(cfg['raw_data'], map_location='cpu', weights_only=True)
    split = read(Path(plan['d20'])/'PUBLIC_SPLIT.json')
    assert len(set(split['fit'])) == 320 and len(set(split['test'])) == 1000
    assert not set(split['fit']) & set(split['test'])
    for folder in plan['feduba_probe_roots']:
        assert read(Path(folder)/'PUBLIC_SPLIT.json') == split
    results = {(r['case'], r['arm']): r for r in read(Path(plan['d20'])/'RESULT.json')['results']}
    prior = {}
    for path in plan['panel_results']:
        for row in read(path)['rows']:
            prior[row['track'],row['round']] = {(q['probe'],q['arm']):q for q in row['probes']}

    def images(ids):
        for part in torch.tensor(ids).split(32):
            x = raw['test_x'][part].permute(0,3,1,2).contiguous().float().cuda()/255
            y = raw['test_y'][part].long().cuda()
            yield x, y

    def cached_probe(spec):
        _, _, meta, conf = spec
        assert sha(meta['payload']) == meta['payload_sha256']
        transform = load_transform(meta['family'], conf, meta['payload'], 'cuda')
        t = meta['target']
        batches = []
        for x,y in images(split['test']):
            keep = y != t
            if keep.any():
                x,y = x[keep],y[keep]
                batches.append((x, transform(x, torch.full_like(y,t)), y))
        return t, batches

    def feature(endpoint, x):
        z = endpoint(x)
        assert endpoint.feature.ndim == 2
        return endpoint.feature, z.argmax(1)

    def logits(head, h):
        return F.linear(h, head.weight, head.bias).argmax(1)

    def basis(rows):
        rows = rows.cpu().double()
        center = rows.mean(0)
        _, s, vh = torch.linalg.svd(rows-center, full_matrices=False)
        energy = s.square()
        assert energy.sum() > 0
        rank = int(torch.searchsorted(energy.cumsum(0), energy.sum()*.95)) + 1
        axes = vh[:rank].T.contiguous().float().cuda()
        assert torch.isfinite(axes).all()
        return center.float().cuda(), axes, rank

    def project(x, axes):
        return (x@axes)@axes.T

    names = ('native','four_routes','feature_pca','feature_random','fc_pca','feature_pca_null_alone',
             'stable','feature_pca_clean','feature_random_clean','fc_pca_clean')
    normal_probes = {'c07','n00','n01'}
    specs = []
    for folder, ids in plan['feduba_probe_roots'].items():
        specs += probe_specs(folder, ids)
    assert len(specs) == 10
    all_rows = []
    started = time.monotonic()
    with torch.inference_mode():
        shared = [(s, cached_probe(s)) for s in specs]
        fit = [x for x,_ in images(split['fit'])]
        for i, task in enumerate(tasks, 1):
            group, track, round_number = task['group'], task['track'], task['round']
            pm, pd = load_native(task['pre'], group, 'cuda')
            qm, qd = load_native(task['post'], group, 'cuda')
            pre, post = Endpoint(pm,group), Endpoint(qm,group)
            h0 = torch.cat([feature(pre,x)[0] for x in fit])
            h1 = torch.cat([feature(post,x)[0] for x in fit])
            center, axes, rank = basis(h1-h0)
            fmean, faxes, fc_rank = basis(h0)
            generator = torch.Generator(device='cpu').manual_seed(2026111204)
            random_matrix = torch.randn(h0.shape[1], rank, dtype=torch.float64, generator=generator)
            random_axes = torch.linalg.qr(random_matrix, mode='reduced').Q.float().cuda()
            delta_w = post.head.weight-pre.head.weight
            removed_w = delta_w-project(delta_w,faxes)
            fc_weight = post.head.weight-removed_w
            fc_bias = post.head.bias+removed_w@fmean
            assert torch.isfinite(fc_weight).all() and torch.isfinite(fc_bias).all()
            selected = shared if group == 'feduba' else [(s,cached_probe(s)) for s in probe_specs(plan['d20'], {track})]
            probe_rows = []
            for spec, (target,batches) in selected:
                probe,arm = spec[:2]
                sums = dict.fromkeys(names,0)
                by_class = [0]*10
                n = 0
                for x,z,y in batches:
                    x0,a0 = feature(pre,x); x1,a1 = feature(post,x)
                    z0,b0 = feature(pre,z); z1,b1 = feature(post,z)
                    stable = (a0==y) & (a1==y)
                    w = stable & (b0==y) & (b1==target)
                    four = w & (logits(post.head,x0)==y) & (logits(pre.head,x1)==y) & (logits(post.head,z0)==y) & (logits(pre.head,z1)==target)
                    def both(h, value):
                        return (logits(pre.head,h)==value) & (logits(post.head,h)==value)
                    dx,dz = x1-x0-center, z1-z0-center
                    px,pz = project(dx,axes),project(dz,axes)
                    p_clean = both(x0+center+px,y)
                    p_revert = four & p_clean & both(z0+center+pz,y)
                    r_clean = both(x0+center+project(dx,random_axes),y)
                    r_revert = four & r_clean & both(z0+center+project(dz,random_axes),y)
                    fc_clean = F.linear(x1,fc_weight,fc_bias).argmax(1)==y
                    fc_revert = w & fc_clean & (F.linear(z1,fc_weight,fc_bias).argmax(1)==y)
                    null_only = p_revert & both(z1-pz,target)
                    values = (w,four,p_revert,r_revert,fc_revert,null_only,stable,p_clean,r_clean,fc_clean)
                    for k,value in zip(names,values):sums[k]+=int(value.sum())
                    hits = torch.bincount(y[w],minlength=10).tolist()
                    by_class = [a+b for a,b in zip(by_class,hits)]
                    n += len(y)
                expected = prior[track,round_number][probe,arm] if group=='feduba' else results[track,arm]
                assert (n,sums['stable'],sums['native'])==(expected['n'],expected['stable'],expected['witness']), (track,round_number,probe,arm)
                ref_classes = expected.get('witness_by_class')
                if ref_classes is None:
                    ref_classes = [0]*10
                    for row in expected['source_counts']:ref_classes[row['source']]=row['witness']
                assert by_class==ref_classes
                assert sums['feature_pca']<=sums['four_routes']<=sums['native']
                probe_rows.append(dict(probe=probe,arm=arm,n=n,primary_panel=group=='badfu' or probe in normal_probes,**sums))
            assert tensor_sha(pm.state_dict())==pd and tensor_sha(qm.state_dict())==qd
            all_rows.append(dict(group=group,track=track,round=round_number,pca_rank=rank,fc_rank=fc_rank,probes=probe_rows))
            if i==18:
                assert all(t['track'] in ('p00','p01','p02') for t in all_rows)
                maxima={k:max(p[k] for t in all_rows for p in t['probes'] if p['primary_panel']) for k in names[:5]}
                write(ROOT/'NORMAL_THRESHOLDS.json',dict(strictly_greater_than=maxima,n=900,calibration_rows=18))
            if i==46:
                assert {x['track'] for x in all_rows if x['group']=='badfu'} == {'c00','c01','c02','c03'}
                write(ROOT/'BADFU_NORMAL_COUNTS.json', [x for x in all_rows if x['group']=='badfu'])
            write(ROOT/'PROGRESS.json',dict(completed=i,total=len(tasks),track=track,round=round_number))
            pre.close(); post.close()
            del pre,post,pm,qm,selected
            torch.cuda.empty_cache()
    write(ROOT/'RESULT.json',dict(state='complete',rows=all_rows,seconds=time.monotonic()-started,
          native_counts_exact=True,model_tensor_states_unchanged=True,new_training_steps=0,new_probe_searches=0))


if __name__=='__main__':
    try:
        (ROOT/'ONCE').open('x').write(str(os.getpid()))
        plan=read(ROOT/'PLAN.json');tasks=preflight(plan)
        write(ROOT/'PREFLIGHT.json',dict(state='passed',approved_case_snapshots=len(tasks)))
        from resource_guard import admit
        observations=admit(plan)
        write(ROOT/'ADMISSION.json',[dict(x,competitors=[dict(pid=p['ProcessId'],name=p['Name']) for p in x['competitors']]) for x in observations])
        run(plan,tasks)
    except BaseException:
        lines=traceback.format_exc().splitlines()
        if 'Admission failed' in lines[-1]:lines[-1]='Resource admission failed before model inference.'
        write(ROOT/'FAILURE.json',dict(traceback='\n'.join(lines)))
        raise SystemExit(1)
