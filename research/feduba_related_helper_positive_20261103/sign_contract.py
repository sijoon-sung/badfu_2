"""One fixed four-image CPU arithmetic contract; no real data or model loading."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import ast,json,shutil,traceback
from pair_binding import ROOT,read,sha,source_profile

def main():
    p=source_profile();assert read(ROOT/'SOURCE_PUBLICATION.json')['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    assert read(ROOT/'SOURCE_REVIEW_RESULT.json')['state']=='passed_sign_only_source_review'
    contract=read(ROOT/'SIGN_CONTRACT_PROFILE.json');assert contract['launch_enabled']
    from native_memory import memory_information
    memory=memory_information();assert memory['availableBytes']>=8*2**30 and memory['commitLimit']-memory['committedBytes']>=16*2**30
    assert shutil.disk_usage(ROOT).free>=80*2**30
    from native_processes import processes
    assert not [r for r in processes() if r['ProcessId'] not in [os.getpid(),os.getppid()] and any(t in r['CommandLine'].lower() for t in p['known_training_process_tokens'])]
    with (ROOT/'SIGN_CONTRACT_ONCE.json').open('x',encoding='utf-8') as f:json.dump({'pid':os.getpid(),'profile_sha256':sha(ROOT/'SIGN_CONTRACT_PROFILE.json'),'memory':memory,'competing_trainers':0},f)
    import torch
    import numpy as np
    from torch import nn
    from torch.utils.data import Dataset
    from core import IndexedDataset,RequestDataset,add_trigger
    torch.set_num_threads(1)
    source=ROOT/'private_inputs/related_util.py';assert sha(source)==p['inputs']['related_helper']['sha256']
    tree=ast.parse(source.read_text(encoding='utf-8'));nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in ['poison_image','apply_noise_patch']]
    assert len(nodes)==2
    env={'torch':torch,'nn':nn,'Dataset':Dataset,'np':np}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),env)
    class Synthetic(Dataset):
        def __init__(self):self.calls=0
        def __len__(self):return 4
        def __getitem__(self,i):
            self.calls+=1
            return torch.full((3,32,32),contract['image_values'][i],dtype=torch.float32),i
    delta=torch.full((1,3,32,32),contract['delta'],dtype=torch.float32)
    refdata=Synthetic();newdata=Synthetic()
    reference=env['poison_image'](refdata,[1,2,3],delta,None)
    candidate=RequestDataset(IndexedDataset(newdata,[10,11,12,13]),[11,12,13],delta,True)
    comparisons=[]
    for i in range(4):
        rx,ry=reference[i];nx,ny=candidate[i]
        raw=torch.full_like(nx,contract['image_values'][i]);expected=(raw+delta[0]).clamp(-1,1) if i in [1,2,3] else raw
        assert torch.equal(rx,nx) and torch.equal(nx,expected) and ry==ny==i
        minus=add_trigger(raw,delta,sign=-1,clip=True)
        if i in [1,2,3]:assert not torch.equal(nx,minus)
        comparisons.append({'position':i,'selected':i in [1,2,3],'source_helper_exact':True,'label_preserved':True,'clip_exact':True})
    assert refdata.calls==8 and newdata.calls==4 and not torch.cuda.is_initialized()
    result={'state':'passed','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'profile_sha256':sha(ROOT/'SIGN_CONTRACT_PROFILE.json'),'related_helper_sha256':sha(source),'comparisons':comparisons,'related_dataset_getitems':refdata.calls,'new_dataset_getitems':newdata.calls,'full_helper_RNG_port':False,'model_loads':0,'model_forwards':0,'real_data_reads':0,'CUDA_initialized':False,'threads':torch.get_num_threads()}
    with (ROOT/'SIGN_CONTRACT_RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
if __name__=='__main__':
    try:main()
    except BaseException:
        with (ROOT/'SIGN_CONTRACT_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f)
        raise
