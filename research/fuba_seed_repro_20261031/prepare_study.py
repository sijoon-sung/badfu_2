"""One finite CPU preparation: fresh seeds, baseline source, no old weights."""
import copy
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
from study_common import ROOT, read, sha, write, once, verify_freeze, case_id


def changed_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def main():
    verify_freeze()
    once('PREPARE_ONCE.json')
    p = read(ROOT / 'PROFILE.json')
    assert p['new_seeds'] == random.Random(p['draw_seed']).sample(range(3, 10000003), 9)
    assert read(ROOT / 'STORAGE_CONTRACT.json')['state'] == 'passed'
    base = Path(p['baseline_review_root'])
    assert sha(base / 'DELIVERY_MANIFEST.json') == p['baseline_manifest_sha256']
    subprocess.run([sys.executable, 'D:/TRAJECTORY_CATALOG_20261023/select_case.py',
                    p['baseline_case_id'], '--purpose', 'diagnostic'], check=True)
    manifest = read(base / 'DELIVERY_MANIFEST.json')
    bp = read(base / 'PROFILE.json')
    assert bp['seed'] == p['baseline_seed'] and bp['partition_seed'] == p['baseline_partition_seed']
    names = ['common.py', 'reference_core.py', 'runner.py', 'test_contracts.py',
             'prepare.py', 'controller.py', 'verify.py', 'audit_committed.py', 'package_delivery.py',
             'CPU_CONTRACTS.json']
    for name in names:
        assert sha(base / name) == manifest['files'][name]['sha256'], name
    seeds_root = ROOT / 'seeds'
    seeds_root.mkdir(exist_ok=False)
    rows = []
    for seed in p['new_seeds']:
        dest = seeds_root / f'seed_{seed}'
        dest.mkdir(exist_ok=False)
        for name in names:
            shutil.copyfile(base / name, dest / name)
        shutil.copyfile(ROOT / 'storage_retry.py', dest / 'storage_retry.py')
        common = (dest / 'common.py').read_text(encoding='utf-8')
        assert common.count('os.replace(tmp, path)') == 2
        common = common.replace('os.replace(tmp, path)', 'replace_with_retry(tmp, path)')
        common = changed_once(common, 'import hashlib\n', 'import hashlib\nfrom storage_retry import replace_with_retry\n')
        (dest / 'common.py').write_text(common, encoding='utf-8', newline='\n')
        guard = (ROOT / 'guard_template.py').read_text(encoding='utf-8').replace('__CASE_ID__', case_id(seed))
        (dest / 'load_checkpoint.py').write_text(guard, encoding='utf-8', newline='\n')
        profile = copy.deepcopy(bp)
        profile.update(id=f'fuba.algorithm_sgd.mnist.dba.s{seed}.fl100.kd10.seed_repro20261031',
                       seed=seed, partition_seed=seed - 3, case_id=case_id(seed),
                       study=p['id'], baseline_source_case=p['baseline_case_id'],
                       storage_retry_only=True)
        write(dest / 'PROFILE.json', profile)
        shutil.copyfile(ROOT / 'PROTOCOL.txt', dest / 'PROTOCOL.txt')
        write(dest / 'CONTRACT_REUSE.json', {'state': 'passed', 'reused_not_reexecuted': True,
              'baseline_case_id': p['baseline_case_id'],
              'baseline_manifest_sha256': p['baseline_manifest_sha256'],
              'CPU_CONTRACTS_sha256': sha(dest / 'CPU_CONTRACTS.json'),
              'reference_core_unchanged_sha256': sha(dest / 'reference_core.py'),
              'test_contracts_unchanged_sha256': sha(dest / 'test_contracts.py')})
        exporter = (dest / 'package_delivery.py').read_text(encoding='utf-8')
        exporter = changed_once(exporter, '*FUBA_REFERENCE_MNIST_DBA_20261031*', '*" + ROOT.name + "*')
        exporter = changed_once(exporter, "manifest = ROOT / 'DELIVERY_MANIFEST.json'", "manifest = PACKET / 'DELIVERY_MANIFEST.json'")
        exporter = changed_once(exporter, "seal = ROOT / 'DELIVERY_SEAL.json'", "seal = PACKET / 'DELIVERY_SEAL.json'")
        exporter = changed_once(exporter, "'schema': 'fuba-mnist-dba-packet-v1', 'packet_root': str(PACKET),",
                  "'schema': 'fuba-seed-packet-v1', 'packet_root': str(PACKET),\n"
                  "          'case_id': read(ROOT / 'PROFILE.json')['case_id'], 'actual_pre_post_pair': True,\n"
                  "          'rounds': 100, 'KD_epochs': 10, 'KD_batches': 470,")
        (dest / 'package_delivery.py').write_text(exporter, encoding='utf-8', newline='\n')
        write(dest / 'SOURCE_PROVENANCE.json', {'baseline_manifest_sha256': p['baseline_manifest_sha256'],
              'unchanged': {n: sha(dest / n) for n in names if n not in ['common.py', 'package_delivery.py']},
              'changed': {'common.py': 'bounded Windows storage retry only',
                          'package_delivery.py': 'seed-specific path and internal delivery seals only'}})
        (dest / 'DELIVERY_PROTOCOL.txt').write_text(
            'R02/D08/D15/N02. One new completed seed packet; no training/inference in export.\n'
            'Keep complete raw history on DISLAB. Export selected strict-CPU tensors and all logs.\n'
            'Internal manifest/seal excluded from manifest inventory; externally pin their hashes.\n'
            'Local transfer and explicit catalogue registration remain required.\n', encoding='utf-8', newline='\n')
        write(dest / 'DELIVERY_SOURCE_FREEZE.json', {'files': {n: sha(dest / n) for n in
              ['package_delivery.py', 'load_checkpoint.py', 'DELIVERY_PROTOCOL.txt']}})
        freeze_names = names + ['storage_retry.py', 'load_checkpoint.py', 'PROFILE.json', 'PROTOCOL.txt',
                               'CONTRACT_REUSE.json', 'SOURCE_PROVENANCE.json', 'DELIVERY_PROTOCOL.txt',
                               'DELIVERY_SOURCE_FREEZE.json']
        write(dest / 'FREEZE.json', {'schema': 'fuba-new-seed-source-v1',
                                    'files': {n: sha(dest / n) for n in freeze_names}})
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='', PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
        subprocess.run([sys.executable, '-u', str(dest / 'prepare.py')], cwd=dest, env=env, check=True)
        ready = read(dest / 'READY.json')
        assert ready['state'] == 'passed' and ready['fresh_random_initialization']
        assert sha(dest / 'author_model.py') == bp['author_model_sha256']
        for name in ['reference_core.py', 'runner.py', 'test_contracts.py', 'prepare.py',
                     'controller.py', 'verify.py', 'audit_committed.py']:
            assert sha(dest / name) == sha(base / name), name
        rows.append({'seed': seed, 'root': str(dest), 'case_id': case_id(seed),
                     'profile_id': profile['id'], 'READY_sha256': sha(dest / 'READY.json'),
                     'FREEZE_sha256': sha(dest / 'FREEZE.json'), 'initial_sha256': sha(dest / 'initial.pt')})
        print(json.dumps({'state': 'seed_prepared', **rows[-1]}), flush=True)
    assert len({r['initial_sha256'] for r in rows}) == 9
    write(ROOT / 'PREPARED.json', {'state': 'passed', 'seeds': rows,
          'numeric_source_unchanged': True, 'baseline_not_rerun': True,
          'baseline_RESULT_sha256': sha(base / 'RESULT.json')})


if __name__ == '__main__':
    main()
