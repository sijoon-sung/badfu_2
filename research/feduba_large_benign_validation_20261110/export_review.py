"""One CPU-only final review packet; no training or endpoint inference."""
import json
import os
from pathlib import Path
import shutil
import zipfile
from bindings import ROOT,read,write,sha


def main():
    (ROOT/'EXPORT_ONCE').open('x').write(str(os.getpid()))
    assert read(ROOT/'DELIVERY_PUBLICATION.json')['all_raw_blob_bytes_verified']
    for name,digest in read(ROOT/'DELIVERY_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    completion=read(ROOT/'COMPLETION.json')
    assert completion['state'] in ('bounded_claim_falsified','bounded_controls_below_frozen_reference')
    cfg=read(ROOT/'PROFILE.json');binding=read(ROOT/'HISTORY_BINDING.json')
    packet=ROOT/'review_packet';packet.mkdir(exist_ok=False)
    def copy(source,relative,expected=None):
        source=Path(source);target=packet/relative
        assert target.resolve().is_relative_to(packet.resolve())
        target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists()
        if expected is not None:assert sha(source)==expected
        shutil.copyfile(source,target);assert sha(target)==sha(source)
        return target
    payloads=[]
    payloads.append((copy(binding['pre']['path'],'models/pre.pt',binding['pre']['sha256']),'model',None))
    for index,verdict in enumerate(completion['results']):
        branch=verdict['branch'];opaque=verdict['opaque']
        result=read(ROOT/('FU_'+branch+'_RESULT.json'));audit=read(ROOT/('FU_'+branch+'_VERIFIED.json'))
        assert audit['state']=='passed' and audit['result_sha256']==sha(ROOT/('FU_'+branch+'_RESULT.json'))
        case=ROOT/'detector'/opaque;assert read(case/'VERIFIED.json')['all_counts_exact']
        payloads.append((copy(result['after']['path'],'models/'+opaque+'_after.pt',result['after']['sha256']),'model',None))
        manifest=read(ROOT/'fu'/branch/'MANIFEST.json')
        last=manifest['rounds'][-1]['trained_roles'][-1]['checkpoint']
        payloads.append((copy(ROOT/last['path'],'representative_roles/'+opaque+'_last.pt',last['sha256']),'role','model'))
        copy(ROOT/'fu'/branch/'epochs.jsonl','logs/'+opaque+'_all1000epochs.jsonl')
        copy(ROOT/'fu'/branch/'MANIFEST.json','logs/'+opaque+'_full_history_manifest.json')
        for p in case.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts:continue
            if p.suffix not in ('.json','.py','.pt','.txt'):continue
            target=copy(p,'detectors/'+opaque+'/'+p.relative_to(case).as_posix())
            if p.suffix=='.pt':payloads.append((target,'transform',None))
        for name in ['FU_'+branch+'_RESULT.json','FU_'+branch+'_VERIFIED.json','CASE_'+branch+'.json',
                     'CATALOG_'+branch+'.json','VERDICT_'+branch+'.json','CLEAN_'+branch+'.json']:
            copy(ROOT/name,'metadata/'+name)
    # Own evaluator request IDs are private packet data, never a server input.
    copy(ROOT/'PRIVATE_REQUESTS.json','private/evaluator_request_IDs.json')
    for relative in ['incidents/publication_timeout/CONTROLLER_STATE.json',
                     'incidents/publication_timeout/CONTROLLER_FAILURE.json',
                     'incidents/pending_import_failure/FINISH_FAILURE.json']:
        p=ROOT/relative
        if p.exists():copy(p,relative)
    for p in ROOT.iterdir():
        if not p.is_file():continue
        if p.suffix=='.py':copy(p,'source/'+p.name)
        elif p.suffix in ('.json','.txt') and p.name not in ('PRIVATE_REQUESTS.json','CATALOG_BEFORE.json','CONTROLLER_FAILURE.json'):
            if not (packet/'metadata'/p.name).exists():copy(p,'metadata/'+p.name)
    import torch
    import model_reference
    from probe_reference import Transform
    torch.set_num_threads(2)
    checks=[]
    def finite(value):
        if isinstance(value,torch.Tensor):assert torch.isfinite(value).all()
        elif isinstance(value,dict):
            for item in value.values():finite(item)
        elif isinstance(value,(list,tuple)):
            for item in value:finite(item)
    for p,kind,key in payloads:
        value=torch.load(p,map_location='cpu',weights_only=True);finite(value)
        if kind in ('model','role'):
            state=value if key is None else value[key]
            model=model_reference.ResNet18();model.load_state_dict(state,strict=True)
            assert all((v>=0).all() for k,v in state.items() if k.endswith(('running_var','num_batches_tracked')))
            del model
        else:
            family=p.stem.split('_')[0]
            opaque=p.relative_to(packet).parts[1]
            transform_cfg=read(packet/'detectors'/opaque/'PROFILE.json')
            model=Transform(family,transform_cfg);model.load_state_dict(value['transform'],strict=True)
            assert len(value['schedule'])==400 and all(len(s)==20 for s in value['schedule'])
            assert all(float(s['step'])==400 for s in value['optimizer']['state'].values())
            del model
        checks.append(dict(path=p.relative_to(packet).as_posix(),kind=kind,sha256=sha(p),strict_cpu_load=True,finite=True))
        del value
    write(packet/'STORAGE_CHECKS.json',dict(checks=checks,model_forward_calls=0,GPU_calls=0))
    scope=dict(completed_branches=[v['branch'] for v in completion['results']],
               unstarted_branches=completion['unstarted_branches'],
               includes='actual pre/after, one last-role model/SGD/RNG per completed branch, all1000 epoch event logs, full history hashes, all derived transforms/optimizers/RNG/schedules/calibration/native evidence/source',
               excludes='bulk all-role/all-round tensor payloads remain on DISLAB; raw CIFAR data and unrelated external-service raw arguments excluded',
               private_request_IDs='evaluator-only; excluded from git and server discovery',
               allowed_purpose='diagnostic only; no default or attack-reproduction approval',
               universal_detection_validated=False)
    write(packet/'PACKET_SCOPE.json',scope)
    files={p.relative_to(packet).as_posix():dict(sha256=sha(p),bytes=p.stat().st_size) for p in packet.rglob('*') if p.is_file()}
    write(ROOT/'REVIEW_MANIFEST.json',dict(scope=scope,files=files,typed_payloads=len(checks)))
    shutil.copyfile(ROOT/'REVIEW_MANIFEST.json',packet/'REVIEW_MANIFEST.json')
    archive=ROOT/'D21_REVIEW_PACKET.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=2) as z:
        for p in packet.rglob('*'):
            if p.is_file():z.write(p,p.relative_to(packet).as_posix())
    write(ROOT/'REVIEW_SEAL.json',dict(file=archive.name,sha256=sha(archive),bytes=archive.stat().st_size,
                                     files=len(files),typed_payloads=len(checks),model_forward_calls=0))
    print(json.dumps(read(ROOT/'REVIEW_SEAL.json')),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        import traceback
        write(ROOT/'EXPORT_FAILURE.json',dict(traceback=traceback.format_exc()));raise
