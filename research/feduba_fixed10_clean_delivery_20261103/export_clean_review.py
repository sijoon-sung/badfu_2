"""One new readonly fixed10 clean packet: strict CPU3/zero1 only, not CA evaluation."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
import importlib.util
import json
from pathlib import Path
import shutil
import traceback
import zipfile
from clean_delivery_binding import require_published_run
from runtime_common import ROOT,read,write,sha,guard,freeze_check
def main():
    p,a=require_published_run();freeze_check('CLEAN_EXPORT_FREEZE.json');guard()
    foundation=Path(p['foundation_root']);binding=read(ROOT/'FOUNDATION_INPUT_BINDING.json')
    assert a['input_binding_sha256']==sha(ROOT/'FOUNDATION_INPUT_BINDING.json')
    for n,d in binding['receipt_sha256'].items():assert sha(foundation/n)==d,n
    assert not list(foundation.glob('*FAILURE.json'))
    with (ROOT/'CLEAN_EXPORT_ONCE.json').open('x',encoding='utf-8') as f:json.dump({'pid':os.getpid(),'case_id':p['normal_case_id']},f)
    import torch
    import model_reference
    torch.set_num_threads(1);assert not torch.cuda.is_initialized()
    packet=Path(p['packet_root']);packet.mkdir(parents=True,exist_ok=False)
    def copy(src,name):
        src=Path(src);dst=(packet/name).resolve();assert dst.is_relative_to(packet.resolve()) and not dst.exists()
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);assert sha(src)==sha(dst)
        return dst
    for n,meta in binding['payloads'].items():
        assert sha(meta['path'])==meta['sha256'];copy(meta['path'],n)
    evidence=['CLEAN_FL_PROFILE.json','SOURCE_PROFILE.json','SOURCE_FREEZE.json','SOURCE_PUBLICATION.json','SOURCE_CHECK_RESULT.json',
        'CLEAN_FL_READY.json','CLEAN_FL_FREEZE.json','LAUNCH_PROFILE.json','RUN_FREEZE.json','RUN_PUBLICATION.json','PREPARATION_RESULT.json',
        'CLEAN_FL_RESULT.json','CLEAN_FL_VERIFIED.json','CLEAN_FL_STATE.json','FOUNDATION_CONTROLLER_STATE.json','FOUNDATION_CONTROLLER_ONCE.json',
        'CLEAN_FL_STARTED.json','COMPLETION.json','PROTOCOL.txt','REPORT_KO.txt','CLEAN_SPLIT.json','clean_fl/MANIFEST.json','clean_fl/events.jsonl',
        'console_clean_fl_runner.py.log','console_verify_clean_fl.py.log']
    for n in evidence:copy(foundation/n,'evidence/'+n)
    for n in read(foundation/'SOURCE_FREEZE.json')['files']:copy(foundation/n,'executed_code/'+n)
    copy(ROOT/'model_reference.py','model_reference.py');copy(ROOT/'review_loader.py','load_checkpoint.py')
    for n in read(ROOT/'SOURCE_FREEZE.json')['files']:copy(ROOT/n,'delivery_code/'+n)
    for n in ['FOUNDATION_INPUT_BINDING.json','FOUNDATION_TERMINAL_CHECK.json','LAUNCH_PROFILE.json','RUN_FREEZE.json','RUN_PUBLICATION.json']:
        copy(ROOT/n,'delivery_receipts/'+n)
    checks=[]
    for n,meta in binding['payloads'].items():
        value=torch.load(packet/n,map_location='cpu',weights_only=True)
        state=value if meta['payload_key'] is None else value[meta['payload_key']]
        assert all(v.device.type=='cpu' and bool(torch.isfinite(v).all()) for v in state.values())
        model=model_reference.ResNet18().cpu().eval();model.load_state_dict(state,strict=True)
        with torch.inference_mode():
            output=model(torch.zeros(1,3,32,32));assert output.shape==(1,10) and bool(torch.isfinite(output).all())
        if meta['payload_key']:
            assert value['epochs']==10 and value['batches']==200 and value['optimizer']['state']
            assert value['rng']['torch_CPU'].numel() and len(value['rng']['torch_CUDA'])==1
            assert all(bool(torch.isfinite(v['momentum_buffer']).all()) for v in value['optimizer']['state'].values())
        checks.append({'file':n,'sha256':meta['sha256'],'payload_key':meta['payload_key'],'strict_CPU_finite_forward':True})
        del model,value,state
    assert len(checks)==3 and not torch.cuda.is_initialized()
    write(packet/'CPU_VERIFIED.json',{'state':'passed','CPU_only':True,'payloads':checks,'clean_correct':binding['clean_correct'],'CA_pct':binding['CA_pct'],
        'performance_source':'Original completed independent DISLAB10000 CA. This storage check has3 zero1 model calls only.'})
    write(packet/'DELIVERY_SCOPE.json',{'case_id':p['normal_case_id'],'purpose':'normal_clean_foundation_diagnostic_only',
        'actual_clean_rounds':20,'actual_original_roles':200,'packet_tensor_payloads':3,'local_role_payloads':1,'last_role_client':19,
        'last_role_original':binding['payloads']['run/last_role.pt'],'all_original_history_retained_at':str(foundation/'clean_fl'),
        'local_packet_includes_all200_role_tensors':False,'all_epoch_logs_included':True,'actual_attack_or_post_unlearning_pair':False,'default_BadFU_cases_changed':False})
    files={path.relative_to(packet).as_posix():{'sha256':sha(path),'bytes':path.stat().st_size} for path in sorted(packet.rglob('*')) if path.is_file()}
    write(packet/'DELIVERY_MANIFEST.json',{'case_id':p['normal_case_id'],'files':files,'payloads':checks})
    digest=sha(packet/'DELIVERY_MANIFEST.json')
    write(packet/'DELIVERY_SEAL.json',{'case_id':p['normal_case_id'],'manifest_sha256':digest,'payload_file_count':len(files),'kind':'normal_fixed10_foundation_not_attack_pair'})
    for path in packet.rglob('*'):
        if path.is_file():path.chmod(0o444)
    spec=importlib.util.spec_from_file_location('new_fixed10_packet_guard',packet/'load_checkpoint.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    checked=module.verify(packet,digest)
    archive=ROOT/'CLEAN_REVIEW_DELIVERY.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as f:
        for path in sorted(packet.rglob('*')):
            if path.is_file():f.write(path,path.relative_to(packet).as_posix())
    write(ROOT/'CLEAN_REVIEW_DELIVERY_REMOTE.json',{'state':'exported_verified_normal_review','case_id':p['normal_case_id'],'packet_root':str(packet),
        'archive_path':str(archive),'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'manifest_sha256':digest,
        'seal_sha256':sha(packet/'DELIVERY_SEAL.json'),'payload_file_count':len(files),'packet_total_files':len(files)+2,'tensor_payload_count':3,'guard':checked,
        'pre':{'path':str(packet/'run/before.pt'),'sha256':binding['payloads']['run/before.pt']['sha256'],'payload_key':None},
        'local_delivery_complete':False,'catalogue_registered':False,'FedUBA_attack_completed':False})
if __name__=='__main__':
    try:main()
    except BaseException:
        write(ROOT/'CLEAN_EXPORT_FAILURE.json',{'state':'failed_preserved','pid':os.getpid(),'traceback':traceback.format_exc()});raise
