"""Author-function evaluation of both local and aggregated diagnostic models."""
import ast
import json
import os
from pathlib import Path
import torch
from run import ROOT,read,sha,write,frozen,guard,module


def main():
    frozen();assert read(ROOT/'CPU_AUDIT.json')['state']=='passed'
    for name,digest in read(ROOT/'INDEPENDENT_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    resources=guard();write('INDEPENDENT_STARTED.json',{'pid':os.getpid(),'resources':resources})
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic=True;torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
    root=Path('D:/FUBA_AUTHOR_MODELS_20261115');freeze=read(root/'SOURCE_FREEZE.json')['files']
    for name in ['upstream/utils/comm_utils.py','upstream/utils/dba_attack_utils.py']:assert sha(root/name)==freeze[name]
    nodes=[n for n in ast.parse((root/'upstream/utils/comm_utils.py').read_text(encoding='utf-8')).body
           if isinstance(n,ast.FunctionDef) and n.name in ['test','attack_dba']]
    assert len(nodes)==2;env={'torch':torch};exec(compile(ast.Module(body=nodes,type_ignores=[]),'author_eval','exec'),env)
    triggers={};exec(compile((root/'upstream/utils/dba_attack_utils.py').read_text(encoding='utf-8'),'author_trigger','exec'),triggers)
    Net=module('independent_Net',ROOT/'inputs/author_model.py').Net
    from torchvision.datasets import MNIST
    from torchvision.transforms import ToTensor
    data=MNIST(read(ROOT/'inputs/PROFILE.json')['data_root'],train=False,download=False,transform=ToTensor())
    loader=torch.utils.data.DataLoader(data,batch_size=512,shuffle=False,num_workers=0)
    result=read(ROOT/'RESULT.json');rows=[]
    for arm in ['algorithm_sgd','experimental_adam']:
        for kind,item,key in [('local',result['rows'][arm]['phase'],'model'),
                              ('aggregate',result['rows'][arm]['aggregate_file'],'after')]:
            assert sha(ROOT/item['path'])==item['sha256']
            net=Net().cuda().eval();net.load_state_dict(torch.load(ROOT/item['path'],map_location='cpu',weights_only=True)[key],strict=True)
            ca=env['test'](net,loader,'cuda');asr=env['attack_dba'](net,loader,8,'cuda',triggers['add_backdoor_all'])
            bias=0
            with torch.inference_mode():
                for x,y in loader:
                    pred=net(x.cuda()).argmax(1).cpu();bias+=int(((pred==8)&(y!=8)).sum())
            cc,hits=round(ca*10000/100),round(asr*9026/100);old=result['rows'][arm][kind]
            row={'arm':arm,'kind':kind,'clean_correct':cc,'target_successes':hits,'clean_target_bias':bias,
                'exact':cc==old['clean_correct'] and hits==old['target_successes'] and bias==old['clean_target_bias']}
            rows.append(row);write(f'independent/{arm}_{kind}.json',row);del net
    passed=all(x['exact'] for x in rows)
    write('INDEPENDENT_RESULT.json',{'state':'passed' if passed else 'mismatch_preserved','rows':rows,
        'models':4,'clean_N':10000,'non_target_N':9026,'evaluator':'original author test/attack_dba; separate clean-bias pass',
        'layout':'FP32 contiguous NCHW B512 deterministic noTF32','new_training':0})
    assert passed,'Independent discrepancy preserved'
    print(json.dumps({'state':'passed','models':4}),flush=True)


if __name__=='__main__':main()
