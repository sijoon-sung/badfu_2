"""Model-free source conformance audit of a historical selector call site."""
import ast,hashlib,io,json,os,shutil,subprocess,sys,time,tokenize,traceback,zipfile
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


def fname(n):return ast.unparse(n.func)
def top(tree,name):return next((n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name),None)
def imports(tree):
    aliases={}
    for n in tree.body:
        if isinstance(n,ast.Import):
            for a in n.names:aliases[a.asname or a.name]=a.name
        if isinstance(n,ast.ImportFrom):
            for a in n.names:aliases[a.asname or a.name]=(n.module or '')+'.'+a.name
    return aliases
def resolved(name,aliases):
    first,sep,rest=name.partition('.');return aliases.get(first,first)+(sep+rest if sep else '')
def calls(node,aliases):return [{'line':n.lineno,'callee':fname(n),'resolved':resolved(fname(n),aliases)} for n in ast.walk(node) if isinstance(n,ast.Call)]
def access_sites(rows):
    out=[]
    for r in rows:
        s=r['resolved'];last=s.rsplit('.',1)[-1];tags=[]
        if last in ['parameters','named_parameters','get_parameter']:tags.append('model_parameter_access')
        if s in ['torch.autograd.grad','torch.autograd.functional.hessian','torch.autograd.functional.hvp','torch.autograd.functional.vhp'] or last in ['backward','requires_grad_']:tags.append('gradient_or_Hessian_API')
        if last in ['CrossEntropyLoss','cross_entropy','nll_loss','NLLLoss']:tags.append('label_loss_API')
        if last in ['enumerate','argsort','sort','sorted']:tags.append('iteration_or_sort_index')
        if tags:out.append({**r,'tags':tags})
    return out
def local_graph(tree,entry):
    defs={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))};seen=set();pending=[entry];edges={}
    while pending:
        key=pending.pop()
        if key in seen or key not in defs:continue
        seen.add(key);node=defs[key]
        child=sorted({n.func.id for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in defs})
        edges[key]=child;pending.extend(child)
    return defs,seen,edges
