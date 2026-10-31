"""Conditional one-step synthetic fixture; never a defense efficacy result."""
import json,os,time,traceback
from pathlib import Path
import torch
import stage05_common as s
from stage08 import norm,loss
core=s.core;OUT=s.HERE/'stage12_contract'


def main():
    freeze=core.read(s.HERE/'STAGE12_CONTRACT_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    parent=core.read(s.HERE/'stage11/RESULT.json');audit=core.read(s.HERE/'stage11/INDEPENDENT_VERIFICATION.json')
    assert parent['state']=='completed' and parent['cases']['attack_cover850']['state']=='failed_necessary_ASR'
    assert not any(parent['method_necessary_gates'].values())
    assert audit['state']=='passed' and audit['scope']=='finished_pipeline'
    s.verify_sources();selected,sealed,states=s.snapshot();assert not torch.cuda.is_initialized()
    OUT.mkdir(exist_ok=True)
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'fixture_only':True},f)
    torch.manual_seed(20261031);cls=sealed.model_class(Path(selected['source_root']))
    model=cls().eval();native=states['post'];model.load_state_dict(native,strict=True)
    head=model.get_submodule('model.fc')
    for p in head.parameters():p.requires_grad_(False)
    params=[p for p in model.parameters() if p.requires_grad]
    assert len(params)==len(list(model.parameters()))-2
    optimizer=torch.optim.Adam(params,lr=.0001,weight_decay=0)
    raw=torch.rand((2,3,32,32),generator=torch.Generator().manual_seed(20261031+1200))
    with torch.no_grad():target=(model(norm(raw))/2).softmax(1).roll(1,1)
    optimizer.zero_grad(set_to_none=True);value=loss(target,model(norm(raw)))
    assert torch.isfinite(value);value.backward()
    assert all(p.grad is None for p in head.parameters())
    assert any(p.grad is not None and bool(p.grad.abs().sum()>0) for p in params)
    assert all(p.grad is None or torch.isfinite(p.grad).all() for p in params)
    optimizer.step();state={k:v.detach().clone() for k,v in model.state_dict().items()}
    assert all(torch.isfinite(v).all() for v in state.values())
    for k in state:
        if core.is_buffer(k) or k.startswith('model.fc.'):assert torch.equal(state[k],native[k]),k
    assert any(not torch.equal(v,native[k]) for k,v in state.items() if not core.is_buffer(k) and not k.startswith('model.fc.'))
    fixture=OUT/'one_step_synthetic_fixture.pt'
    torch.save({'fixture_model_state':state,'optimizer':optimizer.state_dict(),'rng':torch.get_rng_state(),
                'synthetic_raw':raw,'model_derived_target_T2':target,'steps':1},fixture)
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    result={'state':'passed','fixture_only':True,'synthetic_images':2,'optimizer_steps':1,
        'groundtruth_labels_or_actual_trigger_used':False,'new_FL_or_FU':False,'defense_efficacy_evaluated':False,
        'candidate_source_sha256':core.sha(s.HERE/'backbone_only_candidate.py'),
        'verifier_source_sha256':core.sha(__file__),'source_case':selected['case_id'],
        'source_post_sha256':selected['server_inputs']['post']['sha256'],'fixture_sha256':core.sha(fixture),
        'head_gradient_none':True,'head_state_exactly_unchanged':True,'BN_buffers_exactly_unchanged':True,
        'finite_nonzero_backbone_gradient':True,'backbone_updated':True,'CUDA_initialized':torch.cuda.is_initialized()}
    with (s.HERE/'STAGE12_GRADIENT_CONTRACT.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True)
        with (OUT/'FAILURE.json').open('x',encoding='utf8') as f:json.dump({'traceback':traceback.format_exc()},f,indent=2);f.write('\n')
        raise
