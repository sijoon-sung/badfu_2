"""Append one delivered seed case to each host's own catalogue, preserving history."""
import argparse
import copy
import json
from pathlib import Path
from study_common import ROOT, read, sha, write


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--catalog-root', type=Path, required=True)
    p.add_argument('--evidence-dir', type=Path, required=True)
    p.add_argument('--label', choices=['main', 'pr', 'dislab'], required=True)
    args = p.parse_args()
    for name, digest in read(ROOT / 'DELIVERY_TOOLS_FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest, name
    root, evidence = args.catalog_root.resolve(), args.evidence_dir.resolve()
    entry = json.loads((evidence / 'CATALOG_ENTRY.json').read_text(encoding='utf-8'))
    audit_bytes = (evidence / 'CATALOG_AUDIT.json').read_bytes()
    path = root / 'catalog.json'
    old_bytes = path.read_bytes()
    old = json.loads(old_bytes.decode('utf-8'))
    assert sha(root / 'audit/AUDIT.json') == old['audit_sha256']
    for audit in old['supplemental_audits']:
        target = (root / audit['path']).resolve()
        assert target.is_relative_to((root / 'audit').resolve()) and sha(target) == audit['sha256']
    assert not any(c['id'] == entry['id'] for c in old['cases']), 'Already registered; inspect guard instead'
    new = copy.deepcopy(old)
    audit_rel = f"audit/FUBA_SEED_REPRO_S{entry['seed']}_20261031_DELIVERY.json"
    target = root / audit_rel
    assert not target.exists()
    backup = evidence / f'CATALOG_BEFORE_{args.label}.json'
    with backup.open('xb') as stream:
        stream.write(old_bytes)
    with target.open('xb') as stream:
        stream.write(audit_bytes)
    supplemental = {'path': audit_rel, 'sha256': sha(target), 'case_id': entry['id']}
    new['supplemental_audits'].append(supplemental)
    new['cases'].append(entry)
    assert new['cases'][:-1] == old['cases']
    assert new['supplemental_audits'][:-1] == old['supplemental_audits']
    assert all(new[k] == old[k] for k in old if k not in ['cases', 'supplemental_audits'])
    view = root / entry['folder'] / 'README.md'
    assert view.resolve().is_relative_to(root)
    view.parent.mkdir(parents=True, exist_ok=False)
    r = json.loads((evidence / 'RESULT.json').read_text(encoding='utf-8'))
    view.write_text('# FUBA MNIST/DBA seed diagnostic pair\n\n'
                    f"Case `{entry['id']}`. Allowed purpose: diagnostic only. R02/D08/D15/N02.\n\n"
                    f"Actual100R/KD10. Before CA{r['before']['CA_pct']}/ASR{r['before']['ASR_pct']}; "
                    f"after CA{r['after']['CA_pct']}/ASR{r['after']['ASR_pct']}. "
                    f"Registered gates: before={r['before_gate']}, after={r['after_gate']}.\n\n"
                    f"Remote review copy: {entry['source_root']}\n\nLocal copy: {entry['local_copy']['root']}\n\n"
                    'Bare endpoint payload_key=null. Selected tensors and all logs are sealed; full raw phases remain on DISLAB. '
                    'Existing defaults/cases/audits are unchanged. Select explicit case through select_case.py. '
                    'Declared Algorithm-SGD interpretation; not author-certified unique code, ten-seed mean, CIFAR/IBA success, '
                    'or trigger-independent non-IID detection.\n', encoding='utf-8', newline='\n')
    assert path.read_bytes() == old_bytes, 'Catalogue changed concurrently; preserve evidence and stop'
    write(path, new)
    output = evidence / f'REGISTRATION_{args.label}.json'
    assert not output.exists()
    write(output, {'state': 'registered', 'case_id': entry['id'], 'label': args.label,
          'old_cases_preserved': len(old['cases']), 'old_audits_preserved': len(old['supplemental_audits']),
          'defaults_unchanged': True, 'audit_sha256': supplemental['sha256'], 'source_sha256': sha(Path(__file__))})
    print(json.dumps({'state': 'registered', 'label': args.label, 'case_id': entry['id'],
                      'old_cases_preserved': len(old['cases']), 'defaults_unchanged': True}))


if __name__ == '__main__':
    main()
