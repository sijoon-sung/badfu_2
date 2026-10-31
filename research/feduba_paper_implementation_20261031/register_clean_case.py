"""Append one diagnostic normal case to each host's own catalogue; preserve defaults."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
from runtime_common import ROOT, read, write, sha, freeze_check

CASE = 'feduba.paper.cifar10.cleanfl20.s42.20261031'


def main():
    freeze_check('CLEAN_REGISTRATION_FREEZE.json')
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog-root', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--local-ledger', type=Path)
    parser.add_argument('--host-label', choices=['main', 'pr', 'dislab'], required=True)
    args = parser.parse_args()
    catroot = args.catalog_root.resolve()
    remote = read(args.receipt)
    assert remote['case_id'] == CASE and remote['state'] == 'exported_verified_normal_review'
    local = read(args.local_ledger) if args.local_ledger else None
    assert (args.host_label != 'dislab') == (local is not None)
    chosen = local if local else remote
    if local:
        assert local['state'] == 'local_delivery_complete' and local['case_id'] == CASE
        assert all(local[k] == remote[k] for k in ['manifest_sha256', 'seal_sha256', 'archive_sha256', 'archive_bytes'])
    packet = Path(chosen['packet_root'])
    assert sha(packet / 'DELIVERY_MANIFEST.json') == remote['manifest_sha256']
    assert sha(packet / 'DELIVERY_SEAL.json') == remote['seal_sha256']
    metadata = read(packet / 'DELIVERY_MANIFEST.json')
    assert sha(packet / 'load_checkpoint.py') == metadata['files']['load_checkpoint.py']['sha256']
    spec = importlib.util.spec_from_file_location('registration_review_guard', packet / 'load_checkpoint.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    guard_state = module.verify(packet, remote['manifest_sha256'])
    catalogue_path = catroot / 'catalog.json'
    old_bytes = catalogue_path.read_bytes(); old_sha = sha(catalogue_path)
    old = json.loads(old_bytes); catalogue = copy.deepcopy(old)
    assert not any(c['id'] == CASE for c in catalogue['cases']), 'Case already registered; inspect instead of repeating append'
    ledger = ROOT / 'registrations' / ('clean_' + args.host_label)
    ledger.mkdir(parents=True, exist_ok=False)
    (ledger / 'catalog_before.json').write_bytes(old_bytes)
    evidence = {'state': 'normal_foundation_delivery_verified', 'case_id': CASE, 'host_label': args.host_label,
                'archive_sha256': remote['archive_sha256'], 'archive_bytes': remote['archive_bytes'],
                'manifest_sha256': remote['manifest_sha256'], 'seal_sha256': remote['seal_sha256'],
                'packet_total_files': remote['packet_total_files'], 'guard': guard_state,
                'CPU_evidence': read(packet / 'CPU_VERIFIED.json'),
                'scope': read(packet / 'DELIVERY_SCOPE.json'), 'local_ledger': local,
                'prior_catalogue_sha256': old_sha, 'prior_case_count': len(old['cases']),
                'normal_only_no_backdoor_pair': True}
    audit_name = 'FEDUBA_CLEANFL20_S42_20261031_DELIVERY.json'
    audit_path = catroot / 'audit' / audit_name
    assert not audit_path.exists()
    write(audit_path, evidence)
    audit_path.chmod(0o444)
    catalogue.setdefault('supplemental_audits', []).append({'path': 'audit/' + audit_name, 'sha256': sha(audit_path)})
    primary = Path(remote['packet_root'])
    def checkpoint_guard(root):
        return {'manifest_path': str(root / 'DELIVERY_MANIFEST.json'), 'manifest_sha256': remote['manifest_sha256'],
                'seal_path': str(root / 'DELIVERY_SEAL.json'), 'seal_sha256': remote['seal_sha256'],
                'loader_path': str(root / 'load_checkpoint.py')}
    pre = {'path': str(primary / 'run/before.pt'), 'sha256': remote['pre']['sha256'], 'payload_key': None}
    folder = '05_diagnostic/FedUBA_cleanFL20_s42_20261031'
    case = {'id': CASE, 'folder': folder, 'title': 'FedUBA CIFAR10 정상 FL20 기반 모델·진단 전용',
            'family': 'feduba_clean_foundation', 'source_root': 'D:/FEDUBA_PAPER_IMPLEMENTATION_20261031',
            'integrity': 'passed_actual20R_200roles_all_CPU_history_independent10000_and_readonly_packet',
            'reproduction': 'normal_only_no_STG_SSS_BEA_or_unlearning_pair', 'seed': 42,
            'post_type': 'none_clean_pre_only', 'allowed_purposes': ['diagnostic'],
            'related_cards': ['R03', 'R02', 'N02', 'D08', 'D15'],
            'server_inputs': {'pre': pre}, 'checkpoint_guard': checkpoint_guard(primary),
            'history_scope': {'raw_root': 'D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/clean_fl',
                'manifest_sha256': metadata['files']['evidence/clean_fl/MANIFEST.json']['sha256'],
                'all200_role_tensors_only_on_DISLAB': True, 'local_history_use_approved': False,
                'role_payload_key': 'model', 'global_payload_key': None},
            'evaluator_only': {'N': 10000, 'clean_correct': evidence['CPU_evidence']['clean_correct'],
                'CA_pct': evidence['CPU_evidence']['CA_pct'], 'ASR_measured': False, 'actual_attack_pair': False},
            'evidence': ['audit/' + audit_name]}
    if local:
        case['local_copy'] = {'root': str(packet), 'server_inputs': {'pre': {
            'path': str(packet / 'run/before.pt'), 'sha256': remote['pre']['sha256'], 'payload_key': None}},
            'checkpoint_guard': checkpoint_guard(packet)}
    catalogue['cases'].append(case)
    assert catalogue['cases'][:-1] == old['cases']
    assert catalogue['supplemental_audits'][:-1] == old.get('supplemental_audits', [])
    for key in old:
        if key not in ['cases', 'supplemental_audits']: assert catalogue[key] == old[key], key
    assert sha(catalogue_path) == old_sha, 'Concurrent catalogue modification'
    write(catalogue_path, catalogue)
    view = catroot / folder; view.mkdir(parents=True, exist_ok=False)
    (view / 'README.md').write_text('# FedUBA normal FL20 diagnostic foundation\n\nActual20R/200roles/2000epochs/40000batches; independent CA87.95% (8795/10000). No ASR or attack/unlearning pair.\n\nThe readonly review packet contains initial/pre plus one last-role optimizer/RNG payload and all epoch logs/evidence. All200 role tensors remain at the registered original DISLAB path. Local endpoint copies do not authorize history consumption. BadFU defaults and all previous cases/audits are preserved.\n', encoding='utf-8', newline='\n')
    env = os.environ.copy(); env.update(PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    location = 'local' if local else 'dislab'
    command = [sys.executable, '-B', str(catroot / 'select_case.py'), CASE]
    output = subprocess.check_output(command + ['--purpose', 'diagnostic', '--location', location], env=env, text=True, encoding='utf-8')
    selected = json.loads(output)
    assert selected['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selected['server_inputs']['pre']['sha256'] == remote['pre']['sha256']
    denied = []
    for purpose in ['retrain_activation', 'client_history']:
        result = subprocess.run(command + ['--purpose', purpose, '--location', location], env=env, capture_output=True, text=True, encoding='utf-8')
        assert result.returncode != 0
        denied.append({'purpose': purpose, 'exit_code': result.returncode, 'message': result.stdout + result.stderr})
    report = {'state': 'registered_diagnostic_only', 'case_id': CASE, 'host_label': args.host_label,
              'old_case_count': len(old['cases']), 'new_case_count': len(catalogue['cases']),
              'all_old_cases_defaults_and_audits_preserved': True, 'catalogue_sha256': sha(catalogue_path),
              'external_audit_sha256': sha(audit_path), 'selection': selected, 'unapproved_purposes_denied': denied}
    write(ledger / 'REGISTERED.json', report)
    print(json.dumps({k: report[k] for k in ['state', 'host_label', 'old_case_count', 'new_case_count']}))


if __name__ == '__main__': main()
