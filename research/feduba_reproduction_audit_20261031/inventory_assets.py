"""Read-only bounded name inventory; does not select/load model tensors."""
import json
import os
from pathlib import Path

ROOTS = ['D:/', 'C:/Users/DISLAB/Documents/antigravity/dazzling-lovelace']
SKIP = {'.git', 'node_modules', 'envs', '.venv', 'venv', 'data', 'reader_deps',
        'reader_pinned', 'FEDUBA_REPRO_AUDIT_20261031', 'DETECTION_CLAIM_AUDIT_20261031'}
found, errors, counts = [], [], {}
for root in ROOTS:
    count = 0
    for parent, dirs, files in os.walk(root, onerror=lambda e: errors.append(str(e))):
        dirs[:] = [x for x in dirs if x not in SKIP]
        count += len(files)
        for name in dirs + files:
            if 'feduba' in name.lower():
                found.append(str(Path(parent) / name))
    counts[root] = count
result = {'schema': 'bounded-feduba-name-inventory-v1', 'roots': ROOTS,
          'excluded_names': sorted(SKIP), 'files_examined_by_name': counts,
          'matched_paths': found, 'errors': errors,
          'scope': 'Filename/dirname inventory only, not tensor provenance verification; unlabelled or excluded files may exist.'}
Path(__file__).with_name('ASSET_INVENTORY.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
