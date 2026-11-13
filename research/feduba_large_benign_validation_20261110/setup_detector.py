"""Register a verified derived endpoint and prepare an opaque detector input."""
import json
from pathlib import Path
import shutil
from bindings import ROOT,read,write,sha,make_guard,append_case,select


def main(branch,index):
    result=read(ROOT/('FU_'+branch+'_RESULT.json'));verified=read(ROOT/('FU_'+branch+'_VERIFIED.json'))
    assert verified['state']=='passed' and verified['result_sha256']==sha(ROOT/('FU_'+branch+'_RESULT.json'))
    binding=read(ROOT/'HISTORY_BINDING.json');pre=binding['pre'];post=result['after']
    case_id='feduba.public_fixed10.cifar10.s42.large_normal.'+branch+'.fu20.20261110'
    files={}
    for label,meta in [('pre',pre),('post',post)]:
        p=Path(meta['path']);files[label]=dict(path=str(p),sha256=meta['sha256'],bytes=p.stat().st_size)
    for name in ['PROFILE.json','FU_'+branch+'_RESULT.json','FU_'+branch+'_VERIFIED.json']:
        p=ROOT/name;files[name]=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
    guard=make_guard(branch,case_id,files)
    entry=dict(id=case_id,family='feduba',source_root=str(ROOT/'fu'/branch),post_type='actual_normal_FedEraser20_diagnostic',
               allowed_purposes=['diagnostic'],server_inputs=dict(pre=pre,post=post),checkpoint_guard=guard,
               provenance='New legitimate large deletion; full20R/200roles/1000epochs and independent reconstruction passed. No attack/default approval.')
    append_case(entry,branch);selected=select(case_id,'diagnostic')
    write(ROOT/('CASE_'+branch+'.json'),selected)
    opaque=f'n{index:02d}';out=ROOT/'detector'/opaque;out.mkdir(parents=True,exist_ok=False)
    names=['run_search.py','verify_nonempty.py','route_core.py','probe_reference.py','feduba_model.py',
           'resource_guard.py','SHARED_SERVICE_IDENTITIES.json','checkpoint_guard.py']
    for name in names:shutil.copyfile(ROOT/name,out/name)
    cfg=read(ROOT/'DETECTOR_PROFILE.json');resource=read(ROOT/'PROFILE.json')
    cfg['id']='blind_route_detector.fixed_D20.D21.'+opaque
    cfg['success_rule']='D21 fixed 299/900 reference; evaluator controller only, no method score threshold'
    cfg['admission']=resource['admission'];cfg['memory_fraction']=resource['memory_fraction']
    cfg['resource_revision']='declared new validation resource profile, same scientific D20 fields'
    write(out/'PROFILE.json',cfg)
    write(out/'INPUTS.json',dict(cases=[dict(id=opaque,architecture='feduba',pre=selected['server_inputs']['pre'],post=selected['server_inputs']['post'])]))
    write(out/'FREEZE.json',dict(files={n:sha(out/n) for n in names+['PROFILE.json','INPUTS.json']},new_case=opaque,
                               original_D20_search_repeated=False,source_algorithm='D20 fixed four-route correction'))
    write(ROOT/('DETECTOR_READY_'+opaque+'.json'),dict(opaque=opaque,branch=branch,case_id=case_id,root=str(out),
                  files={n:dict(path=str(out/n),sha256=sha(out/n)) for n in ['PROFILE.json','INPUTS.json','FREEZE.json']},
                  publication_required=True,search_started=False))
    return out
