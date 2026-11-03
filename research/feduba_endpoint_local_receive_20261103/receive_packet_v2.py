"""One actual endpoint-only receive. Inactive until separate actual run publication."""
import json,os,stat,subprocess,sys,time,traceback,zipfile,zlib,hashlib
from pathlib import Path,PurePosixPath
from receive_common_v2 import ROOT,read,sha,record,event,source_checks,runtime_files,admission,verify_packet,packet_path

def main():
    p=source_checks(actual=True);runtime_files(p);bind=read(ROOT/'INPUT_BINDING.json');manifest=read(bind['manifest']['path'])
    assert read(bind['archive_integrity']['path'])['state']=='passed_full_endpoint_archive_CRC_member_SHA_and_scalar_log_schema'
    assert read(bind['archive_integrity_completion']['path'])['result_sha256']==bind['archive_integrity']['sha256']
    assert manifest['models']==p['models'] and len(manifest['files'])==14 and read(bind['registration']['path'])['case_ids']==p['case_ids']
    for m in p['source_catalogues'].values():assert sha(m['path'])==m['sha256'] and len(read(m['path'])['cases'])==m['case_count']
    packet=packet_path(p);seal=packet.with_name(packet.name+'_SEAL.json');archive=Path(p['local_archive_path']);assert not packet.exists() and not seal.exists() and not archive.parent.exists()
    record('RECEIVE_ONCE_V2.json',{'pid':os.getpid(),'unix':time.time(),'run_freeze_sha256':sha(ROOT/'RUN_FREEZE_V2.json')});record('RECEIVE_ADMISSION_V2.json',admission(p))
    private=ROOT/'private_ledger'/'v2';private.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='-1',PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    def child(script,label):
        with (private/(label+'.stdout.log')).open('xb') as stdout,(private/(label+'.stderr.log')).open('xb') as stderr:
            r=subprocess.run([p['runtime']['path'],'-B','-u',str(ROOT/script)],env=env,stdout=stdout,stderr=stderr)
        event({'stage':label,'child_exit_code':r.returncode});assert r.returncode==0,label
    child('probe_cpu_runtime_v2.py','CPU_runtime_probe');assert read(ROOT/'CPU_RUNTIME_VERIFIED_V2.json')['state']=='usable_declared_CPU_runtime_verified'
    assert sha(p['transport_library']['path'])==p['transport_library']['sha256'];sys.path.insert(0,str(Path(p['transport_library']['path']).parent));import dislab_audit as transport
    assert transport.REMOTE==p['transfer_remote'];archive.parent.mkdir(exist_ok=False);event({'stage':'new_archive_transfer_started','archive_sha256':p['archive']['sha256']})
    with (private/'transfer.stdout.log').open('xb') as stdout,(private/'transfer.stderr.log').open('xb') as stderr:
        t=subprocess.run(['scp.exe','-q',*transport.FLAGS,p['transfer_remote']+':'+p['archive']['path'].replace(chr(92),'/'),str(archive)],stdout=stdout,stderr=stderr)
    assert t.returncode==0 and archive.stat().st_size==p['archive']['bytes'] and sha(archive)==p['archive']['sha256']
    record('TRANSFER_RECEIPT_V2.json',{'state':'new_pinned_archive_received_hash_exact','exit_code':t.returncode,'archive_sha256':sha(archive),'bytes':archive.stat().st_size,'old_transfer_task_reused':False});event({'stage':'new_archive_received_hash_exact'})
    prefix=p['packet_name']+'/';expected={prefix+n:m for n,m in manifest['files'].items()};expected[prefix+'ENDPOINT_MANIFEST.json']={'sha256':p['manifest_sha256'],'bytes':bind['manifest']['bytes']};expected[p['packet_name']+'_SEAL.json']={'sha256':p['seal_sha256'],'bytes':bind['seal']['bytes']}
    outputs=[];parent=Path(p['local_review_parent']);parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'r') as z:
        infos=z.infolist();assert len(infos)==len({i.filename for i in infos})==p['maximum_entries']==16 and set(i.filename for i in infos)==set(expected)
        assert sum(i.file_size for i in infos)<=p['maximum_uncompressed_bytes']
        for info in infos:
            path=PurePosixPath(info.filename);dest=parent/info.filename;meta=expected[info.filename]
            assert not path.is_absolute() and '..' not in path.parts and path.as_posix()==info.filename and ':' not in info.filename and chr(92) not in info.filename and dest.resolve().is_relative_to(parent.resolve())
            assert not info.is_dir() and not info.flag_bits&1 and stat.S_IFMT(info.external_attr>>16)!=stat.S_IFLNK and info.file_size==meta['bytes']<=p['maximum_member_bytes']
            dest.parent.mkdir(parents=True,exist_ok=True);h=hashlib.sha256();total=crc=0
            with z.open(info) as source,dest.open('xb') as output:
                for block in iter(lambda:source.read(4194304),b''):output.write(block);h.update(block);total+=len(block);crc=zlib.crc32(block,crc)
                output.flush();os.fsync(output.fileno())
            assert total==info.file_size and crc&0xffffffff==info.CRC and h.hexdigest()==meta['sha256']==sha(dest);dest.chmod(0o444);outputs.append({'name':info.filename,'bytes':total,'sha256':h.hexdigest(),'CRC_exact':True})
    archive.chmod(0o444);guard=verify_packet(p);record('RECEIVED_PACKET_GUARD_V2.json',guard);event({'stage':'all16archive_members_received_and_guarded','hashed_packet_files':14})
    child('verify_cpu_storage_v2.py','CPU_storage_check');cpu=read(ROOT/'CPU_STORAGE_VERIFIED_V2.json');assert cpu['state']=='passed_four_endpoint_strict_CPU_finite_zero1_storage_checks' and len(cpu['rows'])==4 and cpu['zero1_forward_calls']==4
    assert sha(archive)==p['archive']['sha256'];verify_packet(p)
    for m in p['source_catalogues'].values():assert sha(m['path'])==m['sha256']
    record('RECEIVE_RESULT_V2.json',{'state':'received_four_endpoints_and_passed_local_CPU_storage_checks_registration_pending','archive':{'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive)},'packet_root':str(packet),'manifest_sha256':p['manifest_sha256'],'external_seal_sha256':p['seal_sha256'],'members':outputs,'models':p['models'],'CPU_storage_receipt_sha256':sha(ROOT/'CPU_STORAGE_VERIFIED_V2.json'),'CPU_runtime_receipt_sha256':sha(ROOT/'CPU_RUNTIME_VERIFIED_V2.json'),'new_model_loads':4,'CPU_zero1_forward_calls':4,'real_data_inference_or_training':False,'raw_private_query_or_RNG_transfer':False,'frozen_packet_scope_unchanged':True,'source_catalogues_unchanged':True,'catalogue_registration_complete':False,'local_delivery_complete':False,'performance_success':False,'overall_goal_complete':False});record('RECEIVE_COMPLETION_V2.json',{'state':'completed_receive_and_CPU_storage_only','exit_code':0,'result_sha256':sha(ROOT/'RECEIVE_RESULT_V2.json'),'catalogue_registration_complete':False,'local_delivery_complete':False,'overall_goal_complete':False});print(json.dumps({'state':'received_four_endpoints_and_passed_local_CPU_storage_checks_registration_pending'}))
if __name__=='__main__':
    try:main()
    except BaseException:record('RECEIVE_FAILURE_V2.json',{'state':'failed_preserved_no_retry','traceback':traceback.format_exc()});raise
