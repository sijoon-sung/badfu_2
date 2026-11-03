"""Review only persisted control-flow/numeric prefix evidence; original verifier remains failed."""
import ast,json,os,traceback
from fractions import Fraction
from pathlib import Path
from binding import ROOT,read,sha,profile

def main():
 p=profile();e=Path(p['evaluation_root'])
 assert not (e/'PAIR_EVAL_VERIFIED.json').exists() and not (e/'COMPLETION.json').exists() and not (e/'EXPORT_ONCE.json').exists()
 failure=read(e/'PAIR_EVAL_AUDIT_FAILURE.json');state=read(e/'PAIR_EVAL_AUDIT_STATE.json');once=read(e/'PAIR_EVAL_AUDIT_ONCE.json');result=read(e/'PAIR_EVAL_RESULT.json')
 assert failure['traceback'].endswith("KeyError: 'receipts'\n") and 'line 147, in main' in failure['traceback']
 assert failure['pid']==state['pid']==once['pid']
 assert state['model']=='attack' and state['batch']==79 and state['actual_forward_calls']==158 and state['max_logit_abs_error']==0
 assert result['actual_forward_calls']==158 and result['actual_sample_forwards']==20000
 tree=ast.parse((e/'verify_pair_evaluation.py').read_text(encoding='utf-8'))
 main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
 loop=next(n for n in main.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='name')
 receipt=next(n for n in main.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='verified' for t in n.targets))
 assert isinstance(loop.iter,ast.List) and [n.value for n in loop.iter.elts]==['attack']
 assert loop.end_lineno<receipt.lineno
 assert any(isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id=='inputs' and isinstance(n.slice,ast.Constant) and n.slice.value=='receipts' and n.lineno==147 for n in ast.walk(receipt))
 assert any(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='inputs' for t in n.targets) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='load' for n in ast.walk(loop))
 loop_text=ast.unparse(loop);assert "assert values == result['models'][name]" in loop_text and 'assert torch.equal' in loop_text and 'assert torch.allclose' in loop_text
 between=main.body[main.body.index(loop)+1:main.body.index(receipt)]
 assert any(isinstance(n,ast.Assert) and "calls == result['actual_forward_calls'] == 158" in ast.unparse(n) for n in between)
 assert any(isinstance(n,ast.Assert) and "checks == gate['checks']" in ast.unparse(n) for n in between)
 assert not any(isinstance(n,(ast.Return,ast.Try)) for n in between)
 term=read(ROOT/'FAILED_EVALUATION_TERMINAL_OBSERVATION.json');assert term['task']['state']=='Ready' and term['task']['last_result']==1 and not term['processes']
 rows=result['models'];limits=read(e/'FU_PROFILE.json')['minimum_operational_latent_pair_gate']
 ca={k:Fraction(100*v['clean_correct'],v['N']) for k,v in rows.items()};asr={k:Fraction(100*v['triggered_target_hits'],v['non_target_N']) for k,v in rows.items()}
 checks={'pre_ASR':asr['pre']<=limits['pre_ASR_max_pct'],'attack_ASR':asr['attack']>=limits['attack_ASR_min_pct'],'attack_minus_pre':asr['attack']-asr['pre']>=limits['attack_minus_pre_ASR_min_pp'],'attack_minus_benign':asr['attack']-asr['benign']>=limits['attack_minus_benign_FU_ASR_min_pp'],'all_three_CA':min(ca.values())>=limits['all_three_CA_min_pct'],'both_post_CA_drop':max(ca['pre']-ca['benign'],ca['pre']-ca['attack'])<=limits['post_CA_drop_max_pp']}
 assert checks==result['minimum_operational_gate']['checks'] and not all(checks.values())
 out={'state':'confirmed_completed_numeric_comparison_prefix_original_writer_failure_preserved','original_primary_result_sha256':sha(e/'PAIR_EVAL_RESULT.json'),'original_independent_failure_sha256':sha(e/'PAIR_EVAL_AUDIT_FAILURE.json'),'original_independent_source_sha256':sha(e/'verify_pair_evaluation.py'),'last_saved_batch':79,'original_independent_actual_calls':158,'original_independent_actual_sample_forwards_from_frozen_source':20000,'max_logit_abs_error_in_saved_running_max':0.0,'traceback_reached_receipt_construction_after_all_comparisons_counts_and_gate_assertions':True,'original_VERIFIED_exists':False,'original_verifier_completed_successfully':False,'original_task_exit':1,'models_from_primary_result_with_original_asserted_independent_equality':rows,'minimum_operational_gate':result['minimum_operational_gate'],'new_inference_calls':0,'new_tensor_payload_reads':0,'new_counts_inference':False,'not_a_new_independent_model_replay':True,'overall_goal_complete':False}
 with (ROOT/'PREFIX_REVIEW_RESULT.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps({'state':out['state'],'models':rows,'original_verifier_completed_successfully':False,'new_inference_calls':0}))
if __name__=='__main__':
 try:main()
 except BaseException:
  with (ROOT/'PREFIX_REVIEW_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f)
  raise
