"""Bounded global/local gamma interpretation comparison, without retraining."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
sys.dont_write_bytecode = True
import torch
from torchvision.datasets import MNIST

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    with Path(path).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.write('\n')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


def main():
    for name, digest in read(ROOT / 'FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest
    p = read(ROOT / 'PROFILE.json')
    selection = json.loads(subprocess.check_output([sys.executable, p['catalog_selector'], p['case_id'], '--purpose', 'diagnostic']).decode('utf-8'))
    assert selection['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selection['checkpoint_guard']['manifest_sha256'] == p['manifest_sha256']
    src = Path(p['review_root'])
    helper = module('gamma_common', src / 'common.py')
    core = module('gamma_core', src / 'reference_core.py')
    idle = helper.guard()
    write(ROOT / 'STARTED.json', {'pid': os.getpid(), 'resource_guard': idle, 'time_unix': time.time(), 'selection': selection})
    try:
        torch.set_num_threads(1)
        torch.backends.cudnn.benchmark = False
        cfg = read(src / 'PROFILE.json')
        meta = read(src / 'DELIVERY_MANIFEST.json')
        Net = helper.load_model_class()
        train = MNIST(cfg['data_root'], train=True, download=False)
        test = MNIST(cfg['data_root'], train=False, download=False)
        tx = test.data.cuda().float().unsqueeze(1).div_(255)
        ty = test.targets.cuda()
        splits = read(src / 'SPLIT.json')['indices']

        def payload(rel, key):
            rel = rel.replace('\\', '/')
            f = (src / rel).resolve()
            assert f.is_relative_to(src.resolve()) and sha(f) == meta['files'][rel]['sha256']
            value = torch.load(f, map_location='cpu', weights_only=True)
            return value if key == '$' else value[key]

        def evaluate(model, x, y):
            model.eval()
            correct = success = bias = count = 0
            with torch.inference_mode():
                for start in range(0, len(y), 512):
                    xb, yb = x[start:start + 512], y[start:start + 512]
                    logits, attacked = model(xb), model(core.stamp(xb, 4))
                    assert bool(torch.isfinite(logits).all() & torch.isfinite(attacked).all())
                    clean, target, non = logits.argmax(1), attacked.argmax(1), yb != 8
                    correct += int((clean == yb).sum()); success += int(((target == 8) & non).sum())
                    bias += int(((clean == 8) & non).sum()); count += int(non.sum())
            return {'N': len(y), 'non_target_N': count, 'clean_correct': correct, 'target_successes': success,
                    'clean_target_count': bias, 'CA_pct': 100 * correct / len(y), 'ASR_pct': 100 * success / count,
                    'clean_target_bias_pct': 100 * bias / count, 'trigger_role': 4}

        results = []
        for round_number, client in p['fixed_roles']:
            role = read(src / f'run/roles/round{round_number:04d}_client{client:02d}.json')
            bundle = payload(f'run/rounds/round{round_number:04d}.pt', '$')
            assert role['role'] == 'attacker' and role['client'] == client and role['round'] == round_number
            incoming, embedded, rep = [Net().cuda() for _ in range(3)]
            incoming.load_state_dict(bundle['incoming'], strict=True)
            embedded.load_state_dict(payload(role['phases'][2]['path'], 'model'), strict=True)
            rep.load_state_dict(payload(role['phases'][3]['path'], 'model'), strict=True)
            positions = torch.randperm(3000, generator=torch.Generator().manual_seed(cfg['partition_seed'] + client))[:300]
            ids = torch.tensor(splits[client])[positions]
            vx, vy = train.data[ids].cuda().float().unsqueeze(1).div_(255), train.targets[ids].cuda()
            scores = []
            for gamma in p['gamma']:
                predicted = core.expected(core.affine(incoming, embedded, gamma), rep, p['mixture'])
                scores.append({'gamma': gamma, **evaluate(predicted, vx, vy)})
            local = role['decision']
            original_gamma = local['gamma']
            selected_global = next(s for s in scores if s['gamma'] == original_gamma)
            selected_local = next(s for s in local['scores'] if s['gamma'] == original_gamma)
            passed = [s['gamma'] for s in scores if s['ASR_pct'] < 10]
            gamma = max(passed) if passed else 0.
            original = read(src / f'run/evaluation/round{round_number:04d}.json')
            if gamma == original_gamma:
                counterfactual = original
                model_record = None
            else:
                uploaded = helper.cpu(core.affine(incoming, embedded, gamma).state_dict())
                submitted = copy.deepcopy(bundle['submitted'])
                submitted[bundle['clients'].index(client)] = uploaded
                state = {k: torch.stack([s[k] for s in submitted]).mean(0) for k in bundle['incoming']}
                model = Net().cuda().eval(); model.load_state_dict(state, strict=True)
                counterfactual = evaluate(model, tx, ty)
                path = ROOT / f'counterfactual_round{round_number:04d}_client{client:02d}.pt'
                with path.open('xb') as f:
                    torch.save({'model': state, 'scope': 'single_round_diagnostic_counterfactual_not_full_trajectory'}, f)
                model_record = {'path': path.name, 'sha256': sha(path), 'payload_key': 'model'}
            item = {'round': round_number, 'client': client, 'original_gamma': original_gamma,
                    'original_local_scores_reused': local['scores'], 'new_global_scores': scores,
                    'original_selected_local_ASR': selected_local['ASR_pct'],
                    'original_selected_global_ASR': selected_global['ASR_pct'],
                    'new_gamma': gamma, 'global_constraint_met': bool(passed),
                    'scope_violation': selected_local['ASR_pct'] < 10 and selected_global['ASR_pct'] >= 10,
                    'original_actual_round': original, 'counterfactual_round': counterfactual,
                    'derived_model': model_record}
            results.append(item)
            print(json.dumps({k: item[k] for k in ['round', 'client', 'original_gamma', 'new_gamma', 'global_constraint_met', 'scope_violation']}), flush=True)
        last = results[-1]
        h1 = any(r['scope_violation'] for r in results)
        h2 = last['original_actual_round']['ASR_pct'] > 10 and last['counterfactual_round']['ASR_pct'] <= 10 and last['counterfactual_round']['CA_pct'] >= 97
        write(ROOT / 'RESULT.json', {'state': 'complete', 'profile': p['id'], 'H1_scope_failure': h1,
              'H2_last_round_gate': h2, 'followup_full_run_justified_by_this_change': h1 and h2,
              'roles': results, 'training_performed': False, 'original_models_modified': False,
              'derived_models_are_diagnostic_only': True, 'case_id': p['case_id'],
              'source_sha256': sha(ROOT / 'runner.py'), 'resource_guard': idle})
    except BaseException:
        write(ROOT / 'FAILURE.json', {'traceback': traceback.format_exc()})
        raise


if __name__ == '__main__':
    main()
