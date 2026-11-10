"""Read-only UTF-8 metadata and resources; does not import torch or load tensors."""
import ctypes
import hashlib
import json
from pathlib import Path
import platform
import subprocess

root = Path('D:/TRAJECTORY_CATALOG_20261023')
catalog = json.loads((root / 'catalog.json').read_text(encoding='utf-8-sig'))
wanted = {'badfu.confirmed.s20261023.v1', 'badfu.paper32.s20261020',
          'badfu.multiseed.s20261023', 'fuba.v7.s20261023.pre100.post.kd10'}
rows = []
for case in catalog['cases']:
    row = {k: case.get(k) for k in ['id', 'family', 'post_type', 'reproduction', 'allowed_purposes']}
    if case['id'] in wanted or case['id'].startswith('feduba.public_fixed10.'):
        row['server_inputs'] = case['server_inputs']
        row['checkpoint_guard'] = case.get('checkpoint_guard')
    rows.append(row)
class Memory(ctypes.Structure):
    _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong),
                ('total', ctypes.c_ulonglong), ('avail', ctypes.c_ulonglong),
                ('total_page', ctypes.c_ulonglong), ('avail_page', ctypes.c_ulonglong),
                ('total_virtual', ctypes.c_ulonglong), ('avail_virtual', ctypes.c_ulonglong),
                ('avail_extended', ctypes.c_ulonglong)]
memory = Memory(); memory.length = ctypes.sizeof(memory)
assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
gpu = subprocess.run(['nvidia-smi', '--query-gpu=index,name,utilization.gpu,memory.free,memory.used',
                      '--format=csv,noheader,nounits'], capture_output=True, text=True)
apps = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory',
                       '--format=csv,noheader,nounits'], capture_output=True, text=True)
print(json.dumps(dict(host=platform.node(), catalog_sha256=hashlib.sha256((root / 'catalog.json').read_bytes()).hexdigest(),
    cases=rows, available_memory=memory.avail, logical_cpu=__import__('os').cpu_count(),
    gpu=gpu.stdout.strip(), compute_apps=apps.stdout.strip(), torch_imports=0, tensor_loads=0), ensure_ascii=True))
