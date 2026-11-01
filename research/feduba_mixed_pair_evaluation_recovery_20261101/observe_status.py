"""Repeatable bounded metadata reader; no finite job is invoked."""
from pathlib import Path
import hashlib
import json
import sys
sys.stdout.reconfigure(encoding='utf-8')
r=Path(__file__).resolve().parent
f=json.loads((r/'SOURCE_FREEZE.json').read_text(encoding='utf-8'))
p=r/'QUERY_STATUS.ps1';assert hashlib.sha256(p.read_bytes()).hexdigest()==f['files'][p.name]
sys.path.insert(0,str(r.parent/'00_trajectories'))
import dislab_audit as transport
raw=transport.remote(p.read_text(encoding='utf-8'));assert len(raw)<=25000
v=json.loads(raw);assert v['root']=='D:/FEDUBA_MIXED_PAIR_EVALUATION_RECOVERY_20261101'
print(json.dumps({'state':'passed_bounded_evaluation_recovery_metadata_observation','response_characters':len(raw),
    'model_queries':0,'finite_job_reexecuted':False,'observation':v},ensure_ascii=False,indent=2))
