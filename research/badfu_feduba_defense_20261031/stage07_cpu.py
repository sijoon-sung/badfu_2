"""CPU numerical profile for the fixed H5/H6 deleted-member audit."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import traceback
import numpy as np
import torch
import stage05_common as s
import stage05_delete as d
core=s.core
OUT=s.HERE/'stage07_cpu'


@torch.inference_mode()
def extract(model,raw):
    f=[];handle=model.model.fc.register_forward_pre_hook(lambda _m,inputs:f.append(inputs[0].cpu()))
    try:
        for i in range(0,len(raw),32):
            model(core.normalise(raw[i:i+32]))
            if i%3200==0:core.write('PROGRESS.json',{'pid':os.getpid(),'n':len(raw),'completed':min(i+32,len(raw)),'time':time.time()})
    finally:handle.remove()
    z=torch.cat(f);assert z.shape==(len(raw),512) and torch.isfinite(z).all()
    assert not torch.cuda.is_initialized()
    return z


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources();core.OUT=OUT
    freeze=core.read(s.HERE/'STAGE07_CPU_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    cpu=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
        'Get-CimInstance Win32_Processor | Select-Object NumberOfLogicalProcessors,LoadPercentage | ConvertTo-Json -Compress'],text=True))
    assert cpu['NumberOfLogicalProcessors']>=8 and cpu['LoadPercentage']<=60 and not torch.cuda.is_initialized()
    assert not (s.OUT/'DELETE_STARTED.json').exists(),'GPU audit already started'
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU_guard':cpu,'threads':2},f)
    selected,sealed,states=s.snapshot();core.write('SELECTED_CASE.json',selected)
    # Every head existed before this audit; no new candidate selection is allowed.
    fitreceipt=core.read(s.OUT/'FIT_COMPLETED.json')
    assert core.sha(s.OUT/'FIT_RESULT.json')==fitreceipt['result_sha256']
    assert core.sha(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')==fitreceipt['files']['CANDIDATES_BEFORE_EVALUATION.json']
    info=core.read(s.HERE/'STAGE03_INPUTS.json')
    clean,y,trigger=core.load_data(info)
    model=sealed.model_class(selected['source_root'])().eval()
    fixtures={};seconds=0.
    for role in states:
        pair,pre=next((pair,role==a) for pair,a,b in core.PAIRS if role in [a,b])
        reference=s.feature_cache(pair,pre);model.load_state_dict(states[role],strict=True)
        checks={}
        for key,raw in [('clean',clean[:32]),('attack',trigger[:32])]:
            start=time.monotonic();features=extract(model,raw);seconds+=time.monotonic()-start
            z=s.logits(features,s.head(states[role]));ref=s.logits(reference[key][:32],s.head(states[role]))
            checks[key]={'max_feature_error':float((features-reference[key][:32]).abs().max()),
                         'max_logit_error':float((z-ref).abs().max()),'top1_mismatches':int((z.argmax(1)!=ref.argmax(1)).sum())}
        fixtures[role]=checks;core.write('CPU_GPU_FIXTURE.json',fixtures)
        assert all(c['max_feature_error']<=.003 and c['max_logit_error']<=.002 and c['top1_mismatches']==0 for c in checks.values()),(role,checks)
    estimate=seconds/320*(2*(9668+850+850))
    core.write('TIMING_GATE.json',{'fixture_forward_seconds':seconds,'estimated_member_forward_seconds':estimate,'limit_seconds':1200})
    assert estimate<=1200
    datasets,extra=d.data()
    result={'state':'running','cases':{},'profile':'CPU2_FP32_NCHW32_noCUDA_v1','formal_deletion_certificate':False,
            'source_freeze_sha256':core.sha(s.HERE/'STAGE07_CPU_FREEZE.json')}
    for pair,a,b in core.PAIRS:
        raw,labels,ids,key,ny=datasets[pair]
        complete=core.read(extra[key]['path'])
        assert hashlib.sha256(np.asarray(sorted(ids),dtype=np.int64).tobytes()).hexdigest()==complete['audit']['removed_indices_sha256']
        assert len(ids)==complete['audit']['removed_n'] and complete['checkpoint_sha256']==selected['server_inputs'][b]['sha256']
        member={}
        for pre,role in [(True,a),(False,b)]:
            model.load_state_dict(states[role],strict=True);member[pre]=extract(model,raw)
            assert core.tensor_digest(model.state_dict())==core.tensor_digest(states[role])
        path=OUT/('private_'+pair+'_member_features.pt')
        torch.save({'pre':member[True],'post':member[False],'labels':labels},path)
        before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
        methods=s.heads(pair,a,b,states)
        hp=s.HERE/'stage06'/(pair+'_head.pt')
        assert core.sha(hp)==core.read(s.HERE/'stage06/CANDIDATES_BEFORE_EVALUATION.json')[pair]['head_sha256']
        methods['H6']=(False,torch.load(hp,map_location='cpu',weights_only=True))
        reports={}
        for name,(pre,h) in methods.items():
            nonmember=(before if pre else after)['attack' if pair.startswith('attack') else 'clean']
            reports[name]=s.membership(s.logits(member[pre],h),labels,s.logits(nonmember,h),ny)
        base=reports['native_post']
        for name,row in reports.items():
            increases={score:{m:row['scores'][score][m]-base['scores'][score][m] for m in ['advantage','weighted_class_advantage']} for score in base['scores']}
            gap=abs(row['weighted_accuracy_gap'])-abs(base['weighted_accuracy_gap'])
            row['increase_over_post']=increases;row['absolute_accuracy_gap_increase']=gap
            row['necessary_deletion_audit_gate']=all(v<=.04+1e-12 for values in increases.values() for v in values.values()) and gap<=.02+1e-12
        result['cases'][pair]={'removed_n':len(ids),'removed_hash_matches_original_training':True,
            'private_features_sha256':core.sha(path),'variants':reports}
        core.write('RESULT.json',result)
        print(json.dumps({'pair':pair,'H5':reports['H5'],'H6':reports['H6']}),flush=True)
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    assert not torch.cuda.is_initialized()
    result.update(state='completed',finished_unix=time.time(),CUDA_initialized=False)
    core.write('RESULT.json',result)
    core.write('COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),
        'files':{p.name:core.sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
    print('STAGE07_CPU_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);core.OUT=OUT;core.write('FAILURE.json',{'traceback':traceback.format_exc()});raise
