"""New receive-stage stdlib contracts. No model or dataset imports."""
import hashlib,importlib.util,json,os,shutil,stat,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda:f.read(4194304),b''):h.update(data)
    return h.hexdigest()
def record(name,value):
    with (ROOT/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def event(value):
    with (ROOT/'LEDGER_V2.jsonl').open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps({'unix':time.time(),**value},allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def validate_readiness_binding(launch):
    path=Path(launch['readiness_observation_path']).resolve()
    assert path.is_relative_to(ROOT.resolve()) and path.name.startswith('NATIVE_RECEIVE_READINESS_') and path.suffix=='.json'
    assert sha(path)==launch['readiness_observation_sha256']
    observation=read(path);assert observation['state']=='completed_native_readiness_observation_only' and observation['native_ready'] is True
    assert observation['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE_V2.json')
    assert launch['readiness_max_age_seconds']==300 and -5<=time.time()-observation['utc_unix']<=300
    return observation

def source_checks(actual=False):
    p=read(ROOT/'PROFILE_V2.json');assert ROOT==Path(p['execution_root']) and not p['receive_enabled'] and not p['catalogue_registration_enabled']
    for n,h in read(ROOT/'SOURCE_FREEZE_V2.json')['files'].items():assert sha(ROOT/n)==h,n
    for m in read(ROOT/'INPUT_BINDING.json').values():assert sha(m['path'])==m['sha256'] and Path(m['path']).stat().st_size==m['bytes']
    if actual:
        launch=read(ROOT/'RECEIVE_LAUNCH_PROFILE_V2.json');pub=read(ROOT/'RUN_PUBLICATION_V2.json')
        assert launch['receive_enabled'] and launch['CPU_storage_checks_enabled'] and not launch['catalogue_registration_enabled']
        assert launch['source_profile_sha256']==sha(ROOT/'PROFILE_V2.json') and launch['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE_V2.json')
        validate_readiness_binding(launch)
        assert pub['state']=='published_actual_local_endpoint_receiver_v2_before_execution' and pub['run_freeze_sha256']==sha(ROOT/'RUN_FREEZE_V2.json')
        for n,h in read(ROOT/'RUN_FREEZE_V2.json')['files'].items():assert sha(ROOT/n)==h,n
    return p
def native_snapshot(p):
    from native_memory import memory_information
    m=memory_information();disk=shutil.disk_usage(ROOT).free;g=p['resource_guard']
    ok=m['availableBytes']>=g['native_available_GiB']*2**30 and m['commitLimit']-m['committedBytes']>=g['commit_free_GiB']*2**30 and disk>=g['disk_free_GiB']*2**30
    return {'utc_unix':time.time(),'memory':m,'disk_free_bytes':disk,'native_ready':ok,'waiter_started':False}
def admission(p):
    from native_processes import processes
    obs=native_snapshot(p);assert obs['native_ready'],'Native RAM/commit/disk guard unmet; no waiter'
    gpu=subprocess.check_output(['C:/Windows/System32/nvidia-smi.exe','--id=0','--query-gpu=utilization.gpu,memory.free,memory.used','--format=csv,noheader,nounits'],text=True).strip();util,free,used=[int(v.strip()) for v in gpu.split(',')];g=p['resource_guard']
    competitors=[v for v in processes() if v['ProcessId'] not in [os.getpid(),os.getppid()] and any(t.lower() in v['CommandLine'].lower() for t in p['known_training_process_tokens'])]
    assert util<=g['GPU_util_max'] and free>=g['GPU_free_MiB_min'] and used<=g['GPU_used_MiB_max'] and not competitors,'GPU/competitor guard unmet; no app closure'
    return {**obs,'GPU':gpu,'competitors':0}
def runtime_files(p):
    for m in p['runtime']['expected_files']:assert sha(m['path'])==m['sha256'] and Path(m['path']).stat().st_size==m['bytes']
def packet_path(p):return Path(p['local_review_parent'])/p['packet_name']
def verify_packet(p):
    root=packet_path(p);manifest_path=root/'ENDPOINT_MANIFEST.json';seal=root.with_name(root.name+'_SEAL.json')
    assert sha(manifest_path)==p['manifest_sha256'] and sha(seal)==p['seal_sha256'] and not manifest_path.stat().st_mode&stat.S_IWRITE and not seal.stat().st_mode&stat.S_IWRITE
    m=read(manifest_path);assert m['models']==p['models'] and len(m['files'])==14 and read(seal)['manifest_sha256']==p['manifest_sha256']
    assert {v.relative_to(root).as_posix() for v in root.rglob('*') if v.is_file()}==set(m['files'])|{'ENDPOINT_MANIFEST.json'}
    for n,v in m['files'].items():
        f=(root/n).resolve();assert f.is_relative_to(root.resolve()) and f.stat().st_size==v['bytes'] and sha(f)==v['sha256'] and not f.stat().st_mode&stat.S_IWRITE,n
    selections=read(root/'CASE_SELECTIONS.json');provenance=read(root/'SOURCE_PROVENANCE.json');binding=read(ROOT/'INPUT_BINDING.json');registered=read(binding['registration']['path'])
    assert provenance['source_case_ids']==registered['case_ids']==p['case_ids']
    for branch,cid in p['case_ids'].items():assert selections[branch]==registered['selections'][branch] and selections[branch]['case_id']==cid and selections[branch]['purpose']=='diagnostic' and selections[branch]['guard_state']=='all_snapshot_files_verified_on_this_host'
    assert {n for n in m['files'] if n.endswith('.pt')}=={v['file'] for v in p['models'].values()} and all(v['payload_key'] is None for v in p['models'].values())
    return {'state':'local_received_packet_hashes_and_explicit_diagnostic_identity_verified','manifest_sha256':sha(manifest_path),'seal_sha256':sha(seal),'hashed_files':14,'models':4,'tensor_loads':0,'source_case_ids':p['case_ids']}
