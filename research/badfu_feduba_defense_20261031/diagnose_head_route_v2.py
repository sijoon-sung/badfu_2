"""Public-only factorial function diagnosis; all evaluator truth stays unopened."""
import json,os,shutil,subprocess,time,traceback
from pathlib import Path
import torch
import torch.nn.functional as F
import stage05_common as s
from stage09 import proxy_metrics
core=s.core;OUT=s.HERE/'head_route_diagnosis_v2'


def write(name,obj):
    with (OUT/name).open('w',encoding='utf8') as f:json.dump(obj,f,indent=2);f.write('\n')


@torch.inference_mode()
def features(model,public,phase):
    parts=[];zs=[]
    handle=model.model.fc.register_forward_pre_hook(lambda _m,args:parts.append(args[0].detach().clone()))
    try:
        for i in range(0,len(public),32):
            zs.append(model(core.normalise(public[i:i+32])))
            write('PROGRESS.json',{'phase':phase,'completed':min(i+32,len(public)),'n':len(public)})
    finally:handle.remove()
    f=torch.cat(parts);z=torch.cat(zs).double()
    assert f.shape==(500,512) and z.shape==(500,10) and torch.isfinite(f).all() and torch.isfinite(z).all()
    return f,z


def classify(f,st):
    return torch.cat([F.linear(v,st['model.fc.weight'],st['model.fc.bias']) for v in f.split(32)]).double()


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources();freeze=core.read(s.HERE/'HEAD_ROUTE_V2_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    parent=core.read(s.HERE/'stage11/RESULT.json');audit=core.read(s.HERE/'stage11/INDEPENDENT_VERIFICATION.json')
    assert parent['state']=='completed' and audit['state']=='passed' and audit['scope']=='finished_pipeline'
    assert audit['root_result_snapshot_sha256']==core.sha(s.HERE/'stage11/RESULT.json')
    assert parent['cases']['attack_cover850']['state']=='failed_necessary_ASR'
    cpu=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Processor | Select-Object NumberOfLogicalProcessors,LoadPercentage | ConvertTo-Json -Compress'],text=True))
    if cpu.get('LoadPercentage') is None:
        fallback=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
            "Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -eq '_Total' | Select-Object PercentProcessorTime | ConvertTo-Json -Compress"],text=True))
        assert fallback.get('PercentProcessorTime') is not None,'no valid CPU load measurement'
        cpu['LoadPercentage']=fallback['PercentProcessorTime'];cpu['load_source']='PerfOS_Processor_total'
    else:cpu['load_source']='Win32_Processor'
    assert cpu['NumberOfLogicalProcessors']>=8 and 0<=cpu['LoadPercentage']<=60 and shutil.disk_usage(OUT).free>=4*1024**3
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu},f)
    tick=time.monotonic();selected,sealed,states=s.snapshot();cls=sealed.model_class(Path(selected['source_root']))
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    public=raw['test_x'][core.read(s.HERE/'PROXY_SPLIT.json')['fit_ids']]
    report={'state':'running','cases':{},'new_training':False,'actual_attack_inference':False,'diagnostic_only':True}
    for pair,role in [('benign_big19336','clean_big_post'),('attack_cover850','post')]:
        assert time.monotonic()-tick<900
        folder=s.HERE/'stage11'/pair;receipt=core.read(folder/'COMPLETED.json')
        decl=core.read(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json')
        entry=decl['raw_models']['all_class_disjoint'];path=folder/entry['path']
        assert entry['sha256']==receipt['files'][path.name]==core.sha(path)
        student=torch.load(path,map_location='cpu',weights_only=True);native=states[role]
        model=cls().eval();model.load_state_dict(native,strict=True);nf,nz=features(model,public,pair+'_native')
        assert core.tensor_digest(model.state_dict())==core.tensor_digest(native)
        model.load_state_dict(student,strict=True);sf,sz=features(model,public,pair+'_student')
        assert core.tensor_digest(model.state_dict())==core.tensor_digest(student)
        assert torch.equal(classify(nf,native),nz) and torch.equal(classify(sf,student),sz)
        saved_path=folder/'private_all_class_disjoint_proxy.pt';assert core.sha(saved_path)==receipt['files'][saved_path.name]
        saved=torch.load(saved_path,map_location='cpu',weights_only=True)
        oldraw=saved['candidate_logits'][saved['alphas'].index(1.)]
        differences={'native_maxabs':float((nz-saved['teacher_logits']).abs().max()),'raw_maxabs':float((sz-oldraw).abs().max())}
        assert differences['native_maxabs']<=1e-4 and differences['raw_maxabs']<=1e-4
        assert torch.equal(nz.argmax(1),saved['teacher_logits'].argmax(1)) and torch.equal(sz.argmax(1),oldraw.argmax(1))
        routes={'nativebody_nativehead':nz,'nativebody_studenthead':classify(nf,student),
                'studentbody_nativehead':classify(sf,native),'studentbody_studenthead':sz}
        metrics={name:proxy_metrics(nz,z) for name,z in routes.items()}
        payload=OUT/('private_'+pair+'_features.pt');torch.save({'native_features':nf,'student_features':sf,'routes':routes},payload)
        candidate={k:v.clone() for k,v in student.items()}
        for k in ['model.fc.weight','model.fc.bias']:candidate[k]=native[k].clone()
        cp=OUT/(pair+'_rawbody_posthead.pt');torch.save(candidate,cp)
        report['cases'][pair]={'routes':metrics,'saved_public_logit_differences':differences,
            'feature_payload_sha256':core.sha(payload),'counterfactual_model_sha256':core.sha(cp),
            'source_case_receipt_sha256':core.sha(folder/'COMPLETED.json')}
        write('RESULT.json',report)
        if not metrics['studentbody_nativehead']['eligible']:
            report['stopping_reason']='studentbody_nativehead_fails_public_utility_in_'+pair;break
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    report['state']='completed';write('RESULT.json',report)
    write('COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),'freeze_sha256':core.sha(s.HERE/'HEAD_ROUTE_V2_FREEZE.json')})
    print(json.dumps(report),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);write('FAILURE.json',{'traceback':traceback.format_exc()});raise
