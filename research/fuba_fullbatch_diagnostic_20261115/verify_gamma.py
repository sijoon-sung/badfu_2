"""One independent reconstruction of every saved gamma point on original heldout data."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import torch
from run import ROOT,read,sha,write,frozen,guard


def main():
    frozen();assert read(ROOT/'STATE.json')['state']=='complete'
    assert read(ROOT/'CPU_AUDIT.json')['state']=='passed'
    for name,digest in read(ROOT/'GAMMA_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    resources=guard();write(ROOT/'GAMMA_AUDIT_STARTED.json',{'pid':os.getpid(),'resources':resources},True)
    torch.set_num_threads(1);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic=True;torch.backends.cudnn.benchmark=False
    torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
    source=Path('D:/FUBA_AUTHOR_MODELS_20261115');refs=read(source/'SOURCE_FREEZE.json')['files']
    for name in ['upstream/utils/comm_utils.py','upstream/utils/dba_attack_utils.py']:assert sha(source/name)==refs[name]
    tree=ast.parse((source/'upstream/utils/comm_utils.py').read_text(encoding='utf-8'))
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['test','attack_dba']]
    assert len(nodes)==2;env={'torch':torch}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'author_functions','exec'),env)
    triggers={};exec(compile((source/'upstream/utils/dba_attack_utils.py').read_text(encoding='utf-8'),'author_triggers','exec'),triggers)
    spec=importlib.util.spec_from_file_location('author_Net',ROOT/'inputs/author_model.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    from torchvision.datasets import MNIST
    profile=read(ROOT/'inputs/PROFILE.json');splits=read(ROOT/'inputs/SPLIT.json')['indices']
    data=MNIST(profile['data_root'],train=True,download=False)
    validation={}
    for c in range(4):
        indices=torch.tensor(splits[c])[torch.randperm(3000,generator=torch.Generator().manual_seed(profile['partition_seed']+c))[:300]]
        vx=data.data[indices].cuda().float().unsqueeze(1)/255;vy=data.targets[indices].cuda()
        validation[c]=(torch.utils.data.DataLoader(torch.utils.data.TensorDataset(vx,vy),batch_size=512,shuffle=False,num_workers=0),int((vy!=8).sum()))
    model=mod.Net().cuda().eval();rows=[]
    arm='fullbatch'
    for entry in read(ROOT/'MANIFEST.json')['rounds']:
        assert sha(ROOT/entry['path'])==entry['sha256']
        bundle=torch.load(ROOT/entry['path'],weights_only=True,map_location='cpu')
        for role in bundle['roles']:
            c=role['client']
            if c>=4:continue
            models=[]
            for i in (2,3):
                p=role['phases'][i];assert sha(ROOT/p['path'])==p['sha256']
                models.append(torch.load(ROOT/p['path'],weights_only=True,map_location='cpu')['model'])
            embedding,rep=models;loader,non_target=validation[c]
            trigger=triggers['add_backdoor_all']
            points=[]
            for i in range(11):
                gamma=i/10
                state={k:.25*(bundle['incoming'][k]+gamma*(embedding[k]-bundle['incoming'][k]))+.75*rep[k] for k in embedding}
                model.load_state_dict(state,strict=True)
                ca=env['test'](model,loader,'cuda');asr=env['attack_dba'](model,loader,8,'cuda',trigger)
                cc,hits=round(ca*300/100),round(asr*non_target/100)
                saved=role['decision']['scores'][i]
                points.append({'gamma':gamma,'clean_correct':cc,'target_successes':hits,'non_target_N':non_target,
                               'exact':cc==saved['clean_correct'] and hits==saved['target_successes'] and non_target==saved['non_target_N']})
            passing=[p['gamma'] for p in points if 10*p['target_successes']<p['non_target_N']]
            selected=max(passing) if passing else 0.
            row={'arm':arm,'round':entry['round'],'client':c,'points':points,'selected_gamma':selected,
                 'exact':all(p['exact'] for p in points) and selected==role['decision']['gamma']}
            rows.append(row);write(ROOT/'gamma_independent'/f'{arm}_{entry["round"]:04d}_{c:02d}.json',row,True)
    assert len(rows)==4
    write(ROOT/'GAMMA_AUDIT.json',{'state':'passed' if all(r['exact'] for r in rows) else 'mismatch_preserved',
         'traces':4,'points':44,'validation_N':300,'evaluator':'original author functions; independent Eq3 state reconstruction; FP32 deterministic noTF32',
         'all_points_and_selected_gammas_exact':all(r['exact'] for r in rows),'rows':rows,'training':0},True)
    print(json.dumps({'traces':len(rows),'all_exact':all(r['exact'] for r in rows)}),flush=True)


if __name__=='__main__':main()
