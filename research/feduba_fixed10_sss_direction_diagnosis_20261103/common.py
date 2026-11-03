"""Local contract helpers for saved-query arithmetic, without model or torch imports."""
import hashlib,json,os,shutil,time
from pathlib import Path
from native_memory import memory_information
from native_processes import processes
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def once(name,value):
    with (ROOT/name).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def published():
    frozen=read(ROOT/'SOURCE_FREEZE.json')
    for n,d in frozen['files'].items():assert sha(ROOT/n)==d,n
    pub=read(ROOT/'SOURCE_PUBLICATION.json')
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    assert pub['profile_sha256']==sha(ROOT/'PROFILE.json') and pub['input_binding_sha256']==sha(ROOT/'INPUT_BINDING.json')
    p,b=read(ROOT/'PROFILE.json'),read(ROOT/'INPUT_BINDING.json')
    assert p['execution_enabled'] and p['model_load_enabled'] is False and p['new_model_queries']==0
    for name in ['SSS_result','SSS_verified','split']:assert sha(b[name]['path'])==b[name]['sha256'],name
    assert sha(ROOT/'private_inputs/QUERY_INDEX.json')==b['query_index_sha256']
    return p,b
class ResourceBusy(Exception):pass
def guard():
    p=read(ROOT/'PROFILE.json');rules=p['resources'];m=memory_information();free=shutil.disk_usage(ROOT).free
    markers=['fu_runner.py','clean_fl_runner.py','stg_runner.py','mixed_cpu_trigger.py','mixed_surrogate.py','train_teacher.py','mpi_train.py']
    other=[r for r in processes() if r['ProcessId']!=os.getpid() and any(s in r['CommandLine'].replace(chr(92),'/').lower() for s in markers)]
    state={'memory':m,'disk_free_bytes':free,'competing_trainer_count':len(other)}
    if m['availableBytes']<rules['native_available_bytes'] or m['commitLimit']-m['committedBytes']<rules['native_commit_free_bytes'] or free<rules['disk_free_bytes'] or other:raise ResourceBusy(json.dumps(state))
    return state
