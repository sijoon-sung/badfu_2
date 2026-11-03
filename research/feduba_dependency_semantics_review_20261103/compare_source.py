"""Source-only semantic comparison of pinned saved dependency candidates."""
import ast,copy,difflib,hashlib,io,json,os,shutil,subprocess,sys,time,traceback,tokenize,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def exclusive(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def guard(p):
    from native_memory import memory_information
    from native_processes import processes
    start=time.monotonic();g=p['resource_guard']
    while True:
        m=memory_information();disk=shutil.disk_usage(ROOT).free
        gpu=subprocess.check_output(['C:/Windows/System32/nvidia-smi.exe','--query-gpu=utilization.gpu,memory.free,memory.used','--format=csv,noheader,nounits'],text=True).strip()
        util,free,used=[int(x.strip()) for x in gpu.split(',')]
        competitors=[r for r in processes() if r['ProcessId'] not in [os.getpid(),os.getppid()] and any(t.lower() in r['CommandLine'].lower() for t in p['known_training_process_tokens'])]
        ok=m['availableBytes']>=g['native_available_GiB']*2**30 and m['commitLimit']-m['committedBytes']>=g['commit_free_GiB']*2**30 and disk>=g['disk_free_GiB']*2**30 and util<=g['GPU_util_max'] and free>=g['GPU_free_MiB_min'] and used<=g['GPU_used_MiB_max'] and not competitors
        if ok:return {'memory':m,'disk_free_bytes':disk,'GPU':gpu,'competitors':0,'wait_seconds':time.monotonic()-start}
        assert time.monotonic()-start<g['max_wait_seconds'],'Admission guard timeout; no automatic retry'
        time.sleep(g['poll_seconds'])

class StripDocs(ast.NodeTransformer):
    def visit_Module(self,n):return self.clean(n)
    def visit_ClassDef(self,n):return self.clean(n)
    def visit_FunctionDef(self,n):return self.clean(n)
    def visit_AsyncFunctionDef(self,n):return self.clean(n)
    def clean(self,n):
        self.generic_visit(n)
        if n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant) and isinstance(n.body[0].value.value,str):n.body=n.body[1:]
        return n
def canonical(n):return ast.dump(StripDocs().visit(copy.deepcopy(n)),include_attributes=False)
def top(tree,name):return next((n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==name),None)
def method(n,name):return next((v for v in n.body if isinstance(v,ast.FunctionDef) and v.name==name),None) if isinstance(n,ast.ClassDef) else None
def compare(a,b):
    r={'both_present':a is not None and b is not None}
    if not r['both_present']:return r
    r['canonical_AST_exact']=canonical(a)==canonical(b)
    if isinstance(a,ast.ClassDef) and isinstance(b,ast.ClassDef):
        r['common_methods']={n:canonical(method(a,n))==canonical(method(b,n)) for n in sorted({v.name for v in a.body if isinstance(v,ast.FunctionDef)}&{v.name for v in b.body if isinstance(v,ast.FunctionDef)})}
    return r
