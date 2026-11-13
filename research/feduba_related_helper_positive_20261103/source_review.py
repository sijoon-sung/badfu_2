"""Source-only review of one sign change; no torch import or model calculation."""
import ast,json,sys,traceback
from pathlib import Path
from pair_binding import ROOT,source_profile,read,sha

def main():
    p=source_profile();assert read(ROOT/'SOURCE_PUBLICATION.json')['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    original=Path(p['baseline_root'])
    for name,meta in read(ROOT/'COPY_PROVENANCE.json')['unchanged_files'].items():
        assert sha(ROOT/name)==sha(original/name)==meta['sha256'],name
    old=(original/'core.py').read_text(encoding='utf-8');new=(ROOT/'core.py').read_text(encoding='utf-8')
    new=new.replace('Related Narcissus-helper positive-sign interpretation; differs from paper Eq.8 minus.','Eq.8 replacement of selected owned images, preserving labels and dataset size.')
    assert new.count('sign=1, clip=True')==1
    assert new.replace('sign=1, clip=True','sign=-1, clip=True')==old
    old=(original/'fu_runner.py').read_text(encoding='utf-8');new=(ROOT/'fu_runner.py').read_text(encoding='utf-8')
    new=new.replace("    assert args.branch == 'attack', 'Only the newly declared positive attack branch is authorized'\n",'')
    new=new.replace("read(Path(read(ROOT / 'SOURCE_PROFILE.json')['baseline_root']) / 'FU_benign_VERIFIED.json')","read(ROOT / 'FU_benign_VERIFIED.json')")
    new=new.replace("read(ROOT / 'SIGN_CONTRACT_RESULT.json')","read(ROOT / 'FU_POLICY_CPU_RESULT.json')")
    assert new==old,'Only declared gate changes allowed; numeric loops exact'
    files=list(ROOT.glob('*.py'))
    for f in files:ast.parse(f.read_text(encoding='utf-8'))
    fu=read(ROOT/'FU_PROFILE.json');completed=read(original/'FU_LAUNCH_PROFILE.json')
    required={n.slice.value for f in ['fu_runner.py','verify_fu.py'] for n in ast.walk(ast.parse((ROOT/f).read_text(encoding='utf-8'))) if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Name) and n.value.id=='p' and isinstance(n.slice,ast.Constant) and isinstance(n.slice.value,str)}
    assert required.issubset(set(fu)|{'history_manifest_sha256','trigger_binding_sha256'}),sorted(required-set(fu))
    assert fu['history_global_payload_key'] is None and fu['history_role_payload_key']=='model'
    assert fu['minimum_operational_latent_pair_gate']==completed['minimum_operational_latent_pair_gate']
    assert p['fixed_selected_clients']==[2,3,5,7,9,12,13,16,18,19]
    assert sha(ROOT/'private_inputs/related_util.py')==p['inputs']['related_helper']['sha256']
    assert 'torch' not in sys.modules
    value={'state':'passed_sign_only_source_review','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'python_AST_files':len(files),'unchanged_byte_files':len(read(ROOT/'COPY_PROVENANCE.json')['unchanged_files']),'one_core_sign_literal_only_numeric_change':True,'runner_numeric_loops_exact':True,'required_FU_keys':sorted(required),'all_six_gates_unchanged':True,'model_loads':0,'forwards':0}
    with (ROOT/'SOURCE_REVIEW_RESULT.json').open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
    print(json.dumps(value))
if __name__=='__main__':
    try:main()
    except BaseException:
        with (ROOT/'SOURCE_REVIEW_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f)
        raise
