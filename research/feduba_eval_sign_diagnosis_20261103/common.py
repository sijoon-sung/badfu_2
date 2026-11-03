"""Read-only fixed inputs and isolated outputs for the sign diagnostic."""
import hashlib,importlib.metadata,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(65536),b''):h.update(block)
    return h.hexdigest()
def write(name,value):
    p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_name(p.name+'.tmp')
    with tmp.open('w',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)
def once(name,value):
    with (ROOT/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def meta(p):
    p=Path(p);return {'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'payload_key':None}
def checked(m,base=None):
    p=Path(m['path'])
    if not p.is_absolute():p=Path(base or ROOT)/p
    assert p.is_absolute() and sha(p)==m['sha256'] and p.stat().st_size==m['bytes'],str(p)
    return p
def source_check():
    p=read(ROOT/'PROFILE.json');b=read(ROOT/'INPUT_BINDING.json')
    assert p['launch_enabled'] and ROOT==Path(p['execution_root'])
    assert list(sys.version_info[:3])==p['python_version']
    for name,version in p['package_versions'].items():assert importlib.metadata.version(name)==version
    for name,digest in read(ROOT/'SOURCE_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest,name
    for m in b['receipts'].values():checked(m)
    old=read(b['receipts']['baseline_primary']['path']);plus=read(b['receipts']['plus_primary']['path']);v=read(b['receipts']['plus_recovery']['path'])
    assert v['state']=='passed' and v['max_logit_abs_error']==0 and v['primary_result_sha256']==b['receipts']['plus_primary']['sha256']
    assert b['positive_rows']=={'pre':old['models']['pre'],'benign':old['models']['benign'],'minus_attack':old['models']['attack'],'plus_attack':plus['models']['attack']}
    for name,oldname in [('pre','pre'),('benign','benign'),('minus_attack','attack')]:assert b['models'][name]['sha256']==old['source_models'][oldname]['sha256']
    assert b['models']['plus_attack']['sha256']==plus['source_models']['attack']['sha256']
    assert b['delta']['sha256']==old['delta']['sha256']==plus['delta']['sha256']
    for m in b['models'].values():checked(m)
    checked(b['delta'])
    assert len(old['input_packets'])==79 and b['test_file_sha256']==old['test_file_sha256']==plus['test_file_sha256']
    assert not (Path(b['receipts']['plus_primary']['path']).parent/'PAIR_EVAL_VERIFIED.json').exists()
    return p,b,old
def require_run():
    p,b,old=source_check();pub=read(ROOT/'RUN_PUBLICATION.json')
    assert pub['state']=='published_actual_fixed_endpoint_negative_sign_diagnosis_before_queries'
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json') and pub['run_freeze_sha256']==sha(ROOT/'RUN_FREEZE.json')
    assert len(pub['commit'])==40
    for name,digest in read(ROOT/'RUN_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest,name
    assert read(ROOT/'SOURCE_REVIEW_RESULT.json')['state']=='passed_source_only_sign_diagnosis_review'
    return p,b,old
def guard(p):
    from native_memory import memory_information
    from native_processes import processes
    m=memory_information();gpu=subprocess.check_output(['C:/Windows/System32/nvidia-smi.exe','--query-gpu=utilization.gpu,memory.free,memory.used','--format=csv,noheader,nounits'],text=True).strip()
    util,free,used=[int(v.strip()) for v in gpu.split(',')]
    peers=[r for r in processes() if r['ProcessId'] not in [os.getpid(),os.getppid()] and any(t in r['CommandLine'].lower() for t in p['known_training_process_tokens'])]
    disk=shutil.disk_usage(ROOT).free
    ok=m['availableBytes']>=8*2**30 and m['commitLimit']-m['committedBytes']>=16*2**30 and util<=5 and free>=4000 and used<=6000 and disk>=80*2**30 and not peers
    return ok,{'memory':m,'GPU_util':util,'GPU_free_MiB':free,'GPU_used_MiB':used,'disk_free_bytes':disk,'competitors':len(peers),'time':time.time()}
def select_case(p,b):
    s=json.loads(subprocess.check_output([sys.executable,'-B',p['catalog_root']+'/select_case.py',p['case_id'],'--purpose','diagnostic'],text=True,encoding='utf-8'))
    assert s['guard_state']=='all_snapshot_files_verified_on_this_host'
    assert s['server_inputs']['pre']['sha256']==b['models']['pre']['sha256'] and s['server_inputs']['pre']['payload_key'] is None
    return s
def load(m,base=None):
    import torch
    value=torch.load(checked(m,base),map_location='cpu',weights_only=True)
    return value if m.get('payload_key') is None else value[m['payload_key']]
def save(path,value):
    import torch
    path=ROOT/path;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as f:torch.save(value,f);f.flush();os.fsync(f.fileno())
    m=meta(path);m['path']=path.relative_to(ROOT).as_posix();return m
def setup():
    import torch
    torch.set_num_threads(1);torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.use_deterministic_algorithms(True)
    assert os.environ['CUBLAS_WORKSPACE_CONFIG']==':4096:8'
    return torch
def diagnostic_gates(rows,attack,limits):
    hits={k:v['triggered_target_hits'] for k,v in rows.items()};ca={k:v['clean_correct'] for k,v in rows.items()}
    checks={'pre_ASR':hits['pre']*100<=limits['pre_ASR_max_pct']*9000,'attack_ASR':hits[attack]*100>=limits['attack_ASR_min_pct']*9000,'attack_minus_pre':(hits[attack]-hits['pre'])*100>=limits['attack_minus_pre_ASR_min_pp']*9000,'attack_minus_benign':(hits[attack]-hits['benign'])*100>=limits['attack_minus_benign_FU_ASR_min_pp']*9000,'all_three_CA':min(ca[k] for k in ['pre','benign',attack])*100>=limits['all_three_CA_min_pct']*10000,'both_post_CA_drop':max(ca['pre']-ca[k] for k in ['benign',attack])*100<=limits['post_CA_drop_max_pp']*10000}
    return {'checks':checks,'passed':all(checks.values()),'diagnostic_negative_route_only':True,'standard_positive_failure_replaced':False}
