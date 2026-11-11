"""Bind completed history and sample legitimate requests before any new CUDA work."""
import math
import pickle
import shutil
from pathlib import Path
import traceback

from bindings import ROOT, FOUNDATION, CAT, append_case, checked, make_guard, read, select, sha, write

HISTORY = 'feduba.public_fixed10.cifar10.s42.full20.history.diagnostic.20261110'
D21 = Path('D:/FEDUBA_LARGE_BENIGN_VALIDATION_20261110')
CASE_PREFIX = 'feduba.public_fixed10.cifar10.s42.large_normal_rounds.20261111.'


def seal_panel(stage, pre, tracks, evidence):
    inputs = {'pre': pre}
    summaries = []
    for opaque, source_case, rounds in tracks:
        assert opaque.isalnum()
        summaries.append(dict(opaque=opaque, source_case=source_case, rounds=list(rounds)))
        for r, meta in rounds.items():
            key = f'{opaque}_r{r:02d}'
            assert key not in inputs
            inputs[key] = meta
    files = {k: dict(path=v['path'], sha256=v['sha256'], bytes=v['bytes']) for k, v in inputs.items()}
    for i, p in enumerate(evidence):
        files['evidence'+str(i)] = dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size)
    case_id = CASE_PREFIX + stage
    guard = make_guard('d22_'+stage, case_id, files)
    entry = dict(id=case_id, family='feduba', source_root=str(ROOT), post_type='multi_round_diagnostic',
                 allowed_purposes=['diagnostic'], server_inputs=inputs, checkpoint_guard=guard,
                 provenance='Hash-bound actual FedEraser round endpoints for D22 fixed probe panel, no default change.')
    append_case(entry, 'd22_'+stage)
    chosen = select(case_id, 'diagnostic')
    assert chosen['server_inputs'] == inputs
    write(ROOT / ('PANEL_'+stage+'_BINDING.json'), dict(case_id=case_id, server_inputs=inputs, tracks=summaries))


