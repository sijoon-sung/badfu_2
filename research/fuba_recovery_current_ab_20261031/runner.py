"""Current-runtime A/B follow-on: reuse prior SGD control and train the unused Adam arm once."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
import traceback
sys.dont_write_bytecode = True
import numpy as np
import torch
from torchvision.datasets import MNIST

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    with (ROOT / name).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write('\n')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec); sys.modules[name] = obj; spec.loader.exec_module(obj)
    return obj


def restore(r):
    random.setstate(r['python'])
    n = r['numpy']; np.random.set_state((n[0], np.array(n[1], dtype=np.uint32), n[2], n[3], n[4]))
    torch.set_rng_state(r['torch_CPU']); torch.cuda.set_rng_state_all(r['torch_CUDA'])


def main():
    p = read(ROOT / 'PROFILE.json')
    for name, digest in read(ROOT / 'FREEZE.json')['files'].items():
        assert sha(ROOT / name) == digest
    selector = 'D:/TRAJECTORY_CATALOG_20261023/select_case.py'
    selection = json.loads(subprocess.check_output([sys.executable, selector, p['case_id'], '--purpose', 'diagnostic']).decode('utf-8'))
    assert selection['guard_state'] == 'all_snapshot_files_verified_on_this_host'
    assert selection['checkpoint_guard']['manifest_sha256'] == p['manifest_sha256']
    src, raw = Path(p['review_root']), Path(p['raw_root'])
    helper, core = module('recovery_common', src / 'common.py'), module('recovery_core', src / 'reference_core.py')
    idle = helper.guard()
    write('STARTED.json', {'pid': os.getpid(), 'time_unix': time.time(), 'resource_guard': idle, 'selection': selection})
    try:
        torch.set_num_threads(1); torch.backends.cudnn.benchmark = False
        snapshot = read(src / 'FULL_REMOTE_RAW_MANIFEST.json')['files']
        def load(rel):
            rel = rel.replace('\\', '/')
            path = (raw / rel).resolve()
            assert path.is_relative_to(raw.resolve()) and sha(path) == snapshot[rel]['sha256'], rel
            return torch.load(path, map_location='cpu', weights_only=True)
        phase3 = load('run/phases/round0099_client04/phase03.pt')
        phase4 = load('run/phases/round0099_client04/phase04.pt')
        assert snapshot['run/phases/round0099_client04/phase03.pt']['sha256'] == p['phase3_sha256']
        assert snapshot['run/phases/round0099_client04/phase04.pt']['sha256'] == p['phase4_sha256']
        bundle = load('run/rounds/round0099.pt')
        cfg = read(src / 'PROFILE.json'); splits = read(src / 'SPLIT.json')['indices']
        train = MNIST(cfg['data_root'], train=True, download=False)
        test = MNIST(cfg['data_root'], train=False, download=False)
        order = torch.randperm(3000, generator=torch.Generator().manual_seed(cfg['partition_seed'] + 4))[300:]
        ids = torch.tensor(splits[4])[order]
        x, y = train.data[ids].cuda().float().unsqueeze(1).div_(255), train.targets[ids].cuda()
        tx, ty = test.data.cuda().float().unsqueeze(1).div_(255), test.targets.cuda()
        Net = helper.load_model_class()
        reference = Net().cuda(); reference.load_state_dict(phase3['model'], strict=True)
        settings = core.Settings()
        logs = []
        def log(arm):
            def emit(**value):
                record = {'arm': arm, **value}; logs.append(record)
                with (ROOT / 'epochs.jsonl').open('a', encoding='utf-8') as f:
                    f.write(json.dumps(record, allow_nan=False) + '\n')
            return emit
        def save(name, model, optimizer, loader_rng):
            with (ROOT / name).open('xb') as f:
                torch.save(helper.cpu({'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                                      'rng': helper.rng(), 'loader_rng': loader_rng, 'epochs': 50, 'batches': 2150}), f)
        def evaluate(model):
            model.eval(); correct = success = bias = non_count = 0
            with torch.inference_mode():
                for start in range(0, 10000, 512):
                    xb, yb = tx[start:start+512], ty[start:start+512]
                    out, attack = model(xb), model(core.stamp(xb, 4))
                    assert bool(torch.isfinite(out).all() & torch.isfinite(attack).all())
                    clean, predicted, non = out.argmax(1), attack.argmax(1), yb != 8
                    correct += int((clean == yb).sum()); success += int(((predicted == 8) & non).sum())
                    bias += int(((clean == 8) & non).sum()); non_count += int(non.sum())
            return {'N':10000,'non_target_N':non_count,'clean_correct':correct,'target_successes':success,
                    'CA_pct':correct/100,'ASR_pct':100*success/non_count,'clean_target_bias_pct':100*bias/non_count}
        current_path = Path(p['current_A_path'])
        assert sha(current_path) == p['current_A_sha256']
        current = torch.load(current_path, map_location='cpu', weights_only=True)
        assert torch.equal(current['loader_rng'], phase4['loader_rng'])
        full_x = train.data.cuda().float().unsqueeze(1).div_(255)
        full_y = train.targets.cuda()
        client_ids = torch.tensor(splits[4], device='cuda')
        train_pos = torch.randperm(3000, generator=torch.Generator().manual_seed(cfg['partition_seed'] + 4))[300:].cuda()
        input_bit_equal = torch.equal(x, full_x[client_ids][train_pos]) and torch.equal(y, full_y[client_ids][train_pos])
        assert input_bit_equal, 'Input path mismatch; preserve before B'
        del full_x, full_y, client_ids, train_pos
        original = Net().cuda(); original.load_state_dict(phase4['model'], strict=True)
        a = Net().cuda(); a.load_state_dict(current['model'], strict=True)
        preflight = {'original': evaluate(original), 'current_A': evaluate(a)}
        differences = {k: abs(preflight['original'][k] - preflight['current_A'][k]) for k in ['CA_pct','ASR_pct','clean_target_bias_pct']}
        behavior_gate = max(differences.values()) <= p['behavior_tolerance_pct_points']
        write('CONTROL_PREFLIGHT.json', {'original_bit_guard_failed_preserved': True, 'input_and_labels_bit_equal': input_bit_equal,
              'loader_RNG_equal': True, 'behavior': preflight, 'differences_pct_points': differences, 'gate_passed': behavior_gate})
        assert behavior_gate, 'Behavioral control unstable; preserve before B'
        rng_a = current['loader_rng']; equal = False
        shutil.copy2(current_path, ROOT / 'SGD_recovery_reused.pt')
        b = copy.deepcopy(reference); restore(phase3['rng']); b.train()
        opt_b = torch.optim.Adam(b.parameters(), lr=.001, betas=(.9, .999), eps=1e-8, weight_decay=0, foreach=True)
        ref = torch.nn.utils.parameters_to_vector(reference.parameters()).detach()
        gen = torch.Generator(device='cuda').manual_seed(p['phase_seed'])
        batches_b = 0
        for epoch in range(50):
            permutation = torch.randperm(len(y), generator=gen, device='cuda')
            total = torch.zeros((), device='cuda'); finite = torch.ones((), dtype=torch.bool, device='cuda')
            for idx in permutation.split(64):
                opt_b.zero_grad(set_to_none=True)
                loss = torch.nn.functional.cross_entropy(b(x[idx]), y[idx])
                vector = torch.nn.utils.parameters_to_vector(b.parameters())
                loss = loss + 2 * (vector - ref).square().sum()
                finite.logical_and_(torch.isfinite(loss.detach())); loss.backward(); opt_b.step()
                total.add_(loss.detach() * len(idx)); batches_b += 1
            assert bool(finite & torch.stack([torch.isfinite(v).all() for v in b.state_dict().values()]).all())
            log('Adam')(phase='recovery_B', epoch=epoch + 1, epochs=50, batches=batches_b, examples=2700,
                        loss=float(total) / len(y), optimizer='Adam')
        rng_b = gen.get_state(); assert batches_b == 2150 and torch.equal(rng_a, rng_b)
        save('Adam_recovery.pt', b, opt_b, rng_b)
        results = {'reference': evaluate(reference)}
        for label, recovered in [('SGD', a), ('Adam', b)]:
            state = helper.cpu(recovered.state_dict())
            upload = {k: bundle['incoming'][k] + state[k] - phase3['model'][k] for k in state}
            model = Net().cuda().eval(); model.load_state_dict(upload, strict=True)
            submission_metric = evaluate(model)
            submitted = copy.deepcopy(bundle['submitted']); submitted[bundle['clients'].index(4)] = upload
            aggregated = {k: torch.stack([s[k] for s in submitted]).mean(0) for k in state}
            model.load_state_dict(aggregated, strict=True)
            round_metric = evaluate(model)
            with (ROOT / (label + '_derived.pt')).open('xb') as f:
                torch.save({'upload': upload,'aggregate': aggregated,'scope':'single_round_diagnostic_only'},f)
            results[label] = {'recovered': preflight['current_A'] if label == 'SGD' else evaluate(recovered), 'upload': submission_metric, 'round': round_metric}
        ma, mb = results['SGD']['recovered'], results['Adam']['recovered']; rb = results['Adam']['round']
        supported = ma['ASR_pct'] - mb['ASR_pct'] >= 20 and mb['CA_pct'] >= 97 and mb['CA_pct'] >= ma['CA_pct'] - 1 and rb['CA_pct'] >= 97 and rb['ASR_pct'] <= 10
        assert len(logs) == 50
        write('RESULT.json', {'state':'complete','profile':p['id'],'hypothesis_supported':supported,
              'control_original_tensor_equality':False,'control_behavior_gate':True,'exact_input_and_loader_verified':True,'same_loader_RNG':True,'actual_phase_epochs_new':50,'reused_A_phase_epochs':50,
              'actual_batches_new':2150,'reused_A_batches':2150,'metrics':results,'full_FL_or_FU_run':False,'original_models_modified':False,
              'literal_SGD_and_Adam_equivalent':False,'case_id':p['case_id'],'resource_guard':idle})
        print(json.dumps({'state':'complete','hypothesis_supported':supported,'metrics':results}),flush=True)
    except BaseException:
        write('FAILURE.json', {'traceback':traceback.format_exc()}); raise


if __name__ == '__main__':
    main()
