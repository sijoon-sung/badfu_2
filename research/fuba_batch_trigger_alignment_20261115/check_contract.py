"""Actual source-statement oracle on synthetic CPU tensors, once."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import torch
from batch_trigger import compose_batch


ROOT=Path(__file__).resolve().parent


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    torch.set_num_threads(1)
    frozen=json.loads((ROOT/'FREEZE.json').read_text())
    for name,digest in frozen['files'].items():assert sha(ROOT/name)==digest
    source=(ROOT/'upstream/train_method_dba.py').read_bytes();meta=json.loads((ROOT/'SOURCE.json').read_text())
    assert hashlib.sha1(b'blob '+str(len(source)).encode()+b'\0'+source).hexdigest()==meta['git_blob']
    tree=ast.parse(source);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='defender_train')
    nodes=sorted([n for n in ast.walk(fn) if isinstance(n,ast.Assign) and 63<=n.lineno<=66],key=lambda n:n.lineno)
    assert len(nodes)==4
    code=compile(ast.Module(body=nodes,type_ignores=[]),'original_public_batch_construction','exec')
    trigger_path=Path('D:/FUBA_AUTHOR_MODELS_20261115/upstream/utils/dba_attack_utils.py')
    trigger_freeze=json.loads((trigger_path.parents[2]/'SOURCE_FREEZE.json').read_text())
    assert sha(trigger_path)==trigger_freeze['files']['upstream/utils/dba_attack_utils.py']
    trigger_env={};exec(compile(trigger_path.read_text(),'original_public_DBA_triggers','exec'),trigger_env)
    inputs=torch.full((64,1,28,28),.2);labels=torch.arange(64)%10;rows=[]
    for role in range(5):
        seed=2100+role;generator=torch.Generator().manual_seed(seed);torch.manual_seed(seed)
        seen=[]
        for batch in range(2):
            env={'torch':torch,'inputs':inputs.clone(),'labels':labels.clone(),'config':SimpleNamespace(target_label=8),
                 'attack_func':trigger_env['add_backdoor_all' if role==4 else f'add_backdoor_{role+1}']}
            exec(code,env)
            transformed,targets,mask=compose_batch(inputs,labels,role,generator=generator)
            assert torch.equal(mask,env['mask']) and torch.equal(transformed,env['perturbed_inputs']) and torch.equal(targets,env['labels'])
            assert torch.equal(torch.get_rng_state(),generator.get_state())
            assert torch.equal(inputs,torch.full_like(inputs,.2)) and torch.equal(labels,torch.arange(64)%10)
            seen.append(mask);rows.append({'role':role,'batch':batch,'poisoned':int(mask.sum()),'source_exact':True})
        assert not torch.equal(seen[0],seen[1])
    result={'state':'passed','public_statement_lines':[63,64,65,66],'roles':5,'batches':10,'samples_per_batch':64,
            'rows':rows,'all_mask_image_label_RNG_exact':True,'CUDA_initialized':torch.cuda.is_initialized(),
            'real_data_training':0,'ASR_evaluation':0,'actual_FU':False,'full_run_authorized_by_this_contract':False,
            'source_git_blob':meta['git_blob'],'executed_files':frozen['files']}
    with (ROOT/'RESULT.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
