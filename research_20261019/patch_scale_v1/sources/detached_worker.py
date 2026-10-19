"""Detached Windows worker entry point; does not alter the locked experiment."""
from pathlib import Path
import runpy
import sys

root = Path(__file__).resolve().parent.parent
repo = root.parent.parent
sys.stdout = (root/'worker.stdout.log').open('a', encoding='utf-8', buffering=1)
sys.stderr = (root/'worker.stderr.log').open('a', encoding='utf-8', buffering=1)
print('Detached worker entry point started', flush=True)
sys.argv = [str(root/'sources/scale_patch_experiment.py'), '--repo', str(repo), '--out', str(root)]
runpy.run_path(str(root/'sources/scale_patch_experiment.py'), run_name='__main__')
