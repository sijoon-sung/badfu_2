"""Concurrent source-only AST/provenance review; no model, fixture or query replay."""
import ast
import json
from pathlib import Path
import sys
import traceback
from pair_binding import ROOT,FOUNDATION,source_profile,read,sha
def main():
    p=source_profile();assert not (ROOT/'SOURCE_REVIEW_RESULT.json').exists()
    files=list(ROOT.glob('*.py'))
    for f in files:ast.parse(f.read_text(encoding='utf-8'))
    for n,m in read(ROOT/'COPY_PROVENANCE.json')['unchanged'].items():assert sha(ROOT/n)==sha(Path(m['source']))==m['sha256'],n
    assert sha(FOUNDATION/'SOURCE_FREEZE.json')==p['foundation_source_freeze_sha256']
    assert sha(FOUNDATION/'RUN_FREEZE.json')==p['foundation_run_freeze_sha256']
    assert read(ROOT/'SSS_PROFILE.json')['launch_enabled'] is False
    assert read(ROOT/'SSS_PROFILE.json')['SSS_target_class_only']==2 and read(ROOT/'SSS_PROFILE.json')['request_budget']==125
    # All actual query/logit/score math remains the byte-identical observe_and_rank and core.
    old=Path('D:/FEDUBA_MIXED_PAIR_20261101')
    def function(path,name):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        return next(n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    assert ast.dump(function(ROOT/'sss_runner.py','query_backend'))==ast.dump(function(old/'sss_runner.py','query_backend'))
    # Preserve the exact two-CPU-batch replay loop and original numerical tolerances.
    def replay(path):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        return next(n for n in ast.walk(tree) if isinstance(n,ast.With) and any(isinstance(v,ast.Call) and isinstance(v.func,ast.Attribute) and v.func.attr=='inference_mode' for item in n.items for v in ast.walk(item.context_expr)))
    assert ast.dump(replay(ROOT/'verify_sss.py'))==ast.dump(replay(old/'verify_sss.py'))
    assert 'torch' not in sys.modules
    with (ROOT/'SOURCE_REVIEW_RESULT.json').open('x',encoding='utf-8') as f:
        json.dump({'state':'passed_fixed10_newSSS_source_only','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),
            'python_AST_files':len(files),'unchanged_files':len(read(ROOT/'COPY_PROVENANCE.json')['unchanged']),
            'query_backend_AST_exact':True,'CPU_two_batch_replay_loop_AST_exact':True,
            'foundation_source_and_run_freezes_exact':True,'new_model_loads':0,'new_forward_queries':0,
            'actual_preparation_or_query_started':False},f,indent=2)
if __name__=='__main__':
    try:main()
    except BaseException:
        with (ROOT/'SOURCE_REVIEW_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f,indent=2)
        raise
