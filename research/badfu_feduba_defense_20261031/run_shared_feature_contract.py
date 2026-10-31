"""Once-only contract logging wrapper; no native stderr escapes to SSH."""
import os,runpy,sys
from pathlib import Path
r=Path(__file__).resolve().parent;os.chdir(r)
sys.stdout=(r/'shared_feature_contract_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'shared_feature_contract_stderr.log').open('x',encoding='utf8',buffering=1)
runpy.run_path(str(r/'check_shared_feature.py'),run_name='__main__')
