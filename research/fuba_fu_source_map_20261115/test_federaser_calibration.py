"""Compare restored calibration to the author's directly linked source on CPU."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import zipfile
import torch
from federaser_calibration import calibrate_author_layers

ROOT=Path(__file__).resolve().parent


class Fixture(torch.nn.Module):
    def __init__(self,values):
        super().__init__()
        self.w=torch.nn.Parameter(torch.tensor(values,dtype=torch.float64))


def main():
    torch.set_num_threads(1)
    archive=ROOT/'FedEraser-Code.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()=='4babbbf2d9f93b0e29a7accdcc6667670b9e99072f44031a6b8390c0b121839b'
    with zipfile.ZipFile(archive) as z:source=z.read('FedEraser-Code/Fed_Unlearn_base.py').decode()
    parsed=ast.parse(source)
    functions=[n for n in parsed.body if isinstance(n,ast.FunctionDef) and n.name=='unlearning_step_once']
    assert len(functions)==1
    env={'torch':torch,'copy':copy}
    exec(compile(ast.Module(body=functions,type_ignores=[]),'official-FedEraser','exec'),env)
    old=Fixture([0,0]);new=Fixture([10,20])
    old_clients={3:Fixture([2,4]),12:Fixture([4,4])}
    new_clients={3:Fixture([10,20.5]),12:Fixture([10,21.5])}
    reference=env['unlearning_step_once'](list(old_clients.values()),list(new_clients.values()),old,new)
    actual,details=calibrate_author_layers(old.state_dict(),{i:m.state_dict() for i,m in old_clients.items()},
        new.state_dict(),{i:m.state_dict() for i,m in new_clients.items()},erased_client=4)
    assert torch.equal(actual['w'],reference.state_dict()['w'])
    assert torch.equal(actual['w'],torch.tensor([10.,25.],dtype=torch.float64))
    assert not torch.equal(actual['w'],torch.tensor([10.,21.],dtype=torch.float64)), 'The FUBA new-norm substitution must fail'
    try:calibrate_author_layers(old.state_dict(),{4:old.state_dict()},new.state_dict(),{4:new.state_dict()},erased_client=4)
    except ValueError:pass
    else:raise AssertionError('Deleted client accepted')
    try:calibrate_author_layers(old.state_dict(),{3:Fixture([1,1]).state_dict()},new.state_dict(),{3:new.state_dict()},erased_client=4)
    except ValueError:pass
    else:raise AssertionError('Undefined nonzero-old/zero-new direction accepted')
    result={'state':'passed','device':'CPU','CUDA_initialized':torch.cuda.is_initialized(),
            'official_function_tensor_exact':True,'old_vs_new_norm_counterexample':True,
            'client_exclusion_and_zero_direction_checked':True,'real_FU_training':False,'details':details,
            'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
            'executed_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['test_federaser_calibration.py','federaser_calibration.py','unlearning_kernels.py']}}
    with (ROOT/'FEDERASER_CONTRACT.json').open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))


if __name__=='__main__':main()
