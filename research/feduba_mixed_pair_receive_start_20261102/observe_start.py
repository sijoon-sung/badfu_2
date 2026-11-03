"""Repeatable bounded metadata, no model or archive/finite verification."""
from start_ops import ROOT,V2,v2,freeze,current_task,memory_information
def main():
    p=freeze()
    out={'utc':v2.now(),'state':'read_only_start_recovery_metadata','model_queries':0,'finite_reexecution':False,
         'task':current_task(p),'current_receivers':v2.own_processes(),'memory':memory_information(),
         'receipts':{},'historical_V2_LAUNCH_FAILURE_preserved':True}
    for folder,names in [(ROOT,['START_ONCE.json','START_TERMINAL.json','START_FAILURE.json']),
        (V2,['RECEIVE_ONCE.json','ACTUAL_PROCESS.json','RESOURCE_WAIT_BEGIN.json','RECEIVE_STATE.json',
             'EXTRACTION_ONCE.json','RECEIVE_FAILURE.json','RECEIVE_TERMINAL.json','LOCAL_STORAGE_COMPLETION_SUMMARY.json'])]:
        for n in names:
            if(folder/n).exists():out['receipts'][str(folder.name)+'/'+n]={'sha256':v2.digest(folder/n),'content':v2.read(folder/n)}
    p2=v2.read(V2/'RECEIVE_PROFILE.json')
    out['local_packet_exists']=__import__('pathlib').Path(p2['local_packet']).exists()
    import json
    value=json.dumps(out,ensure_ascii=False,indent=2)
    assert len(value)<=25000
    print(value)
if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    main()
