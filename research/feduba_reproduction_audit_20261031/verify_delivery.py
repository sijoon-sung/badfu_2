"""Verify saved receipts, without repeating source-function execution."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parent
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
freeze = json.loads((root / 'FREEZE.json').read_text(encoding='utf-8'))
for name, expected in freeze['files'].items():
    assert digest(root / name) == expected, name
r = json.loads((root / 'RESULTS.json').read_text(encoding='utf-8'))
assert r['freeze_sha256'] == digest(root / 'FREEZE.json')
assert r['training_started'] is False and r['gpu_used'] is False
assert len(r['source']) == 9
for name, expected in r['source'].items():
    assert digest(root / 'upstream_author' / name) == expected['sha256'], name
for module, missing in [('Fed_Unlearn_main', 'utils'), ('trigger_generate_function', 'models')]:
    attempt = r['original_import_attempts'][module]
    assert attempt['returncode'] != 0
    assert "No module named '" + missing + "'" in attempt['stderr']
assert r['sensitivity_identity_contract'][0]['positions_matching_oracle'] == 0
assert r['sensitivity_identity_contract'][1]['positions_matching_oracle'] == 32
assert r['client_identity_contract']['attacker_client_ids_in_FL_and_FU'] == [5, 7]
assert r['client_identity_contract']['client_ids_used_by_surrogate_target_data_helper'] == [2, 3]
assert not (root / 'audit_stderr.txt').read_text(encoding='utf-8-sig').strip()
inventory = json.loads((root / 'ASSET_INVENTORY.json').read_text(encoding='utf-8'))
summary = {k: inventory[k] for k in ['schema', 'roots', 'excluded_names', 'files_examined_by_name', 'scope']}
summary.update(matched_path_count=len(inventory['matched_paths']), error_count=len(inventory['errors']),
               raw_inventory_sha256=digest(root / 'ASSET_INVENTORY.json'),
               completeness='incomplete_name_inventory_no_global_absence_claim')
(root / 'ASSET_SUMMARY.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
public_files = ['PROTOCOL.txt', 'FREEZE.json', 'audit_feduba.py', 'inventory_assets.py',
                'verify_delivery.py', 'RESULTS.json', 'STARTED.json', 'ASSET_SUMMARY.json',
                'CODE_PAPER_MATRIX.txt', 'DETECTION_GATES.txt', 'REPORT_KO.txt']
receipt = {'schema': 'feduba-saved-receipt-verification-v1', 'state': 'passed',
           'checked_utc': datetime.now(timezone.utc).isoformat(),
           'preregistered_commit': '23159e615cd19e8d6b93c569c1110206da9ca2df',
           'no_audit_rerun': True, 'no_model_training_or_evaluation': True,
           'files_sha256': {n: digest(root / n) for n in public_files}}
(root / 'DISLAB_VERIFICATION.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'state': receipt['state'], 'checked_files': len(public_files),
                  'inventory_errors': summary['error_count'], 'inventory_matches': summary['matched_path_count']}))
