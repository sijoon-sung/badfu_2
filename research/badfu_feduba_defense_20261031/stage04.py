"""Label/trigger-free block rollback selection, then separate evaluation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
import torch
import stage03 as core

HERE=Path(__file__).resolve().parent
OUT=HERE/'stage04'
core.OUT=OUT


def make_state(pre,post,mask):
    result={}
    for k,v in post.items():
        if k.startswith('model.fc.'):
            result[k]=v.clone();continue
        if k.startswith(('model.conv1.','model.bn1.')):block=0
        else:
            block=next((i for i in range(1,5) if k.startswith(f'model.layer{i}.')),None)
            assert block is not None,k
        result[k]=(pre[k] if mask&(1<<block) else v).clone()
    return result


def select_mask(rows):
    """Only public-proxy predictions and structural masks are inputs."""
    eligible=[r for r in rows if r['agreement']>=.98-1e-12 and
              min(r['teacher_class_agreement'])>=.95-1e-12 and r['KL']<=.02+1e-12]
    assert eligible and any(r['mask']==0 for r in eligible)
    return min(eligible,key=lambda r:(-r['restored_blocks'],r['KL'],r['disagree_n'],r['mask']))


def main():
    OUT.mkdir(exist_ok=True)
    frozen=core.read(HERE/'STAGE04_FREEZE.json')
    for n,h in frozen['files'].items():assert core.sha(HERE/n)==h,n
    assert core.sha(HERE/'stage03/RESULT.json')==core.read(HERE/'stage03/COMPLETED.json')['result_sha256']
    core.resource_guard()
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time()},f)
    info=core.read(HERE/'STAGE03_INPUTS.json')
    selection=json.loads(subprocess.check_output([sys.executable,info['selector'],
        'badfu.confirmed.s20261023.v1','--purpose','purification_pilot'],text=True,encoding='utf8'))
    core.write('SELECTED_CASE.json',selection)
    snap=Path(selection['source_root']);guard=selection['checkpoint_guard']
    assert core.sha(guard['manifest_path'])==guard['manifest_sha256']
    declared=core.read(guard['manifest_path'])
    assert core.sha(guard['loader_path'])==declared['files']['load_confirmed.py']['sha256']
    spec=importlib.util.spec_from_file_location('sealed_stage04',guard['loader_path'])
    sealed=importlib.util.module_from_spec(spec);spec.loader.exec_module(sealed)
    sealed.verify(snap,guard['manifest_sha256'])
    states={}
    for r,e in selection['server_inputs'].items():
        assert core.sha(e['path'])==e['sha256']
        s=torch.load(e['path'],map_location='cpu',weights_only=True)
        states[r]=s if e['payload_key'] is None else s[e['payload_key']]
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.cuda.set_per_process_memory_fraction(.25)
    assert core.sha(info['clean_path'])==info['clean_path_sha256']
    raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    split=core.read(HERE/'PROXY_SPLIT.json');fit=torch.tensor(split['fit_ids']);heldout=torch.tensor(split['heldout_ids'])
    proxy=raw['test_x'][fit]
    native={r:torch.load(HERE/'inputs'/('logits_'+r+'.pt'),weights_only=True).double() for r in states}
    model=sealed.model_class(snap)().cuda().eval()
    choices={};all_rows={}
    for pair,a,b in core.PAIRS:
        teacher=native[b][fit];probs=teacher.softmax(1);target=teacher.argmax(1)
        rows=[]
        for mask in range(32):
            state=make_state(states[a],states[b],mask)
            model.load_state_dict(state,strict=True)
            core.CURRENT_VARIANT=f'{pair}_proxy_mask{mask:02d}'
            features=core.extract(model,proxy).double()
            z=features@state['model.fc.weight'].double().T+state['model.fc.bias'].double()
            pred=z.argmax(1)
            kl=float((probs*(teacher.log_softmax(1)-z.log_softmax(1))).sum(1).mean())
            assert kl>=-1e-10
            rows.append({'mask':mask,'restored_blocks':mask.bit_count(),
               'agreement':float((pred==target).double().mean()),'disagree_n':int((pred!=target).sum()),
               'teacher_class_agreement':[float((pred[target==c]==c).double().mean()) if (target==c).any() else 1. for c in range(10)],
               'teacher_class_n':[int((target==c).sum()) for c in range(10)],'KL':max(0.,kl)})
        choice=select_mask(rows);choices[pair]=choice;all_rows[pair]=rows
        state=make_state(states[a],states[b],choice['mask'])
        torch.save(state,OUT/(pair+'_selected.pt'))
        core.write('PROXY_CANDIDATES.json',all_rows)
        core.write('SELECTION_BEFORE_TRIGGER.json',{'choices':choices,
                  'true_labels_used':False,'ASR_used':False,'actual_trigger_loaded':False,
                  'models':{p.name:core.sha(p) for p in OUT.glob('*_selected.pt')}})
        print(json.dumps({'selected':pair,**choice}),flush=True)
    selection_sha=core.sha(OUT/'SELECTION_BEFORE_TRIGGER.json')
    clean,y,attack=core.load_data(info)
    result={'state':'running','selection_sha256_before_trigger':selection_sha,'cases':{},
            'rule_uses_attack_metadata':False,'deletion_quality_checked':False}
    for pair,a,b in core.PAIRS:
        state=torch.load(OUT/(pair+'_selected.pt'),weights_only=True)
        model.load_state_dict(state,strict=True);core.CURRENT_VARIANT=pair+'_selected_full'
        fc=core.extract(model,clean).double();fa=core.extract(model,attack).double()
        z=fc@state['model.fc.weight'].double().T+state['model.fc.bias'].double()
        za=fa@state['model.fc.weight'].double().T+state['model.fc.bias'].double()
        metric=core.metrics(z,y,native[a],native[b],heldout)
        baseline=core.metrics(native[b],y,native[a],native[b],heldout)
        drops=[u-v for u,v in zip(baseline['class_CA_pct'],metric['class_CA_pct'])]
        row={'choice':choices[pair],'heldout_clean':metric,
             'full_clean_correct':int((z.argmax(1)==y).sum()),'clean_n':10000,
             'attack_target_n':int((za.argmax(1)==0).sum()),'attack_n':9000,
             'ASR_pct':100*float((za.argmax(1)==0).double().mean()),
             'overall_drop_pp':baseline['CA_pct']-metric['CA_pct'],'worst_class_drop_pp':max(drops)}
        row['necessary_utility_gate']=(row['overall_drop_pp']<=.5+1e-10 and max(drops)<=2+1e-10 and
            (not pair.startswith('benign') or metric['beneficial_kept_fraction']>=.9))
        result['cases'][pair]=row;core.write('RESULT.json',result)
        assert core.sha(OUT/'SELECTION_BEFORE_TRIGGER.json')==selection_sha
    sealed.verify(snap,guard['manifest_sha256'])
    result.update(state='completed',necessary_gate_passed=all(v['necessary_utility_gate'] for v in result['cases'].values()) and
                  result['cases']['attack_cover850']['ASR_pct']<=10.,finished_unix=time.time())
    core.write('RESULT.json',result)
    core.write('COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),
           'freeze_sha256':core.sha(HERE/'STAGE04_FREEZE.json'),
           'files':{p.name:core.sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
    print('STAGE04_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);core.write('FAILURE.json',{'traceback':traceback.format_exc()});raise