def prepare_stored():
    (ROOT/'PREPARE_ONCE').open('x').write('metadata only\n')
    source = read(ROOT/'SOURCE_FREEZE.json')
    assert read(ROOT/'SOURCE_PUBLICATION.json')['all_raw_blob_bytes_verified']
    assert read(ROOT/'SOURCE_PUBLICATION.json')['freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    for n,d in source['files'].items():assert sha(ROOT/n)==d,n
    design = read(ROOT/'DESIGN.json')
    (ROOT/'CATALOG_BEFORE.json').write_bytes((CAT/'catalog.json').read_bytes())
    chosen = select(HISTORY,'client_history')
    assert sha(D21/'HISTORY_BINDING.json') == design['history_binding_sha256']
    shutil.copyfile(D21/'HISTORY_BINDING.json', ROOT/'HISTORY_BINDING.json')
    hb=read(ROOT/'HISTORY_BINDING.json'); pre=hb['pre']
    assert len(hb['history']['rounds'])==20 and pre['sha256']==chosen['server_inputs']['pre']['sha256']
    assert hb['case_id']==HISTORY
    evidence = []; tracks = []
    for t in design['stored']:
        root=Path(t['root']); branch=t['branch']; mp=root/'fu'/branch/'MANIFEST.json'; vp=root/('FU_'+branch+'_VERIFIED.json')
        assert sha(mp)==t['manifest_sha256'] and sha(vp)==t['audit_sha256']
        result=read(vp); manifest=read(mp)
        assert result['state']=='passed' and len(manifest['rounds'])==20
        idx=result.get('file_hashes',result.get('history_hashes')); snapshots={}
        end=select(t['case_id'],'diagnostic')['server_inputs']
        assert end['pre']['sha256']==pre['sha256']
        for r in design['stored_rounds']:
            row=manifest['rounds'][r-1]; assert row['round']==r
            m=row['after']; assert idx[m['path']]==m['sha256'],(t['opaque'],r)
            path=(root/m['path']).resolve(); assert path.is_relative_to(root.resolve())
            meta=dict(m,path=str(path),payload_key=None); checked(meta); snapshots[r]=meta
        assert snapshots[20]['sha256']==end['post']['sha256']
        tracks.append((t['opaque'],t['source_case'],snapshots)); evidence.extend([mp,vp])
    seal_panel('stored',pre,tracks,evidence)
    prepare_requests(design)
    names=list(source['files'])+['SOURCE_FREEZE.json','DESIGN.json','PROFILE.json','PRIVATE_REQUESTS.json','HISTORY_BINDING.json','PANEL_stored_BINDING.json']
    write(ROOT/'RUN_FREEZE.json',dict(files={n:sha(ROOT/n) for n in sorted(set(names))}, GPU_computation_started=False))
    write(ROOT/'PREPARED.json',dict(state='prepared',stored_tracks=len(tracks),stored_rounds=design['stored_rounds'],
          private_IDs_exported=False,tensor_loads=0,GPU_calls=0,run_freeze_sha256=sha(ROOT/'RUN_FREEZE.json')))


def prepare_requests(design):
    import numpy as np
    assert sha(D21/'PROFILE.json')==design['training_template_sha256']
    cfg=read(D21/'PROFILE.json');parts_path=FOUNDATION/'CLEAN_SPLIT.json'
    assert sha(parts_path)==design['clean_split_sha256']
    parts=read(parts_path)['indices'];clients=cfg['fixed_clients']
    assert len(parts)==20 and sorted(sum(parts,[]))==list(range(50000))
    data=Path(cfg['data_root'])/'cifar-10-batches-py'
    for n,d in cfg['data_files_sha256'].items():assert sha(data/n)==d,n
    labels=[]; brightness=[]
    for i in range(1,6):
        with (data/f'data_batch_{i}').open('rb') as f:
            record=pickle.load(f,encoding='bytes'); labels.extend(record[b'labels'])
            brightness.extend(np.asarray(record[b'data']).sum(1,dtype=np.int64).tolist())
    labels=np.asarray(labels); brightness=np.asarray(brightness)
    pool=np.asarray(sorted(sum([parts[c] for c in clients],[]))); assert len(pool)==25000
    private={}; info={}; sets={}
    prior=read(D21/'PRIVATE_REQUESTS.json')['balanced5000']['selected_by_owner']; sets['balanced_original']=set(sum(prior.values(),[]))
    assert len(sets['balanced_original'])==5000
    for name,rule in design['new'].items():
        ids=[]; rng=np.random.default_rng(rule['seed'])
        for c in range(10):
            p=pool[labels[pool]==c]
            if rule['distribution']=='dark40':p=p[np.lexsort((p,brightness[p]))][:len(p)*2//5]
            assert len(p)>=500
            ids.extend(rng.permutation(p)[:500].tolist())
        removed=set(ids);assert len(removed)==5000 and all(removed!=x for x in sets.values())
        sets[name]=removed
        by_owner={str(c):[i for i in parts[c] if i in removed] for c in clients}
        assert set(sum(by_owner.values(),[]))==removed and all(by_owner.values())
        kept={str(c):len(parts[c])-len(by_owner[str(c)]) for c in clients};assert min(kept.values())>0
        private[name]=dict(selected_by_owner=by_owner,retained_count=kept)
        info[name]=dict(removed=5000,class_counts=np.bincount(labels[ids],minlength=10).tolist(),
          retained_by_owner=kept,removed_by_owner={k:len(v) for k,v in by_owner.items()},
          expected_batches=10*sum(math.ceil(n/128)*5 for n in kept.values()), mean_raw_brightness=float(brightness[ids].mean()/3072),**rule)
        assert info[name]['class_counts']==[500]*10
    write(ROOT/'PRIVATE_REQUESTS.json',private)
    write(ROOT/'REQUEST_SUMMARY.json',dict(requests=info,original_random_mean_raw_brightness=float(brightness[sorted(sets['balanced_original'])].mean()/3072),
      request_intersection_counts={a:{b:len(va&vb) for b,vb in sets.items()} for a,va in sets.items()},participating=25000,all_training=50000))
    cfg.update(id='feduba.large_normal_repeats.prefix10.s42.20261111',branch_order=list(info),requests=info,rounds=10,
      private_requests_sha256=sha(ROOT/'PRIVATE_REQUESTS.json'),history_binding_sha256=sha(ROOT/'HISTORY_BINDING.json'),
      original_training_run_reused=False,schedule_horizon=20,stopping_route_witness=None,stopping_n=None)
    write(ROOT/'PROFILE.json',cfg)


def prepare_new():
    design=read(ROOT/'DESIGN.json'); pre=read(ROOT/'HISTORY_BINDING.json')['pre']; tracks=[]; evidence=[]
    for i, name in enumerate(design['new']):
        rp=ROOT/('FU_'+name+'_RESULT.json'); vp=ROOT/('FU_'+name+'_VERIFIED.json'); mp=ROOT/'fu'/name/'MANIFEST.json'
        a=read(vp); result=read(rp); m=read(mp)
        assert a['state']=='passed' and a['result_sha256']==sha(rp) and sha(mp)==result['manifest_sha256']
        assert a['rounds']==result['rounds']==len(m['rounds'])==10
        snaps={}
        for r in design['new_rounds']:
            row=m['rounds'][r-1]; assert row['round']==r
            after=row['after']; assert a['file_hashes'][after['path']]==after['sha256']
            path=(ROOT/after['path']).resolve(); assert path.is_relative_to(ROOT.resolve())
            snaps[r]=dict(after,path=str(path),payload_key=None)
        assert snaps[10]['sha256']==result['after']['sha256']
        tracks.append((f'u{i:02d}',None,snaps));evidence.extend([rp,vp,mp])
    seal_panel('new',pre,tracks,evidence)


if __name__=='__main__':
    try:prepare_stored()
    except BaseException:
        write(ROOT/'PREPARE_FAILURE.json',dict(traceback=traceback.format_exc()));raise
