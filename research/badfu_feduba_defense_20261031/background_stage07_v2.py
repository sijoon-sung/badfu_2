"""Exclusive logs for a once-only CPU membership audit."""
import json
import os
from pathlib import Path
import runpy
import sys
import time
import traceback
r=Path(__file__).resolve().parent;os.chdir(r)
sys.stdout=(r/'stage07_v2_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'stage07_v2_stderr.log').open('x',encoding='utf8',buffering=1)
try:runpy.run_path(str(r/'stage07_cpu_v2.py'),run_name='__main__')
except BaseException:
    traceback.print_exc()
    (r/'STAGE07_V2_WRAPPER_EXIT.json').write_text(json.dumps({'state':'failed','pid':os.getpid(),'time':time.time(),'traceback':traceback.format_exc()},indent=2)+'\n',encoding='utf8');raise
else:
    (r/'STAGE07_V2_WRAPPER_EXIT.json').write_text(json.dumps({'state':'completed','pid':os.getpid(),'time':time.time()},indent=2)+'\n',encoding='utf8')
