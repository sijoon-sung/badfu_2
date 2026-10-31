"""Finite, read-only CPU check of all nine generated sources and profiles."""
import ast
import json
from pathlib import Path
import zipfile
from study_common import ROOT, read, sha, write, verify_freeze
from study_controller import resource_guard

verify_freeze()
assert not (ROOT / 'PREPARATION_AUDIT.json').exists()
p = read(ROOT / 'PROFILE.json')
base = Path(p['baseline_review_root'])
bp = read(base / 'PROFILE.json')
rows = []
for item in read(ROOT / 'PREPARED.json')['seeds']:
    root = Path(item['root'])
    q = read(root / 'PROFILE.json')
    for k, v in bp.items():
        if k not in ['id', 'seed', 'partition_seed']:
            assert q[k] == v, k
    assert q['partition_seed'] == q['seed'] - 3
    for path in root.glob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'))
    new = ast.parse((root / 'common.py').read_text(encoding='utf-8'))
    old = ast.parse((base / 'common.py').read_text(encoding='utf-8'))
    for x in [n for n in old.body if isinstance(n, ast.FunctionDef) and n.name not in ['write', 'save']]:
        y = next(n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == x.name)
        assert ast.dump(x) == ast.dump(y), x.name
    rows.append({'seed': q['seed'], 'numeric_config_unchanged': True, 'syntax_all_sources': True,
                 'nonstorage_common_functions_AST_identical': True,
                 'source_hashes': read(root / 'READY.json')['source_hashes']})
okay, resources = resource_guard()
write(ROOT / 'PREPARATION_AUDIT.json', {'state': 'passed', 'CPU_only': True, 'new_seed_count': 9,
      'rows': rows, 'resource_guard_passed': okay, 'resources': resources,
      'old_baseline_not_rerun': True, 'audit_source_sha256': sha(Path(__file__))})
with zipfile.ZipFile(ROOT / 'PREPARATION_METADATA.zip', 'x', compression=zipfile.ZIP_DEFLATED) as z:
    for name in ['PREPARED.json', 'PREPARATION_AUDIT.json', 'STORAGE_CONTRACT.json']:
        z.write(ROOT / name, name)
    for item in read(ROOT / 'PREPARED.json')['seeds']:
        root = Path(item['root'])
        for name in ['PROFILE.json', 'FREEZE.json', 'READY.json', 'CONTRACT_REUSE.json',
                     'SOURCE_PROVENANCE.json', 'DELIVERY_SOURCE_FREEZE.json']:
            z.write(root / name, 'prepared_profiles/seed_' + str(item['seed']) + '/' + name)
    root = Path(read(ROOT / 'PREPARED.json')['seeds'][0]['root'])
    for name in ['common.py', 'package_delivery.py', 'load_checkpoint.py']:
        z.write(root / name, 'generated_source_example/' + name)
write(ROOT / 'PREPARATION_RECEIPT.json', {'state': 'passed',
      'archive_sha256': sha(ROOT / 'PREPARATION_METADATA.zip'),
      'archive_bytes': (ROOT / 'PREPARATION_METADATA.zip').stat().st_size,
      'STUDY_FREEZE_sha256': sha(ROOT / 'STUDY_FREEZE.json')})
print(json.dumps({'state': 'passed', 'seeds': 9, 'numeric_config_unchanged': True, 'syntax': True,
                  'resource_guard_passed': okay, 'resources': resources}))
