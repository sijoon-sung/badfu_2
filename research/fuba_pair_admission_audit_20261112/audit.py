"""Read-only endpoint admission and round arithmetic over sealed records."""
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT = Path(__file__).resolve().parent


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def counts(row, n):
    ca, asr = row['clean_correct'], row['target_successes']
    assert row.get('N', 10000) == 10000 and row['non_target_N'] == n
    assert 0 <= ca <= 10000 and 0 <= asr <= n
    for key, expected in [('CA_pct', ca/100), ('clean_acc_pct', ca/100), ('ASR_pct', asr*100/n)]:
        if key in row:
            assert math.isclose(row[key], expected, rel_tol=0, abs_tol=1e-10), key
    return ca, asr


def stages(packet, item):
    result = read(packet/'RESULT.json')
    n = item['non_target']
    before, after = (counts(result[k], n) for k in ('before', 'after'))
    independent = read(packet/item['independent'])
    if item['key'] == 'v5':
        pre = read(Path(item['v5_pre_independent']))
        pre_manifest = read(Path(item['v5_pre_manifest']))['files']
        assert pre['last_checkpoint_sha256'] == pre_manifest['checkpoint_round0100.pt']['sha256']
        assert pre_manifest['classifier.pt']['sha256'] == result['before_classifier_sha256']
        assert pre_manifest['aggregate_generator.pt']['sha256'] == result['fixed_generator_sha256']
        assert independent['before_classifier_sha256'] == result['before_classifier_sha256']
        assert independent['fixed_generator_sha256'] == result['fixed_generator_sha256']
        assert counts(pre, n) == before
        assert counts(independent['after'], n) == after
    elif item['key'] in ('v6', 'v7'):
        assert independent['same_G_sha256'] == result['same_G_sha256']
        for stage, expected in [('before', before), ('after', after)]:
            assert independent[stage]['classifier_sha256'] == result[f'{stage}_sha256']
            assert counts(independent[stage], n) == expected
    else:
        assert independent['rounds'] == 100 and result['KD_epochs'] == 10
        for stage, expected in [('before', before), ('after', after)]:
            assert counts(independent['independent_counts'][stage], n) == expected
    return before, after


def audit_case(item, entry):
    assert entry['seed'] == item['seed']
    assert entry['allowed_purposes'] == ['diagnostic']
    packet = Path(entry['source_root'])
    assert packet == Path(item['root'])
    profile = read(packet/'PROFILE.json')
    assert profile['seed'] == item['seed'] and profile.get('partition_seed') == item['partition_seed']
    evidence = read(packet/('MANIFEST.json' if item['key']=='v5' else 'DELIVERY_MANIFEST.json'))
    assert evidence['case_id'] == item['case_id'] and evidence['actual_pre_post_pair']
    for kind in ('pre','post'):
        model = entry['server_inputs'][kind]
        path = Path(model['path'])
        sealed = evidence['files'][path.relative_to(packet).as_posix()]
        assert sealed['sha256'] == model['sha256'] == digest(path)
        assert sealed['bytes'] == path.stat().st_size
    before, after = stages(packet, item)
    minimum, n = item['min_clean'], item['non_target']
    subtraction = counts(read(packet/item['subtraction']), n) if item.get('subtraction') else None
    rounds = []
    if item.get('round_dir'):
        directory = packet/item['round_dir']
        manifest = read(packet/'DELIVERY_MANIFEST.json')['files']
        for r in range(1, 101):
            p = directory/f'round{r:04}.json'
            m = manifest[p.relative_to(packet).as_posix()]
            assert digest(p) == m['sha256'] and p.stat().st_size == m['bytes'], str(p)
            ca, asr = counts(read(p), n)
            rounds.append(dict(round=r, clean_correct=ca, target_successes=asr))
        assert (rounds[-1]['clean_correct'], rounds[-1]['target_successes']) == before
    return dict(key=item['key'], case_id=item['case_id'], seed=item['seed'], condition=item['condition'],
        n=10000, non_target=n, clean_floor=minimum/100, before=before, after_subtraction=subtraction, after=after,
        partition_seed=item['partition_seed'], endpoint_hashes_verified=2,
        before_pass=before[0]>=minimum and before[1]*10<=n,
        after_pass=after[0]>=minimum and after[1]*5>=3*n,
        allowed_for_activation='retrain_activation' in entry['allowed_purposes'],
        round_count=len(rounds),
        rounds_clean_ok=sum(q['clean_correct']>=minimum for q in rounds) if rounds else None,
        rounds_suppressed=sum(q['target_successes']*10<=n for q in rounds) if rounds else None,
        rounds_both=sum(q['clean_correct']>=minimum and q['target_successes']*10<=n for q in rounds) if rounds else None,
        rounds=rounds)


def badfu_check(data):
    by = {(r['case'],r['round'],r['split']):r['scores']['pca'] for r in data['checkpoint_scores']}
    output = []
    for r in (10,20,30,40):
        for p in ('A','B'):
            n = {k:by[k,r,p] for k in ('c00','c01','c02','c03') if (k,r,p) in by}
            a = {k:by[k,r,p] for k in ('c04','c05')}
            output.append(dict(round=r,panel=p,normal=n,attack=a,min_attack_minus_max_normal=min(a.values())-max(n.values())))
    return output


def main():
    plan = read(ROOT/'PLAN.json')
    freeze = read(ROOT/'FREEZE.json')
    receipt = read(ROOT/'PUBLICATION.json')
    assert receipt['all_raw_blob_bytes_verified'] and digest(ROOT/'FREEZE.json')==receipt['freeze_sha256']
    assert all(digest(ROOT/n)==v for n,v in freeze['files'].items())
    for p,v in plan['references'].items():
        assert digest(Path(p))==v,p
    catalog = {e['id']:e for e in read(plan['catalog'])['cases']}
    assert {k for k,e in catalog.items() if e.get('family','').lower()=='fuba' and 'retrain_activation' in e.get('allowed_purposes',[])} == set()
    audits = [audit_case(q, catalog[q['case_id']]) for q in plan['packets']]
    assert len(audits)==5 and sum(a['round_count'] for a in audits)==400
    admissible = [q['case_id'] for q in audits if q['before_pass'] and q['after_pass'] and q['allowed_for_activation']]
    source = read(plan['badfu'])
    result = dict(state='passed_metadata_audit', fuba=audits, admitted=admissible, catalogue_sha256=digest(Path(plan['catalog'])),
        badfu_existing_detector=badfu_check(source), model_loads=0, new_inferences=0, new_training=0)
    (ROOT/'RESULT.json').open('xb').write((json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in result.items() if k!='fuba'}))


if __name__=='__main__':
    main()
