"""Evaluate the new FU endpoint once through the original author evaluator."""
import ast
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import json
from pathlib import Path
import torch
from run import ROOT,read,sha,write,frozen,ops,module


def main():
    frozen();assert read(ROOT/'STATE.json')['state']=='complete'
    assert read(ROOT/'CPU_AUDIT.json')['state']=='passed'
    for name,digest in read(ROOT/'INDEPENDENT_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    resources=ops.guard();write('INDEPENDENT_STARTED.json',{'pid':os.getpid(),'resources':resources})
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic=True;torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
    source=Path('D:/FUBA_AUTHOR_MODELS_20261115');refs=read(source/'SOURCE_FREEZE.json')['files']
    for name in ['upstream/utils/comm_utils.py','upstream/utils/dba_attack_utils.py']:
        assert sha(source/name)==refs[name]
    tree=ast.parse((source/'upstream/utils/comm_utils.py').read_text())
    funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['test','attack_dba']]
    assert len(funcs)==2;env={'torch':torch}
    exec(compile(ast.Module(body=funcs,type_ignores=[]),'author_evaluator','exec'),env)
    triggers={};exec(compile((source/'upstream/utils/dba_attack_utils.py').read_text(),'author_triggers','exec'),triggers)
    from torchvision.datasets import MNIST
    from torchvision.transforms import ToTensor
    ds=MNIST(read(ROOT/'inputs/PROFILE.json')['data_root'],train=False,download=False,transform=ToTensor())
    loader=torch.utils.data.DataLoader(ds,batch_size=512,shuffle=False,num_workers=0)
    result=read(ROOT/'RESULT.json');assert sha(ROOT/'after.pt')==result['after']['sha256']
    net=module('author_Net',ROOT/'inputs/author_model.py').Net().cuda().eval()
    net.load_state_dict(torch.load(ROOT/'after.pt',map_location='cpu',weights_only=True),strict=True)
    ca=env['test'](net,loader,'cuda');asr=env['attack_dba'](net,loader,8,'cuda',triggers['add_backdoor_all'])
    cc,hits=round(ca*100),round(asr*9026/100);m=result['evaluation']
    match=cc==m['clean_correct'] and hits==m['target_successes']
    write('INDEPENDENT_RESULT.json',{'state':'passed' if match else 'mismatch_preserved','CA_correct':cc,'ASR_hits':hits,
        'N':10000,'non_target_N':9026,'CA_pct':ca,'ASR_pct':asr,'exact_integer_match':match,
        'evaluator':'original-author-functions-FP32-contiguous-B512-deterministic-noTF32',
        'before_model_reevaluated':False,'full_paper_reproduced':False})
    print(json.dumps({'match':match,'CA_correct':cc,'ASR_hits':hits}),flush=True)


if __name__=='__main__':main()
