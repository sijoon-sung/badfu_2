"""One post-completion evaluation through the original author functions for all new rounds."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import time
import torch
from run import ROOT, read, sha, write, frozen, guard


def main():
    frozen()
    assert read(ROOT/'STATE.json')['state']=='complete'
    assert read(ROOT/'CPU_AUDIT.json')['state']=='passed'
    for name,digest in read(ROOT/'INDEPENDENT_FREEZE.json')['files'].items():
        assert sha(ROOT/name)==digest
    resources=guard()
    write(ROOT/'INDEPENDENT_STARTED.json',{'pid':os.getpid(),'time':time.time(),'resources':resources},True)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic=True
    torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.allow_tf32=False
    torch.backends.cuda.matmul.allow_tf32=False
    source_root=Path('D:/FUBA_AUTHOR_MODELS_20261115')
    refs=read(source_root/'SOURCE_FREEZE.json')['files']
    for p in ['upstream/utils/comm_utils.py','upstream/utils/dba_attack_utils.py']:
        assert sha(source_root/p)==refs[p]
    tree=ast.parse((source_root/'upstream/utils/comm_utils.py').read_text(encoding='utf-8'))
    funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['test','attack_dba']]
    assert len(funcs)==2
    original={'torch':torch}
    exec(compile(ast.Module(body=funcs,type_ignores=[]),'author_comm_utils','exec'),original)
    triggers={}
    exec(compile((source_root/'upstream/utils/dba_attack_utils.py').read_text(encoding='utf-8'),'author_dba','exec'),triggers)
    spec=importlib.util.spec_from_file_location('author_Net',ROOT/'inputs/author_model.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    from torchvision.datasets import MNIST
    from torchvision.transforms import ToTensor
    ds=MNIST(read(ROOT/'inputs/PROFILE.json')['data_root'],train=False,download=False,transform=ToTensor())
    loader=torch.utils.data.DataLoader(ds,batch_size=512,shuffle=False,num_workers=0)
    rows=[]
    arm='fullbatch'
    for entry in read(ROOT/'MANIFEST.json')['rounds']:
        path=ROOT/entry['path'];assert sha(path)==entry['sha256']
        b=torch.load(path,weights_only=True,map_location='cpu')
        model=mod.Net().cuda().eval();model.load_state_dict(b['after'],strict=True)
        ca=original['test'](model,loader,'cuda')
        asr=original['attack_dba'](model,loader,8,'cuda',triggers['add_backdoor_all'])
        cc,hits=round(ca*10000/100),round(asr*9026/100)
        old=entry['evaluation']
        row={'arm':arm,'round':entry['round'],'CA_correct':cc,'ASR_hits':hits,
             'CA_pct':ca,'ASR_pct':asr,'exact_integer_match':cc==old['clean_correct'] and hits==old['target_successes']}
        rows.append(row)
        write(ROOT/'independent'/f'{arm}_{entry["round"]:04d}.json',row,True)
        print(json.dumps(row),flush=True)
        del model,b
    write(ROOT/'INDEPENDENT_RESULT.json',{'state':'passed' if all(x['exact_integer_match'] for x in rows) else 'mismatch_preserved',
         'rows':rows,'models':1,'N_per_model':10000,'non_target_N':9026,'evaluator':'author-functions-FP32-contiguous-B512',
         'time':time.time()},True)


if __name__=='__main__':main()
