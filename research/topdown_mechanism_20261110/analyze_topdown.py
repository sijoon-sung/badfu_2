"""Native cached behavior first, then exact margin channels; CPU-only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SOURCE = Path('D:/BADFU_FEDUBA_DEFENSE_20261031')
PAIRS = [('attack_cover850', 'pre', 'post'), ('benign_same850', 'clean_pre', 'clean_post'),
         ('benign_big19336', 'clean_pre', 'clean_big_post')]


def sha(p):
    digest = hashlib.sha256()
    with Path(p).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def write(p, data):
    with Path(p).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    freeze = read(HERE / 'FREEZE.json')
    for name, digest in freeze['files'].items():
        assert sha(HERE / name) == digest, name
    args.output.mkdir(exist_ok=False)
    write(args.output / 'STARTED.json', dict(pid=os.getpid(), source_freeze=sha(HERE / 'FREEZE.json')))
    for entry in read(HERE / 'REMOTE_CACHE_METADATA.json'):
        assert sha(SOURCE / entry['name']) == entry['sha256'], entry['name']
    selection = json.loads(subprocess.check_output([
        sys.executable, 'D:/TRAJECTORY_CATALOG_20261023/select_case.py',
        'badfu.confirmed.s20261023.v1', '--purpose', 'retrain_activation'], text=True, encoding='utf-8'))
    assert selection['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    write(args.output / 'SELECTED_CASE.json', selection)
    import numpy as np
    import torch
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    assert os.environ.get('CUDA_VISIBLE_DEVICES') == '-1'
    manifest = read(SOURCE / 'INPUT_MANIFEST.json')
    complete = read(SOURCE / 'stage03/COMPLETED.json')
    report = read(SOURCE / 'stage03/RESULT.json')
    assert sha(SOURCE / 'stage03/RESULT.json') == complete['result_sha256']
    def cache(name):
        p = SOURCE / 'inputs' / name
        assert sha(p) == manifest['cache_files'][name]
        return torch.load(p, map_location='cpu', weights_only=True)
    heads = cache('head_states.pt')
    clean = cache('clean_predictions.pt')
    labels = clean['labels'].numpy().astype(np.int64)
    info = read(SOURCE / 'STAGE03_INPUTS.json')
    assert sha(info['record_path']) == info['record_path_sha256']
    record = torch.load(info['record_path'], map_location='cpu', weights_only=False)
    entries = record['bd_test']['bd_data_container']['data_dict']
    ids = np.asarray([int(k) for k in entries], dtype=np.int64)
    assert len(ids) == 9000 and sorted(ids.tolist()) == np.flatnonzero(labels != 0).tolist()
    assert all(int(v['other_info'][0]) == 0 for v in entries.values())
    del record
    refs = read(HERE / 'REFERENCE_IDS.json')
    ref = next(r for r in refs if r['n'] == 50 and r['sampling'] == 'balanced' and r['draw'] == 0)['image_ids']
    literal = read(SOURCE / 'NATIVE_REFERENCE.json')['metrics']
    used = {}
    def features(pair, before):
        flag = 0 if before else 1
        row = next(r for r in report['rows'] if r['pair'] == pair and r['W'] == r['BN'] == r['head'] == flag)
        p = SOURCE / 'stage03' / row['feature_path']
        assert sha(p) == complete['files'][p.name]
        used[str(p)] = complete['files'][p.name]
        data = torch.load(p, map_location='cpu', weights_only=True)
        assert tuple(data['clean'].shape) == (10000, 512) and tuple(data['attack'].shape) == (9000, 512)
        converted = {key: value.numpy().astype(np.float64) for key, value in data.items()}
        assert all(np.isfinite(value).all() for value in converted.values())
        return converted
    rows = []
    for pair, a, b in PAIRS:
        pre, post = features(pair, True), features(pair, False)
        w0, w1 = (heads['weights'][r].numpy().astype(np.float64) for r in [a, b])
        b0, b1 = (heads['biases'][r].numpy().astype(np.float64) for r in [a, b])
        zc0, zc1 = pre['clean'] @ w0.T + b0, post['clean'] @ w1.T + b1
        za0, za1 = pre['attack'] @ w0.T + b0, post['attack'] @ w1.T + b1
        for role, zc, za in [(a, zc0, za0), (b, zc1, za1)]:
            assert int((zc.argmax(1) == labels).sum()) == literal[role]['clean_correct']
            expected_target = round(literal[role]['ASR_pct'] * 90)
            assert int((za.argmax(1) == 0).sum()) == expected_target, role
        h = pre['clean'][ref]
        mu = h.mean(0)
        eigen, vectors = np.linalg.eigh((h - mu) @ (h - mu).T)
        order = np.argsort(eigen)[::-1]
        eigen, vectors = eigen[order], vectors[:, order]
        positive = eigen > eigen[0] * 1e-12
        eigen, vectors = eigen[positive], vectors[:, positive]
        k = int(np.searchsorted(np.cumsum(eigen) / eigen.sum(), .95)) + 1
        v = (h - mu).T @ vectors[:, :k] / np.sqrt(eigen[:k])[None, :]
        dw = w1 - w0
        dp = (dw @ v) @ v.T
        dq = dw - dp
        def terms(h0, h1):
            return [(h0 - mu) @ dp.T, (h0 - mu) @ dq.T,
                    (h1 - h0) @ w1.T,
                    np.broadcast_to(dw @ mu + b1 - b0, (len(h0), 10))]
        tc, ta = terms(pre['clean'], post['clean']), terms(pre['attack'], post['attack'])
        error = max(float(np.max(np.abs(sum(tc) - (zc1 - zc0)))),
                    float(np.max(np.abs(sum(ta) - (za1 - za0)))))
        assert error <= 1e-8
        y = labels[ids]
        ix = np.arange(len(y))
        margin = lambda z: z[ix, 0] - z[ix, y]
        interaction = margin(za1 - za0) - margin(zc1[ids] - zc0[ids])
        channels = [margin(x) - margin(c[ids]) for x, c in zip(ta, tc)]
        interaction_error = float(np.max(np.abs(sum(channels) - interaction)))
        assert interaction_error <= 1e-8 and np.max(np.abs(channels[3])) == 0
        clean_ok = (zc0[ids].argmax(1) == y) & (zc1[ids].argmax(1) == y)
        witness = clean_ok & (za0.argmax(1) == y) & (za1.argmax(1) == 0)
        perp_only = (za0 + ta[1]).argmax(1)
        without_perp = (za1 - ta[1]).argmax(1)
        body_only = (za0 + ta[2]).argmax(1)
        source_rows = []
        for c in range(1, 10):
            mask = y == c
            source_rows.append(dict(source=c, n=int(mask.sum()), clean_both_correct_n=int((mask & clean_ok).sum()),
                before_target_n=int(((za0.argmax(1) == 0) & mask).sum()),
                after_target_n=int(((za1.argmax(1) == 0) & mask).sum()),
                new_semantic_witness_n=int((mask & witness).sum()),
                interaction_mean=float(interaction[mask].mean()),
                channel_means=[float(x[mask].mean()) for x in channels]))
        private = args.output / ('private_' + pair + '.npz')
        np.savez(private, labels=y, interaction=interaction, parallel=channels[0], perpendicular=channels[1],
                 body=channels[2], constant=channels[3], witness=witness,
                 clean_ok=clean_ok, before_prediction=za0.argmax(1), after_prediction=za1.argmax(1),
                 perp_only_prediction=perp_only, without_perp_prediction=without_perp,
                 body_only_prediction=body_only)
        row = dict(pair=pair, pre_role=a, post_role=b, clean_correct_before=int((zc0.argmax(1) == labels).sum()),
            clean_correct_after=int((zc1.argmax(1) == labels).sum()), n_clean=10000, n_condition=9000,
            condition_target_before=int((za0.argmax(1) == 0).sum()), condition_target_after=int((za1.argmax(1) == 0).sum()),
            new_semantic_witness_n=int(witness.sum()),
            witness_without_perp_still_target_n=int((witness & (without_perp == 0)).sum()),
            perp_only_target_n=int((perp_only == 0).sum()), without_perp_target_n=int((without_perp == 0).sum()),
            body_only_target_n=int((body_only == 0).sum()), k=k,
            channel_interaction_means=[float(x.mean()) for x in channels],
            interaction_mean=float(interaction.mean()),
            witness_perp_opposes_n=int((witness & (channels[1] < 0)).sum()),
            logit_decomposition_maxabs=error, interaction_maxabs=interaction_error,
            source_rows=source_rows, private_path=private.name, private_sha256=sha(private))
        rows.append(row)
        print(json.dumps({k: row[k] for k in ['pair', 'new_semantic_witness_n', 'witness_without_perp_still_target_n', 'perp_only_target_n', 'body_only_target_n', 'channel_interaction_means']}), flush=True)
    for path, digest in used.items():
        assert sha(path) == digest
    write(args.output / 'RESULT.json', dict(state='passed', evaluator='native_cached_conditional_margin_channels_v1',
        rows=rows, used_feature_hashes=used, checkpoint_case=selection['case_id'], post_type=selection['post_type'],
        actual_trigger_is_evaluator_only=True, new_model_forward=0, new_training=0, independent_FL_seeds=1,
        deployment_detector_status='unvalidated_unknown_condition_acquisition_and_independent_benign_calibration_missing'))


if __name__ == '__main__':
    main()
