"""One-time metadata registration and explicit catalogue selection; no torch."""
import copy
import json
import subprocess
import sys
from pathlib import Path
from checkpoint_guard import sha

ROOT = Path(__file__).resolve().parent
CAT = Path('D:/TRAJECTORY_CATALOG_20261023')
OLD_SHA = '8cbb86b98bf44cfa344daca6df1326f1b2fafe946c3eceb3cf75dd961a21ec38'
NEW_ID = 'badfu.s20261023.normal_largest0.dislab.endpoint_20261110'


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def main():
    (ROOT/'PREPARE_ONCE').open('x').write('metadata-only\n')
    original = (CAT/'catalog.json').read_bytes()
    assert sha(CAT/'catalog.json') == OLD_SHA
    cat = json.loads(original)
    before = copy.deepcopy(cat)
    assert len(cat['cases']) == 28 and all(c['id'] != NEW_ID for c in cat['cases'])
    confirmed = next(c for c in cat['cases'] if c['id'] == 'badfu.confirmed.s20261023.v1')
    pre = copy.deepcopy(confirmed['server_inputs']['clean_pre'])
    post = dict(path='D:/MULTISEED_ACTUAL_FU_20261022/badfu/seed_20261023/normal_largest0_FU/final.pt',
                sha256='f6ec46894135725df8fa2da260d9325d1dbdde397de88421cfcc7d965b1f5ba2', payload_key=None)
    files = {}
    for name, binding in [('pre', pre), ('post', post)]:
        assert sha(binding['path']) == binding['sha256']
        files[name] = dict(path=binding['path'], sha256=binding['sha256'], bytes=Path(binding['path']).stat().st_size)
    loader = ROOT/'checkpoint_guard.py'
    files[loader.name] = dict(sha256=sha(loader), bytes=loader.stat().st_size)
    write(ROOT/'GUARD_MANIFEST.json', dict(case_id=NEW_ID, files=files, purpose='diagnostic', model_mutations=0))
    write(ROOT/'GUARD_SEAL.json', dict(manifest_sha256=sha(ROOT/'GUARD_MANIFEST.json')))
    guard = dict(manifest_path=str(ROOT/'GUARD_MANIFEST.json'), manifest_sha256=sha(ROOT/'GUARD_MANIFEST.json'),
                 seal_path=str(ROOT/'GUARD_SEAL.json'), seal_sha256=sha(ROOT/'GUARD_SEAL.json'), loader_path=str(loader))
    entry = dict(id=NEW_ID, family='badfu', post_type='retained_data_retraining',
                 source_root=str(Path(post['path']).parent), allowed_purposes=['diagnostic'],
                 server_inputs=dict(pre=pre, post=post), checkpoint_guard=guard,
                 provenance='Existing 22.790% normal deletion, same SHA as 20261030 local endpoint audit; no new training/history approval')
    cat['cases'].append(entry)
    audit_path = CAT/'audit/NORMAL_LARGEST0_DISLAB_20261110.json'
    assert not audit_path.exists()
    write(audit_path, dict(previous_catalog_sha256=OLD_SHA, entry=entry, old_cases_preserved=True, old_defaults_preserved=True))
    cat.setdefault('supplemental_audits', []).append(dict(path='audit/'+audit_path.name, sha256=sha(audit_path)))
    assert cat['cases'][:-1] == before['cases']
    for key in before:
        if key not in ('cases', 'supplemental_audits'): assert cat[key] == before[key]
    (ROOT/'CATALOG_BEFORE.json').write_bytes(original)
    write(ROOT/'CATALOG_AFTER.json', cat)
    (CAT/'catalog.json').write_bytes((ROOT/'CATALOG_AFTER.json').read_bytes())
    specs = [('c00', confirmed['id'], 'retrain_activation', 'clean_pre', 'clean_big_post', 'badfu'),
             ('c01', NEW_ID, 'diagnostic', 'pre', 'post', 'badfu'),
             ('c02', confirmed['id'], 'retrain_activation', 'clean_pre', 'clean_post', 'badfu'),
             ('c03', 'badfu.paper32.s20261020', 'retrain_activation', 'pre', 'infected_benign_post', 'badfu'),
             ('c04', confirmed['id'], 'retrain_activation', 'pre', 'post', 'badfu'),
             ('c05', 'badfu.paper32.s20261020', 'retrain_activation', 'pre', 'post', 'badfu'),
             ('c06', 'fuba.v7.s20261023.pre100.post.kd10', 'diagnostic', 'pre', 'post', 'fuba')]
    for cid, condition in [('c07', 'benignfu20'), ('c08', 'minusrequestfu20'), ('c09', 'plusrequestfu20')]:
        specs.append((cid, 'feduba.public_fixed10.cifar10.s42.sss125.'+condition+'.20261103', 'diagnostic', 'pre', 'post', 'feduba'))
    cases = []; receipts = []
    for cid, case_id, purpose, pre_key, post_key, architecture in specs:
        result = subprocess.run([sys.executable, str(CAT/'select_case.py'), case_id, '--purpose', purpose],
                                capture_output=True, encoding='utf-8', check=True)
        selected = json.loads(result.stdout)
        receipts.append(selected)
        inputs = selected['server_inputs']
        cases.append(dict(id=cid, architecture=architecture, pre=inputs[pre_key], post=inputs[post_key]))
    write(ROOT/'SELECTED_CASES.json', receipts)
    write(ROOT/'INPUTS.json', dict(cases=cases))
    write(ROOT/'REGISTRATION.json', dict(old_sha256=OLD_SHA, new_sha256=sha(CAT/'catalog.json'),
                                       old_cases_preserved=True, old_defaults_preserved=True, cases=29,
                                       all_explicit_selections_passed=True, model_mutations=0))
    print('prepared: 10 explicit pairs; one diagnostic metadata append; zero model mutations')


if __name__ == '__main__':
    main()
