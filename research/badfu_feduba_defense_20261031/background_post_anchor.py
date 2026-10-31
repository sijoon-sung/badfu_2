"""Exclusive once-only wrapper for the Post-anchored consistency repair."""
import json,os,runpy,sys,time,traceback
from pathlib import Path
r=Path(__file__).resolve().parent;os.chdir(r)
sys.stdout=(r/'post_anchor_run_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'post_anchor_run_stderr.log').open('x',encoding='utf8',buffering=1)
try:runpy.run_path(str(r/'post_anchor_run.py'),run_name='__main__')
except BaseException:
    traceback.print_exc()
    (r/'POST_ANCHOR_WRAPPER_EXIT.json').write_text(json.dumps({'state':'failed','pid':os.getpid(),'time':time.time(),'traceback':traceback.format_exc()},indent=2)+'\n',encoding='utf8');raise
else:
    (r/'POST_ANCHOR_WRAPPER_EXIT.json').write_text(json.dumps({'state':'completed','pid':os.getpid(),'time':time.time()},indent=2)+'\n',encoding='utf8')
