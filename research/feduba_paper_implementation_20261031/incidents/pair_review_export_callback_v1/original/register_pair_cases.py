"""Append two diagnostic endpoints to each host's own catalogue, preserving prior bytes/evidence."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import argparse
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode = True
from pair_review_common import ROOT, CASES, read, write, digest, freeze, verify


def main():
    freeze()
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog-root', type=Path, required=True)
    parser.add_argument('--host-label', choices=['main', 'pr', 'dislab'], required=True)
    parser.add_argument('--local-ledger', type=Path)
    args = parser.parse_args()
    remote = read(ROOT / 'PAIR_REVIEW_DELIVERY_REMOTE.json')
    local = read(args.local_ledger) if args.local_ledger else None
    assert (args.host_label != 'dislab') == (local is not None)
    if local:
        assert local['state'] == 'local_delivery_complete' and local['case_ids'] == CASES
        assert all(local[k] == remote[k] for k in ['manifest_sha256', 'seal_sha256', 'archive_sha256', 'archive_bytes'])
    packet = Path((local or remote)['packet_root']); primary = Path(remote['packet_root'])
    assert digest(packet / 'DELIVERY_SEAL.json') == remote['seal_sha256']
    guard = verify(packet, remote['manifest_sha256'])
    metadata, scope = read(packet / 'DELIVERY_MANIFEST.json'), read(packet / 'DELIVERY_SCOPE.json')
    evaluated = read(packet / 'evidence/root/PAIR_EVAL_VERIFIED.json')
    assert evaluated['state'] == 'passed' and not evaluated['minimum_operational_gate']['passed']
    assert scope['local_full_history_use_approved'] is False
    catroot = args.catalog_root.resolve(); path = catroot / 'catalog.json'
    original_bytes = path.read_bytes(); original_sha = digest(path)
    original = json.loads(original_bytes); catalogue = copy.deepcopy(original)
    assert not any(c['id'] in CASES.values() for c in original['cases']), 'Already registered; inspect completion ledger'
    prior_audits = {p.relative_to(catroot).as_posix(): digest(p) for p in (catroot / 'audit').rglob('*') if p.is_file()}
    ledger = ROOT / 'registrations' / ('pair_' + args.host_label); ledger.mkdir(parents=True, exist_ok=False)
    (ledger / 'catalog_before.json').write_bytes(original_bytes)
    audit_name = 'FEDUBA_PAIR_S42_CPU_SSS125_FU20_20261031_DELIVERY.json'
    audit = catroot / 'audit' / audit_name
    write(audit, {'state': 'verified_diagnostic_pair_delivery_performance_failed', 'case_ids': CASES,
          'host_label': args.host_label, 'archive_sha256': remote['archive_sha256'], 'archive_bytes': remote['archive_bytes'],
          'manifest_sha256': remote['manifest_sha256'], 'seal_sha256': remote['seal_sha256'], 'guard': guard,
          'scope': scope, 'CPU_evidence_sha256': metadata['files']['CPU_VERIFIED.json']['sha256'],
          'evaluated_metrics': evaluated['models'], 'minimum_operational_gate': evaluated['minimum_operational_gate'],
          'prior_catalogue_sha256': original_sha, 'prior_case_count': len(original['cases']),
          'all_prior_external_audits_sha256': prior_audits, 'local_delivery_complete': local is not None,
          'original_export_receipt_modified': False, 'detection_success_implied': False})
    audit.chmod(0o444)
    catalogue.setdefault('supplemental_audits', []).append({'path': 'audit/' + audit_name, 'sha256': digest(audit)})
    def checkpoint_guard(root):
        return {'manifest_path': str(root / 'DELIVERY_MANIFEST.json'), 'manifest_sha256': remote['manifest_sha256'],
                'seal_path': str(root / 'DELIVERY_SEAL.json'), 'seal_sha256': remote['seal_sha256'],
                'loader_path': str(root / 'load_checkpoint.py')}
    def inputs(root, branch):
        return {key: {'path': str(root / filename), 'sha256': remote['models'][source]['sha256'], 'payload_key': None}
                for key, source, filename in [('pre', 'pre', 'run/before.pt'), ('post', branch, f'run/{branch}_after.pt')]}
    for branch, case_id in CASES.items():
        folder = f'05_diagnostic/{case_id}'
        case = {'id': case_id, 'folder': folder, 'title': f'FedUBA CPU trigger / SSS125 / actual {branch} FedEraser20 diagnostic',
                'family': 'feduba_declared_paper_CPU_trigger', 'source_root': 'D:/FEDUBA_PAPER_IMPLEMENTATION_20261031',
                'integrity': 'both_FU20_full_CPU_and_all10000_three_models_independently_verified_readonly_packet',
                'reproduction': 'failed_minimum_latent_activation_performance_gate', 'seed': 42,
                'post_type': f'actual_FedEraser20_{branch}_same_selected_source_IDs', 'allowed_purposes': ['diagnostic'],
                'related_cards': ['R03', 'R02', 'N02', 'D08', 'D15'], 'server_inputs': inputs(primary, branch),
                'checkpoint_guard': checkpoint_guard(primary),
                'history_scope': {'raw_root': f'D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/fu/{branch}',
                   'manifest_sha256': metadata['files'][f'evidence/fu/{branch}/MANIFEST.json']['sha256'],
                   'representative_role_tensors_only_in_packet': True, 'local_history_use_approved': False,
                   'role_payload_key': 'model', 'global_payload_key': None},
                'evaluator_only': {'metrics': evaluated['models'], 'target': 2, 'trigger_multiplier': 1.5,
                   'trigger': {'path': str(primary / 'run/delta.pt'), 'sha256': remote['delta']['sha256'], 'payload_key': None},
                   'minimum_operational_gate': evaluated['minimum_operational_gate'],
                   'paired_control_case_id': CASES['benign' if branch == 'attack' else 'attack'],
                   'verified_stealth_latent_pair': False, 'original_GPU_STG_audit_remains_failed': True},
                'evidence': ['audit/' + audit_name]}
        if local:
            case['local_copy'] = {'root': str(packet), 'server_inputs': inputs(packet, branch),
                                  'checkpoint_guard': checkpoint_guard(packet)}
        catalogue['cases'].append(case)
        view = catroot / folder; view.mkdir(parents=True, exist_ok=False)
        (view / 'README.md').write_text('Diagnostic FedUBA declared CPU-trigger / SSS125 paired FedEraser20.\n\n'
              'Both actual20R branches and independent full10000 evaluation completed; latent activation performance gates failed. '
              'Private readonly packet includes endpoints, fixed representative real contributions/optimizer/RNG and full logs/query/evaluation evidence. '
              'Whole original histories remain on DISLAB. Local full-history consumption is not approved. '
              'All prior cases/defaults/audits and original GPU-STG failure remain preserved.\n', encoding='utf-8', newline='\n')
    assert catalogue['cases'][:-2] == original['cases']
    assert catalogue['supplemental_audits'][:-1] == original.get('supplemental_audits', [])
    for key in original:
        if key not in ['cases', 'supplemental_audits']: assert catalogue[key] == original[key]
    assert digest(path) == original_sha
    # Preserve the host's UTF8 display convention, indentation and newline style.
    text = original_bytes.decode('utf-8'); match = re.search(r'\n( +)"', text)
    indent = len(match[1]) if match else 2
    rendered = json.dumps(catalogue, ensure_ascii=not any(ord(c) > 127 for c in text), indent=indent, allow_nan=False)
    if text.endswith('\n'): rendered += '\n'
    if '\r\n' in text: rendered = rendered.replace('\n', '\r\n')
    temp = path.with_name('catalog.pair_append.tmp'); temp.write_bytes(rendered.encode('utf-8'))
    assert digest(path) == original_sha; os.replace(temp, path)
    env = os.environ.copy(); env.update(PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    selections, denied = {}, []
    for branch, case_id in CASES.items():
        command = [sys.executable, '-B', str(catroot / 'select_case.py'), case_id,
                   '--location', 'local' if local else 'dislab']
        output = subprocess.check_output(command + ['--purpose', 'diagnostic'], env=env, text=True, encoding='utf-8')
        selected = json.loads(output); assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
        assert selected['server_inputs'] == inputs(packet, branch)
        selections[branch] = selected
        for purpose in ['retrain_activation', 'client_history']:
            rejected = subprocess.run(command + ['--purpose', purpose], env=env, capture_output=True)
            assert rejected.returncode != 0; denied.append({'case_id': case_id, 'purpose': purpose, 'exit_code': rejected.returncode})
    assert all(digest(catroot / name) == sha for name, sha in prior_audits.items())
    after = read(path); assert after['cases'][:-2] == original['cases']
    write(ledger / 'REGISTERED.json', {'state': 'registered_two_diagnostic_cases', 'host_label': args.host_label,
          'case_ids': CASES, 'old_case_count': len(original['cases']), 'new_case_count': len(after['cases']),
          'all_old_cases_defaults_and_audits_preserved': True, 'catalogue_sha256': digest(path),
          'external_audit_sha256': digest(audit), 'selections': selections, 'unapproved_purposes_denied': denied})


if __name__ == '__main__': main()
