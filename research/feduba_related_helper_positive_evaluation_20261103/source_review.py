"""Review source and unchanged model-loop arithmetic, no torch import."""
import ast,json,sys,traceback
from pathlib import Path
from eval_binding import ROOT,source_profile,read,sha

def model_loop(text):
    tree=ast.parse(text)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    return next(n for n in main.body if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='name')
def main():
    p=source_profile();assert read(ROOT/'SOURCE_PUBLICATION.json')['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    for n,d in p['reused_helpers'].items():assert sha(ROOT/n)==d==sha(Path(p['baseline_root'])/n),n
    files=list(ROOT.glob('*.py'))
    for f in files:ast.parse(f.read_text(encoding='utf-8'))
    for n in ['evaluate_pair.py','verify_pair_evaluation.py']:
        old=(Path(p['baseline_root'])/n).read_text(encoding='utf-8')
        new=(ROOT/n).read_text(encoding='utf-8').replace('EVAL_RUN_FREEZE.json','PAIR_EVAL_RUN_FREEZE.json')
        a=model_loop(old);b=model_loop(new)
        assert isinstance(b.iter,ast.List) and [x.value for x in b.iter.elts]==['attack']
        assert ast.dump(ast.Module(body=a.body,type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=b.body,type_ignores=[]),include_attributes=False),n
    e=read(ROOT/'EVAL_PROFILE.json');fu=read(ROOT/'FU_PROFILE.json')
    assert not e['launch_enabled'] and e['model_order']==['attack'] and e['primary_sample_forwards']==e['independent_sample_forwards']==20000
    assert e['primary_and_independent_each_forward_calls']==158 and e['N']==10000 and e['non_target_N']==9000 and e['target']==2
    assert fu['minimum_operational_latent_pair_gate']==read(Path(p['baseline_root'])/'FU_PROFILE.json')['minimum_operational_latent_pair_gate']
    old=(Path(p['baseline_root'])/'verify_pair_evaluation.py').read_text(encoding='utf-8');new=(ROOT/'verify_pair_evaluation.py').read_text(encoding='utf-8')
    assert old[old.index('    # Independently compare ratios'):old.index("    load(result['delta'])")]==new[new.index('    # Independently compare ratios'):new.index("    load(result['delta'])")]
    assert 'torch' not in sys.modules
    value={'state':'passed_new_attack_only_eval_review_source','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'python_AST_files':len(files),'exact_reused_helper_files':len(p['reused_helpers']),'primary_and_independent_model_loop_bodies_AST_exact':True,'new_models_only':['attack'],'each_sample_forwards':20000,'each_calls':158,'original_six_gate_integer_code_exact':True,'new_strict_CPU_models':3,'new_zero1_calls':3,'model_loads':0,'forwards':0,'actual_prepare_started':False}
    with (ROOT/'SOURCE_REVIEW_RESULT.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
    print(json.dumps(value))
if __name__=='__main__':
    try:main()
    except BaseException:
        with (ROOT/'SOURCE_REVIEW_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f)
        raise
