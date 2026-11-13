"""Independent SVD and row-difference/input-difference verification; no CNN."""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = Path('D:/BADFU_FEDUBA_DEFENSE_20261031')


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    import numpy as np
    import torch
    torch.set_num_threads(2)
    result = read(args.results / 'RESULT.json')
    completion = read(SOURCE / 'stage03/COMPLETED.json')
    original = read(SOURCE / 'stage03/RESULT.json')
    manifest = read(SOURCE / 'INPUT_MANIFEST.json')
    for n in ['head_states.pt', 'clean_predictions.pt']:
        assert sha(SOURCE / 'inputs' / n) == manifest['cache_files'][n]
    heads = torch.load(SOURCE / 'inputs/head_states.pt', weights_only=True, map_location='cpu')
    labels = torch.load(SOURCE / 'inputs/clean_predictions.pt', weights_only=True, map_location='cpu')['labels'].numpy()
    info = read(SOURCE / 'STAGE03_INPUTS.json')
    assert sha(info['record_path']) == info['record_path_sha256']
    record = torch.load(info['record_path'], weights_only=False, map_location='cpu')
    ids = np.asarray(list(record['bd_test']['bd_data_container']['data_dict']), dtype=np.int64)
    del record
    refs = read(HERE / 'REFERENCE_IDS.json')
    ref = next(r for r in refs if r['n'] == 50 and r['sampling'] == 'balanced' and r['draw'] == 0)['image_ids']
    checks = []
    for row in result['rows']:
        pair = row['pair']
        def features(flag):
            entry = next(r for r in original['rows'] if r['pair'] == pair and r['W'] == r['BN'] == r['head'] == flag)
            p = SOURCE / 'stage03' / entry['feature_path']
            assert sha(p) == completion['files'][p.name]
            raw = torch.load(p, weights_only=True, map_location='cpu')
            return {k: v.numpy().astype(np.float64) for k, v in raw.items()}
        a, b = features(0), features(1)
        old = heads['weights'][row['pre_role']].numpy().astype(np.float64)
        new = heads['weights'][row['post_role']].numpy().astype(np.float64)
        h = a['clean'][ref]
        _, singular, right = np.linalg.svd(h - h.mean(0), full_matrices=False)
        k = int(np.searchsorted(np.cumsum(singular ** 2) / sum(singular ** 2), .95)) + 1
        assert k == row['k']
        basis = right[:k].T
        y = labels[ids]
        dweight = new - old
        drows = dweight[0] - dweight[y]
        source_rows = new[0] - new[y]
        input_change = a['attack'] - a['clean'][ids]
        representation_change = (b['attack'] - a['attack']) - (b['clean'][ids] - a['clean'][ids])
        direct_head = np.einsum('nd,nd->n', drows, input_change)
        direct_parallel = np.einsum('nk,nk->n', drows @ basis, input_change @ basis)
        direct_perpendicular = direct_head - direct_parallel
        direct_body = np.einsum('nd,nd->n', source_rows, representation_change)
        p = args.results / row['private_path']
        assert sha(p) == row['private_sha256']
        with np.load(p, allow_pickle=False) as z:
            assert np.array_equal(z['labels'], y)
            assert len(y) == 9000 and np.isfinite(z['interaction']).all()
            errors = [float(np.max(np.abs(actual - z[name]))) for actual, name in [
                (direct_parallel, 'parallel'), (direct_perpendicular, 'perpendicular'),
                (direct_body, 'body'), (direct_head + direct_body, 'interaction')]]
            assert max(errors) <= 1e-8, (pair, errors)
            assert np.all(z['constant'] == 0)
            assert int(z['witness'].sum()) == row['new_semantic_witness_n']
            witness = z['clean_ok'] & (z['before_prediction'] == y) & (z['after_prediction'] == 0)
            assert np.array_equal(witness, z['witness'])
            assert int((witness & (z['without_perp_prediction'] == 0)).sum()) == row['witness_without_perp_still_target_n']
            assert int((witness & (z['perpendicular'] < 0)).sum()) == row['witness_perp_opposes_n']
            for sr in row['source_rows']:
                mask = y == sr['source']
                assert int((mask & witness).sum()) == sr['new_semantic_witness_n']
                assert int((mask & (z['after_prediction'] == 0)).sum()) == sr['after_target_n']
                assert abs(math.fsum(z['interaction'][mask].tolist()) / int(mask.sum()) - sr['interaction_mean']) <= 1e-10
            assert sum(r['new_semantic_witness_n'] for r in row['source_rows']) == row['new_semantic_witness_n']
            for name in ['perp_only', 'without_perp', 'body_only']:
                assert int((z[name + '_prediction'] == 0).sum()) == row[name + '_target_n']
        checks.append(dict(pair=pair, separate_SVD_scalar_inner_product_maxabs=errors,
                           all_input_rows_checked=9000, class_rows_checked=9))
    for p, digest in result['used_feature_hashes'].items():
        assert sha(p) == digest
    receipt = dict(state='passed', result_sha256=sha(args.results / 'RESULT.json'),
                   checks=checks, new_model_forward=0, independent_training_seeds=0)
    with (args.results / 'CHECKED.json').open('x', encoding='utf-8', newline='\n') as f:
        json.dump(receipt, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps(receipt), flush=True)


if __name__ == '__main__':
    main()
