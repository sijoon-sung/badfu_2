import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
import subprocess
import sys
from runtime_common import ROOT, freeze_check
freeze_check('ASSET_CPU2_FREEZE.json')
with (ROOT / 'asset_cpu2_console.log').open('x', encoding='utf-8', newline='\n', buffering=1) as stream:
    raise SystemExit(subprocess.call([sys.executable, '-u', str(ROOT / 'prepare_external_assets_cpu2.py')],
                     cwd=ROOT, env=os.environ.copy(), stdout=stream, stderr=subprocess.STDOUT))
