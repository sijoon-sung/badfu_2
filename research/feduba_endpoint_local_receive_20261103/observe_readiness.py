"""One native-only readiness observation; never starts receiver or imports torch."""
import json,os,time
from receive_common import ROOT,read,sha,record,source_checks,native_snapshot

def main():
    p=source_checks();pub=read(ROOT/'READINESS_RUN_PUBLICATION.json')
    assert p['readiness_observation_enabled'] and pub['state']=='published_local_endpoint_native_readiness_only' and pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    value=native_snapshot(p);value.update(state='completed_native_readiness_observation_only',pid=os.getpid(),source_freeze_sha256=sha(ROOT/'SOURCE_FREEZE.json'),torch_imported=False,CPU_runtime_probed=False,receiver_started=False,transfer_started=False)
    record('READINESS_OBSERVATION.json',value)
    if not value['native_ready']:record('RECEIVER_NOT_STARTED.json',{'state':'not_started_native_resource_guard_unmet','readiness_sha256':sha(ROOT/'READINESS_OBSERVATION.json'),'waiter_started':False,'receiver_started':False,'model_transfer_started':False,'CPU_runtime_probed':False,'catalogue_modified':False,'next_action':'No retry/polling of this completed observer. A later distinct receive-attempt contract needs fresh native metadata.'})
    print(json.dumps({'state':value['state'],'native_ready':value['native_ready'],'available_GiB':value['memory']['availableBytes']/2**30,'commit_free_GiB':(value['memory']['commitLimit']-value['memory']['committedBytes'])/2**30,'receiver_started':False}))
if __name__=='__main__':main()
