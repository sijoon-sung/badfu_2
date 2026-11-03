"""Stdlib-only durable metadata for one separate receive-only recovery."""
import os, sys, json, hashlib, datetime, csv, io, subprocess
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent.parent
OLD = BASE / 'research/feduba_mixed_pair_delivery_20261101'
SCHTASKS = 'C:/Windows/System32/schtasks.exe'
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(65536),b''): h.update(block)
    return h.hexdigest()
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False)
        f.write('\n');f.flush();os.fsync(f.fileno())
def state(value):
    value={'utc':now(),'pid':os.getpid(),**value}
    tmp=ROOT/'RECEIVE_STATE.tmp'
    write(tmp,value);os.replace(tmp,ROOT/'RECEIVE_STATE.json')
def event(event_type,**fields):
    with (ROOT/'private_run/RECEIVE_EVENTS.jsonl').open('a',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps({'utc':now(),'pid':os.getpid(),'event_type':event_type,**fields},allow_nan=False)+'\n')
        f.flush();os.fsync(f.fileno())
def frozen(publication=True):
    p=read(ROOT/'RECEIVE_PROFILE.json')
    for name,h in read(ROOT/'SOURCE_FREEZE.json')['files'].items():
        assert digest(ROOT/name)==h,name
    for name,h in p['preserved_original_sha256'].items():
        assert digest(OLD/name)==h,name
    for name,h in read(OLD/'SOURCE_FREEZE.json')['files'].items():
        assert digest(OLD/name)==h,name
    for name,h in read(OLD/'MONITOR_FREEZE.json')['files'].items():
        assert digest(OLD/name)==h,name
    assert p['launch_enabled'] is True
    if publication:
        pub=read(ROOT/'RECEIVE_PUBLICATION.json')
        assert pub['state']=='published_actual_receive_only_recovery_before_execution'
        assert pub['source_freeze_sha256']==digest(ROOT/'SOURCE_FREEZE.json')
        assert pub['profile_sha256']==digest(ROOT/'RECEIVE_PROFILE.json')
        assert len(pub['commit'])==40
    return p
def old_module():
    sys.path.insert(0,str(OLD))
    import pair_review_common as original
    assert Path(original.__file__).resolve()==OLD/'pair_review_common.py'
    return original
def own_processes():
    sys.path.insert(0,str(OLD))
    from native_processes import processes
    tags=['feduba_mixed_delivery_transfer_receive_once.py','receive_pair_review.py',
          str(ROOT/'receive_recovery.py').lower().replace('\\','/')]
    return [r for r in processes() if any(t.lower() in r['CommandLine'].lower().replace('\\','/') for t in tags)]
def absence(p):
    old_names=['PAIR_REVIEW_RECEIVE_ONCE.json','PAIR_REVIEW_RECEIVE_FAILURE.json','PAIR_REVIEW_LOCAL_COMPLETE.json']
    assert all(not (OLD/n).exists() for n in old_names),'Original receive receipt appeared; preserve and stop'
    assert not (OLD/'PAIR_REVIEW_DELIVERY.zip.part').exists()
    assert (OLD/'PAIR_REVIEW_DELIVERY.zip').stat().st_size==p['archive_bytes']
    assert not Path(p['local_packet']).exists(),'Packet/partial appeared; no retry'
    for folder in ['mixed_pair_dislab','mixed_pair_main','mixed_pair_pr']:
        assert not (OLD/'registrations'/folder).exists(),'Registration evidence appeared'
def decode_output(data):
    if data.startswith((b'\xff\xfe',b'\xfe\xff')):return data.decode('utf-16')
    if b'\x00' in data[:100]:return data.decode('utf-16-le')
    return data.decode('cp949',errors='replace')
def task(args):
    r=subprocess.run([SCHTASKS,*args],capture_output=True)
    return {'returncode':r.returncode,'stdout':decode_output(r.stdout),
            'stderr':decode_output(r.stderr)}
def task_absent(name):
    r=task(['/Query','/FO','CSV','/NH'])
    assert r['returncode']==0,'Task inventory read failed'
    rows=list(csv.reader(io.StringIO(r['stdout'])))
    assert rows and all(len(v)>=3 for v in rows if v),'Invalid task inventory'
    assert not any(v and v[0].lower()==('\\'+name).lower() for v in rows),'Recovery task already exists'
    return {'task_absent':True,'task_name':name,'inventory_query_exit_code':0}
def task_snapshot(name):
    r=task(['/Query','/TN',name,'/V','/FO','CSV'])
    return {'returncode':r['returncode'],'own_task_csv':r['stdout'],'own_task_error':r['stderr']}
