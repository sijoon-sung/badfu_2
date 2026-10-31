"""Append this delivered diagnostic case, preserving every old case/default/audit."""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--catalog-root', required=True)
    p.add_argument('--label', choices=['main', 'pr', 'dislab'], required=True)
    args = p.parse_args()
    here = Path(__file__).resolve().parent
    root = Path(args.catalog_root).resolve()
    entry = json.loads((here / 'CATALOG_ENTRY.json').read_text(encoding='utf-8'))
    audit_bytes = (here / 'CATALOG_AUDIT.json').read_bytes()
    name = 'FUBA_REFERENCE_MNIST_DBA_20261031_DELIVERY.json'
    rel = 'audit/' + name
    cat_path = root / 'catalog.json'
    old_bytes = cat_path.read_bytes()
    old = json.loads(old_bytes.decode('utf-8'))
    assert not any(c['id'] == entry['id'] for c in old['cases']), 'Case already registered; inspect instead of repeating'
    new = copy.deepcopy(old)
    target = root / rel
    assert not target.exists()
    with target.open('xb') as stream:
        stream.write(audit_bytes)
    supplemental = {'path': rel, 'sha256': hashlib.sha256(audit_bytes).hexdigest(), 'case_id': entry['id']}
    new['supplemental_audits'].append(supplemental)
    new['cases'].append(entry)
    assert new['cases'][:-1] == old['cases'] and new['supplemental_audits'][:-1] == old['supplemental_audits']
    assert all(new[k] == old[k] for k in old if k not in ['cases', 'supplemental_audits'])
    backup = here / f'CATALOG_BEFORE_{args.label}.json'
    with backup.open('xb') as stream:
        stream.write(old_bytes)
    temp = cat_path.with_name('catalog.reference_case.tmp')
    with temp.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(new, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    assert cat_path.read_bytes() == old_bytes, 'Catalogue changed concurrently'
    temp.replace(cat_path)
    view = root / entry['folder'] / 'README.md'
    view.parent.mkdir(parents=True, exist_ok=False)
    view.write_text('# FUBA MNIST/DBA diagnostic pair\n\n'
                    f"Fixed case `{entry['id']}`. Allowed purpose: diagnostic only.\n\n"
                    'Actual100R/KD10 and stored models/logs verified; both performance gates failed. '
                    'Before CA99.11/ASR30.60048748; after CA99.08/ASR32.35098604.\n\n'
                    f"Original remote review copy: {entry['source_root']}\n\n"
                    f"Local copy: {entry['local_copy']['root']}\n\n"
                    'Select this explicit case through select_case.py; verify its external seal and declared payload_key. '
                    'Full raw/all phase tensors remain on DISLAB. Existing defaults are unchanged. '
                    'This is neither CIFAR/IBA reproduction success nor D08/D15 non-IID detection evidence.\n',
                    encoding='utf-8', newline='\n')
    print(json.dumps({'state': 'registered', 'label': args.label, 'case_id': entry['id'],
                     'old_cases_preserved': len(old['cases']), 'defaults_and_old_audits_unchanged': True,
                     'audit_sha256': supplemental['sha256']}))


if __name__ == '__main__':
    main()
