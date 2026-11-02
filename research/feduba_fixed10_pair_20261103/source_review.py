"""Concurrent source/required-profile-field review; no model or GPU query."""
import ast
import json
from pathlib import Path
import sys
import traceback
from pair_binding import ROOT,source_profile,read,sha
def main():
    p=source_profile();assert not (ROOT/'SOURCE_REVIEW_RESULT.json').exists()
    files=list(ROOT.glob('*.py'))
    for f in files:ast.parse(f.read_text(encoding='utf-8'))
    for n,d in p['reused_helpers'].items():assert sha(ROOT/n)==sha(Path(p['prior_pair_root'])/n)==d,n
    fu=read(ROOT/'FU_PROFILE.json');old=read(p['inputs']['original_FU_actual_profile']['path'])
    for k in ['history_global_payload_key','history_role_payload_key']:assert k in fu and fu[k]==old[k]
    required={node.slice.value for n in ['fu_runner.py','verify_fu.py'] for node in ast.walk(ast.parse((ROOT/n).read_text())) if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and node.value.id=='p' and isinstance(node.slice,ast.Constant) and isinstance(node.slice.value,str)}
    assert required.issubset(set(fu)|{'history_manifest_sha256','trigger_binding_sha256'}),required-set(fu)
    assert read(ROOT/'PAIR_EVAL_PROFILE.json')['launch_enabled'] is False and fu['launch_enabled'] is False
    assert fu['minimum_operational_latent_pair_gate']==old['minimum_operational_latent_pair_gate']
    for root,key,n in [(Path(p['foundation_root']),'foundation_source_freeze_sha256','SOURCE_FREEZE.json'),(Path(p['foundation_root']),'foundation_run_freeze_sha256','RUN_FREEZE.json'),(Path(p['sss_root']),'SSS_source_freeze_sha256','SOURCE_FREEZE.json')]:assert sha(root/n)==p[key]
    assert p['fixed_selected_clients']==[2,3,5,7,9,12,13,16,18,19]
    assert 'torch' not in sys.modules
    with (ROOT/'SOURCE_REVIEW_RESULT.json').open('x',encoding='utf-8') as f:
        json.dump({'state':'passed_fixed10_pair_source_only','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),
            'python_AST_files':len(files),'exact_reused_files':len(p['reused_helpers']),
            'FU_runner_verifier_and_primary_independent_evaluator_bytes_unchanged':True,
            'required_FU_profile_keys':sorted(required),'history_global_payload_key':fu['history_global_payload_key'],
            'history_role_payload_key':fu['history_role_payload_key'],'all_original_six_gates_unchanged':True,
            'new_foundation_and_SSS_freezes_exact':True,'model_loads':0,'model_forwards':0,'actual_prepare_training_started':False},f,indent=2)
if __name__=='__main__':
    try:main()
    except BaseException:
        with (ROOT/'SOURCE_REVIEW_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f,indent=2)
        raise
