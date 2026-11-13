"""Separate start-only metadata contract for the already created, unrun V2 task."""
import sys,json,subprocess,hashlib,xml.etree.ElementTree as ET,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent.parent
V2=BASE/'research/feduba_mixed_pair_receive_recovery_v2_20261102'
sys.path.insert(0,str(V2))
import receive_ops as v2
sys.path.insert(0,str(v2.OLD))
from native_memory import memory_information
def freeze(publication=True):
    p=v2.read(ROOT/'START_PROFILE.json')
    for n,h in v2.read(ROOT/'SOURCE_FREEZE.json')['files'].items():assert v2.digest(ROOT/n)==h,n
    for n,h in p['prior_v2_sha256'].items():assert v2.digest(V2/n)==h,n
    v2.frozen()
    assert p['launch_enabled'] is True
    if publication:
        pub=v2.read(ROOT/'START_PUBLICATION.json')
        assert pub['state']=='published_start_only_existing_unrun_V2_task_before_run_request'
        assert pub['source_freeze_sha256']==v2.digest(ROOT/'SOURCE_FREEZE.json')
        assert pub['profile_sha256']==v2.digest(ROOT/'START_PROFILE.json')
        assert len(pub['commit'])==40
    return p
def canonical(text):
    return ET.canonicalize(text,strip_text=True)
def current_task(p):
    xml=v2.task(['/Query','/TN',p['task_name'],'/XML'])
    assert xml['returncode']==0,'Existing V2 task query failed'
    h=hashlib.sha256(canonical(xml['stdout']).encode('utf-8')).hexdigest()
    assert h==p['registered_task_canonical_sha256'],'Registered task definition changed'
    run=subprocess.run(['C:/Windows/System32/cscript.exe','//Nologo',str(ROOT/'read_task.js'),p['task_name']],capture_output=True)
    assert run.returncode==0,{'COM_metadata_exit':run.returncode,'stderr':v2.decode_output(run.stderr)}
    meta=json.loads(v2.decode_output(run.stdout))
    assert meta['run_level']==0,'Require actual COM RunLevel LUA0, no privilege change'
    assert meta['enabled'] is True
    return {'COM':meta,'canonical_xml_sha256':h,'xml_query_exit_code':0}
def preflight(p):
    v2.absence(v2.read(V2/'RECEIVE_PROFILE.json'))
    assert not v2.own_processes()
    for n in ['TASK_START_REQUESTED.json','private_run/TASK_RUN_RESULT.json','RECEIVE_ONCE.json','RECEIVE_FAILURE.json']:
        assert not(V2/n).exists(),n
    assert v2.read(V2/'LAUNCH_TERMINAL_OBSERVATION.json')['run_request_count']==0
    checked=current_task(p)
    assert checked['COM']['last_result']==267011 and checked['COM']['state']==3,'Require real never-run Ready task'
    return checked
