"""Read-only UTF8 source/receipt preparation, no model/tensor loading."""
import hashlib,json,os,shutil,subprocess,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def exclusive(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
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
    p=read(ROOT/'METADATA_PROFILE.json');pub=read(ROOT/'METADATA_RUN_PUBLICATION.json');freeze=read(ROOT/'METADATA_SOURCE_FREEZE.json')
    assert ROOT==Path(p['execution_root']) and p['launch_enabled'] and not p['registration_enabled'] and list(sys.version_info[:3])==p['python_version']
    assert pub['state']=='published_actual_diagnostic_metadata_preparation_before_execution' and pub['source_freeze_sha256']==sha(ROOT/'METADATA_SOURCE_FREEZE.json')
    for n,h in freeze['files'].items():assert sha(ROOT/n)==h,n
    exclusive('METADATA_ONCE.json',{'pid':os.getpid(),'unix':time.time()});exclusive('METADATA_ADMISSION.json',guard(p))
    catroot=Path(p['catalog_root']);raw=(catroot/'catalog.json').read_bytes();cat=json.loads(raw.decode('utf-8'));assert len(cat['cases'])==p['expected_case_count']
    packets=read(ROOT/'PACKET_BINDING.json');rows={}
    for key,m in packets.items():
        manifest=Path(m['root'])/m['manifest'];assert sha(manifest)==m['manifest_sha256'] and sha(m['seal'])==m['seal_sha256']
        data=read(manifest);seal=read(m['seal']);assert seal['manifest_sha256']==m['manifest_sha256'] and len(data['files'])==m['hashed_files']
        typed=data['payloads'] if key=='baseline' else data['typed_payloads'];assert len(typed)==m['typed_payloads']
        models=[v for v in typed if v.get('kind')=='model' or v.get('CPU_strict_finite_zero1')]
        rows[key]={'manifest_keys':list(data),'model_rows':models,'hashed_files':len(data['files']),'typed_payloads':len(typed)}
    result={'state':'completed_UTF8_readonly_registration_metadata_preparation','catalog_sha256':hashlib.sha256(raw).hexdigest(),'case_count':len(cat['cases']),'case_ids':[c['id'] for c in cat['cases']],'defaults':{k:cat[k] for k in ['default_case','default_full_history_case','default_checkpoint_case']},'selector_source_sha256':sha(catroot/'select_case.py'),'packets':rows,'new_case_registration':0,'catalogue_or_packet_changes':0,'new_tensor_or_model_loads':0,'new_CPU_or_model_calls':0,'whole_catalogue_copied_to_local':False,'overall_goal_complete':False}
    assert (catroot/'catalog.json').read_bytes()==raw and 'torch' not in sys.modules and 'numpy' not in sys.modules
    exclusive('PREPARATION_METADATA_OBSERVATION.json',result);exclusive('METADATA_COMPLETION.json',{'state':'completed_registration_metadata_preparation_only','exit_code':0,'result_sha256':sha(ROOT/'PREPARATION_METADATA_OBSERVATION.json'),'finished_unix':time.time(),'overall_goal_complete':False});print(json.dumps({'state':result['state'],'case_count':result['case_count'],'catalog_sha256':result['catalog_sha256']}))
if __name__=='__main__':
    try:main()
    except BaseException:
        exclusive('METADATA_FAILURE.json',{'state':'failed_preserved_no_retry','traceback':traceback.format_exc()});raise