def main():
    p=read(ROOT/'PROFILE.json');b=read(ROOT/'INPUT_BINDING.json');f=read(ROOT/'SOURCE_FREEZE.json');pub=read(ROOT/'RUN_PUBLICATION.json')
    assert ROOT==Path(p['execution_root']) and p['launch_enabled'] and list(sys.version_info[:3])==p['python_version']
    assert pub['state']=='published_actual_historical_selector_source_review_before_execution' and len(pub['commit'])==40 and pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    for n,h in f['files'].items():assert sha(ROOT/n)==h,n
    for meta in [b['archive'],*b['reference_sources'].values()]:assert sha(meta['path'])==meta['sha256'] and Path(meta['path']).stat().st_size==meta['bytes']
    assert read(b['reference_sources']['archive_completion']['path'])['state']=='completed_bounded_source_only_review'
    assert read(b['reference_sources']['semantics_completion']['path'])['state']=='completed_bounded_dependency_source_semantics_review'
    exclusive('ONCE.json',{'pid':os.getpid(),'unix':time.time(),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json')});exclusive('ADMISSION.json',guard(p))
    texts={};trees={};member_meta={}
    with zipfile.ZipFile(b['archive']['path']) as z:
        for name,meta in b['source_members'].items():
            raw=z.read(name);assert len(raw)==meta['bytes'] and hashlib.sha256(raw).hexdigest()==meta['sha256']
            encoding,_=tokenize.detect_encoding(io.BytesIO(raw).readline);texts[name]=raw.decode(encoding);trees[name]=ast.parse(texts[name],filename=name)
            member_meta[name]={'sha256':meta['sha256'],'bytes':len(raw),'git_blob':hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()}
    it=trees['FedUBA-code/influence_function.py'];ct=trees['FedUBA-code/Fed_data_change.py'];entry=top(it,'influence_sort_function');assert entry is not None
    aliases=imports(it);defs,reachable,edges=local_graph(it,'influence_sort_function')
    facts={name:{'line':defs[name].lineno,'end_line':defs[name].end_lineno,'arguments':ast.unparse(defs[name].args),'calls':calls(defs[name],aliases),'access_sites':access_sites(calls(defs[name],aliases)),'returns':[ast.unparse(n.value) for n in ast.walk(defs[name]) if isinstance(n,ast.Return)]} for name in sorted(reachable)}
    access=[{'function':name,**r} for name,v in facts.items() for r in v['access_sites']]
    caller_sites=[{'line':n.lineno,'callee':fname(n),'positional_args':[ast.unparse(v) for v in n.args]} for n in ast.walk(ct) if isinstance(n,ast.Call) and fname(n)=='influence_sort_function']
    assert caller_sites
    refs={k:Path(m['path']).read_text(encoding='utf-8') for k,m in b['reference_sources'].items() if k in ['paperlinked_change','actual_logger','actual_runner','actual_core','paper_page6_text']}
    rt={k:ast.parse(v,filename=k) for k,v in refs.items() if k!='paper_page6_text'}
    observer=top(rt['actual_logger'],'observe_and_rank');assert observer is not None
    oc=calls(observer,imports(rt['actual_logger']));pubsort=top(rt['paperlinked_change'],'high_sensitivity_sort');assert pubsort is not None
    pubcalls=calls(pubsort,imports(rt['paperlinked_change']))
    body={'historical_influence_source':texts['FedUBA-code/influence_function.py'],'historical_change_source':texts['FedUBA-code/Fed_data_change.py'],'actual_observer_source':ast.unparse(observer),'paperlinked_high_sensitivity_source':ast.unparse(pubsort),'reachable_historical_function_names':sorted(reachable)}
    exclusive('SOURCE_BODY_REVIEW.json',body)
    page=' '.join(refs['paper_page6_text'].split())
    assert 'two forward passes per sample' in page and 'requires neither gradients' in page
    parameter=any('model_parameter_access' in r['tags'] for r in access);gradient=any('gradient_or_Hessian_API' in r['tags'] for r in access)
    observer_access=access_sites(oc);observer_query_calls=[r for r in oc if r['callee']=='query_logits']
    assert 'torch' not in sys.modules and 'numpy' not in sys.modules
    for meta in [b['archive'],*b['reference_sources'].values()]:assert sha(meta['path'])==meta['sha256']
    result={'state':'completed_historical_selector_source_information_access_review','scope':'Syntactic source reachability; branch execution and runtime numerical behavior were not measured. Attacker observer interface is distinguished from its query-service harness.','historical_member_metadata':member_meta,'historical_influence_source_matches_previously_known_unused_root_git_blob':member_meta['FedUBA-code/influence_function.py']['git_blob']==b['previously_observed_unused_root_influence_git_blob'],'historical_entry_arguments':ast.unparse(entry.args),'historical_local_call_graph':edges,'historical_reachable_functions':facts,'historical_reachable_information_access':access,'historical_actual_caller_sites':caller_sites,'historical_import_aliases':aliases,'historical_parameter_API_present_in_reachable_source':parameter,'historical_gradient_or_Hessian_API_present_in_reachable_source':gradient,'necessary_forward_only_paper_contract_supported_by_this_source':not(parameter or gradient),'actual_observer_query_call_sites':observer_query_calls,'actual_observer_access_sites':observer_access,'actual_observer_parameter_or_gradient_API_present':any(any(t in r['tags'] for t in ['model_parameter_access','gradient_or_Hessian_API']) for r in observer_access),'actual_observer_decorators':[ast.unparse(v) for v in observer.decorator_list],'paperlinked_high_sensitivity_calls':pubcalls,'paper_forward_only_constraints_confirmed_in_cached_text':True,'paper_PDF_fresh_extraction':False,'source_body_review_sha256':sha(ROOT/'SOURCE_BODY_REVIEW.json'),'source_member_reads':2,'download_calls':0,'upstream_code_executions':0,'torch_imports':0,'RNG_executions':0,'real_data_tensor_model_loads':0,'gradient_or_forward_executions':0,'optimizer_steps':0,'selector_adopted':False,'new_training_launched':False,'old_finite_jobs_rerun':0,'overall_goal_complete':False}
    exclusive('RESULT.json',result);exclusive('COMPLETION.json',{'state':'completed_bounded_historical_selector_source_review','exit_code':0,'finished_unix':time.time(),'result_sha256':sha(ROOT/'RESULT.json'),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'overall_goal_complete':False})
    print(json.dumps({'state':result['state'],'historical_reachable_functions':sorted(reachable),'parameter_API':parameter,'gradient_API':gradient,'actual_observer_query_sites':len(observer_query_calls),'actual_caller_sites':len(caller_sites)}))
if __name__=='__main__':
    try:main()
    except BaseException:
        exclusive('FAILURE.json',{'state':'failed_preserved_no_retry','pid':os.getpid(),'traceback':traceback.format_exc()});raise
