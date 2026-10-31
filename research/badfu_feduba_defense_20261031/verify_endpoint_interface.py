"""Read-only source fixture, not an actual FedUBA attack/defense evaluation."""
import hashlib,importlib.util,json,os,subprocess,time,traceback
from pathlib import Path
import torch
from endpoint_interface import BADFU,FEDUBA,EndpointSpec,forward_raw,normalise_raw

HERE=Path(__file__).resolve().parent;OUT=HERE/'endpoint_interface_contract'
SOURCE=Path('D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/model_reference.py')
SHA='57d92398d95a1669c02590052c457f59332286c288f9e0aee2baf83beb192fc3'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    freeze=json.loads((HERE/'ENDPOINT_INTERFACE_FREEZE.json').read_text(encoding='utf8'))
    for n,h in freeze['files'].items():assert sha(HERE/n)==h,n
    assert sha(SOURCE)==SHA
    cpu=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command','Get-CimInstance Win32_Processor | Select-Object NumberOfLogicalProcessors,LoadPercentage | ConvertTo-Json -Compress'],text=True))
    assert cpu['NumberOfLogicalProcessors']>=8 and cpu['LoadPercentage']<=60
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu},f)
    torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(20261031)
    spec=importlib.util.spec_from_file_location('p04_declared_feduba_fixture',SOURCE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    model=module.ResNet18().eval();raw=torch.rand((2,3,32,32),generator=torch.Generator().manual_seed(20261031+18))
    before={k:v.detach().clone() for k,v in model.state_dict().items()}
    for p in model.parameters():p.requires_grad_(False)
    direct_x=raw.clone().requires_grad_(True);wrapped_x=raw.clone().requires_grad_(True)
    direct=model(direct_x*2-1);wrapped,features=forward_raw(model,wrapped_x,FEDUBA,with_features=True)
    assert wrapped.shape==(2,10) and features.shape==(2,512) and torch.equal(direct,wrapped)
    assert torch.equal(model.linear(features),wrapped)
    direct_grad=torch.autograd.grad(direct.square().mean(),direct_x)[0]
    wrapped_grad=torch.autograd.grad(wrapped.square().mean(),wrapped_x)[0]
    assert torch.isfinite(wrapped_grad).all() and torch.equal(direct_grad,wrapped_grad) and wrapped_grad.abs().sum()>0
    assert all(torch.equal(v,before[k]) for k,v in model.state_dict().items())
    assert not model.linear._forward_pre_hooks
    # Both explicit profiles normalize known values as declared, without claiming a
    # new BadFU native checkpoint evaluation in this source-only fixture.
    endpoints=torch.stack([torch.zeros(3,1,1),torch.ones(3,1,1)])
    assert torch.equal(normalise_raw(endpoints,FEDUBA),endpoints*2-1)
    for c in range(3):
        assert abs(float(normalise_raw(endpoints.double(),BADFU)[0,c,0,0])+BADFU.mean[c]/BADFU.std[c])<1e-12
    rejected=[]
    for name,network,profile,x in [
        ('wrong_head',model,BADFU,raw),
        ('surrogate201',module.ResNet18_201().eval(),FEDUBA,raw),
        ('uint8',model,FEDUBA,(raw*255).byte()),
        ('out_of_range',model,FEDUBA,raw+1),
        ('training_mode',module.ResNet18().train(),FEDUBA,raw)]:
        try:forward_raw(network,x,profile,with_features=True)
        except (ValueError,AttributeError):rejected.append(name)
        else:raise AssertionError(name+' was not rejected')
    assert not torch.cuda.is_initialized() and sha(SOURCE)==SHA
    result={'state':'passed','fixture':'new_random_initialization_two_synthetic_images','actual_FedUBA_model_selected':False,
            'source_sha256':SHA,'interface_sha256':sha(HERE/'endpoint_interface.py'),'verifier_sha256':sha(__file__),
            'exact_logits_and_feature_head_reconstruction':True,'exact_finite_input_gradient':True,
            'BN_buffers_and_all_model_state_unchanged':True,'forward_hook_removed':True,'normalization_endpoints_checked':True,
            'rejected':rejected,'CUDA_initialized':False,'defense_efficacy_evaluated':False}
    with (OUT/'RESULT.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    with (OUT/'COMPLETED.json').open('x',encoding='utf8') as f:json.dump({'result_sha256':sha(OUT/'RESULT.json'),'freeze_sha256':sha(HERE/'ENDPOINT_INTERFACE_FREEZE.json')},f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True)
        with (OUT/'FAILURE.json').open('x',encoding='utf8') as f:json.dump({'traceback':traceback.format_exc()},f,indent=2);f.write('\n')
        raise
