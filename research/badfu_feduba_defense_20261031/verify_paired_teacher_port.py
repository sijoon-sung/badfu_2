"""Compatibility audit on sealed BadFU arrays and random FedUBA state fixtures."""
import importlib.util,json,os,time,traceback
from pathlib import Path
import torch
import stage05_common as s
from endpoint_interface import BADFU,FEDUBA
from paired_teacher import aligned_reference
from sourcepair_pilot import cpu_guard
core=s.core;OUT=s.HERE/'paired_teacher_port'
SOURCE=Path('D:/FEDUBA_PAPER_IMPLEMENTATION_20261031/model_reference.py')
SOURCE_SHA='57d92398d95a1669c02590052c457f59332286c288f9e0aee2baf83beb192fc3'


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources()
    freeze=core.read(s.HERE/'PAIRED_TEACHER_PORT_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    assert core.sha(SOURCE)==SOURCE_SHA
    cpu=cpu_guard();assert not torch.cuda.is_initialized()
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu},f)
    selected,sealed,states=s.snapshot();cls=sealed.model_class(Path(selected['source_root']))
    fit=torch.tensor(core.read(s.HERE/'PROXY_SPLIT.json')['fit_ids'])
    original={k:core.tensor_digest(v) for k,v in states.items()};legacy={}
    for pair,a,b in core.PAIRS:
        x=s.original_cache('features_'+a+'.pt')[fit];y=s.original_cache('features_'+b+'.pt')[fit]
        candidate,detail=aligned_reference(states[a],states[b],x,y,BADFU)
        p=s.OUT/(pair+'_aligned_model.pt');assert core.sha(p)==core.read(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')['models'][p.name]
        previous=torch.load(p,map_location='cpu',weights_only=True)
        assert candidate.keys()==previous.keys() and all(torch.equal(v,previous[k]) for k,v in candidate.items())
        assert all(torch.equal(v,states[a][k]) for k,v in candidate.items() if not k.startswith('model.fc.'))
        cls().load_state_dict(candidate,strict=True)
        legacy[pair]={'exact_full_state_equality':True,'matched_tensors':len(candidate),'head_path':detail['head_path']}
    assert all(core.tensor_digest(v)==original[k] for k,v in states.items())
    spec=importlib.util.spec_from_file_location('paired_teacher_feduba_fixture',SOURCE)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    torch.manual_seed(20261031+2200);pre=module.ResNet18().eval();post=module.ResNet18().eval()
    ps={k:v.detach().clone() for k,v in pre.state_dict().items()};qs={k:v.detach().clone() for k,v in post.state_dict().items()}
    pd=core.tensor_digest(ps);qd=core.tensor_digest(qs)
    x=torch.randn((128,512),generator=torch.Generator().manual_seed(20261031+2201))
    out,detail=aligned_reference(ps,qs,x,x.clone(),FEDUBA)
    assert torch.equal(out['linear.weight'],qs['linear.weight']) and torch.equal(out['linear.bias'],qs['linear.bias'])
    assert all(torch.equal(v,ps[k]) for k,v in out.items() if not k.startswith('linear.'))
    module.ResNet18().load_state_dict(out,strict=True)
    rejected=[]
    invalid=x.clone();invalid[0,0]=float('nan')
    for name,one,two,z,w,profile in [
        ('wrong_head',ps,qs,x,x,BADFU),
        ('surrogate201',module.ResNet18_201().state_dict(),module.ResNet18_201().state_dict(),x,x,FEDUBA),
        ('wrong_features',ps,qs,x[:,:511],x[:,:511],FEDUBA),
        ('nonfinite',ps,qs,invalid,x,FEDUBA)]:
        try:aligned_reference(one,two,z,w,profile)
        except ValueError:rejected.append(name)
        else:raise AssertionError('invalid input accepted: '+name)
    assert core.tensor_digest(ps)==pd and core.tensor_digest(qs)==qd
    assert core.tensor_digest(pre.state_dict())==pd and core.tensor_digest(post.state_dict())==qd
    assert not torch.cuda.is_initialized() and core.sha(SOURCE)==SOURCE_SHA
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    result={'state':'passed','case_id':selected['case_id'],'purpose':'purification_pilot','BadFU_legacy_states':legacy,
        'FedUBA_fixture':'two_new_random10class_models_same_coordinate_synthetic128x512_features',
        'FedUBA_exact_Post_head_Pre_nonhead':True,'all_original_endpoint_states_unchanged':True,
        'actual_FedUBA_checkpoint_selected':False,'fresh_model_inference':False,'training_or_gradient_updates':False,
        'defense_efficacy_evaluated':False,'trusted_teacher':False,'rejected':rejected,
        'verifier_sha256':core.sha(__file__),'constructor_sha256':core.sha(s.HERE/'paired_teacher.py')}
    with (OUT/'RESULT.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    with (OUT/'COMPLETED.json').open('x',encoding='utf8') as f:json.dump({'result_sha256':core.sha(OUT/'RESULT.json'),
        'source_freeze_sha256':core.sha(s.HERE/'PAIRED_TEACHER_PORT_FREEZE.json')},f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True)
        with (OUT/'FAILURE.json').open('x',encoding='utf8') as f:json.dump({'traceback':traceback.format_exc()},f,indent=2);f.write('\n')
        raise
