"""Once-only full-pipeline audit launcher after the actual completion receipt."""
import hashlib,json,os,runpy,sys,time,traceback
from pathlib import Path
r=Path(__file__).resolve().parent;os.chdir(r)
if not (r/'stage11/COMPLETED.json').exists():raise RuntimeError('pipeline not completed')
if (r/'stage11/INDEPENDENT_VERIFICATION.json').exists():raise RuntimeError('full audit already completed')
sys.stdout=(r/'stage11_full_v2_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'stage11_full_v2_stderr.log').open('x',encoding='utf8',buffering=1)
sys.argv=[str(r/'verify_stage11_v2.py')]
try:runpy.run_path(str(r/'verify_stage11_v2.py'),run_name='__main__')
except BaseException:
    traceback.print_exc()
    (r/'STAGE11_FULL_AUDIT_EXIT.json').write_text(json.dumps({'state':'failed','pid':os.getpid(),'time':time.time(),'traceback':traceback.format_exc()},indent=2)+'\n',encoding='utf8')
    raise
else:
    (r/'STAGE11_FULL_AUDIT_EXIT.json').write_text(json.dumps({'state':'completed','pid':os.getpid(),'time':time.time(),
        'result_sha256':hashlib.sha256((r/'stage11/INDEPENDENT_VERIFICATION.json').read_bytes()).hexdigest()},indent=2)+'\n',encoding='utf8')
