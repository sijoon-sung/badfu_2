"""Exclusive CPU re-entry, original GPU task and failure remain unchanged."""
import json,os,runpy,sys,time,traceback
from pathlib import Path
r=Path(__file__).resolve().parent;os.chdir(r)
sys.stdout=(r/'postonly_input_cpu_v2_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'postonly_input_cpu_v2_stderr.log').open('x',encoding='utf8',buffering=1)
try:runpy.run_path(str(r/'postonly_input_cpu_v2.py'),run_name='__main__')
except BaseException:
    traceback.print_exc()
    (r/'POST_ONLY_INPUT_CPU_V2_EXIT.json').write_text(json.dumps({'state':'failed','pid':os.getpid(),'time':time.time(),'traceback':traceback.format_exc()},indent=2)+'\n',encoding='utf8');raise
else:
    (r/'POST_ONLY_INPUT_CPU_V2_EXIT.json').write_text(json.dumps({'state':'completed','pid':os.getpid(),'time':time.time()},indent=2)+'\n',encoding='utf8')
