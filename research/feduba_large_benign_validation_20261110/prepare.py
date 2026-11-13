"""One CPU metadata preparation: no checkpoint tensor load, training or inference."""
import importlib.metadata
import json
import math
import pickle
import sys
from pathlib import Path
import numpy as np
from bindings import ROOT,FOUNDATION,CAT,read,write,absolute,sha,make_guard,append_case,select


def main():
    (ROOT/'PREPARE_ONCE').open('x').write('metadata and official labels only\n')
    assert read(ROOT/'SOURCE_PUBLICATION.json')['all_raw_blob_bytes_verified']
    for name,digest in read(ROOT/'SOURCE_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    original=(CAT/'catalog.json').read_bytes()
    assert sha(CAT/'catalog.json')=='b4da557f61a8e9f8afad4b5dbd87202126e88b37bfb74393e02cbf17f9144e6b'
    (ROOT/'CATALOG_BEFORE.json').write_bytes(original)
    profile=read(FOUNDATION/'CLEAN_FL_PROFILE.json');ready=read(FOUNDATION/'CLEAN_FL_READY.json')
    expected={'clean_fl/MANIFEST.json':'dc4c4e338c56506b629aee8140b21e43b8d9579d52447c9857f1fdce68caf4fe',
              'CLEAN_SPLIT.json':'97d697be302c69d23b641d6670d57931878798609a0c4a324794bd7d4ba7cfee',
              'CLEAN_FL_VERIFIED.json':'c18d7af6b0800cc8ff8810d4440f337239d04839ea320b46ff8251baa37485a2',
              'CLEAN_FL_RESULT.json':'8bd7cc42bdc90472b63695a6241a45accfab1360b9bba12812c3d5531b6253c7',
              'CLEAN_FL_READY.json':'788ce2f3d0da0c3daf160b31bc4b969ceb0d71eea090a178933375714dd2b11f',
              'CLEAN_FL_PROFILE.json':'70693581f53c79ff9f7ca23bf2a3914765ae123618a513099cf22c0cb70ccd1d'}
    for name,digest in expected.items():assert sha(FOUNDATION/name)==digest,name
    assert read(FOUNDATION/'CLEAN_FL_VERIFIED.json')['state']=='passed'
    history=absolute(read(FOUNDATION/'clean_fl/MANIFEST.json'))
    clients=[2,3,5,7,9,12,13,16,18,19]
    assert len(history['rounds'])==20 and all(row['clients']==clients for row in history['rounds'])
    parts=read(FOUNDATION/'CLEAN_SPLIT.json')['indices']
    assert len(parts)==20 and sorted(sum(parts,[]))==list(range(50000))
    pre=read(FOUNDATION/'CLEAN_FL_RESULT.json')['before']
    # Original result uses relative paths, like the pinned manifest.
    pre=absolute(pre)
    assert pre['sha256']=='a4cd527f7e59dc459b6e25ef6049fcad83b3bbfdd80d2800c3368ec27b0a1af5'
    pre['payload_key']=None
    files={name:dict(path=str(FOUNDATION/name),sha256=digest,bytes=(FOUNDATION/name).stat().st_size) for name,digest in expected.items()}
    metadata=[history['fresh_initial']]+[row['after'] for row in history['rounds']]
    metadata += [role['checkpoint'] for row in history['rounds'] for role in row['roles']]
    for index,meta in enumerate(metadata):
        p=Path(meta['path']);files['history_'+str(index)]=dict(path=str(p),sha256=meta['sha256'],bytes=p.stat().st_size)
    case_id='feduba.public_fixed10.cifar10.s42.full20.history.diagnostic.20261110'
    guard=make_guard('history',case_id,files)
    entry=dict(id=case_id,family='feduba',source_root=str(FOUNDATION),post_type='clean_full20_history_diagnostic',
               allowed_purposes=['diagnostic','global_history','client_history'],server_inputs=dict(pre=pre),checkpoint_guard=guard,
               provenance='Original completed verified cleanFL20 full history, 221 checkpoint references hash-verified; new normal-FU validation only, no default change')
    append_case(entry,'history');write(ROOT/'HISTORY_CASE_SELECTION.json',select(case_id,'client_history'))
    write(ROOT/'HISTORY_BINDING.json',dict(case_id=case_id,pre=pre,history=history,foundation_root=str(FOUNDATION),
                                          original_audit_sha256=expected['CLEAN_FL_VERIFIED.json'],files_verified=len(files)))
    labels=[];data_dir=Path(profile['data_root'])/'cifar-10-batches-py'
    for name,digest in ready['data_files_sha256'].items():assert sha(data_dir/name)==digest,name
    for i in range(1,6):
        with (data_dir/('data_batch_'+str(i))).open('rb') as f:labels.extend(pickle.load(f,encoding='bytes')[b'labels'])
    labels=np.asarray(labels);assert len(labels)==50000
    participating=np.asarray(sorted(sum([parts[c] for c in clients],[])));assert len(participating)==25000
    rng=np.random.default_rng(20261110)
    balanced=[]
    for c in range(10):balanced.extend(rng.permutation(participating[labels[participating]==c])[:500].tolist())
    request_sets={'balanced5000':balanced,'class2_all':participating[labels[participating]==2].tolist()}
    request_info={};private={}
    for name,ids in request_sets.items():
        removed=set(ids);assert len(removed)==len(ids)
        by_owner={str(c):[i for i in parts[c] if i in removed] for c in clients}
        assert set(sum(by_owner.values(),[]))==removed
        retained={str(c):len(parts[c])-len(by_owner[str(c)]) for c in clients};assert min(retained.values())>0
        expected_batches=20*sum(math.ceil(n/128)*5 for n in retained.values())
        private[name]=dict(selected_by_owner=by_owner,retained_count=retained)
        request_info[name]=dict(removed=len(ids),fraction_of_participating25000=len(ids)/25000,
                               fraction_of_all50000=len(ids)/50000,class_counts=np.bincount(labels[ids],minlength=10).tolist(),
                               removed_by_owner={k:len(v) for k,v in by_owner.items()},retained_by_owner=retained,expected_batches=expected_batches)
    assert len(balanced)==5000 and request_info['balanced5000']['class_counts']==[500]*10
    write(ROOT/'PRIVATE_REQUESTS.json',private)
    cfg=dict(id='feduba.large_benign.fixed20.s42.20261110',related_cards=['D20','D02','D06','D07','D08','D15','R03'],
             foundation_root=str(FOUNDATION),history_case_id=case_id,data_root=profile['data_root'],fixed_clients=clients,
             branch_order=['balanced5000','class2_all'],requests=request_info,rounds=20,local_epochs=5,batch_size=128,
             optimizer='SGD .01 cosine20 momentum.9 weight_decay0',role_seed='42+500000+round*10000+client*100',
             private_requests_sha256=sha(ROOT/'PRIVATE_REQUESTS.json'),history_binding_sha256=sha(ROOT/'HISTORY_BINDING.json'),
             admission=dict(memory_gib=6,disk_gib=80,gpu_free_mib=3584,gpu_util_max=10,wait_seconds=120),memory_fraction=.25,
             expected_original_catalog_sha256=__import__('hashlib').sha256(original).hexdigest(),
             baseline_detector_root='D:/BLIND_ROUTE_DETECTOR_V2_20261110',stopping_route_witness=299,stopping_n=900,
             old_jobs_repeated=False,original_models_modified=False,
             data_files_sha256=ready['data_files_sha256'],python_version=list(sys.version_info[:3]),
             packages={n:importlib.metadata.version(n) for n in ['torch','torchvision','numpy']})
    assert cfg['packages']=={'torch':'2.7.1+cu118','torchvision':'0.22.1+cu118','numpy':'1.26.4'}
    assert cfg['python_version']==[3,12,10]
    write(ROOT/'PROFILE.json',cfg)
    names=list(read(ROOT/'SOURCE_FREEZE.json')['files'])+['SOURCE_FREEZE.json','PROFILE.json','PRIVATE_REQUESTS.json','HISTORY_BINDING.json','HISTORY_CASE_SELECTION.json','CATALOG_history.json']
    write(ROOT/'RUN_FREEZE.json',dict(files={n:sha(ROOT/n) for n in names},GPU_computation_started=False))
    write(ROOT/'PREPARED.json',dict(state='prepared',requests=request_info,history_case_id=case_id,checkpoint_tensor_loads=0,
                                   image_inference=0,GPU_training=0,run_freeze_sha256=sha(ROOT/'RUN_FREEZE.json')))
    print(json.dumps(dict(state='prepared',requests=request_info)),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        import traceback
        write(ROOT/'PREPARE_FAILURE.json',dict(traceback=traceback.format_exc()));raise
