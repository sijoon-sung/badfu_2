"""One source-only review before the new conditional inference."""
import ast,json,os,time,traceback
from common import ROOT,read,once,write,sha,source_check
def main():
    once('SOURCE_REVIEW_ONCE.json',{'pid':os.getpid(),'created':time.time()})
    p,b,old=source_check();files=[]
    for f in sorted(ROOT.glob('*.py')):ast.parse(f.read_text(encoding='utf-8'));files.append(f.name)
    tree=ast.parse((ROOT/'sign_eval.py').read_text(encoding='utf-8'))
    assert not [n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ['train','backward','step']]
    modelcalls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='model']
    assert len(modelcalls)==2
    subtractions=[n for n in ast.walk(tree) if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Sub) and ast.unparse(n)=='clean - delta * 1.5']
    assert len(subtractions)==2
    assert p['model_order']==['pre','benign','minus_attack','plus_attack'] and p['eval_sign']==-1
    assert (p['additional_primary_calls'],p['additional_independent_calls'],p['additional_primary_sample_forwards'],p['additional_independent_sample_forwards'])==(316,316,40000,40000)
    assert len(old['input_packets'])==79 and p['batch_size']==128 and p['target']==2 and p['non_target_N']==9000
    assert p['positive_forward_calls']==p['clean_forward_calls']==p['training_optimizer_steps']==0
    assert p['logit_atol']==1e-6 and p['logit_rtol']==1e-5 and not p['AMP'] and not p['TF32'] and p['deterministic']
    assert b['positive_rows']['minus_attack']['triggered_target_hits']==1244 and b['positive_rows']['plus_attack']['triggered_target_hits']==5287
    limits=read(b['receipts']['baseline_fu_profile']['path'])['minimum_operational_latent_pair_gate']
    assert limits=={'pre_ASR_max_pct':20,'attack_ASR_min_pct':80,'attack_minus_pre_ASR_min_pp':50,'attack_minus_benign_FU_ASR_min_pp':50,'all_three_CA_min_pct':80,'post_CA_drop_max_pp':5}
    assert 'torch' not in __import__('sys').modules
    write('SOURCE_REVIEW_RESULT.json',{'state':'passed_source_only_sign_diagnosis_review','parsed_python_files':files,'fixed_four_endpoint_SHA_bound':True,'two_fixed_negative_input_expressions':True,'model_calls_one_per_batch_each_mode':True,'no_train_backward_optimizer_calls':True,'original_limits_unchanged':limits,'positive_clean_reinference':False,'model_loads':0,'forward_calls':0,'torch_imports':0})
    print('Source-only review passed; no tensors or models loaded')
if __name__=='__main__':
    try:main()
    except BaseException:
        write('SOURCE_REVIEW_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
