"""Once-only source-preserving query pilot, with internal stderr capture."""
import json,os,runpy,sys,time,traceback
from pathlib import Path
r=Path(__file__).resolve().parent;os.chdir(r)
sys.stdout=(r/'sourcepair_pilot_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'sourcepair_pilot_stderr.log').open('x',encoding='utf8',buffering=1)
try:runpy.run_path(str(r/'sourcepair_pilot.py'),run_name='__main__')
except BaseException:
    traceback.print_exc()
    (r/'SOURCEPAIR_PILOT_EXIT.json').write_text(json.dumps({'state':'failed','pid':os.getpid(),'time':time.time(),'traceback':traceback.format_exc()},indent=2)+'\n',encoding='utf8');raise
else:
    (r/'SOURCEPAIR_PILOT_EXIT.json').write_text(json.dumps({'state':'completed','pid':os.getpid(),'time':time.time()},indent=2)+'\n',encoding='utf8')
