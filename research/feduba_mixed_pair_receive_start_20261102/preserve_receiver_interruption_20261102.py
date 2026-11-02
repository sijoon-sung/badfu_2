"""Read-only own task and bounded event-log metadata; no restart, model or policy change."""
from pathlib import Path
import sys,json,subprocess,xml.etree.ElementTree as ET,datetime,hashlib
BASE=Path(__file__).resolve().parents[2]
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from start_ops import freeze,current_task,v2,V2,memory_information
def main():
    p=freeze();task=current_task(p);rows=v2.own_processes()
    assert task['COM']['state']==3 and task['COM']['last_result']==1073807364 and not rows
    private=ROOT/'private_run/receiver_interruption_20261102'
    private.mkdir(exist_ok=False)
    def query(label,args):
        result=subprocess.run(['C:/Windows/System32/wevtutil.exe',*args],capture_output=True)
        assert len(result.stdout)+len(result.stderr)<=262144,'Bounded metadata exceeded; preserve before further query'
        v2.write(private/(label+'.json'),{'returncode':result.returncode,'stdout':v2.decode_output(result.stdout),'stderr':v2.decode_output(result.stderr)})
        return result.returncode,v2.decode_output(result.stdout),v2.decode_output(result.stderr)
    channel='Microsoft-Windows-TaskScheduler/Operational'
    code,config,err=query('task_history_config',['gl',channel,'/f:xml'])
    enabled=None
    if code==0:
        c=ET.fromstring(config)
        enabled=c.attrib.get('enabled')
        if enabled is None:
            enabled=next((x.text for x in c.iter() if x.tag.split('}')[-1]=='enabled'),None)
    code,xml,err=query('own_task_events',['qe',channel,'/q:*[EventData[Data[@Name="TaskName"]="\\'+p['task_name']+'"]]','/c:15','/rd:true','/f:xml','/e:Events'])
    ns={'e':'http://schemas.microsoft.com/win/2004/08/events/event'}
    def parse_events(xml,own=False):
        if not xml.strip():return []
        root=ET.fromstring(xml);events=[x for x in root.iter() if x.tag.split('}')[-1]=='Event']
        out=[]
        for e in events:
            s=e.find('e:System',ns)
            if s is None:continue
            d={x.attrib.get('Name',''):x.text for x in e.findall('e:EventData/e:Data',ns)}
            row={'event_id':s.findtext('e:EventID',namespaces=ns),
                 'utc':s.find('e:TimeCreated',ns).attrib.get('SystemTime'),
                 'provider':s.find('e:Provider',ns).attrib.get('Name')}
            if own:
                assert d.get('TaskName')=='\\'+p['task_name']
                row['own_task_fields']={k:v for k,v in d.items() if k in ['TaskName','ResultCode','ProcessId','ActionName','InstanceId','TaskInstanceId','Reason','UserName']}
            out.append(row)
        return out
    own=parse_events(xml,True) if code==0 else []
    lower='2026-11-02T04:16:45.000Z';upper='2026-11-02T04:35:53.000Z'
    window="TimeCreated[@SystemTime>='"+lower+"' and @SystemTime<='"+upper+"']"
    system_q="*[System["+window+" and (EventID=12 or EventID=13 or EventID=41 or EventID=1074 or EventID=6005 or EventID=6006)]]"
    sc,sx,se=query('bounded_boot_shutdown_system_events',['qe','System','/q:'+system_q,'/c:20','/rd:true','/f:xml','/e:Events'])
    rc,rx,re=query('bounded_resource_pressure_system_events',['qe','System','/q:*[System['+window+" and Provider[@Name='Microsoft-Windows-Resource-Exhaustion-Detector'] and EventID=2004]]",'/c:5','/rd:true','/f:xml','/e:Events'])
    state=v2.read(V2/'RECEIVE_STATE.json')
    events_path=V2/'private_run/RECEIVE_EVENTS.jsonl'
    data=events_path.read_bytes()
    with(private/'PRESERVED_RECEIVE_EVENTS_PREFIX.jsonl').open('xb') as f:f.write(data)
    records=[json.loads(x) for x in data.splitlines()]
    assert records and all(x['event_type']=='resource_guard' and x['state']=='waiting_fixed_memory_guard' for x in records)
    assert records[-1]['sample']==state['sample']==46 and state['elapsed_seconds']<86400
    copied=private/'PRESERVED_RECEIVE_STATE.json'
    with copied.open('xb')as f:f.write((V2/'RECEIVE_STATE.json').read_bytes())
    missing=['EXTRACTION_ONCE.json','RECEIVE_FAILURE.json','RECEIVE_TERMINAL.json','LOCAL_STORAGE_COMPLETION_SUMMARY.json','private_run/PAIR_REVIEW_LOCAL_COMPLETE.json']
    assert all(not(V2/x).exists()for x in missing)
    p2=v2.read(V2/'RECEIVE_PROFILE.json')
    assert not Path(p2['local_packet']).exists()
    archive=v2.OLD/'PAIR_REVIEW_DELIVERY.zip'
    assert archive.stat().st_size==1530790988 and not (v2.OLD/'PAIR_REVIEW_DELIVERY.zip.part').exists()
    o={'state':'receiver_ended_without_producer_terminal_during_guardwait_no_retry',
       'utc':v2.now(),'current_task':task,'current_receivers':rows,'current_memory':memory_information(),
       'last_receiver_state':state,'last_result_decimal':1073807364,'last_result_hex':hex(1073807364),
       'last_result_NTSTATUS_symbol':'DBG_TERMINATE_PROCESS','NTSTATUS_definition_is_not_killer_or_unique_cause_evidence':True,
       'NTSTATUS_source':'https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55',
       'exact_termination_time_or_actor_or_mechanism_proved':False,
       'normal_24h_timeout_observed':False,'RAM_shortage_proved_as_termination_cause':False,
       'task_history':{'configuration_query_exit':code if False else None,'enabled':enabled,'own_task_events_query_exit':code,'own_task_events':own,'query_error':err},
       'bounded_system_window':{'from_utc':lower,'to_utc':upper,
            'boot_shutdown_query_exit':sc,'boot_shutdown_timestamps_only':parse_events(sx)if sc==0 else [],
            'resource_pressure_query_exit':rc,'resource_pressure_timestamps_only':parse_events(rx)if rc==0 else [],
            'event_timing_is_not_unique_process_termination_causality':True},
       'preserved_guardwait_prefix':{'records':len(records),'samples':[records[0]['sample'],records[-1]['sample']],
            'first_utc':records[0]['utc'],'last_utc':records[-1]['utc'],'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'all_guardwait_no_extraction_or_CPU':True},
       'missing_producer_receipts':missing,'local_packet_exists':False,'archive_bytes':archive.stat().st_size,
       'archive_rehashed_or_transferred':False,'models_loaded_or_queried':0,'new_receiver_or_task_run_requests':0,
       'all_prior_source_freezes_validated':True,'catalogue_registration_called':False,
       'current_observer_metadata_only':True,'overall_goal_complete':False}
    # Repeated metadata is permitted; the incident snapshot itself is exclusive.
    assert not v2.own_processes()
    assert current_task(p)['COM']['last_result']==1073807364
    v2.write(ROOT/'RECEIVER_INTERRUPTION_OBSERVATION_20261102.json',o)
    print(json.dumps(o,ensure_ascii=False,indent=2))
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()
