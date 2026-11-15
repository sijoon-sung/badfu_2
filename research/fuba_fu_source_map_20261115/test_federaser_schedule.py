"""Execute original AST control flow with IDs and recording callbacks, no models."""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile
import numpy as np
from federaser_schedule import author_schedule

ROOT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for name, sha in json.loads((ROOT/'FEDERASER_SCHEDULE_FREEZE.json').read_text())['files'].items():
        assert digest(ROOT/name) == sha, name
    assert not (ROOT/'FEDERASER_SCHEDULE_CONTRACT.json').exists()
    archive = ROOT/'FedEraser-Code.zip'
    assert digest(archive) == '4babbbf2d9f93b0e29a7accdcc6667670b9e99072f44031a6b8390c0b121839b'
    with zipfile.ZipFile(archive) as z:
        source = z.read('FedEraser-Code/Fed_Unlearn_base.py').decode('utf-8')
    funcs = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'unlearning']
    assert len(funcs) == 1
    results = []
    for total in [20, 100]:
        calls, overlays, training = [], [], []
        ids = [0, 1, 2, 3, 4]
        erased = 2
        def fedavg(clients):
            overlays.append(clients)
            return ('overlay', clients[0][0])
        def local(global_model, loaders, test, config):
            training.append({'local_epochs': int(config.local_epoch), 'global_epochs': int(config.global_epoch)})
            return [(global_model, c) for c in ids if c != erased]
        def calibration(old_clients, new_clients, old_global, new_global):
            calls.append({'old_client_round': old_clients[0][0], 'old_global_round': old_global,
                          'retained_ids': [p[1] for p in old_clients]})
            assert [p[1] for p in new_clients] == [c for c in ids if c != erased]
            return ('calibration', len(calls))
        env = {'copy': copy, 'np': np, 'fedavg': fedavg, 'global_train_once': local,
               'unlearning_step_once': calibration, 'print': lambda *a, **k: None}
        exec(compile(ast.Module(body=funcs, type_ignores=[]), 'original-FedEraser-unlearning', 'exec'), env)
        config = SimpleNamespace(if_unlearning=True, forget_client_idx=erased, N_client=5,
                                 global_epoch=total, unlearn_interval=2, local_epoch=10,
                                 forget_local_epoch_ratio=.5)
        old_clients = [(r, c) for r in range(1, total+1) for c in ids]
        outputs = env['unlearning'](list(range(total+1)), old_clients, None, None, config)
        plan = author_schedule(global_epochs=total, interval=2, local_epochs=10, calibration_ratio=.5)
        assert overlays == [[(2, c) for c in ids if c != erased]]
        assert len(outputs) == plan['output_updates'] + 1
        assert len(calls) == plan['calibration_calls'] == len(training)
        for observed, expected in zip(calls, plan['calibration']):
            assert observed['old_client_round'] == expected['old_client_round']
            assert observed['old_global_round'] == expected['old_global_round']
            assert observed['retained_ids'] == [0, 1, 3, 4]
        assert all(x == {'local_epochs': 5, 'global_epochs': total//2} for x in training)
        assert config.global_epoch == total and config.local_epoch == 10
        assert old_clients == [(r, c) for r in range(1, total+1) for c in ids]
        results.append({'global_epoch_argument': total, 'plan': plan, 'AST_calls': calls})
    result = {'state': 'passed', 'device': 'CPU', 'real_training': 0, 'model_loads': 0,
              'CUDA_used': False, 'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
              'results': results, 'full_paper_reproduced': False}
    with (ROOT/'FEDERASER_SCHEDULE_CONTRACT.json').open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(json.dumps({'state': 'passed', 'cases': 2, 'calibration_calls': [9, 49]}), flush=True)


if __name__ == '__main__':
    main()
