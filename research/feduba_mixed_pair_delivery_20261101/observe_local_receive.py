from pathlib import Path
import json,sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,str(Path.cwd()/'research/feduba_mixed_pair_delivery_20261101'))
from native_memory import memory_information
from native_processes import processes
tags=['feduba_mixed_delivery_transfer_receive_once.py','receive_pair_review.py']
rows=[v for v in processes() if any(t in v['CommandLine'] for t in tags)]
out={'state':'read_only_local_receiver_resource_observation','memory':memory_information(),'own_storage_processes':rows,'model_queries':0,'finite_reexecution':False}
print(json.dumps(out,indent=2))
