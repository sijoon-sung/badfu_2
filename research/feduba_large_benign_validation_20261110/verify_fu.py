"""Independent CPU storage, identity, epoch and FedEraser reconstruction audit."""
import argparse
import hashlib
import json
import math
import os
import traceback
from pathlib import Path
from bindings import ROOT,FOUNDATION,read,write,sha,checked,require_publication


def main(branch):
    cfg=require_publication();(ROOT/('VERIFY_'+branch+'_ONCE')).open('x').write(str(os.getpid()))
    import torch
    torch.set_num_threads(1)
    manifest_path=ROOT/'fu'/branch/'MANIFEST.json'
    result=read(ROOT/('FU_'+branch+'_RESULT.json'));assert sha(manifest_path)==result['manifest_sha256']
    manifest=read(manifest_path);history=read(ROOT/'HISTORY_BINDING.json')['history']
    parts=read(FOUNDATION/'CLEAN_SPLIT.json')['indices'];requests=read(ROOT/'PRIVATE_REQUESTS.json')[branch]
    hashes={};roles_checked=[];total_batches=0
    def finite(value):
        if isinstance(value,torch.Tensor):assert torch.isfinite(value).all()
        elif isinstance(value,dict):
            for item in value.values():finite(item)
        elif isinstance(value,(tuple,list)):
            for item in value:finite(item)
    def load(meta,key=None,derived=True):
        p=Path(meta['path']);p=p if p.is_absolute() else ROOT/p
        assert sha(p)==meta['sha256'] and p.stat().st_size==meta['bytes']
        if derived:hashes[str(p.relative_to(ROOT)).replace('\\','/')]=meta['sha256']
        payload=torch.load(p,map_location='cpu',weights_only=True);finite(payload)
        return payload if key is None else payload[key]
    incoming=load(manifest['initial']);initial_reference=load(history['fresh_initial'],derived=False)
    assert all(torch.equal(incoming[k],initial_reference[k]) for k in incoming)
    del initial_reference
    assert len(manifest['rounds'])==20
    for row,old_row in zip(manifest['rounds'],history['rounds']):
        r=row['round'];assert r==old_row['round'] and row['clients']==cfg['fixed_clients']==old_row['clients']
        assert [role['client'] for role in row['trained_roles']]==cfg['fixed_clients']
        assert [role['client'] for role in row['calibrated_roles']]==cfg['fixed_clients']
        old_global=load(old_row['incoming'],derived=False)
        old_meta={x['client']:x['checkpoint'] for x in old_row['roles']}
        cal_meta={x['client']:x['checkpoint'] for x in row['calibrated_roles']}
        accumulator={k:torch.zeros_like(v) for k,v in incoming.items()};last_counter={}
        for role in row['trained_roles']:
            c=role['client'];expected=[i for i in parts[c] if i not in set(requests['selected_by_owner'][str(c)])]
            payload=load(role['checkpoint']);new=payload['model'];old=load(old_meta[c],'model',False)
            assert payload['source_indices']==expected and payload['removed_ids']==requests['selected_by_owner'][str(c)]
            assert payload['incoming']==row['incoming'] and payload['original_local']==old_meta[c]
            assert payload['schedule']['seed']==42+500000+r*10000+c*100
            assert payload['schedule']['epochs']==5 and payload['schedule']['batch_size']==128
            assert payload['schedule']['lr']==.01*(1+math.cos(math.pi*(r-1)/20))/2
            nb=math.ceil(len(expected)/128);assert payload['batches']==nb*5==role['batches']
            assert len(payload['epochs'])==5 and role['source_N']==len(expected)
            for ep,record in enumerate(payload['epochs'],1):
                assert record['epoch']==ep and record['examples']==len(expected) and record['batches']==nb
                assert sorted(record['source_ids'].tolist())==sorted(expected)
                assert record['cumulative_role_batches']==ep*nb
                assert {'rng_before_epoch','rng','loader_rng_before_epoch','loader_rng'}.issubset(record)
            assert len(payload['edge_batches'])==2
            assert all(torch.isfinite(s['momentum_buffer']).all() for s in payload['optimizer']['state'].values())
            stored_cal=load(cal_meta[c])
            for key,g in incoming.items():
                d_old=(old[key]-old_global[key]).float()
                d_new=new[key]-g
                old_length=torch.linalg.vector_norm(d_old.reshape(-1))
                new_length=torch.linalg.vector_norm(d_new.float().reshape(-1))
                direction=d_new if float(new_length)==0 else d_new/new_length
                reconstructed=(g+old_length*direction).to(g.dtype)
                assert torch.equal(reconstructed,stored_cal[key]),(r,c,key,'calibration')
                accumulator[key]+=stored_cal[key]
                if 'num_batches_tracked' in key:last_counter[key]=stored_cal[key].clone()
            roles_checked.append(dict(round=r,client=c,source_N=len(expected),epochs=5,batches=nb*5,
                                      source_ids_and_epochs_exact=True,optimizer_rng_finite=True,calibration_exact=True))
            total_batches+=nb*5
            del payload,new,old,stored_cal
        output=load(row['after'])
        for key in output:
            expected=last_counter[key] if 'num_batches_tracked' in key else accumulator[key]/10
            assert torch.equal(output[key],expected),(r,key,'aggregation')
        assert row['total_batches']==total_batches
        incoming=output
        write(ROOT/'AUDIT_STATE.json',dict(branch=branch,round=r,roles=len(roles_checked),batches=total_batches))
    final=load(result['after'])
    assert all(torch.equal(final[k],incoming[k]) for k in final)
    assert total_batches==cfg['requests'][branch]['expected_batches']==result['batches']
    assert len(roles_checked)==200
    write(ROOT/('FU_'+branch+'_VERIFIED.json'),dict(state='passed',branch=branch,rounds=20,roles=roles_checked,
           epochs=1000,batches=total_batches,file_hashes=hashes,calibration_and_aggregation_exact=True,
           training_gradient_and_augmentation_replayed=False,result_sha256=sha(ROOT/('FU_'+branch+'_RESULT.json'))))
    print(json.dumps(dict(state='passed',branch=branch,roles=200,batches=total_batches)),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('branch');args=p.parse_args()
    try:main(args.branch)
    except BaseException:write(ROOT/('VERIFY_'+args.branch+'_FAILURE.json'),dict(traceback=traceback.format_exc()));raise
