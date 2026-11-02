"""Source/metadata validation only, no torch import or finite fixture replay."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
from foundation_binding import ROOT,read,sha,source_profile
from native_memory import memory_information
from native_processes import processes

def normalized(text,selector):
    tree=ast.parse(text)
    class Normalize(ast.NodeTransformer):
        def visit_ImportFrom(self,node):
            return None if node.module=='foundation_binding' else node
        def visit_Expr(self,node):
            if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='require_actual_foundation':return None
            return self.generic_visit(node)
        def visit_Assign(self,node):
            if any(isinstance(t,ast.Name) and t.id==selector for t in node.targets):node.value=ast.Constant(value='participant_selector_only')
            return self.generic_visit(node)
    return ast.dump(Normalize().visit(tree),include_attributes=False)

def main():
    p=source_profile();assert not (ROOT/'SOURCE_CHECK_RESULT.json').exists()
    for path in ROOT.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'))
    for n,s in p['reused_helpers'].items():assert sha(ROOT/n)==sha(Path(p['old_foundation_root'])/n)==s,n
    for v in p['inputs'].values():assert sha(v['path'])==v['sha256'],v['path']
    for n,selector in [('clean_fl_runner.py','clients'),('verify_clean_fl.py','expected')]:
        old=(Path(p['old_foundation_root'])/n).read_text(encoding='utf-8')
        new=(ROOT/n).read_text(encoding='utf-8')
        assert normalized(old,selector)==normalized(new,selector),n
    tree=ast.parse(Path(p['inputs']['upstream_main']['path']).read_text(encoding='utf-8'))
    selected=[ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='selected_clients' for t in n.targets)]
    assert selected==[p['fixed_selected_clients']]==[[2,3,5,7,9,12,13,16,18,19]]
    cp=read(ROOT/'CLEAN_FL_PROFILE.json')
    assert cp['fixed_selected_clients']==p['fixed_selected_clients'] and cp['attack_owners']==[5,7]
    assert [cp[k] for k in ['rounds','local_epochs','batch_size','clients','clients_per_round']]==[20,10,128,20,10]
    assert (cp['local_lr'],cp['momentum'],cp['weight_decay'],cp['seed'],cp['partition_seed'])==(.01,.9,0,42,42)
    memory=memory_information()
    assert memory['availableBytes']>=8*2**30 and memory['commitLimit']-memory['committedBytes']>=16*2**30
    raw=subprocess.check_output(['C:/Windows/System32/nvidia-smi.exe','--query-gpu=utilization.gpu,memory.free,memory.used','--format=csv,noheader,nounits'],text=True).strip()
    util,free,used=[int(v.strip()) for v in raw.split(',')]
    assert util<=5 and free>=4000 and used<=6000
    peers=[r for r in processes() if r['ProcessId'] not in [os.getpid(),os.getppid()] and any(t in r['CommandLine'].lower() for t in p['known_training_process_tokens'])]
    assert not peers and shutil.disk_usage(ROOT).free>=80*2**30
    assert 'torch' not in sys.modules
    with (ROOT/'SOURCE_CHECK_RESULT.json').open('x',encoding='utf-8') as f:
        json.dump({'state':'passed_fixed10_source_and_metadata','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),
            'python_AST_files':len(list(ROOT.glob('*.py'))),'clean_runner_and_independent_verifier_AST_exact_except_declared_selector_and_publication_binding':True,
            'public_default_fixed_clients_exact':True,'fixed_selected_clients':selected[0],
            'memory':memory,'GPU':{'util':util,'free':free,'used':used},'competing_trainers':0,
            'model_loads':0,'model_forwards':0,'completed_fixture_rerun':False},f,indent=2)
if __name__=='__main__':
    try:main()
    except BaseException:
        with (ROOT/'SOURCE_CHECK_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f,indent=2)
        raise
