"""Audit P10 receipts and independently recalculate both classes of thresholds."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'receipts'
PREVIOUS = ROOT.parent / 'badfu_recovery_margin_real_20261115'
P09 = ROOT.parent / 'badfu_paired_svd_20261115'
NORMAL = ('normal193', 'normal228')
PATHS = ('balanced', 'client1_weighted')
STAGES = ('immediate', *PATHS)
ARMS = ('baseline', 'scale', 'endpoint', 'during')


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def utility(row, base):
    total = row['public']['correct'] - base['public']['correct']
    grouped = min(a-b for a,b in zip(row['public']['class_correct'], base['public']['class_correct'], strict=True))
    client = min(row['clients'][k]['correct'] - base['clients'][k]['correct'] for k in ('1','2','3'))
    assert row['public']['class_n'] == base['public']['class_n'] == [160] * 10
    assert row['public']['n'] == base['public']['n'] == 1600
    assert all(row['clients'][k]['n'] == base['clients'][k]['n'] == 160 for k in ('1','2','3'))
    return total >= -32 and grouped >= -8 and client >= -8


def verify(name):
    sel = read(OUT / f'{name}_SELECTION.json')
    data = read(OUT / f'{name}_RESULT.json')
    assert set(data['clean']) == set(data['archive']) == set(sel['stages']) == set(ARMS)
    for arm in ARMS:
        steps = sel['stages'][arm]
        assert len(steps) == 5
        norms = [step['applied_norm'] for step in steps]
        candidates = [step['candidate_count'] for step in steps]
        assert 0 <= sum(norms) <= sel['budget'] + 1e-5
        assert candidates == {'baseline': [0]*5, 'endpoint': [0,0,0,0,40]}.get(arm, [8]*5)
        if arm in ('scale','during'):
            assert all(v <= sel['budget'] / 5 + 1e-5 for v in norms)
        if arm == 'baseline':
            assert not any(norms) and not any(step['fresh_transport_recomputed'] for step in steps)
        for phase in STAGES:
            archive = data['archive'][arm][phase]
            assert archive['n'] == 1440 == archive['original_correct'] + archive['target'] + archive['other_wrong']
            assert archive['restored_at_immediate_still_correct'] <= archive['original_correct']
            assert archive['restored_at_immediate_still_correct'] <= data['archive'][arm]['immediate']['restored_at_immediate_still_correct']
    assert data['passed_normal'] == all(utility(data['clean']['during'][phase], data['clean']['baseline'][phase]) for phase in STAGES)
    print(name, 'normal utility', data['passed_normal'])
    return data


def main():
    remote = read(OUT / 'REMOTE_SHA256.json')
    for name, digest in remote.items():
        assert sha(OUT / name) == digest
    hashes = read(ROOT / 'FREEZE.json')
    assert read(OUT / 'STARTED.json')['source_sha256'] == hashes['run_history_direction.py']
    for name, digest in hashes.items():
        assert any(f.is_file() and sha(f) == digest for f in (ROOT/name, PREVIOUS/name, P09/name))
    assert read(OUT / 'DATA_RECEIPT.json') == read(PREVIOUS / 'receipts' / 'DATA_RECEIPT.json')
    assert read(OUT / 'PAIRS.json') == read(P09 / 'receipts' / 'PAIRS.json')
    summary = read(OUT / 'SUMMARY.json')
    normals = [verify(name)['passed_normal'] for name in NORMAL]
    recovered = False
    if all(normals):
        attack = verify('attack20')
        arc = attack['archive']
        recovered = attack['passed_normal'] and all(
            arc['baseline'][p]['target'] - arc['during'][p]['target'] >= 72
            and arc['during'][p]['original_correct'] - arc['baseline'][p]['original_correct'] >= 72
            and all(arc['during'][p]['restored_at_immediate_still_correct'] > arc[c][p]['restored_at_immediate_still_correct']
                    for c in ('scale','endpoint'))
            for p in PATHS
        )
        assert summary['state'] == 'complete' and summary['cases'] == [*NORMAL, 'attack20']
    else:
        assert summary['state'] == 'normal_gate_failed' and summary['cases'] == list(NORMAL)
        assert 'attack20_RESULT.json' not in remote
    assert summary['attack_effect_gate'] == recovered
    print(f'verified {len(remote)} receipts; effect gate={recovered}')


if __name__ == '__main__':
    main()
