"""Guarded source-contract launcher. Not deployed or run during H11."""
import json,os,runpy,sys,time,traceback
from pathlib import Path
r=Path(__file__).resolve().parent;os.chdir(r)
if not (r/'stage11/COMPLETED.json').exists():raise RuntimeError('parent incomplete')
if (r/'STAGE12_GRADIENT_CONTRACT.json').exists():raise RuntimeError('contract already completed')
sys.stdout=(r/'stage12_contract_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'stage12_contract_stderr.log').open('x',encoding='utf8',buffering=1)
sys.argv=[str(r/'verify_stage12_gradient.py')]
try:runpy.run_path(str(r/'verify_stage12_gradient.py'),run_name='__main__')
except BaseException:
    traceback.print_exc()
    (r/'STAGE12_CONTRACT_EXIT.json').write_text(json.dumps({'state':'failed','pid':os.getpid(),'time':time.time(),'traceback':traceback.format_exc()},indent=2)+'\n',encoding='utf8')
    raise
else:
    (r/'STAGE12_CONTRACT_EXIT.json').write_text(json.dumps({'state':'completed','pid':os.getpid(),'time':time.time()},indent=2)+'\n',encoding='utf8')
