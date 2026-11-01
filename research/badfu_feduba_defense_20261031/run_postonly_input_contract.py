"""Exclusive new synthetic CPU contract logging wrapper."""
import os,runpy,sys
from pathlib import Path
r=Path(__file__).resolve().parent;os.chdir(r)
sys.stdout=(r/'postonly_input_contract_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'postonly_input_contract_stderr.log').open('x',encoding='utf8',buffering=1)
runpy.run_path(str(r/'check_postonly_inputs.py'),run_name='__main__')
