"""New once-only matched query-generator experiment; parent evaluator adapter."""
import json,os,shutil,time,traceback
from pathlib import Path
import torch
import stage05_common as s
import post_anchor_run as parent
from adaptive_query_method import ARMS,train_and_select
from sourcepair_pilot import cpu_guard,run_case as generate_bank
core=s.core;OUT=s.HERE/'adaptive_query_run'


def write(root,name,obj):
    p=root/name;t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n',encoding='utf8');os.replace(t,p)


def evaluate(*args,**kwargs):
    previous=parent.ARMS;parent.ARMS=ARMS.copy()
    try:return parent.evaluate(*args,**kwargs)
    finally:parent.ARMS=previous


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources();freeze=core.read(s.HERE/'ADAPTIVE_QUERY_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    contract=core.read(s.HERE/'ADAPTIVE_QUERY_OBJECTIVE_CONTRACT.json')
    assert contract['state']=='passed' and contract['method_sha256']==core.sha(s.HERE/'adaptive_query_method.py')
    audit=core.read(s.HERE/'post_anchor_run/INDEPENDENT_VERIFICATION.json')
    diagnosis=core.read(s.HERE/'post_anchor_diagnosis/RESULT.json')
    assert audit['state']=='passed' and audit['root_result_sha256']==core.sha(s.HERE/'post_anchor_run/RESULT.json')
    assert diagnosis['state']=='passed_saved_output_diagnosis' and diagnosis['parent_audit_sha256']==core.sha(s.HERE/'post_anchor_run/INDEPENDENT_VERIFICATION.json')
    cpu=cpu_guard();assert not torch.cuda.is_initialized() and shutil.disk_usage(OUT).free>=8*1024**3
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu,'arms':ARMS},f)
    selected,sealed,states=s.snapshot();cls=sealed.model_class(Path(selected['source_root']))
    info=core.read(s.HERE/'STAGE03_INPUTS.json');assert core.sha(info['clean_path'])==info['clean_path_sha256']
    raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    split=core.read(s.HERE/'PROXY_SPLIT.json');public=raw['test_x'][split['fit_ids']];held=torch.tensor(split['heldout_ids'])
    whole=time.monotonic();survivors=ARMS.copy()
    summary={'state':'running','large_passed_arms':[],'cases':{},'new_FL_seeds':0,'FedUBA_evaluated':False,
        'scope':'one_existing_BadFU_seed_matched_generator_refresh','parent_outputs_immutable':True}
    for pair,a,b in [('benign_big19336','clean_pre','clean_big_post'),('attack_cover850','pre','post'),('benign_same850','clean_pre','clean_post')]:
        folder=OUT/pair;folder.mkdir(exist_ok=False);tick=time.monotonic()
        def deadline():assert time.monotonic()-tick<3600 and time.monotonic()-whole<10800,'bounded profile runtime'
        hp=s.OUT/(pair+'_aligned_model.pt');assert core.sha(hp)==core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['models'][hp.name]
        teacher=torch.load(hp,map_location='cpu',weights_only=True)
        write(folder,'SOURCE_INPUTS.json',{'case_id':selected['case_id'],'purpose':'purification_pilot',
            'pre_role':a,'post_role':b,'post_sha256':selected['server_inputs'][b]['sha256'],'teacher_sha256':core.sha(hp)})
        bankroot=s.HERE/'sourcepair_pilot'/pair
        if not (bankroot/'COMPLETED.json').exists():
            assert pair=='benign_same850','never regenerate completed banks'
            bankroot=folder/'query_generation';bankroot.mkdir(exist_ok=False)
            generate_bank(pair,states[b],teacher,public,cls,bankroot,deadline)
        receipt=core.read(bankroot/'COMPLETED.json');bp=bankroot/'private_teacher_source_bank.pt';ip=bankroot/'private_initials.pt'
        dec=train_and_select(states[b],teacher,public,cls,folder,deadline,bp,ip,receipt['files'][bp.name],receipt['files'][ip.name])
        report=evaluate(pair,a,b,states,dec,cls,folder,info,raw['test_y'].long(),held,survivors,deadline)
        write(folder,'COMPLETED.json',{'result_sha256':core.sha(folder/'RESULT.json'),
            'bank_receipt_path':str(bankroot/'COMPLETED.json'),'bank_receipt_sha256':core.sha(bankroot/'COMPLETED.json'),
            'files':{p.name:core.sha(p) for p in folder.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
        summary['cases'][pair]=report
        survivors=[arm for arm in survivors if report.get('cases',{}).get(arm,{}).get('necessary_gate',False)]
        if pair=='benign_big19336':summary['large_passed_arms']=survivors.copy()
        write(OUT,'RESULT.json',summary);sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
        if not survivors:break
    summary['method_necessary_gates']={arm:all(summary['cases'].get(pair,{}).get('cases',{}).get(arm,{}).get('necessary_gate',False)
        for pair in ['benign_big19336','attack_cover850','benign_same850']) for arm in ARMS}
    assert not torch.cuda.is_initialized()
    summary.update(state='completed',same850_executed='benign_same850' in summary['cases'],CUDA_initialized=False,finished_unix=time.time())
    write(OUT,'RESULT.json',summary);write(OUT,'COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),
        'source_freeze_sha256':core.sha(s.HERE/'ADAPTIVE_QUERY_FREEZE.json')})
    print('ADAPTIVE_QUERY_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True);write(OUT,'FAILURE.json',{'traceback':traceback.format_exc()});raise
