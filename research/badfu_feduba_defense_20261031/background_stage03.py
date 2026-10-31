"""Scheduled direct-Python wrapper; does not change the frozen experiment."""
import json
import os
from pathlib import Path
import runpy
import sys
import time
import traceback

root=Path(__file__).resolve().parent
os.chdir(root)
sys.stdout=(root/'stage03_recovery_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(root/'stage03_recovery_stderr.log').open('x',encoding='utf8',buffering=1)
try:
    runpy.run_path(str(root/'stage03.py'),run_name='__main__')
except BaseException:
    traceback.print_exc()
    (root/'STAGE03_WRAPPER_EXIT.json').write_text(json.dumps({'pid':os.getpid(),'time_unix':time.time(),
        'state':'failed','traceback':traceback.format_exc()},indent=2)+'\n',encoding='utf8')
    raise
else:
    (root/'STAGE03_WRAPPER_EXIT.json').write_text(json.dumps({'pid':os.getpid(),'time_unix':time.time(),
        'state':'completed'},indent=2)+'\n',encoding='utf8')
