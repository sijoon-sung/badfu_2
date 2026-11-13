"""New stdlib-only necessary-condition check of a related mixing helper."""
import ast,hashlib,json,os,shutil,subprocess,sys,time,traceback,types
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def exclusive(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
    p=read(ROOT/'PROFILE.json');b=read(ROOT/'INPUT_BINDING.json');pub=read(ROOT/'RUN_PUBLICATION.json')
    assert ROOT==Path(p['execution_root']) and p['launch_enabled']
    assert list(sys.version_info[:3])==p['python_version']
    assert pub['state']=='published_actual_concoct_source_review_before_execution' and len(pub['commit'])==40
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    for n,h in read(ROOT/'SOURCE_FREEZE.json')['files'].items():assert sha(ROOT/n)==h,n
    for m in b['inputs'].values():assert sha(m['path'])==m['sha256'] and Path(m['path']).stat().st_size==m['bytes']
    from native_memory import memory_information
    from native_processes import processes
    memory=memory_information()
    assert memory['availableBytes']>=8*2**30 and memory['commitLimit']-memory['committedBytes']>=16*2**30
    assert shutil.disk_usage(ROOT).free>=80*2**30
    gpu=subprocess.check_output(['C:/Windows/System32/nvidia-smi.exe','--query-gpu=utilization.gpu,memory.free,memory.used','--format=csv,noheader,nounits'],text=True).strip()
    util,free,used=[int(x.strip()) for x in gpu.split(',')];assert util<=5 and free>=4000 and used<=6000
    assert not [r for r in processes() if r['ProcessId'] not in [os.getpid(),os.getppid()] and any(t in r['CommandLine'].lower() for t in p['known_training_process_tokens'])]
    exclusive('ONCE.json',{'pid':os.getpid(),'time':time.time(),'profile_sha256':sha(ROOT/'PROFILE.json'),'memory':memory,'GPU':gpu,'competitors':0})
    source=ast.parse(Path(b['inputs']['related_util']['path']).read_text(encoding='utf-8'))
    cls=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='concoct_dataset')
    init=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
    args=[n.arg for n in init.args.args][1:]
    assert args==['target_dataset','outter_dataset'] and not init.args.defaults and init.args.vararg is None
    public=ast.parse(Path(b['inputs']['public_trigger']['path']).read_text(encoding='utf-8'))
    calls=[n for n in ast.walk(public) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='concoct_dataset']
    assert len(calls)==1 and len(calls[0].args)==3 and not calls[0].keywords
    actual=ast.parse(Path(b['inputs']['actual_mixed_common']['path']).read_text(encoding='utf-8'))
    actual_class=next(n for n in actual.body if isinstance(n,ast.ClassDef) and n.name=='MixedImages')
    actual_getitem=next(n for n in actual_class.body if isinstance(n,ast.FunctionDef) and n.name=='__getitem__')
    transform_calls=[n for n in ast.walk(actual_getitem) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='self' and n.func.attr=='transform']
    assert len(transform_calls)==1
    assert any(isinstance(n,ast.Constant) and n.value==200 for n in ast.walk(actual_getitem))
    env={'torch':types.SimpleNamespace(utils=types.SimpleNamespace(data=types.SimpleNamespace(Dataset=object)))}
    code=ast.Module(body=[cls],type_ignores=[]);ast.fix_missing_locations(code)
    exec(compile(code,'<pinned_related_concoct_AST_only>','exec'),env)
    class CountingDataset:
        def __init__(self,prefix,labels):
            self.prefix=prefix;self.labels=labels;self.calls=[];self.classes=list(range(len(labels)))
        def __len__(self):return len(self.labels)
        def __getitem__(self,i):
            self.calls.append(i);return self.prefix+str(i),self.labels[i]
    outer=CountingDataset('o',[0,1,2]);target=CountingDataset('t',[9,9])
    related=env['concoct_dataset'](target,outer)
    assert len(related)==5
    rows=[related[i] for i in range(5)]
    assert rows==[('o0',0),('o1',1),('o2',2),('t0',3),('t1',3)]
    assert outer.calls==[0,0,1,1,2,2] and target.calls==[0,1]
    try:
        env['concoct_dataset'](target,outer,True)
        raise AssertionError('Unexpected direct three-argument compatibility')
    except TypeError as error:expected_error=str(error)
    assert len(outer.calls)+len(target.calls)==8
    assert 'torch' not in sys.modules and 'numpy' not in sys.modules
    for m in b['inputs'].values():assert sha(m['path'])==m['sha256']
    result={'state':'completed_related_concoct_source_compatibility_review','related_constructor_args':args,'FedUBA_call_positional_args':3,'FedUBA_third_arg_AST':ast.unparse(calls[0].args[2]),'exact_direct_drop_in_compatible':False,'expected_three_argument_TypeError':expected_error,'synthetic_composite_positions':5,'synthetic_labels':[r[1] for r in rows],'outer_getitem_calls':len(outer.calls),'target_getitem_calls':len(target.calls),'total_wrapped_getitems':8,'actual_MixedImages_transform_calls_per_getitem_source':1,'actual_target_label_literal_source':200,'concatenation_and_extra_class_mapping_supports_declared_candidate_only':True,'missing_FedUBA_helper_recovered':False,'third_flag_semantics_known':False,'causal_performance_explanation_established':False,'new_correction_adopted':False,'new_training_authorized_by_this_result':False,'torch_imports':0,'RNG_executions':0,'model_tensor_or_real_data_reads':0,'forward_calls':0,'optimizer_steps':0,'overall_goal_complete':False}
    exclusive('RESULT.json',result)
    exclusive('COMPLETION.json',{'state':'completed_finite_model_free_helper_review_candidate_closed','result_sha256':sha(ROOT/'RESULT.json'),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'commit':pub['commit'],'exit_code':0,'finished_unix':time.time(),'new_model_calculation':False,'overall_goal_complete':False})
    print(json.dumps(result))
if __name__=='__main__':
    try:main()
    except BaseException:
        exclusive('FAILURE.json',{'state':'failed_preserved','pid':os.getpid(),'traceback':traceback.format_exc()});raise
