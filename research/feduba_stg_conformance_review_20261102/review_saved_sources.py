"""Read stdlib AST/JSON and saved losses only; never imports torch or runs a model."""
from pathlib import Path
import ast,json,hashlib,datetime
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent.parent
T=BASE/'research/feduba_mixed_trigger_20261101'
S=BASE/'research/feduba_mixed_surrogate_20261101'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return ast.parse(p.read_text(encoding='utf-8'))
def func(t,n):return next(x for x in t.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))and x.name==n)
def calls(t,fn):
    return [x.lineno for x in ast.walk(t)if isinstance(x,ast.Call)and ast.unparse(x.func)==fn]
def assign(t,name):
    return next(x for x in ast.walk(t)if isinstance(x,ast.Assign)and any(isinstance(v,ast.Name)and v.id==name for v in x.targets))
def main():
    up=ROOT/'private_inputs/upstream_trigger_generate_function.py';raw=up.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='bb5096dbb192fa8d5cffa7fc9d97559d15157127'
    assert sha(up)=='53e7743598665a9f36c11530b9381261f3c7ce6cc1d517eac9706822d944fd06'
    sf=read(T/'SOURCE_FREEZE.json')
    for n,h in sf['files'].items():assert sha(T/n)==h,n
    source=read(T/'SOURCE_PROFILE.json');launch=read(T/'LAUNCH_PROFILE.json')
    assert launch['source_profile_sha256']==sha(T/'SOURCE_PROFILE.json')
    assert source['constants']['optimizer']=='SGD'
    assert source['constants']['theta_and_BN_mode']=='eval_frozen'
    a=func(tree(up),'trigger_generate')
    original_optimizer=assign(a,'batch_opt')
    assert ast.unparse(original_optimizer.value.func)=='torch.optim.RAdam'
    original_scheduler=assign(a,'trigger_scheduler')
    assert ast.unparse(original_scheduler.value.func)=='torch.optim.lr_scheduler.CosineAnnealingLR'
    assert calls(a,'poi_warm_up_model.train') and not calls(a,'poi_warm_up_model.eval')
    entry=func(tree(T/'mixed_cpu_trigger.py'),'main')
    executed_optimizer=assign(entry,'optimizer')
    assert ast.unparse(executed_optimizer.value.func)=='torch.optim.SGD'
    assert calls(entry,'projected_sgd_batch')
    assert not calls(entry,'optimizer.step') and not calls(entry,'scheduler.step')
    helper=func(tree(T/'stg_training.py'),'projected_sgd_batch')
    assert calls(helper,'core.trigger_step')
    core=func(tree(T/'core.py'),'trigger_step')
    assert calls(core,'optimizer.step') and calls(core,'delta.clamp_')
    binding=func(tree(T/'trigger_common.py'),'model_and_target')
    assert calls(binding,'model.eval')
    m=read(T/'MANIFEST.json');assert len(m['epochs'])==100
    assert all(v['examples']==200 and v['batches']==2 for v in m['epochs'])
    endpoint=read(S/'ENDPOINT_RESULT.json')
    teacher=launch['teacher_bindings']['teacher']['sha256']
    assert teacher==endpoint['fixed_teacher']['sha256']==m['teacher']['sha256']
    p=read(S/'PROFILE.json')
    assert p['endpoint_minimal_condition'].startswith('target correct > original0/200')
    old_BN=BASE/'research/feduba_stage_diagnosis_20261101/REPORT_KO.txt'
    evidence={
      'state':'completed_readonly_source_and_saved_log_review_no_model_queries',
      'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'related_cards':['R03','R02','N02','D08','D15'],
      'public_upstream':{'repo':'ity207/FedUBA','commit':'005959ab8a955f4dcf094930ce6953af8fee827b','file':'trigger_generate_function.py',
          'Git_blob_sha1':'bb5096dbb192fa8d5cffa7fc9d97559d15157127','bytes':len(raw),'sha256':sha(up),
          'URL':'https://github.com/ity207/FedUBA/blob/005959ab8a955f4dcf094930ce6953af8fee827b/trigger_generate_function.py',
          'trigger_optimizer':{'function':'torch.optim.RAdam','line':original_optimizer.lineno},
          'trigger_scheduler':{'function':'CosineAnnealingLR','line':original_scheduler.lineno},
          'warmup_train_call_lines':calls(a,'poi_warm_up_model.train'),
          'poi_model_eval_calls':[],'loop_stops_on_zero_gradient':bool(calls(a,'np.sum'))},
      'executed_path':[
          {'file':'mixed_cpu_trigger.py','function':'main','optimizer':'torch.optim.SGD','optimizer_line':executed_optimizer.lineno,'callee':'projected_sgd_batch','call_lines':calls(entry,'projected_sgd_batch')},
          {'file':'stg_training.py','function':'projected_sgd_batch','callee':'core.trigger_step','call_lines':calls(helper,'core.trigger_step')},
          {'file':'core.py','function':'trigger_step','optimizer_step_lines':calls(core,'optimizer.step'),'in_place_projection_lines':calls(core,'delta.clamp_')},
          {'file':'trigger_common.py','function':'model_and_target','model_eval_lines':calls(binding,'model.eval')}],
      'actual_source_and_profile':{'source_freeze_sha256':sha(T/'SOURCE_FREEZE.json'),'source_files_checked':len(sf['files']),
          'source_profile_sha256':sha(T/'SOURCE_PROFILE.json'),'launch_profile_sha256':sha(T/'LAUNCH_PROFILE.json'),
          'constants':{k:source['constants'][k]for k in ['epochs','batches','optimizer','alpha','momentum','weight_decay','projection_every_batch','theta_and_BN_mode','epsilon_model','epsilon_raw','seed']}},
      'teacher_endpoint':{'source_SHA256':sha(S/'ENDPOINT_RESULT.json'),'teacher_sha256':teacher,'summary':endpoint['summary'],
          'minimal_condition':p['endpoint_minimal_condition'],'condition_passed':endpoint['minimal_functional_condition_passed'],
          'does_not_prove_transfer_or_attack':endpoint['condition_is_not_sufficient_for_transfer_or_attack']},
      'completed_trigger_saved_training_log':{'manifest_SHA256':sha(T/'MANIFEST.json'),'epochs':len(m['epochs']),
          'first3':[{'epoch':v['epoch'],'loss':v['loss']}for v in m['epochs'][:3]],
          'last3':[{'epoch':v['epoch'],'loss':v['loss']}for v in m['epochs'][-3:]],
          'minimum_logged_loss':min(v['loss']for v in m['epochs']),
          'counts_derived_from_CE':False,'matched_fixed_input_improvement_claimed':False,
          'same_metric_as_victim_ASR':False,'new_model_queries':0},
      'causality_limits':{'known_declared_source_differences_confirmed':True,'single_cause_identified':False,
          'RAdam_or_BN_change_adopted':False,'old_teacher_BN_CPU8_rejection_preserved':True,
          'old_BN_report_sha256':sha(old_BN),'new_teacher_BN_comparison_performed':False,
          'missing_author_models_utils_concoct_body_recovered':False,
          'paper_Algorithm1_unique_implementation_resolved':False,
          'D08_D15_unknowntrigger_independent_detection_resolved':False},
      'model_loads':0,'forward_calls':0,'gradient_calls':0,'optimizer_steps':0,'completed_job_reexecution':False,
      'local_storage_or_registration_called':False,
      'input_file_sha256':{str(x.relative_to(BASE)).replace('\\','/'):sha(x)for x in [
          T/'mixed_cpu_trigger.py',T/'stg_training.py',T/'core.py',T/'trigger_common.py',T/'SOURCE_PROFILE.json',
          T/'LAUNCH_PROFILE.json',T/'MANIFEST.json',S/'PROFILE.json',S/'ENDPOINT_RESULT.json',
          BASE/'research/feduba_mixed_pair_eval_native_v2_20261101/PAPER_COMPARISON.txt',
          BASE/'research/feduba_reproduction_audit_20261031/CODE_PAPER_MATRIX.txt',
          BASE/'research/feduba_paper_implementation_20261031/CORE_CONTRACT.txt']}
    }
    with(ROOT/'EVIDENCE.json').open('x',encoding='utf-8',newline='\n')as f:json.dump(evidence,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'state':evidence['state'],'upstream_blob_verified':True,'executed_source_files':len(sf['files']),
        'optimizer_difference_confirmed':True,'mode_difference_confirmed':True,
        'completed_training_log_final_CE':m['epochs'][-1]['loss'],'causal_source_not_isolated':True,'new_model_queries':0}))
if __name__=='__main__':main()
