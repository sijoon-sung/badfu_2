"""Frozen DISLAB CPU intervention screen, then one predeclared head repair."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import traceback

import torch

HERE = Path(__file__).resolve().parent
PAIRS = [('benign_big19336', 'clean_pre', 'clean_big_post'),
         ('benign_same850', 'clean_pre', 'clean_post'),
         ('attack_cover850_clean_only', 'pre', 'post')]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                       allow_nan=False) + '\n', encoding='utf8')


def fit_transport(features, targets, initial):
    """No true labels, target IDs, triggers, ASR, or request truth accepted."""
    x = torch.cat([features.double(), torch.ones(len(features), 1)], 1)
    gram = x.T @ x
    ridge = .01 * float(gram.trace()) / x.shape[1]
    residual = targets.double() - x @ initial
    correction = torch.linalg.solve(gram + ridge * torch.eye(x.shape[1]), x.T @ residual)
    fitted = initial + correction
    assert torch.isfinite(fitted).all()
    return fitted, ridge


def evaluate(logits, labels, pre, post, ids):
    y = labels[ids]
    pred = logits[ids].argmax(1)
    pred_pre = pre[ids].argmax(1)
    pred_post = post[ids].argmax(1)
    beneficial = (pred_pre != y) & (pred_post == y)
    harmful = (pred_pre == y) & (pred_post != y)
    class_counts = [int(((pred == y) & (y == c)).sum()) for c in range(10)]
    class_n = [int((y == c).sum()) for c in range(10)]
    return {'n': len(ids), 'correct': int((pred == y).sum()),
            'ca_pct': 100 * float((pred == y).double().mean()),
            'class_correct': class_counts, 'class_n': class_n,
            'class_ca_pct': [100*a/n for a,n in zip(class_counts,class_n)],
            'post_beneficial_n': int(beneficial.sum()),
            'post_beneficial_kept_n': int(((pred == y) & beneficial).sum()),
            'post_beneficial_kept_fraction': float((pred[beneficial] == y[beneficial]).double().mean()) if beneficial.any() else 1.,
            'post_harmful_n': int(harmful.sum()),
            'post_harmful_repaired_n': int(((pred == y) & harmful).sum()),
            'disagree_with_post_n': int((pred != pred_post).sum())}


def gate(candidate, baseline, benign):
    overall_drop = baseline['ca_pct'] - candidate['ca_pct']
    drops = [a-b for a,b in zip(baseline['class_ca_pct'], candidate['class_ca_pct'])]
    return {'overall_drop_pp': overall_drop, 'worst_class_drop_pp': max(drops),
            'overall_pass': overall_drop <= .5 + 1e-10,
            'class_pass': max(drops) <= 2. + 1e-10,
            'beneficial_pass': not benign or candidate['post_beneficial_kept_fraction'] >= .9,
            'passed': overall_drop <= .5 + 1e-10 and max(drops) <= 2. + 1e-10 and
                      (not benign or candidate['post_beneficial_kept_fraction'] >= .9)}


def main():
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    freeze = json.loads((HERE / 'FREEZE.json').read_text(encoding='utf8'))
    for n,h in freeze['files'].items():
        assert sha(HERE/n) == h, ('frozen source changed', n)
    manifest = json.loads((HERE/'INPUT_MANIFEST.json').read_text(encoding='utf8'))
    for n,h in manifest['cache_files'].items():
        assert sha(HERE/'inputs'/n) == h, ('input mismatch',n)
    with (HERE/'STAGE01_STARTED.json').open('x',encoding='utf8') as f:
        json.dump({'pid':os.getpid(),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   'freeze_sha256':sha(HERE/'FREEZE.json')},f)
    load = lambda n: torch.load(HERE/'inputs'/n,map_location='cpu',weights_only=True)
    heads = load('head_states.pt')
    truth = load('clean_predictions.pt')
    labels = truth['labels'].long()
    assert labels.shape == (10000,)
    features = {r:load('features_'+r+'.pt').double() for r in heads['weights']}
    native = {r:load('logits_'+r+'.pt').double() for r in heads['weights']}
    audit = {}
    for r in features:
        z = features[r] @ heads['weights'][r].double().T + heads['biases'][r].double()
        error = float((z-native[r]).abs().max())
        disagreements = int((z.argmax(1) != truth['predictions'][r]).sum())
        assert torch.isfinite(features[r]).all() and torch.isfinite(z).all()
        assert error <= 2e-5 and disagreements == 0, (r,error,disagreements)
        audit[r] = {'reconstruction_max_error':error,'argmax_mismatch_n':disagreements}
    generator = torch.Generator().manual_seed(20261031)
    permutation = torch.randperm(10000,generator=generator)
    fit_ids, test_ids = permutation[:500],permutation[500:]
    write('PROXY_SPLIT.json',{'fit_ids':fit_ids.tolist(),'heldout_ids':test_ids.tolist(),
                             'new_external_test_set':False,'labels_used_by_fit':False})
    stage1 = {}
    predictions = {}
    for name,a,b in PAIRS:
        hybrid = features[a] @ heads['weights'][b].double().T + heads['biases'][b].double()
        baseline = evaluate(native[b],labels,native[a],native[b],test_ids)
        metric = evaluate(hybrid,labels,native[a],native[b],test_ids)
        stage1[name] = {'post':baseline,'hybrid':metric,'gate':gate(metric,baseline,name.startswith('benign')),
                        'full10000_hybrid':evaluate(hybrid,labels,native[a],native[b],torch.arange(10000))}
        predictions[name] = hybrid.argmax(1)
    write('STAGE01_RESULT.json',{'hypothesis':'H1','cases':stage1,
          'passed':all(v['gate']['passed'] for v in stage1.values()),'calculation_audit':audit,
          'evaluator':'cached_float64_head_transport_v1','new_classifier_forward':False,
          'attack_ASR_measured':False,'formal_deletion_measured':False})
    if not all(v['gate']['passed'] for v in stage1.values()):
        stage2 = {}
        for name,a,b in PAIRS:
            initial = torch.cat([heads['weights'][b].double().T,heads['biases'][b].double()[None]],0)
            transported,ridge = fit_transport(features[a][fit_ids], native[b][fit_ids], initial)
            z = features[a] @ transported[:-1] + transported[-1]
            metric = evaluate(z,labels,native[a],native[b],test_ids)
            path = HERE/('transport_'+name+'.pt')
            torch.save({'weight':transported[:-1].T.contiguous(),'bias':transported[-1].contiguous(),
                        'source_backbone_role':a,'source_head_role':b,'ridge':ridge},path)
            stage2[name] = {'metrics':metric,'gate':gate(metric,stage1[name]['post'],name.startswith('benign')),
                            'ridge':ridge,'derived_head_sha256':sha(path),
                            'full10000':evaluate(z,labels,native[a],native[b],torch.arange(10000))}
        write('STAGE02_RESULT.json',{'hypothesis':'H2','trigger':'H1 failed; predeclared repair',
              'cases':stage2,'passed':all(v['gate']['passed'] for v in stage2.values()),
              'attack_ASR_measured':False,'formal_deletion_measured':False,
              'fit_uses_true_labels':False,'fit_uses_attack_metadata':False})
    torch.save(predictions,HERE/'hybrid_predictions.pt')
    write('COMPLETED.json',{'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'python':platform.python_version(),'torch':torch.__version__,'host':platform.node(),
          'cpu_threads':2,'cuda_used':False,'training_seeds_added':0,
          'files':{p.name:sha(p) for p in HERE.iterdir() if p.is_file() and p.name not in
                   ['COMPLETED.json','STAGE01_STARTED.json']}})
    print(json.dumps({'H1':all(v['gate']['passed'] for v in stage1.values()),
                      'H2':all(v['gate']['passed'] for v in stage2.values()) if 'stage2' in locals() else None}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        write('FAILURE.json',{'traceback':traceback.format_exc()})
        raise
