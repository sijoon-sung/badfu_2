"""One stdlib-only copy of pinned fresh initializer/split, no model initialization."""
import json
import os
from pathlib import Path
import shutil
import traceback
from foundation_binding import ROOT,read,sha,source_profile
def once(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
    p=source_profile();pub=read(ROOT/'SOURCE_PUBLICATION.json')
    assert pub['state']=='published_fixed10_foundation_source_before_metadata_prepare'
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    for value in p['inputs'].values():
        assert sha(value['path'])==value['sha256']
        if 'bytes' in value:assert Path(value['path']).stat().st_size==value['bytes']
    once('PREPARE_ONCE.json',{'pid':os.getpid(),'model_loads':0,'model_forwards':0})
    original=read(p['inputs']['original_ready']['path'])
    assert original['state']=='passed' and original['official_CIFAR10_integrity_checks_passed']
    cp=read(ROOT/'CLEAN_FL_PROFILE.json')
    for n,s in original['data_files_sha256'].items():assert sha(Path(cp['data_root'])/'cifar-10-batches-py'/n)==s,n
    (ROOT/'private_assets').mkdir(exist_ok=False)
    shutil.copyfile(p['inputs']['original_initial']['path'],ROOT/'private_assets/clean_initial.pt')
    shutil.copyfile(p['inputs']['original_split']['path'],ROOT/'CLEAN_SPLIT.json')
    assert sha(ROOT/'private_assets/clean_initial.pt')==original['fresh_initial']['sha256']
    assert sha(ROOT/'CLEAN_SPLIT.json')==original['split_sha256']
    parts=read(ROOT/'CLEAN_SPLIT.json')['indices']
    assert len(parts)==20 and all(len(v)==2500 for v in parts) and sorted(sum(parts,[]))==list(range(50000))
    static=dict(read(ROOT/'SOURCE_FREEZE.json')['files'])
    once('CLEAN_FL_FREEZE.json',{'state':'fixed10_scientific_source_frozen','files':static})
    ready=dict(original,profile=cp['id'],source_hashes=static,initialization_input='Exact copied original seed42 fresh initializer, no old trained checkpoint')
    once('CLEAN_FL_READY.json',ready)
    once('LAUNCH_PROFILE.json',{'id':'feduba.public_fixed10.foundation20.actual.20261103','launch_enabled':True,
        'source_profile_sha256':sha(ROOT/'SOURCE_PROFILE.json'),'execution_root':str(ROOT),
        'fixed_selected_clients':p['fixed_selected_clients'],'rounds':20,'roles':200,'local_epochs':2000,'batches':40000,
        'fresh_initial':ready['fresh_initial'],'split_sha256':ready['split_sha256'],
        'data_files_sha256':ready['data_files_sha256'],'scientific_profile_sha256':sha(ROOT/'CLEAN_FL_PROFILE.json'),
        'new_model_initializations':0,'new_model_loads':0,'new_model_forwards':0,'future_paired_FU_still_required':True})
    once('PREPARATION_RESULT.json',{'state':'prepared_fixed10_same_initial_split_actual_profile',
        'fixed_selected_clients':p['fixed_selected_clients'],'initial_sha256':ready['fresh_initial']['sha256'],
        'split_sha256':ready['split_sha256'],'official_data_bytes_exactly_equal':True,
        'model_loads':0,'model_forwards':0,'new_training_started':False})
    for n in ['SOURCE_FREEZE.json','CLEAN_FL_FREEZE.json','CLEAN_FL_READY.json','LAUNCH_PROFILE.json','PREPARATION_RESULT.json','CLEAN_SPLIT.json','private_assets/clean_initial.pt']:static[n]=sha(ROOT/n)
    once('RUN_FREEZE.json',{'state':'actual_fixed10_foundation_frozen_before_training','files':static})
    print(json.dumps(read(ROOT/'PREPARATION_RESULT.json')))
if __name__=='__main__':
    try:main()
    except BaseException:
        once('PREPARE_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
