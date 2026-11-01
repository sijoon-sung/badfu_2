"""Repeatable bounded metadata reader; never runs the finite audit."""
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
frozen = json.loads((HERE / 'CPU_AUDIT_FREEZE.json').read_text(encoding='utf-8'))
for name in ['observe_cpu_status.py', 'QUERY_CPU_STATUS.ps1']:
    assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == frozen['files'][name]
sys.path.insert(0, str(HERE.parent / '00_trajectories'))
import dislab_audit
raw = dislab_audit.remote((HERE / 'QUERY_CPU_STATUS.ps1').read_text(encoding='utf-8'))
assert len(raw) <= 16000, 'Bounded observer response exceeded; raw output withheld'
value = json.loads(raw)
assert set(value) == {'utc', 'root', 'files', 'processes'}
assert value['root'] == 'D:/FEDUBA_MIXED_ATTACK_PREFIX_GUARD_V2_20261101'
assert 'torch' not in sys.modules
sys.stdout.reconfigure(encoding='utf-8')
print(json.dumps({'state': 'passed_bounded_CPU_audit_metadata_observation', 'response_characters': len(raw),
                  'model_queries': 0, 'finite_audit_executed_by_observer': False, 'observation': value}, indent=2))
