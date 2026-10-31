"""Once-only cached diagnosis logging wrapper."""
import os,runpy,sys
from pathlib import Path
r=Path(__file__).resolve().parent;os.chdir(r)
sys.stdout=(r/'post_confidence_audit_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'post_confidence_audit_stderr.log').open('x',encoding='utf8',buffering=1)
runpy.run_path(str(r/'verify_post_confidence.py'),run_name='__main__')
