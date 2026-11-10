"""Fresh legitimate deletion FU20 branch; original SGD and calibration engines."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import time
import traceback
from bindings import ROOT,FOUNDATION,read,write,checked,sha,require_publication


def main(branch):
    cfg=require_publication()
    (ROOT/('FU_'+branch+'_ONCE')).open('x').write(str(os.getpid()))
    from resource_guard import admit
    write(ROOT/('ADMISSION_'+branch+'.json'),admit(cfg))
    import torch
    from torchvision.datasets import CIFAR10
    from torchvision import transforms
    from fu_core import owned_selection,branch_dataset,local_schedule,calibration_round
    from fu_training import train_role
    import model_reference
    from runtime_common import save
    assert branch in cfg['branch_order']
    for name,version in cfg['packages'].items():assert importlib.metadata.version(name)==version
    torch.set_num_threads(1);torch.backends.cudnn.benchmark=False
    torch.cuda.set_per_process_memory_fraction(cfg['memory_fraction'])
    assert sha(ROOT/'PRIVATE_REQUESTS.json')==cfg['private_requests_sha256']
    binding=read(ROOT/'HISTORY_BINDING.json');assert sha(ROOT/'HISTORY_BINDING.json')==cfg['history_binding_sha256']
    history=binding['history'];parts=read(FOUNDATION/'CLEAN_SPLIT.json')['indices']
    selected=owned_selection(parts,{int(k):v for k,v in read(ROOT/'PRIVATE_REQUESTS.json')[branch]['selected_by_owner'].items()},
                             cfg['fixed_clients'],cfg['requests'][branch]['removed'])
    for name,digest in cfg['data_files_sha256'].items():assert sha(Path(cfg['data_root'])/'cifar-10-batches-py'/name)==digest
    train=CIFAR10(cfg['data_root'],train=True,download=False,transform=transforms.Compose([
        transforms.RandomCrop(32,padding=4),transforms.RandomHorizontalFlip(),transforms.ToTensor(),
        transforms.Normalize((.5,)*3,(.5,)*3)]))
    def load(meta,key=None):
        checked(meta);value=torch.load(meta['path'],map_location='cpu',weights_only=True)
        return value if key is None else value[key]
    out=ROOT/'fu'/branch;out.mkdir(parents=True,exist_ok=False)
    state=load(history['fresh_initial']);incoming=save(out/'initial.pt',state)
    manifest=dict(branch=branch,profile=cfg['id'],initial=incoming,rounds=[],history_binding_sha256=cfg['history_binding_sha256'])
    model=model_reference.ResNet18().cuda();batches=0;started=time.time()
    for record in history['rounds']:
        require_publication()
        r=record['round'];clients=record['clients'];assert clients==cfg['fixed_clients']
        old_global=load(record['incoming'])
        old_meta={role['client']:role['checkpoint'] for role in record['roles']}
        old={c:load(old_meta[c],'model') for c in clients}
        trained={};roles=[]
        for c in clients:
            model.load_state_dict(state,strict=True)
            # No trigger tensor is loaded: benign RetainedDataset ignores delta.
            dataset=branch_dataset(train,parts[c],selected[c],None,'benign')
            retained=[i for i in parts[c] if i not in set(selected[c])]
            schedule=local_schedule(r,c,len(dataset))
            def on_epoch(event):
                row=dict(time=time.time(),branch=branch,round=r,client=c,**event)
                with (out/'epochs.jsonl').open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps(row)+'\n');f.flush()
                write(ROOT/'STATE.json',dict(state='FU_training',pid=os.getpid(),**row))
                print(json.dumps(row),flush=True)
            value=train_role(model,dataset,retained,schedule,'cuda',on_epoch)
            value.update(branch=branch,round=r,client=c,incoming=incoming,removed_ids=selected[c],
                         original_local=old_meta[c],original_incoming=record['incoming'])
            meta=save(out/'trained'/f'round{r:02d}_client{c:02d}.pt',value)
            trained[c]=value['model'];batches+=value['batches']
            roles.append(dict(client=c,checkpoint=meta,source_N=len(dataset),batches=value['batches']))
        after,effective,calibrated,reused=calibration_round(r,clients,cfg['fixed_clients'],old,trained,old_global,state)
        assert not reused
        calibrated_meta=[]
        for c in clients:
            assert all(torch.isfinite(v).all() for v in calibrated[c].values())
            calibrated_meta.append(dict(client=c,checkpoint=save(out/'calibrated'/f'round{r:02d}_client{c:02d}.pt',calibrated[c])))
        model.load_state_dict(after,strict=True)
        meta=save(out/'rounds'/f'round{r:02d}.pt',after)
        stored=load(dict(meta,path=str(ROOT/meta['path'])))
        assert all(torch.equal(stored[k],after[k]) for k in after)
        manifest['rounds'].append(dict(round=r,clients=clients,incoming=incoming,original_incoming=record['incoming'],
                                       trained_roles=roles,calibrated_roles=calibrated_meta,after=meta,total_batches=batches))
        write(out/'MANIFEST.json',manifest);state=after;incoming=meta
        del old,trained,effective,calibrated,old_global,value,stored
    assert batches==cfg['requests'][branch]['expected_batches'] and len(manifest['rounds'])==20
    final=save(out/'after.pt',state)
    result=dict(state='completed_legitimate_FU20',branch=branch,rounds=20,roles=200,epochs=1000,batches=batches,
                after=dict(final,path=str(ROOT/final['path']),payload_key=None),manifest_sha256=sha(out/'MANIFEST.json'),
                seconds=time.time()-started,peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,
                cudnn_deterministic=torch.backends.cudnn.deterministic,cudnn_TF32=torch.backends.cudnn.allow_tf32,
                matmul_TF32=torch.backends.cuda.matmul.allow_tf32,trigger_inputs=0,old_training_repeated=False)
    write(ROOT/('FU_'+branch+'_RESULT.json'),result)
    write(ROOT/'STATE.json',dict(state='FU_complete',branch=branch,pid=os.getpid(),rounds=20,batches=batches))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('branch');args=p.parse_args()
    try:main(args.branch)
    except BaseException:write(ROOT/('FU_'+args.branch+'_FAILURE.json'),dict(traceback=traceback.format_exc()));raise
