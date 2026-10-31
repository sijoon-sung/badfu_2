"""Exclusive once-only CPU training pilot wrapper."""
import json,os,runpy,sys,time,traceback
from pathlib import Path
r=Path(__file__).resolve().parent;os.chdir(r)
sys.stdout=(r/'stage08_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'stage08_stderr.log').open('x',encoding='utf8',buffering=1)
try:runpy.run_path(str(r/'stage08.py'),run_name='__main__')
except BaseException:
    traceback.print_exc()
    (r/'STAGE08_WRAPPER_EXIT.json').write_text(json.dumps({'state':'failed','pid':os.getpid(),'time':time.time(),'traceback':traceback.format_exc()},indent=2)+'\n',encoding='utf8');raise
else:
    (r/'STAGE08_WRAPPER_EXIT.json').write_text(json.dumps({'state':'completed','pid':os.getpid(),'time':time.time()},indent=2)+'\n',encoding='utf8')
