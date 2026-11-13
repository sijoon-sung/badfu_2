"""Direct Python task entry, matching the established DISLAB background pattern."""
import os
from pathlib import Path
import runpy
import sys

root = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
os.environ.update(PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='0')
sys.stdout = (root / 'study_recovery_console.log').open('x', encoding='utf-8', newline='\n', buffering=1)
sys.stderr = sys.stdout
sys.argv = [str(root / 'study_controller_recovery.py')]
runpy.run_path(root / 'study_controller_recovery.py', run_name='__main__')
