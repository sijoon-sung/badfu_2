"""Finite CPU source/identity contracts; never starts upstream training."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['PYTHONIOENCODING'] = 'utf-8'
import ast
import hashlib
import json
import platform
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    'Fed_Unlearn_main.py': '97b806ee736db9dccec13cc0a56684dc40fdd60d',
    'Fed_Unlearn_attack.py': '4baeb0931f39c139c325bcee9b4298e95f64c50a',
    'Fed_data_change.py': 'b2f9931489c07c8e5c1e7fa696fac87eeefd7cb9',
    'Fed_data_preprocess.py': '4eb1850b993b4fae675da99c8cbc45cbd34b2150',
    'Fed_model_initiation.py': '97785086ce548af4799c05e015cf9865b85aaf28',
    'Fed_test.py': '49f3866a7aae53e989c34cf283681f7378b423fb',
    'Fed_train.py': 'f08a854350b32c7c8c55d021e60834468ea2e0a0',
    'trigger_generate_function.py': 'bb5096dbb192fa8d5cffa7fc9d97559d15157127',
    'README.md': '828c165dab43a2b36e5fc7b8fb5cab04e9d1148e',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def extract_node(path, name, namespace):
    parsed = ast.parse(path.read_text(encoding='utf-8'))
    nodes = [n for n in parsed.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name == name]
    assert len(nodes) == 1, (path, name)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


def main():
    freeze = json.loads((ROOT / 'FREEZE.json').read_text(encoding='utf-8'))
    for name, digest in freeze['files'].items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    (ROOT / 'STARTED.json').open('x', encoding='utf-8').write(json.dumps({
        'started_utc': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(),
        'freeze_sha256': sha((ROOT / 'FREEZE.json').read_bytes()),
    }, indent=2) + '\n')
    result = {'schema': 'feduba-source-contract-audit-v1', 'host': platform.node(),
              'python': sys.version, 'pid': os.getpid(), 'freeze_sha256': sha((ROOT / 'FREEZE.json').read_bytes()),
              'training_started': False, 'gpu_used': False, 'source': {}}
    out = ROOT / 'RESULTS.json'
    try:
        source = ROOT / 'upstream_author'
        source.mkdir(exist_ok=False)
        with zipfile.ZipFile(ROOT / 'FedUBA-Code.zip') as z:
            files = [i for i in z.infolist() if not i.is_dir()]
            assert len(files) == len(EXPECTED)
            for info in files:
                assert info.filename == 'FedUBA-Code/' + Path(info.filename).name
                name = Path(info.filename).name
                data = z.read(info)
                blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                assert blob == EXPECTED[name], (name, blob)
                (source / name).write_bytes(data)
                result['source'][name] = {'sha256': sha(data), 'git_blob_sha1': blob, 'bytes': len(data)}
        result['missing_project_modules'] = [n for n in ['utils.py', 'models'] if not (source / n).exists()]
        imports = {}
        for module in ['Fed_Unlearn_main', 'trigger_generate_function']:
            program = 'import sys; sys.path.insert(0, ' + repr(str(source)) + '); import ' + module
            p = subprocess.run([sys.executable, '-I', '-c', program], cwd=source,
                               capture_output=True, text=True, encoding='utf-8', timeout=90)
            imports[module] = {'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
        result['original_import_attempts'] = imports

        import torch
        from torch.utils.data import BatchSampler, DataLoader, SequentialSampler, TensorDataset
        from types import SimpleNamespace
        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        result['torch'] = torch.__version__
        ns = {'torch': torch}
        Args = extract_node(source / 'Fed_Unlearn_main.py', 'Arguments', ns)
        args = Args(None)
        result['profile'] = {k: getattr(args, k) for k in [
            'data_name', 'data_split', 'N_total_client', 'N_client', 'global_epoch',
            'local_epoch', 'local_batch_size', 'local_lr', 'selected_clients',
            'attack_clients_idx', 'triggerToClass', 'multi_test_list', 'trigger_limit', 'seed']}
        sort_fn = extract_node(source / 'Fed_data_change.py', 'high_sensitivity_sort', {
            'torch': torch, 'BatchSampler': BatchSampler, 'SequentialSampler': SequentialSampler,
            'DataLoader': DataLoader,
        })
        x = torch.arange(32, dtype=torch.float64).view(-1, 1) / 31
        dataset = TensorDataset(x, torch.zeros(32, dtype=torch.long))

        class Witness(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.visited = []

            def forward(self, value):
                self.visited.append(value.detach().clone())
                return torch.cat([value.square(), torch.zeros_like(value)], dim=1)

        cases = []
        for shuffle in [True, False]:
            torch.manual_seed(0)
            model = Witness()
            params = SimpleNamespace(device='cpu', trigger=torch.tensor([0.01], dtype=torch.float64))
            loader = DataLoader(dataset, batch_size=1, shuffle=shuffle)
            returned = sort_fn(None, None, loader, model, params)
            visits = [int(round(v.item() * 31)) for v in model.visited[0::2]]
            ranked_actual_ids = [visits[i] for i in returned]
            oracle = list(range(31, -1, -1))
            assert ranked_actual_ids == oracle, 'Witness sensitivity is strictly increasing in dataset ID'
            matches = sum(a == b for a, b in zip(returned, oracle))
            if shuffle:
                assert returned != oracle, 'Preregistered index mismatch not reproduced'
            else:
                assert returned == oracle, 'Sequential positive control failed'
            cases.append({'shuffle': shuffle, 'batch_size': 1, 'sample_count': 32,
                          'visited_dataset_ids': visits, 'returned_as_dataset_ids': returned,
                          'actual_ranked_dataset_ids': ranked_actual_ids, 'oracle_dataset_ids': oracle,
                          'positions_matching_oracle': matches, 'all_correct': returned == oracle})
        result['sensitivity_identity_contract'] = cases

        merge = extract_node(source / 'Fed_data_preprocess.py', 'merge_client_subsets', {'torch': torch})
        synthetic_clients = [torch.utils.data.Subset(dataset, [i]) for i in range(args.N_total_client)]
        declared_owners = [args.selected_clients[i] for i in args.attack_clients_idx]
        actual_merge = merge(synthetic_clients, dataset, args.attack_clients_idx)
        actual_owners = actual_merge.indices
        assert declared_owners == [5, 7] and actual_owners == [2, 3]
        result['client_identity_contract'] = {
            'selected_client_positions': args.attack_clients_idx,
            'attacker_client_ids_in_FL_and_FU': declared_owners,
            'client_ids_used_by_surrogate_target_data_helper': actual_owners,
            'same_owners': declared_owners == actual_owners,
            'helper_call_verified_in_source': 'merge_client_subsets(client_dataset, client_dataset[0].dataset, FL_params.attack_clients_idx)' in
                                             (source / 'Fed_data_preprocess.py').read_text(encoding='utf-8'),
            'scope': 'Exact helper plus unchanged Arguments, synthetic subset IDs; no real private data loaded.',
        }
        assert result['client_identity_contract']['helper_call_verified_in_source']
        result['verdict'] = 'original_release_incomplete_and_identity_contracts_fail_full_reproduction_not_qualified'
        result['limitations'] = [
            'AST extraction runs original functions with synthetic CPU data, not complete FL/FU.',
            'No trained FedUBA pair, CA/ASR, detection performance or impossibility conclusion.',
            'Missing poison_image/poison_image_label definitions prevent confirming perturbation sign/label semantics.',
            'Current Python/PyTorch environment differs from old README requirements; file absence is distribution evidence.',
        ]
    except Exception:
        import traceback
        result['audit_failure'] = traceback.format_exc()
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        raise
    result['finished_utc'] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(result['verdict'])


if __name__ == '__main__':
    main()
