"""Independent metadata-only check of the actual class and brightness composition."""
import json
import pickle
from pathlib import Path
from bindings import ROOT, FOUNDATION, read, write, sha


def main():
    (ROOT/'DOMAIN_AUDIT_ONCE').open('x').write('no model calls\n')
    cfg=read(ROOT/'PROFILE.json');design=read(ROOT/'DESIGN.json')
    assert sha(ROOT/'PRIVATE_REQUESTS.json')==cfg['private_requests_sha256']
    split=FOUNDATION/'CLEAN_SPLIT.json';assert sha(split)==design['clean_split_sha256']
    parts=read(split)['indices'];clients=cfg['fixed_clients']
    owner={i:c for c in clients for i in parts[c]};assert len(owner)==25000
    labels={};brightness={};base=Path(cfg['data_root'])/'cifar-10-batches-py'
    for b in range(1,6):
        n=f'data_batch_{b}';assert sha(base/n)==cfg['data_files_sha256'][n]
        with (base/n).open('rb') as f: q=pickle.load(f,encoding='bytes')
        sums=q[b'data'].sum(axis=1,dtype='int64')
        for j,(y,sv) in enumerate(zip(q[b'labels'],sums)):
            i=(b-1)*10000+j
            if i in owner: labels[i]=y; brightness[i]=int(sv)
    assert len(labels)==len(owner)
    groups={c:{i for i,y in labels.items() if y==c} for c in range(10)}
    low={c:set(sorted(g,key=lambda i:(brightness[i],i))[:(2*len(g))//5]) for c,g in groups.items()}
    new=read(ROOT/'PRIVATE_REQUESTS.json')
    ref=read(Path('D:/FEDUBA_LARGE_BENIGN_VALIDATION_20261110/PRIVATE_REQUESTS.json'))['balanced5000']
    result={}
    for b,req in dict(balanced_original=ref,**new).items():
        selected=set()
        for c,ids in req['selected_by_owner'].items():
            assert not selected.intersection(ids) and all(owner[i]==int(c) for i in ids)
            selected.update(ids)
        assert len(selected)==5000
        assert all(len(g&selected)==500 for g in groups.values())
        low_removed=[len(low[c]&selected) for c in range(10)]
        if b.startswith('dark_'):assert low_removed==[500]*10
        rows=[dict(label=c,before=len(groups[c]),before_low=len(low[c]),after=len(groups[c]-selected),
                   after_low=len(low[c]-selected),removed_low=low_removed[c]) for c in range(10)]
        total_after=sum(z['after'] for z in rows); retained_low=sum(z['after_low'] for z in rows)
        assert total_after==20000
        result[b]=dict(removed_low=sum(low_removed),retained_low=retained_low,retained_total=total_after,
                       retained_low_fraction=retained_low/total_after,per_class=rows)
    write(ROOT/'DOMAIN_AUDIT.json',dict(state='passed',initial_low=sum(map(len,low.values())),initial_total=25000,
       request_hash_verified=True,all_real_owner_and_class_counts_exact=True,no_model_calls=True,requests=result))
    print(json.dumps({b:{k:v for k,v in row.items() if k!='per_class'} for b,row in result.items()}))


if __name__=='__main__':main()
