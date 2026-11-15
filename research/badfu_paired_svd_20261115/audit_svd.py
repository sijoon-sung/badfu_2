"""Verify SVD receipts, independent count gates and unchanged baselines."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'receipts'
P07 = ROOT.parent / 'badfu_recovery_margin_real_20261115'
P08 = ROOT.parent / 'badfu_anchor_attack_diagnostic_20261115'
CASES = {'normal193': 9668, 'normal228': 11395, 'attack23': 850, 'attack20': 850}
ATTACK = ('attack23', 'attack20')
PATHS = ('balanced', 'client1_weighted')


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def utility(reference, evaluated):
    assert len(reference) == len(evaluated) == 13
    overall, grouped, clients = [], [], []
    for x, y in zip(reference, evaluated, strict=True):
        a, b = x['public'], y['public']
        assert a['n'] == b['n'] == 1600 and a['class_n'] == b['class_n'] == [160] * 10
        for item in (a, b):
            assert sum(item['class_correct']) == item['correct']
        overall.append(b['correct'] - a['correct'])
        grouped.extend(q-p for p,q in zip(a['class_correct'], b['class_correct'], strict=True))
        for k in ('1', '2', '3'):
            assert x['clients'][k]['n'] == y['clients'][k]['n'] == 160
            clients.append(y['clients'][k]['correct'] - x['clients'][k]['correct'])
    return {'worst_overall_pp': 100 * min(overall) / 1600, 'worst_class_pp': 100 * min(grouped) / 160,
            'worst_client_pp': 100 * min(clients) / 160, 'auc_distance_increase': None,
            'passed': min(overall) >= -32 and min(grouped) >= -8 and min(clients) >= -8}


def verify_case(name, summary, p08):
    assert load(OUT / f'{name}_SUMMARY.json') == summary
    fit = load(OUT / f'{name}_FIT.json')
    result = load(OUT / f'{name}_RESULT.json')
    assert fit == result['fit'] and fit['policies'] == summary['policies']
    entry = load(P07 / 'INPUTS.json')['models'][name]
    assert fit['model_sha256'] == entry['sha256']
    actual = result['paths']
    assert set(actual) == {'none', 'svd', 'random'}
    assert fit['proposals_clipped'] == 12
    for arm, trajectories in actual.items():
        for route, r in trajectories.items():
            assert r['extra_max'] <= fit['epsilon'] + 1e-10
            assert utility(actual['none'][route]['clean'], r['clean']) == summary['gates'][arm][route]
            for target in r['archive'].values():
                assert target['n'] == 1440
                assert sum(target[k] for k in ('target', 'original_correct', 'other_wrong')) == 1440
    svd = fit['policies']['svd']
    if name in ATTACK:
        assert not fit['exact_zero_residual'] and fit['numerical_rank_checked'] == 4
        assert (svd['rank'], svd['alpha']) == (fit['policies']['random']['rank'], fit['policies']['random']['alpha'])
    else:
        assert fit['exact_zero_residual'] and svd['rank'] == svd['alpha'] == 0.
        assert actual['none'] == actual['svd'] and svd['head_sha256'] == fit['policies']['none']['head_sha256']
    assert svd['proxy_pass']
    stages = {'immediate': ('balanced', 'immediate', 0), **{p: (p, 'final', -1) for p in PATHS}}
    passed = all(x['passed'] for x in summary['gates']['svd'].values())
    for stage, (path, time, t) in stages.items():
        rows = summary['counts'][stage]
        for arm, paths in actual.items():
            assert rows[arm] == {'archive': paths[path]['archive'][time], 'clean': paths[path]['clean'][t]['public']['correct']}
        s, b = rows['svd']['archive'], rows['none']['archive']
        drop = b['target'] - s['target']
        gain = s['original_correct'] - b['original_correct']
        assert summary['gains'][stage] == {'asr_drop_pp': 100 * drop / 1440, 'original_gain_pp': 100 * gain / 1440}
        if name in ATTACK:
            old = p08['cases'][name]
            assert b == old['comparison'][stage]['none']
            assert rows['none']['clean'] == old['clean_correct_of_1600'][stage]['none']
            if t == -1:
                passed = passed and drop >= 72 and gain >= 72
    if name not in ATTACK:
        old = load(P07 / 'receipts' / f'{name}_RESULT.json')['clean']['none']
        for path in PATHS:
            for item, saved in zip(actual['none'][path]['clean'], old[path], strict=True):
                assert item['public'] == saved['public'] and item['clients'] == saved['clients']
    assert passed == summary['passed']
    print(name, svd['rank'], svd['alpha'], passed)
    return passed


def main():
    files = load(OUT / 'REMOTE_SHA256.json')
    for f, digest in files.items():
        assert sha(OUT / f) == digest, f
    freeze = load(ROOT / 'FREEZE.json')
    for f, digest in freeze.items():
        assert any(path.is_file() and sha(path) == digest for path in (ROOT / f, P07 / f)), f
    assert load(OUT / 'STARTED.json')['runner_sha256'] == freeze['run_svd.py']
    assert load(OUT / 'DATA_RECEIPT.json') == load(P07 / 'receipts' / 'DATA_RECEIPT.json')
    pairs = load(OUT / 'PAIRS.json')
    for name, n in CASES.items():
        assert pairs[name]['source_identity_pairs'] == pairs[name]['original_label_matches'] == n
        assert pairs[name]['nonidentical_pairs'] == (n if name in ATTACK else 0)
    assert pairs['attack23']['index_sha256'] == pairs['attack20']['index_sha256']
    result = load(OUT / 'SUMMARY.json')
    assert result['state'] == 'complete'
    p08 = load(P08 / 'receipts' / 'SUMMARY.json')
    all_pass = all([verify_case(k, result['cases'][k], p08) for k in CASES])
    assert all_pass == result['passed']
    print(f'verified {len(files)} remote receipts, paired indices and unchanged blind baselines; gate={all_pass}')


if __name__ == '__main__':
    main()
