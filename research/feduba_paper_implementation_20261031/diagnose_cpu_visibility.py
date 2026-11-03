"""One finite isolated Windows environment/CPU-only visibility diagnosis."""
import json
import os
import subprocess
import sys
from runtime_common import ROOT, read, write, sha

assert not (ROOT / 'CPU_VISIBILITY_DIAGNOSIS.json').exists()
assert read(ROOT / 'ASSET_FAILURE.json')['state'] == 'failed_preserved'
code = "import os,json,torch;print(json.dumps({'CUDA_VISIBLE_DEVICES':os.environ.get('CUDA_VISIBLE_DEVICES'),'available':torch.cuda.is_available(),'device_count':torch.cuda.device_count(),'initialized':torch.cuda.is_initialized(),'default_tensor_device':str(torch.zeros(1).device)}))"
rows = []
for value in ['', '-1']:
    env = os.environ.copy(); env['CUDA_VISIBLE_DEVICES'] = value
    p = subprocess.run([sys.executable, '-c', code], env=env, text=True, capture_output=True, check=True)
    rows.append({'parent_requested_value': value, 'fresh_child': json.loads(p.stdout)})
write(ROOT / 'CPU_VISIBILITY_DIAGNOSIS.json', {'state': 'completed', 'rows': rows,
      'source_sha256': sha(ROOT / 'diagnose_cpu_visibility.py'), 'models_or_data_loaded': False,
      'GPU_tensor_allocations': False, 'original_asset_task_restarted': False})
print(json.dumps(rows))
