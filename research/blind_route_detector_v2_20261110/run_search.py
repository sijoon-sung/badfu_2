"""One finite search: all calibration selections sealed before any test score."""
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    from checkpoint_guard import sha
    from resource_guard import admit
    cfg = json.loads((ROOT/'PROFILE.json').read_text(encoding='utf-8'))
    (ROOT/'SEARCH_ONCE').open('x').write(str(os.getpid()))
    freeze = json.loads((ROOT/'FREEZE.json').read_text(encoding='utf-8'))
    for name, digest in freeze['files'].items(): assert sha(ROOT/name) == digest, name
    from probe_reference import write
    write(ROOT/'ADMISSION_SEARCH.json', admit(cfg))
    import torch
    from route_core import (ARMS, FAMILIES, Transform, Endpoint, load_native, settings, seed,
                            public_data, score, train, tensor_sha, load_transform, release, loss_from_logits, four_routes)
    settings(cfg)
    data, indices = public_data(cfg, 'cuda')
    write(ROOT/'PUBLIC_SPLIT.json', indices)
    inputs = json.loads((ROOT/'INPUTS.json').read_text(encoding='utf-8'))
    selections = []; fixtures = []; begin = time.time()
    # CPU algebra contract with synthetic differentiable logits; no checkpoint inference.
    generator = torch.Generator().manual_seed(19)
    a = torch.randn(4, 10, generator=generator, requires_grad=True)
    b = torch.randn(4, 10, generator=generator, requires_grad=True)
    y = torch.tensor([0, 1, 2, 3]); t = torch.tensor([9, 8, 7, 6])
    baseline = loss_from_logits(a, a, b, b, y, t, 'baseline')
    route = loss_from_logits(a, a, b, b, y, t, 'route')
    ga = torch.autograd.grad(baseline, (a, b), retain_graph=True)
    gb = torch.autograd.grad(route, (a, b))
    assert torch.allclose(baseline, route, atol=1e-7, rtol=1e-7)
    assert all(torch.equal(u, v) for u, v in zip(ga, gb))
    write(ROOT/'ALGEBRA_CONTRACT.json', dict(same_head_loss=True, same_head_gradient=True))
    for case in inputs['cases']:
        folder = ROOT/'artifacts'/case['id']; folder.mkdir(parents=True, exist_ok=True)
        native0, digest0 = load_native(case['pre'], case['architecture'], 'cuda')
        native1, digest1 = load_native(case['post'], case['architecture'], 'cuda')
        pre, post = Endpoint(native0, case['architecture']), Endpoint(native1, case['architecture'])
        x, y = data['fit']; xx = x[:4].detach().clone().requires_grad_(True)
        z0, z1 = pre(xx), post(xx)
        error = max(float((z0-pre.head(pre.feature)).abs().max()), float((z1-post.head(post.feature)).abs().max()))
        assert error <= 1e-5
        gradient = torch.autograd.grad(z0.square().mean()+z1.square().mean(), xx)[0]
        assert torch.isfinite(gradient).all() and gradient.abs().max() > 0
        # Integration contract against isolated head copies without capture hooks.
        reference0 = torch.nn.Linear(pre.head.in_features, pre.head.out_features, bias=pre.head.bias is not None).cuda().requires_grad_(False)
        reference1 = torch.nn.Linear(post.head.in_features, post.head.out_features, bias=post.head.bias is not None).cuda().requires_grad_(False)
        reference0.load_state_dict(pre.head.state_dict(), strict=True)
        reference1.load_state_dict(post.head.state_dict(), strict=True)
        four = four_routes(pre, post, xx)
        saved0, saved1 = pre.feature, post.feature
        direct = (reference0(saved0), reference1(saved0), reference0(saved1), reference1(saved1))
        cross_error = max(float((a-b).abs().max()) for a,b in zip(four, direct))
        assert cross_error <= 1e-5 and pre.feature is saved0 and post.feature is saved1
        loss_a = loss_from_logits(*four, y[:4], (y[:4]+1)%10, 'route')
        loss_b = loss_from_logits(*direct, y[:4], (y[:4]+1)%10, 'route')
        grad_a = torch.autograd.grad(loss_a, xx, retain_graph=True)[0]
        grad_b = torch.autograd.grad(loss_b, xx)[0]
        assert torch.allclose(grad_a, grad_b, atol=1e-7, rtol=1e-5)
        seed(cfg['seed']); identity_check = Transform('additive', cfg).cuda()
        same = score(pre, pre, identity_check, *data['calibration'])
        assert all(row['witness'] == 0 for row in same)
        fixtures.append(dict(case=case['id'], native_head_maxabs=error, cross_head_maxabs=cross_error,
                             four_route_input_gradient_matches_isolated_heads=True, input_gradient_finite=True, same_model_witness=0))
        del xx, z0, z1, gradient, identity_check, reference0, reference1, four, direct, saved0, saved1, loss_a, loss_b, grad_a, grad_b
        pre.feature = post.feature = None
        candidates = {arm: [] for arm in ARMS}
        for family in FAMILIES:
            initial_hashes = []
            for arm in ARMS:
                seed(cfg['seed']); transform = Transform(family, cfg).cuda()
                out = folder/(family+'_'+arm+'.pt')
                reused = out.exists()
                if reused:
                    assert arm == 'baseline' and case['id'] in ('c00','c01')
                    reused_transform = load_transform(family, cfg, out, 'cuda')
                    transform.load_state_dict(reused_transform.state_dict(), strict=True)
                    del reused_transform
                else:
                    train(pre, post, transform, cfg, arm, family, x, y, out)
                initial_hashes.append(json.loads(out.with_suffix('.json').read_text())['initial_tensor_sha256'])
                cal_path = folder/(family+'_'+arm+'_calibration.json')
                if reused:
                    rows = json.loads(cal_path.read_text())
                else:
                    rows = score(pre, post, transform, *data['calibration'])
                    write(cal_path, rows)
                candidates[arm].extend(dict(family=family, **row, payload=str(out), payload_sha256=sha(out)) for row in rows)
                del transform
            assert initial_hashes[0] == initial_hashes[1]
        for arm in ARMS:
            # Python max retains first item: fixed family order, then target order.
            chosen = max(candidates[arm], key=lambda row: row['score'])
            selections.append(dict(case=case['id'], arm=arm, chosen=chosen))
        assert tensor_sha(native0.state_dict()) == digest0 and tensor_sha(native1.state_dict()) == digest1
        release(pre, post); del pre, post, native0, native1
    write(ROOT/'FIXTURES.json', fixtures)
    write(ROOT/'SELECTIONS.json', selections)
    selection_sha = sha(ROOT/'SELECTIONS.json')
    write(ROOT/'SELECTION_SEAL.json', dict(sha256=selection_sha, time=time.time(), all_case_choices_before_test=True))
    results = []
    for case in inputs['cases']:
        native0, digest0 = load_native(case['pre'], case['architecture'], 'cuda')
        native1, digest1 = load_native(case['post'], case['architecture'], 'cuda')
        pre, post = Endpoint(native0, case['architecture']), Endpoint(native1, case['architecture'])
        for selection in [s for s in selections if s['case'] == case['id']]:
            chosen = selection['chosen']; assert sha(chosen['payload']) == chosen['payload_sha256']
            transform = load_transform(chosen['family'], cfg, chosen['payload'], 'cuda')
            row = score(pre, post, transform, *data['test'], targets=[chosen['target']])[0]
            results.append(dict(case=case['id'], arm=selection['arm'], family=chosen['family'], **row,
                                attack_decision=None, status='calibration_required'))
            del transform
        assert tensor_sha(native0.state_dict()) == digest0 and tensor_sha(native1.state_dict()) == digest1
        release(pre, post); del pre, post, native0, native1
    assert sha(ROOT/'SELECTIONS.json') == selection_sha
    write(ROOT/'RESULT.json', dict(results=results, selection_sha256=selection_sha, seconds=time.time()-begin,
                                  torch=torch.__version__, cuda=torch.version.cuda, model_mutations=0,
                                  true_trigger_inputs=0, role_truth_inputs=0, independent_verification_pending=True))
    write(ROOT/'STATE.json', dict(state='search_complete', pid=os.getpid(), seconds=time.time()-begin))
    print('search_complete', flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='strict')
    try:
        main()
    except BaseException:
        (ROOT/'SEARCH_FAILURE.txt').write_text(traceback.format_exc(), encoding='utf-8')
        print(traceback.format_exc(), flush=True)
        raise
