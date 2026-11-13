"""Bind one newly completed plus model and unchanged audited baseline metadata, no torch."""
import json,os,subprocess,sys,traceback
from pathlib import Path
from eval_binding import ROOT,read,sha,checked,source_profile

def once(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def meta(path):return {'path':str(path),'sha256':sha(path),'bytes':path.stat().st_size}
def main():
    p=source_profile();pub=read(ROOT/'SOURCE_PUBLICATION.json')
    assert pub['state']=='published_positive_new_attack_eval_review_source_before_prepare' and pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    assert read(ROOT/'SOURCE_REVIEW_RESULT.json')['state']=='passed_new_attack_only_eval_review_source'
    t=Path(p['training_root']);b=Path(p['baseline_root'])
    term=read(ROOT/'UPSTREAM_TERMINAL_CHECK.json')['task'];assert term['state']=='Ready' and term['last_result']==0 and term['native_process_count']==0 and term['level']=='Limited'
    assert sha(t/'SOURCE_FREEZE.json')==p['training_source_freeze_sha256'] and sha(t/'RUN_FREEZE.json')==p['training_run_freeze_sha256']
    for n in ['CONTROLLER_FAILURE.json','FU_attack_FAILURE.json','FU_attack_AUDIT_FAILURE.json']:assert not (t/n).exists()
    done=read(t/'COMPLETION.json');r=read(t/'FU_attack_RESULT.json');v=read(t/'FU_attack_VERIFIED.json')
    assert done['state']=='completed_positive_attack_FU20_and_independent_CPU_only' and done['result_sha256']==sha(t/'FU_attack_RESULT.json') and done['verified_sha256']==sha(t/'FU_attack_VERIFIED.json')
    assert r['state']=='completed_FU20' and v['state']=='passed' and r['after']==v['after']
    assert (v['rounds'],v['new_trained_roles'],v['actual_local_epochs'],v['actual_batches'])==(20,200,1000,20000) and len(v['history_hashes'])==420
    assert read(t/'FU_LAUNCH_PROFILE.json')['BEA_selected_images']=='clip(x+delta,-1,1)_after_training_augmentation'
    for m in p['baseline_receipts'].values():checked(m)
    baseline=read(b/'PAIR_EVAL_RESULT.json');assert read(b/'PAIR_EVAL_VERIFIED.json')['state']=='passed'
    old_review=read(b/'REMOTE_CHECKPOINT_REVIEW.json');old_packet=Path(old_review['packet_root'])
    assert sha(old_packet/'DELIVERY_MANIFEST.json')==old_review['manifest_sha256'] and sha(old_packet/'DELIVERY_SEAL.json')==old_review['seal_sha256']
    assert baseline['actual_sample_forwards']==60000 and baseline['actual_forward_calls']==474
    assert baseline['precision']=={'TF32':False,'AMP':False,'cudnn_benchmark':False,'deterministic':True}
    assert r['delta']==baseline['delta'] and r['SSS_result_sha256']==read(t/'LAUNCH_PROFILE.json')['selection_sha256']==p['reused_SSS_result_sha256']
    selected=json.loads(subprocess.check_output([sys.executable,'-B',str(Path(p['catalog_root'])/'select_case.py'),p['normal_case_id'],'--purpose','diagnostic'],text=True,encoding='utf-8'))
    assert selected['guard_state']=='all_snapshot_files_verified_on_this_host'
    def absolute(m,directory):
        m=dict(m);path=Path(m['path']);m['path']=str(path if path.is_absolute() else directory/path);checked(m);return m
    models={'pre':absolute(baseline['source_models']['pre'],b),'benign':absolute(baseline['source_models']['benign'],b),'attack':absolute(r['after'],t)}
    assert models['pre']['sha256']==selected['server_inputs']['pre']['sha256']
    manifest=read(t/'fu/attack/MANIFEST.json');assert sha(t/'fu/attack/MANIFEST.json')==r['history_manifest_sha256']
    new_review_models={'attack_after':models['attack']}
    for c in [5,7]:new_review_models['owner'+str(c)+'_last_trained']=absolute(next(x['checkpoint'] for x in manifest['rounds'][-1]['trained_roles'] if x['client']==c),t)
    receipts={'baseline_eval':meta(b/'PAIR_EVAL_RESULT.json'),'baseline_independent_eval':meta(b/'PAIR_EVAL_VERIFIED.json'),'baseline_remote_review':meta(b/'REMOTE_CHECKPOINT_REVIEW.json')}
    for n in ['SOURCE_FREEZE.json','RUN_FREEZE.json','COMPLETION.json','FU_attack_RESULT.json','FU_attack_VERIFIED.json','FU_LAUNCH_PROFILE.json','BASELINE_INPUT_BINDING.json']:receipts['new_training/'+n]=meta(t/n)
    once('PREPARE_ONCE.json',{'pid':os.getpid(),'model_loads':0,'forwards':0})
    once('INPUT_BINDING.json',{'state':'new_plus_attack_and_explicit_completed_pre_benign_evidence_bound','receipts':receipts,'source_models':models,'delta':r['delta'],'new_models_inference':['attack'],'pre_benign_evidence_reused_not_reinferred':True,'new_review_models':new_review_models,'old_readonly_packet':read(b/'REMOTE_CHECKPOINT_REVIEW.json'),'same_standard_route_as_baseline':True,'all_six_gates_unchanged':True})
    ep=read(ROOT/'EVAL_PROFILE.json');ep.update(launch_enabled=True,stage='actual_new_attack_only_evaluation_with_reused_pre_benign',trigger_binding_sha256=r['trigger_binding_sha256']);once('EVAL_LAUNCH_PROFILE.json',ep)
    once('PREPARATION_RESULT.json',{'state':'new_attack_only_eval_review_prepared_model0','attack_sha256':models['attack']['sha256'],'baseline_evaluation_sha256':receipts['baseline_eval']['sha256'],'new_primary_sample_forwards':20000,'new_independent_sample_forwards':20000,'each_calls':158,'new_CPU_review_models':3,'old_model_reinference_calls':0,'model_loads':0})
    files=dict(read(ROOT/'SOURCE_FREEZE.json')['files'])
    for n in ['SOURCE_FREEZE.json','SOURCE_REVIEW_RESULT.json','INPUT_BINDING.json','EVAL_LAUNCH_PROFILE.json','PREPARATION_RESULT.json','UPSTREAM_TERMINAL_CHECK.json']:files[n]=sha(ROOT/n)
    once('EVAL_RUN_FREEZE.json',{'state':'actual_positive_new_attack_eval_review_frozen_before_queries','files':files})
    assert 'torch' not in sys.modules
    print(json.dumps(read(ROOT/'PREPARATION_RESULT.json')))
if __name__=='__main__':
    try:main()
    except BaseException:
        once('PREPARE_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
