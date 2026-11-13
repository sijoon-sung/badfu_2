"""Repeatable bounded metadata monitor; never starts any finite preparation/run."""
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
frozen = json.loads((HERE / 'SOURCE_FREEZE.json').read_text(encoding='utf-8'))
for name in ['observe_status.py', 'QUERY_STATUS.ps1']:
    assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == frozen['files'][name]
sys.path.insert(0, str(HERE.parent / '00_trajectories'))
import dislab_audit
raw = dislab_audit.remote((HERE / 'QUERY_STATUS.ps1').read_text(encoding='utf-8'))
assert len(raw) <= 25000, 'Bounded response exceeded; raw output withheld'
value = json.loads(raw)
assert set(value) == {'utc', 'root', 'files', 'processes', 'committed_rounds', 'last_event'}
assert value['root'] == 'D:/FEDUBA_MIXED_ATTACK_RECOVERY_RUN_20261101'
assert 'torch' not in sys.modules
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps({'state': 'passed_bounded_recovery_metadata_observation', 'response_characters': len(raw),
                  'model_queries': 0, 'finite_job_reexecuted': False, 'observation': value}, indent=2))
