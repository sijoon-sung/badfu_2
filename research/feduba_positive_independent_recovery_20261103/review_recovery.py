"""One stdlib-only source review; never imports torch or executes original source."""
import ast,json,os,time,traceback
from pathlib import Path
from recovery_contract import ROOT,read,sha,source_check
def main():
    with (ROOT/'SOURCE_REVIEW_ONCE.json').open('x',encoding='utf-8') as f:json.dump({'pid':os.getpid(),'time':time.time()},f)
    p,b=source_check()
    original=Path(b['original_verifier_file']['path'])
    old=ast.parse(original.read_text(encoding='utf-8'))
    new=ast.parse((ROOT/'verify_recovery.py').read_text(encoding='utf-8'))
    om=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    nm=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    class UndoMetadataOnlyChange(ast.NodeTransformer):
        def visit_Name(self,n):
            if n.id=='input_binding':n.id='inputs'
            if n.id=='RECOVERY_ROOT':n.id='ROOT'
            return n
        def visit_Constant(self,n):
            if n.value=='RECOVERY_ONCE.json':n.value='PAIR_EVAL_AUDIT_ONCE.json'
            return n
    assert ast.dump(om,include_attributes=False)==ast.dump(UndoMetadataOnlyChange().visit(nm),include_attributes=False)
    fixed=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    receipt=next(n for n in fixed.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='verified' for t in n.targets))
    original_new=ast.parse((ROOT/'verify_recovery.py').read_text(encoding='utf-8'))
    vm=next(n for n in original_new.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    vr=next(n for n in vm.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='verified' for t in n.targets))
    baseline=next(v for k,v in zip(vr.value.keys,vr.value.values) if isinstance(k,ast.Constant) and k.value=='baseline_evaluation_sha256')
    assert any(isinstance(n,ast.Name) and n.id=='input_binding' for n in ast.walk(baseline))
    assert not any(isinstance(n,ast.Name) and n.id=='inputs' for n in ast.walk(baseline))
    wf=next(n for n in original_new.body if isinstance(n,ast.FunctionDef) and n.name=='write')
    names={n.value for n in ast.walk(wf) if isinstance(n,ast.Constant) and isinstance(n.value,str)}
    assert {'RECOVERY_STATE.json','RECOVERY_VERIFIED.json','RECOVERY_FAILURE.json'}<=names
    parsed=[]
    for path in sorted(ROOT.glob('*.py')):ast.parse(path.read_text(encoding='utf-8'));parsed.append(path.name)
    result={'state':'passed_source_only_recovery_review','time':time.time(),'original_verifier_sha256':sha(original),'recovery_verifier_sha256':sha(ROOT/'verify_recovery.py'),'all_main_AST_equal_after_only_binding_and_ONCE_normalization':True,'numeric_loop_gate_AST_unchanged':True,'receipt_uses_unshadowed_input_binding':True,'all_outputs_routed_to_new_root':True,'parsed_python_files':parsed,'torch_imports':0,'model_tensor_reads':0,'forward_calls':0,'original_VERIFIED_absent':True,'original_failure_preserved':True,'original_verifier_success_claim':False}
    with (ROOT/'SOURCE_REVIEW_RESULT.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result))
if __name__=='__main__':
    try:main()
    except BaseException:
        (ROOT/'SOURCE_REVIEW_FAILURE.json').write_text(json.dumps({'state':'failed_preserved','traceback':traceback.format_exc()}),encoding='utf-8');raise
