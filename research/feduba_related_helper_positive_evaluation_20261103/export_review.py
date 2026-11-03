"""New three-model CPU storage check and new readonly packet; old packet unchanged."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import json,shutil,time,traceback,zipfile
from pathlib import Path
import torch
import model_reference
from eval_binding import require_published_run
from runtime_common import ROOT,read,write,sha

def main():
    p,_=require_published_run();binding=read(ROOT/'INPUT_BINDING.json')
    result=read(ROOT/'PAIR_EVAL_RESULT.json');audit=read(ROOT/'PAIR_EVAL_VERIFIED.json')
    assert audit['state']=='passed' and audit['primary_result_sha256']==sha(ROOT/'PAIR_EVAL_RESULT.json')
    assert audit['independent_sample_forwards']==20000 and audit['independent_forward_calls']==158
    packet=Path(p['review_packet_root']);assert not packet.exists()
    with (ROOT/'EXPORT_ONCE.json').open('x',encoding='utf-8') as f:json.dump({'pid':os.getpid(),'started_unix':time.time(),'new_models_only':3},f)
    packet.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    def copy(src,name):
        dest=packet/name;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists();shutil.copyfile(src,dest);assert sha(src)==sha(dest);return dest
    def finite(v):
        if isinstance(v,torch.Tensor):assert bool(torch.isfinite(v).all())
        elif isinstance(v,dict):
            for a in v.values():finite(a)
        elif isinstance(v,(list,tuple)):
            for a in v:finite(a)
    typed=[];new_checks=[]
    for name,m in binding['new_review_models'].items():
        src=Path(m['path']);assert sha(src)==m['sha256']
        dest=copy(src,'models/'+name+'.pt');value=torch.load(dest,map_location='cpu',weights_only=True);finite(value)
        state=value if m['payload_key'] is None else value[m['payload_key']]
        model=model_reference.ResNet18().cpu().eval();model.load_state_dict(state,strict=True)
        with torch.inference_mode():out=model(torch.zeros((1,3,32,32),dtype=torch.float32))
        assert out.shape==(1,10) and bool(torch.isfinite(out).all())
        assert all(torch.equal(x.cpu(),state[k]) for k,x in model.state_dict().items())
        typed.append({'path':dest.relative_to(packet).as_posix(),'sha256':sha(dest),'payload_key':m['payload_key'],'CPU_strict_finite_zero1':True})
        new_checks.append(name);del model,state,value
    assert len(new_checks)==3 and not torch.cuda.is_initialized()
    old=binding['old_readonly_packet'];old_packet=Path(old['packet_root'])
    assert sha(old_packet/'DELIVERY_MANIFEST.json')==old['manifest_sha256'] and sha(old_packet/'DELIVERY_SEAL.json')==old['seal_sha256']
    training=Path(p['training_root'])
    train_names=set(read(training/'SOURCE_FREEZE.json')['files'])|{'SOURCE_FREEZE.json','SOURCE_PUBLICATION.json','RUN_PUBLICATION.json','RUN_FREEZE.json','FU_RUN_FREEZE.json','FU_LAUNCH_PROFILE.json','LAUNCH_PROFILE.json','PREPARATION_RESULT.json','FOUNDATION_INPUT_BINDING.json','BASELINE_INPUT_BINDING.json','SIGN_CONTRACT_RESULT.json','SOURCE_REVIEW_RESULT.json','SSS_RESULT.json','SSS_VERIFIED.json','SSS_REPLAY_COUNT_BINDING.json','FU_attack_RESULT.json','FU_attack_VERIFIED.json','COMPLETION.json','fu/attack/MANIFEST.json','fu/attack/events.jsonl'}
    for n in sorted(train_names):copy(training/n,'new_training/'+n)
    eval_names=set(read(ROOT/'SOURCE_FREEZE.json')['files'])|{'SOURCE_FREEZE.json','SOURCE_PUBLICATION.json','SOURCE_REVIEW_RESULT.json','RUN_PUBLICATION.json','EVAL_RUN_FREEZE.json','EVAL_LAUNCH_PROFILE.json','INPUT_BINDING.json','PREPARATION_RESULT.json','UPSTREAM_TERMINAL_CHECK.json','PAIR_EVAL_RESULT.json','PAIR_EVAL_VERIFIED.json'}
    for n in sorted(eval_names):copy(ROOT/n,'new_evaluation/'+n)
    for src in sorted((ROOT/'pair_evaluation').rglob('*')):
        if src.is_file():
            dest=copy(src,'new_evaluation/pair_evaluation/'+src.relative_to(ROOT/'pair_evaluation').as_posix())
            if src.suffix=='.pt':typed.append({'path':dest.relative_to(packet).as_posix(),'sha256':sha(dest),'payload_key':None,'storage_validation':'primary_and_independent_full_input_logit_validation_reused_no_extra_load'})
    scope={'new_CPU_model_checks':new_checks,'new_zero1_calls':3,'old_models_CPU_reloaded_or_reinferred':0,'old_packet_reference':binding['old_readonly_packet'],'all_new_raw200_trained200calibrated_roles_optimizer_RNG_remain':str(training),'packet_representative_new_owner_roles':[5,7],'standard_performance_reused_pre_benign_and_new_attack':result['models'],'minimum_operational_gate':result['minimum_operational_gate'],'detection_success_implied':False,'local_delivery_complete':False}
    write(packet/'SCOPE.json',scope)
    files={x.relative_to(packet).as_posix():{'sha256':sha(x),'bytes':x.stat().st_size} for x in sorted(packet.rglob('*')) if x.is_file()}
    write(packet/'MANIFEST.json',{'state':'new_positive_attack_readonly_review','files':files,'typed_payloads':typed,'scope':scope})
    outer=packet.with_name(packet.name+'_SEAL.json');assert not outer.exists()
    write(outer,{'packet_root':str(packet),'manifest_sha256':sha(packet/'MANIFEST.json'),'hashed_files':len(files),'typed_payloads':len(typed),'new_CPU_model_checks':3,'old_packet_unmodified':binding['old_readonly_packet']})
    for x in packet.rglob('*'):
        if x.is_file():x.chmod(x.stat().st_mode & ~0o222)
    outer.chmod(outer.stat().st_mode & ~0o222)
    archive=ROOT/'CHECKPOINT_REVIEW.zip';assert not archive.exists()
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for x in sorted(packet.rglob('*')):
            if x.is_file():z.write(x,packet.name+'/'+x.relative_to(packet).as_posix())
        z.write(outer,outer.name)
    write(ROOT/'REMOTE_CHECKPOINT_REVIEW.json',{'state':'completed_new_positive_attack_remote_review','packet_root':str(packet),'manifest_sha256':sha(packet/'MANIFEST.json'),'seal_sha256':sha(outer),'hashed_files':len(files),'typed_payloads':len(typed),'new_CPU_strict_finite_zero1_models':3,'old_model_checks_reused_not_reexecuted':True,'archive':{'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive)},'minimum_operational_gate':result['minimum_operational_gate'],'local_delivery_complete':False,'overall_goal_complete':False})
if __name__=='__main__':
    try:main()
    except BaseException:
        write(ROOT/'EXPORT_FAILURE.json',{'state':'failed_preserved','pid':os.getpid(),'traceback':traceback.format_exc()});raise
