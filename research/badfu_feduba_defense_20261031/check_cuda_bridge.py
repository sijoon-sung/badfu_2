"""Guarded synthetic CUDA bridge contract; original CPU experiment untouched."""
import hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
r=Path(__file__).resolve().parent;OUT=r/'cuda_bridge_contract';OUT.mkdir(exist_ok=True)
sys.stdout=(r/'cuda_bridge_stdout.log').open('x',encoding='utf8',buffering=1)
sys.stderr=(r/'cuda_bridge_stderr.log').open('x',encoding='utf8',buffering=1)
import torch
import stage05_common as s
from stage08 import norm
from sourcepair_pilot import cpu_guard
from cpu_io_cuda_bridge import class_factory
core=s.core


def main():
    s.verify_sources();freeze=core.read(r/'CUDA_BRIDGE_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(r/n)==h,n
    cpu=cpu_guard();assert not torch.cuda.is_initialized()
    inventory=json.loads(subprocess.check_output(['powershell','-NoProfile','-Command',
        "Get-CimInstance Win32_Process | Where-Object {$_.ProcessId -in @(13000,31756,37492)} | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],text=True))
    inv={int(v['ProcessId']):v['CommandLine'] for v in inventory}
    assert 'llama-server' in inv.get(13000,'') and 'server.py --port 8767' in inv.get(31756,'')
    assert 'advanced_prediction_service.py' in inv.get(37492,'') and '--port 8769' in inv[37492]
    gpu_samples=[]
    for _ in range(3):
        row=subprocess.check_output(['nvidia-smi','--query-gpu=memory.total,memory.used,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True).strip()
        total,used,free,util=map(int,row.split(','));assert total==10240 and free>=4096 and util<=5
        pids=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader,nounits'],text=True).splitlines()
        assert {int(x.strip()) for x in pids if x.strip()}<=set(inv),'unknown GPU compute process'
        gpu_samples.append({'total_MiB':total,'used_MiB':used,'free_MiB':free,'utilization_pct':util});time.sleep(1)
    safe_inv={13000:'LMStudio llama-server; arguments omitted',31756:'prediction server port8767',37492:'advanced prediction service port8769'}
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu,'GPU_before':gpu_samples,'existing_services':safe_inv},f,indent=2)
    selected,sealed,states=s.snapshot();base=sealed.model_class(Path(selected['source_root']))
    original=states['pre'];original_digest=core.tensor_digest(original)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.set_float32_matmul_precision('highest');torch.use_deterministic_algorithms(True)
    torch.cuda.set_per_process_memory_fraction(.25,device=0);torch.cuda.reset_peak_memory_stats(0)
    bridge=class_factory(base,'cuda:0');cpu_model=base().eval();cpu_model.load_state_dict(original,strict=True)
    gpu_model=bridge().eval();gpu_model.load_state_dict(original,strict=True)
    assert all(p.device.type=='cuda' for p in gpu_model.parameters())
    exported=gpu_model.state_dict();assert list(exported)==list(original)
    assert all(v.device.type=='cpu' and torch.equal(v,original[k]) for k,v in exported.items())
    raw=torch.rand((2,3,32,32),generator=torch.Generator().manual_seed(20261101+3100))
    a=norm(raw).detach().requires_grad_(True);b=a.detach().clone().requires_grad_(True)
    for model in [cpu_model,gpu_model]:
        for p in model.parameters():p.requires_grad_(False)
    cz=cpu_model(a);gz=gpu_model(b);assert gz.device.type=='cpu' and gz.requires_grad
    torch.save({'synthetic_raw':raw,'cpu_logits':cz.detach(),'cuda_logits':gz.detach()},OUT/'private_logits_comparison.pt')
    assert torch.allclose(cz,gz,atol=1e-5,rtol=1e-4)
    cg=torch.autograd.grad(cz.square().mean(),a)[0];gg=torch.autograd.grad(gz.square().mean(),b)[0]
    torch.save({'cpu_input_gradient':cg,'cuda_input_gradient':gg},OUT/'private_gradient_comparison.pt')
    assert torch.isfinite(gg).all() and cg.norm()>0 and gg.norm()>0
    grad_rel=float((cg-gg).norm()/cg.norm());assert grad_rel<=.01,grad_rel
    logits_error=float((cz-gz).abs().max().detach());sign_agreement=float((cg.sign()==gg.sign()).float().mean())
    for p in gpu_model.parameters():p.requires_grad_(True)
    opt=torch.optim.Adam(gpu_model.parameters(),lr=.0001,weight_decay=0)
    training=norm(torch.rand((42,3,32,32),generator=torch.Generator().manual_seed(20261101+3101)))
    opt.zero_grad(set_to_none=True);loss=gpu_model(training).square().mean();assert torch.isfinite(loss)
    loss.backward();assert all(p.grad is None or torch.isfinite(p.grad).all() for p in gpu_model.parameters())
    opt.step();after=gpu_model.state_dict();assert all(v.device.type=='cpu' and torch.isfinite(v).all() for v in after.values())
    assert any(not torch.equal(v,original[k]) for k,v in after.items())
    for k,v in original.items():
        if core.is_buffer(k):assert torch.equal(after[k],v)
    cpu_model.load_state_dict(after,strict=True)
    reload=bridge().eval();reload.load_state_dict(after,strict=True)
    with torch.no_grad():assert torch.equal(gpu_model(norm(raw)),reload(norm(raw)))
    for state in opt.state.values():
        for v in state.values():
            if isinstance(v,torch.Tensor):assert torch.isfinite(v).all()
    peak_alloc=torch.cuda.max_memory_allocated(0);peak_reserved=torch.cuda.max_memory_reserved(0)
    cap=int(.25*10240*1024**2);assert peak_alloc<=cap and peak_reserved<=cap
    assert core.tensor_digest(original)==original_digest
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    result={'state':'passed','case_id':selected['case_id'],'purpose':'purification_pilot','model_role':'pre',
        'CPU_IO_CUDA_CNN_CPU_state_export':True,'exact_initial_state_export':True,'strict_CPU_and_CUDA_roundtrip':True,
        'one_disposable_synthetic_42_image_Adam_step':True,'actual_training_data_or_trigger_used':False,
        'scientific_defense_efficacy_evaluated':False,'current_CPU_experiment_changed':False,
        'logit_max_abs_error':logits_error,'input_gradient_relative_L2_error':grad_rel,
        'input_gradient_sign_agreement':sign_agreement,'CPU_CUDA_PGD_bit_identity_claimed':False,
        'GPU_allocator_cap_bytes':cap,'peak_allocated_bytes':peak_alloc,'peak_reserved_bytes':peak_reserved,
        'torch_version':torch.__version__,'device':torch.cuda.get_device_name(0),
        'bridge_sha256':core.sha(r/'cpu_io_cuda_bridge.py'),'checker_sha256':core.sha(__file__)}
    with (OUT/'RESULT.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    with (OUT/'COMPLETED.json').open('x',encoding='utf8') as f:json.dump({'result_sha256':core.sha(OUT/'RESULT.json'),
        'source_freeze_sha256':core.sha(r/'CUDA_BRIDGE_FREEZE.json')},f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)


try:main()
except BaseException:
    traceback.print_exc()
    with (OUT/'FAILURE.json').open('x',encoding='utf8') as f:json.dump({'traceback':traceback.format_exc()},f,indent=2);f.write('\n')
    raise
