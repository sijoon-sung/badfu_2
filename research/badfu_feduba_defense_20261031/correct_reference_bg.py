"""Exclusive once-only historical-reference correction wrapper."""
import json,os,runpy,sys,time,traceback
from pathlib import Path
r=Path(__file__).resolve().parent;os.chdir(r)
sys.stdout=(r/'reference_audit_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'reference_audit_stderr.log').open('x',encoding='utf8',buffering=1)
try:runpy.run_path(str(r/'correct_reference_audit.py'),run_name='__main__')
except BaseException:
    traceback.print_exc()
    (r/'REFERENCE_AUDIT_EXIT.json').write_text(json.dumps({'state':'failed','pid':os.getpid(),'time':time.time(),'traceback':traceback.format_exc()},indent=2)+'\n',encoding='utf8');raise
else:
    (r/'REFERENCE_AUDIT_EXIT.json').write_text(json.dumps({'state':'completed','pid':os.getpid(),'time':time.time()},indent=2)+'\n',encoding='utf8')
