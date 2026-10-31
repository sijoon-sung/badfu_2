"""Exclusive diagnosis launcher with internal warning/traceback capture."""
import json,os,runpy,sys,time,traceback
from pathlib import Path
r=Path(__file__).resolve().parent;os.chdir(r)
if (r/'head_route_diagnosis/STARTED.json').exists():raise RuntimeError('diagnosis already started')
sys.stdout=(r/'head_route_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'head_route_stderr.log').open('x',encoding='utf8',buffering=1)
try:runpy.run_path(str(r/'diagnose_head_route.py'),run_name='__main__')
except BaseException:
    traceback.print_exc()
    (r/'HEAD_ROUTE_EXIT.json').write_text(json.dumps({'state':'failed','pid':os.getpid(),'time':time.time(),'traceback':traceback.format_exc()},indent=2)+'\n',encoding='utf8');raise
else:
    (r/'HEAD_ROUTE_EXIT.json').write_text(json.dumps({'state':'completed','pid':os.getpid(),'time':time.time()},indent=2)+'\n',encoding='utf8')
