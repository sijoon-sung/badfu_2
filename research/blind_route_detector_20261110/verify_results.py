"""Independent native inference/counts, no capture hooks or primary score function."""
import json
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    from checkpoint_guard import sha
    from resource_guard import admit
    from probe_reference import write
    cfg = json.loads((ROOT/'PROFILE.json').read_text())
    (ROOT/'VERIFY_ONCE').open('x').write(str(os.getpid()))
    write(ROOT/'ADMISSION_VERIFY.json', admit(cfg))
    import torch
    from route_core import load_native, load_transform, settings
    settings(cfg)
    raw = torch.load(cfg['raw_data'], map_location='cpu', weights_only=True)
    split = json.loads((ROOT/'PUBLIC_SPLIT.json').read_text())
    bindings = json.loads((ROOT/'INPUTS.json').read_text())['cases']
    selections = json.loads((ROOT/'SELECTIONS.json').read_text())
    primary = json.loads((ROOT/'RESULT.json').read_text())
    assert sha(ROOT/'SELECTIONS.json') == primary['selection_sha256']
    assert all(not set(split[a]) & set(split[b]) for a in split for b in split if a != b)
    for selection in selections:
        candidates = []
        for family in ('mask', 'additive', 'conditional'):
            p = ROOT/'artifacts'/selection['case']/(family+'_'+selection['arm']+'_calibration.json')
            candidates.extend((family, row) for row in json.loads(p.read_text()))
        family, best = max(candidates, key=lambda item: item[1]['witness']/item[1]['n'])
        assert (family, best['target'], best['witness']) == (selection['chosen']['family'], selection['chosen']['target'], selection['chosen']['witness_n'] if 'witness_n' in selection['chosen'] else selection['chosen']['witness'])
    rows = []
    with torch.inference_mode():
        for binding in bindings:
            models = [load_native(binding[k], binding['architecture'], 'cuda')[0] for k in ('pre', 'post')]
            def predict(model, xx):
                if binding['architecture'] == 'badfu':
                    xx = (xx-xx.new_tensor([.4914,.4822,.4465])[None,:,None,None])/xx.new_tensor([.2023,.1994,.2010])[None,:,None,None]
                elif binding['architecture'] == 'feduba': xx = (xx-.5)/.5
                return model(xx.contiguous()).argmax(1)
            for selection in [s for s in selections if s['case'] == binding['id']]:
                chosen = selection['chosen']; target = chosen['target']
                assert sha(chosen['payload']) == chosen['payload_sha256']
                transform = load_transform(chosen['family'], cfg, chosen['payload'], 'cuda')
                n = count = stable_count = 0; by_class = {c: [0,0] for c in range(10) if c != target}
                for ids in torch.tensor(split['test']).split(32):
                    y = raw['test_y'][ids].long().cuda(); x = raw['test_x'][ids].permute(0,3,1,2).contiguous().float().cuda()/255
                    take = y != target; y = y[take]; x = x[take]
                    stable = (predict(models[0], x) == y) & (predict(models[1], x) == y)
                    changed = transform(x, torch.full_like(y, target))
                    witness = stable & (predict(models[0], changed) == y) & (predict(models[1], changed) == target)
                    n += len(y); count += int(witness.sum()); stable_count += int(stable.sum())
                    for c in by_class:
                        by_class[c][0] += int((y == c).sum()); by_class[c][1] += int(witness[y == c].sum())
                original = next(r for r in primary['results'] if r['case'] == binding['id'] and r['arm'] == selection['arm'])
                assert (n, count, stable_count) == (original['n'], original['witness'], original['stable'])
                assert all(by_class[r['source']] == [r['n'],r['witness']] for r in original['source_counts'])
                rows.append(dict(case=binding['id'], arm=selection['arm'], n=n, witness=count, counts_exact=True))
                del transform
            del models
            torch.cuda.empty_cache()
    write(ROOT/'VERIFIED.json', dict(rows=rows, all_counts_exact=True, calibration_choice_arithmetic_exact=True, native_models_without_hooks=True,
                                    primary_sha256=sha(ROOT/'RESULT.json'), gradients_independently_replayed=False))
    print('verified: 20 native test counts and source-class counts exact', flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='strict')
    try: main()
    except BaseException:
        (ROOT/'VERIFY_FAILURE.txt').write_text(traceback.format_exc(), encoding='utf-8')
        raise
