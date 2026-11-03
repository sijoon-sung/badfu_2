import datetime,hashlib,importlib.metadata,json,shutil,sys
from pathlib import Path
B=Path(r'C:/Users/sijoo/Documents/ChatGPT/badFU');R=B/'research/feduba_endpoint_review_delivery_20261103';sys.path.insert(0,str(R));from native_memory import memory_information
m=memory_information();disk=shutil.disk_usage(B).free
try:torch_version=importlib.metadata.version('torch')
except importlib.metadata.PackageNotFoundError:torch_version=None
v={'state':'new_native_local_delivery_readiness_metadata_only','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'memory':m,'disk_free_bytes':disk,'available_GiB':m['availableBytes']/2**30,'commit_free_GiB':(m['commitLimit']-m['committedBytes'])/2**30,'readiness_8GiB_available_16GiB_commit_80GiB_disk':m['availableBytes']>=8*2**30 and m['commitLimit']-m['committedBytes']>=16*2**30 and disk>=80*2**30,'python':list(sys.version_info[:3]),'torch_distribution_metadata_only':torch_version,'torch_imported':'torch' in sys.modules,'model_tensor_loads':0,'receiver_or_transfer_launched':False,'DISLAB_prerequisite':False,'native_helper_sha256':hashlib.sha256((R/'native_memory.py').read_bytes()).hexdigest(),'oneoff_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
with (R/'LOCAL_READINESS_OBSERVATION.json').open('x',encoding='utf-8') as f:json.dump(v,f,indent=2)
print(json.dumps(v))