def main():
    p=read(ROOT/'PROFILE.json');b=read(ROOT/'INPUT_BINDING.json');pub=read(ROOT/'RUN_PUBLICATION.json');f=read(ROOT/'SOURCE_FREEZE.json')
    assert ROOT==Path(p['execution_root']) and p['launch_enabled'] and list(sys.version_info[:3])==p['python_version']
    assert pub['state']=='published_actual_dependency_semantics_source_comparison_before_execution' and len(pub['commit'])==40 and pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    for n,h in f['files'].items():assert sha(ROOT/n)==h,n
    for m in [b['archive'],b['upstream_inventory_completion'],*b['reference_sources'].values()]:assert sha(m['path'])==m['sha256'] and Path(m['path']).stat().st_size==m['bytes']
    assert read(b['upstream_inventory_completion']['path'])['state']=='completed_bounded_source_only_review'
    exclusive('ONCE.json',{'pid':os.getpid(),'unix':time.time(),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json')});exclusive('ADMISSION.json',guard(p))
    texts={};trees={}
    with zipfile.ZipFile(b['archive']['path']) as z:
        for name,meta in b['source_members'].items():
            raw=z.read(name);assert len(raw)==meta['bytes'] and hashlib.sha256(raw).hexdigest()==meta['sha256']
            encoding,_=tokenize.detect_encoding(io.BytesIO(raw).readline);texts[name]=raw.decode(encoding)
            if name.endswith('.py'):trees[name]=ast.parse(texts[name],filename=name)
    refs={k:Path(m['path']).read_text(encoding='utf-8') for k,m in b['reference_sources'].items()}
    rt={k:ast.parse(v,filename=k) for k,v in refs.items() if k!='paperlinked_readme'}
    u=trees['FedUBA-code/utils.py'];model=trees['FedUBA-code/models/resnet.py'];names=['apply_noise_patch','poison_image','poison_image_label','concoct_dataset','sur_target_dataset']
    helper_comparisons={n:compare(top(u,n),top(rt['related_util'],n)) for n in names}
    model_names=['BasicBlock','Bottleneck','ResNet','ResNet18','ResNet18_201']
    model_comparisons={n:compare(top(model,n),top(rt['actual_model'],n)) for n in model_names}
    model_all_top_names=sorted({n.name for n in model.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}&{n.name for n in rt['actual_model'].body if isinstance(n,(ast.ClassDef,ast.FunctionDef))})
    model_common_all={n:compare(top(model,n),top(rt['actual_model'],n)) for n in model_all_top_names}
    body={'new_helpers':{n:ast.unparse(top(u,n)) for n in names},'new_model_top_level':{n.name:ast.unparse(n) for n in model.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))},'actual_RequestDataset':ast.unparse(top(rt['actual_core'],'RequestDataset')),'actual_MixedImages':ast.unparse(top(rt['actual_mixed'],'MixedImages')),'Fed_data_change_unified_diff':list(difflib.unified_diff(refs['paperlinked_data_change'].splitlines(),texts['FedUBA-code/Fed_data_change.py'].splitlines(),fromfile='paper-linked',tofile='history-archive',lineterm='')),'README_unified_diff':list(difflib.unified_diff(refs['paperlinked_readme'].splitlines(),texts['FedUBA-code/README.md'].splitlines(),fromfile='paper-linked',tofile='history-archive',lineterm=''))}
    exclusive('SOURCE_BODY_REVIEW.json',body)
    details={}
    for n in names:
        node=top(u,n);assert node is not None
        sig=method(node,'__init__') if isinstance(node,ast.ClassDef) else node
        details[n]={'line':node.lineno,'end_line':node.end_lineno,'arguments':ast.unparse(sig.args),'getitem_binary_operators':[type(v.op).__name__ for v in ast.walk(method(node,'__getitem__') or node) if isinstance(v,ast.BinOp)],'if_tests':[ast.unparse(v.test) for v in ast.walk(node) if isinstance(v,ast.If)]}
    assert 'torch' not in sys.modules and 'numpy' not in sys.modules
    for m in [b['archive'],b['upstream_inventory_completion'],*b['reference_sources'].values()]:assert sha(m['path'])==m['sha256']
    result={'state':'completed_pinned_dependency_semantics_source_comparison','helper_comparisons_to_related_Narcissus':helper_comparisons,'new_helper_source_details':details,'architecture_comparisons_to_actual_declared_model':model_comparisons,'all_common_model_top_level_definitions':model_common_all,'whole_model_module_canonical_AST_exact':canonical(model)==canonical(rt['actual_model']),'body_review_sha256':sha(ROOT/'SOURCE_BODY_REVIEW.json'),'body_review_publication':'DISLAB and local permitted source review only; not public-staged','Fed_data_change_diff_lines':len(body['Fed_data_change_unified_diff']),'README_diff_lines':len(body['README_unified_diff']),'owner_identity_certified':False,'new_code_adopted':False,'source_member_reads':4,'download_calls':0,'upstream_code_executions':0,'RNG_executions':0,'torch_imports':0,'model_tensor_real_data_loads':0,'forward_calls':0,'optimizer_steps':0,'old_finite_jobs_rerun':0,'overall_goal_complete':False}
    exclusive('RESULT.json',result);exclusive('COMPLETION.json',{'state':'completed_bounded_dependency_source_semantics_review','exit_code':0,'finished_unix':time.time(),'result_sha256':sha(ROOT/'RESULT.json'),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'overall_goal_complete':False})
    print(json.dumps({'state':result['state'],'helper_comparisons':helper_comparisons,'model_comparisons':model_comparisons}))
if __name__=='__main__':
    try:main()
    except BaseException:
        exclusive('FAILURE.json',{'state':'failed_preserved_no_retry','pid':os.getpid(),'traceback':traceback.format_exc()});raise
