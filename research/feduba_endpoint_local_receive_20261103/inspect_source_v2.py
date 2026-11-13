"""New bounded stdlib readiness-binding contract/delta review; no receiver invocation."""
import ast,hashlib,importlib.util,json,os,shutil,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def record(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
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

def main():
    ip=read(ROOT/'INSPECTION_PROFILE_V2.json');p=read(ROOT/'PROFILE_V2.json');pub=read(ROOT/'INSPECTION_RUN_PUBLICATION_V2.json');freeze=read(ROOT/'SOURCE_FREEZE_V2.json');old=read(ROOT/'SOURCE_FREEZE.json')
    assert ROOT==Path(ip['execution_root']) and ip['inspection_enabled'] and not p['receive_enabled'] and not p['catalogue_registration_enabled'] and not p['readiness_observation_enabled']
    assert list(sys.version_info[:3])==ip['python_version'] and pub['state']=='published_receiver_readiness_binding_v2_source_before_inspection' and pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE_V2.json')
    for n,h in freeze['files'].items():assert sha(ROOT/n)==h,n
    for n in ['INPUT_BINDING.json','native_memory.py','native_processes.py']:assert sha(ROOT/n)==old['files'][n],n
    record('V2_SOURCE_REVIEW_ONCE.json',{'pid':os.getpid(),'unix':time.time()});record('V2_SOURCE_REVIEW_ADMISSION.json',guard(ip))
    names=['receive_common_v2.py','probe_cpu_runtime_v2.py','verify_cpu_storage_v2.py','receive_packet_v2.py','inspect_source_v2.py'];rows=[]
    for n in names:ast.parse((ROOT/n).read_text(encoding='utf-8'),feature_version=(3,11));rows.append({'file':n,'sha256':sha(ROOT/n),'Python311_AST_parse':True})
    delta=read(ROOT/'V2_DELTA_BINDING.json')
    for item in delta['files']:
        assert sha(ROOT/item['base_file'])==item['base_sha256'];text=(ROOT/item['base_file']).read_text(encoding='utf-8')
        for before,after in item['allowed_literal_replacements']:text=text.replace(before,after)
        assert text==(ROOT/item['new_file']).read_text(encoding='utf-8'),item['new_file']
    assert sha(ROOT/'receive_common.py')==delta['common_base_sha256']
    common=(ROOT/'receive_common_v2.py').read_text(encoding='utf-8');assert 'validate_readiness_binding(launch)' in common and "ROOT/'READINESS_OBSERVATION.json'" not in common
    spec=importlib.util.spec_from_file_location('new_stdlib_readiness_binding',ROOT/'receive_common_v2.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    testroot=ROOT/'private_synthetic_readiness';testroot.mkdir(exist_ok=False);out=[]
    def run(label,ready=True,age=0,wrong_hash=False,outside=False):
        path=ROOT/('NATIVE_RECEIVE_READINESS_SYNTHETIC_'+label+'.json');value={'state':'completed_native_readiness_observation_only','native_ready':ready,'utc_unix':time.time()-age,'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE_V2.json'),'synthetic_contract_test_not_real_native_observation':True}
        with path.open('x',encoding='utf-8') as f:json.dump(value,f)
        launch={'readiness_observation_path':str(path if not outside else ROOT.parent/path.name),'readiness_observation_sha256':'0'*64 if wrong_hash else sha(path),'readiness_max_age_seconds':300}
        accepted=True
        try:module.validate_readiness_binding(launch)
        except AssertionError:accepted=False
        expected=label=='fresh_true';assert accepted==expected,label;out.append({'condition':label,'accepted':accepted,'expected':expected,'synthetic_only':True});path.replace(testroot/path.name)
    run('fresh_true');run('recorded_false',ready=False);run('wrong_SHA',wrong_hash=True);run('outside_root',outside=True);run('stale',age=301)
    assert 'torch' not in sys.modules and 'numpy' not in sys.modules
    result={'state':'passed_prepared_v2_fresh_readiness_binding_source_contract','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE_V2.json'),'source_commit':pub['commit'],'new_AST_files':rows,'unchanged_numeric_CPU_runtime_source_delta_files':3,'synthetic_readiness_contract_cases':out,'old_false_actual_observation_not_overwritten':True,'scope':'Prepared inactive operational source correction only;5syntheticJSON cases are not actual localRAM/runtime observations. Not a complete runtime or receiver execution proof.','real_local_native_RAM_queries':0,'torch_runtime_imports':0,'tensor_model_loads':0,'CPU_model_forwards':0,'archive_or_realdata_read':False,'receiver_or_transfer_started':False,'catalogue_modified':False,'overall_goal_complete':False}
    record('V2_SOURCE_REVIEW_RESULT.json',result);record('V2_SOURCE_REVIEW_COMPLETION.json',{'state':'completed_v2_source_and_synthetic_readiness_contract_only','exit_code':0,'finished_unix':time.time(),'result_sha256':sha(ROOT/'V2_SOURCE_REVIEW_RESULT.json'),'receiver_started':False,'overall_goal_complete':False});print(json.dumps({'state':result['state'],'AST_files':5,'synthetic_cases':5,'model_loads':0}))
if __name__=='__main__':
    try:main()
    except BaseException:record('V2_SOURCE_REVIEW_FAILURE.json',{'state':'failed_preserved_no_retry','traceback':traceback.format_exc()});raise
