import ast
import copy
import hashlib
import json
from pathlib import Path
import time
import torch
from aggregation import aggregate

ROOT = Path(__file__).resolve().parent


class Toy(torch.nn.Module):
    def __init__(self, value):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.full((2, 3), float(value)))
        self.register_buffer('num_batches_tracked', torch.tensor(int(value) * 2))


def main():
    torch.set_num_threads(1)
    assert not torch.cuda.is_initialized()
    reference = Path('D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/upstream/Fed_train.py')
    raw = reference.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    assert blob == 'f08a854350b32c7c8c55d021e60834468ea2e0a0'
    tree = ast.parse(raw)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in ['fedavg', 'median', 'trim_mean']]
    assert len(functions) == 3
    namespace = {'copy': copy, 'torch': torch}
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(reference), 'exec'), namespace)
    models = [Toy(value) for value in [0,1,2,3,4,5,6,7,8,100]]
    states = [model.state_dict() for model in models]
    before = copy.deepcopy(states)
    observed = {}
    for rule, function in [('fedavg', 'fedavg'), ('median', 'median'), ('trim-mean', 'trim_mean')]:
        expected = namespace[function](models, .1).state_dict() if rule == 'trim-mean' else namespace[function](models).state_dict()
        actual = aggregate(states, rule)
        assert all(torch.equal(actual[key], expected[key]) for key in actual)
        observed[rule] = {'weight': float(actual['weight'][0,0]), 'counter': int(actual['num_batches_tracked']), 'exact_reference': True}
    assert observed['median']['weight'] == 4 and observed['median']['counter'] == 8
    assert observed['trim-mean']['weight'] == 4.5 and observed['trim-mean']['counter'] == 9
    assert observed['fedavg']['counter'] == 200
    assert all(torch.equal(a[k], b[k]) for a,b in zip(states,before) for k in a)
    # Boundary fix is intentionally different from public [0:0] behavior.
    short = [Toy(1), Toy(2), Toy(3)]
    old_zero_trim = namespace['trim_mean'](short, .1).state_dict()
    assert bool(torch.isnan(old_zero_trim['weight']).all())
    new_zero_trim = aggregate([m.state_dict() for m in short], 'trim-mean')
    assert float(new_zero_trim['weight'][0,0]) == 2
    failures = []
    invalid = [(states, 'other', .1), ([], 'fedavg', .1), (states, 'trim-mean', -.1), (states, 'trim-mean', .5)]
    bad = copy.deepcopy(states); bad[0]['weight'][0,0] = float('nan')
    invalid.append((bad, 'median', .1))
    bad = copy.deepcopy(states); del bad[0]['num_batches_tracked']
    invalid.append((bad, 'fedavg', .1))
    for args in invalid:
        try:
            aggregate(*args)
        except ValueError:
            failures.append(True)
        else:
            raise AssertionError('invalid state accepted')
    assert len(failures) == 6 and not torch.cuda.is_initialized()
    with (ROOT / 'RESULT.json').open('x', encoding='utf-8') as stream:
        json.dump({'state':'passed','upstream_blob':blob,'reference_SHA256':hashlib.sha256(raw).hexdigest(),
                   'observed':observed,'input_unchanged':True,'invalid_cases_rejected':6,
                   'zero_trim_boundary_fix':True,'real_model_or_data_experiments':0,'CUDA_initialized':False,
                   'time':time.time()},stream,indent=2)


if __name__ == '__main__':
    main()
