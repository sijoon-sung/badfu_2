"""One DISLAB stdlib AST/text review of a prepared inactive local receiver."""
import ast,hashlib,json,os,shutil,subprocess,sys,time,traceback
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
    ip=read(ROOT/'INSPECTION_PROFILE.json');p=read(ROOT/'PROFILE.json');pub=read(ROOT/'INSPECTION_RUN_PUBLICATION.json');freeze=read(ROOT/'SOURCE_FREEZE.json')
    assert ROOT==Path(ip['execution_root']) and ip['inspection_enabled'] and not ip['actual_receiver_enabled'] and list(sys.version_info[:3])==ip['python_version']
    assert not p['receive_enabled'] and p['readiness_observation_enabled'] and not p['catalogue_registration_enabled']
    assert pub['state']=='published_prepared_endpoint_receiver_source_review_before_execution' and pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    for n,h in freeze['files'].items():assert sha(ROOT/n)==h,n
    assert p['archive']['bytes']==165494920 and p['archive']['sha256']=='f74d8f1cd2df54622965606e9614bb73927ed7aef55ccd68761bb6d497a0b58d' and len(p['models'])==4
    assert p['manifest_sha256']=='10cb99c38fbd72aed399e1e1ec258342544ac63520727f03b1f617ccc85c1b1c' and p['seal_sha256']=='69986537c105ee6ee77e1e2db37deb007ee5c4ead0ce22f855521eda7ca0136a'
    assert p['runtime']['python_version']==[3,11,17] and p['runtime']['torch_version']=='2.4.1+cu118' and p['CPU_model_checks']==4
    record('SOURCE_REVIEW_ONCE.json',{'pid':os.getpid(),'unix':time.time(),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json')});record('SOURCE_REVIEW_ADMISSION.json',guard(ip))
    rows=[];trees={}
    for n in freeze['files']:
        if not n.endswith('.py'):continue
        src=(ROOT/n).read_text(encoding='utf-8');tree=ast.parse(src,feature_version=(3,11));trees[n]=tree
        imports=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom))]
        assert not any(any(alias.name.split('.')[0] in ['torch','numpy','torchvision'] for alias in node.names) for node in imports)
        rows.append({'file':n,'sha256':sha(ROOT/n),'Python311_AST_parse':True,'top_level_model_library_import':False})
    assert len(rows)==8
    for n in ['probe_cpu_runtime.py','verify_cpu_storage.py']:
        mainfn=next(x for x in trees[n].body if isinstance(x,ast.FunctionDef) and x.name=='main');torchimport=next(x for x in mainfn.body if isinstance(x,ast.Import) and any(a.name=='torch' for a in x.names))
        calls=[x for x in ast.walk(mainfn) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='admission'];assert len(calls)==1 and calls[0].lineno<torchimport.lineno
        assert 'actual=True' in (ROOT/n).read_text(encoding='utf-8')
    observer=(ROOT/'observe_readiness.py').read_text(encoding='utf-8');assert "source_checks()" in observer and "native_snapshot(p)" in observer and 'subprocess' not in observer and 'import torch' not in observer.replace('never starts receiver or imports torch','')
    receiver=(ROOT/'receive_packet.py').read_text(encoding='utf-8');assert receiver.index('source_checks(actual=True)')<receiver.index('admission(p)')<receiver.index("child('probe_cpu_runtime.py'")<receiver.index("'scp.exe'")<receiver.index("child('verify_cpu_storage.py'")
    cpu=(ROOT/'verify_cpu_storage.py').read_text(encoding='utf-8');assert "weights_only=True" in cpu and "map_location='cpu'" in cpu and "strict=True" in cpu and "torch.inference_mode()" in cpu and "model.eval()" in cpu and "state[k].dtype==v.dtype" in cpu
    assert all(x not in cpu for x in ['.backward(','.step(','.save('])
    assert 'torch' not in sys.modules and 'numpy' not in sys.modules
    result={'state':'passed_prepared_inactive_endpoint_receiver_source_review','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'source_commit':pub['commit'],'source_AST_rows':rows,'scope':'Stdlib AST/text order checks and manual source review only; not execution of the receiver/runtime/ZIP/model checks or comprehensive control-flow proof.','receiver_enabled':False,'actual_launch_profile_exists':False,'local_readiness_observed':False,'local_runtime_imported':False,'archive_or_payload_read':False,'tensor_model_data_loads':0,'CPU_model_forwards':0,'receiver_or_transfer_started':False,'catalogue_modified':False,'overall_goal_complete':False}
    record('SOURCE_REVIEW_RESULT.json',result);record('SOURCE_REVIEW_COMPLETION.json',{'state':'completed_prepared_inactive_source_review_only','exit_code':0,'finished_unix':time.time(),'result_sha256':sha(ROOT/'SOURCE_REVIEW_RESULT.json'),'receiver_started':False,'overall_goal_complete':False});print(json.dumps({'state':result['state'],'AST_files':len(rows),'model_loads':0}))
if __name__=='__main__':
    try:main()
    except BaseException:record('SOURCE_REVIEW_FAILURE.json',{'state':'failed_preserved_no_retry','traceback':traceback.format_exc()});raise
