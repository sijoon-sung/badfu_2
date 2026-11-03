"""Repeatable metadata only; never imports torch or runs storage verification."""
from receive_ops import ROOT,OLD,now,read,digest,frozen,own_processes,task_snapshot
def main():
    p=frozen()
    from native_memory import memory_information
    out={'utc':now(),'state':'read_only_recovery_metadata','memory':memory_information(),
         'current_receivers':own_processes(),'task':task_snapshot(p['task_name']),
         'model_queries':0,'finite_reexecution':False,
         'local_packet_exists':__import__('pathlib').Path(p['local_packet']).exists(),'receipts':{}}
    names=['TASK_ONCE.json','TASK_START_REQUESTED.json','LAUNCH_FAILURE.json','RECEIVE_ONCE.json',
           'ACTUAL_PROCESS.json','RESOURCE_WAIT_BEGIN.json','RECEIVE_STATE.json','RECEIVE_FAILURE.json',
           'RECEIVE_TERMINAL.json','LOCAL_STORAGE_COMPLETION_SUMMARY.json','EXTRACTION_ONCE.json']
    for name in names:
        path=ROOT/name
        if path.exists():out['receipts'][name]={'sha256':digest(path),'content':read(path)}
    out['original_receive_receipts']={n:(OLD/n).exists() for n in
          ['PAIR_REVIEW_RECEIVE_ONCE.json','PAIR_REVIEW_RECEIVE_FAILURE.json','PAIR_REVIEW_LOCAL_COMPLETE.json']}
    import json
    text=json.dumps(out,ensure_ascii=False,indent=2)
    assert len(text)<=25000
    print(text)
if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    main()
