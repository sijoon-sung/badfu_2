"""Single read-only archive-stream integrity check. No tensor/model deserialization."""
import hashlib,json,math,os,shutil,stat,subprocess,sys,time,traceback,zipfile,zlib
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(4194304),b''):h.update(block)
    return h.hexdigest()
def exclusive(n,value):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
def guard(p):
    from native_memory import memory_information
    from native_processes import processes
    start=time.monotonic();g=p['resource_guard']
    while True:
        m=memory_information();disk=shutil.disk_usage(ROOT).free
        gpu=subprocess.check_output(['C:/Windows/System32/nvidia-smi.exe','--query-gpu=utilization.gpu,memory.free,memory.used','--format=csv,noheader,nounits'],text=True).strip()
        util,free,used=[int(x.strip()) for x in gpu.split(',')]
        competitors=[r for r in processes() if r['ProcessId'] not in [os.getpid(),os.getppid()] and any(t.lower() in r['CommandLine'].lower() for t in p['known_training_process_tokens'])]
        ok=m['availableBytes']>=g['native_available_GiB']*2**30 and m['commitLimit']-m['committedBytes']>=g['commit_free_GiB']*2**30 and disk>=g['disk_free_GiB']*2**30 and util<=g['GPU_util_max'] and free>=g['GPU_free_MiB_min'] and used<=g['GPU_used_MiB_max'] and not competitors
        if ok:return {'memory':m,'disk_free_bytes':disk,'GPU':gpu,'competitors':0,'wait_seconds':time.monotonic()-start}
        assert time.monotonic()-start<g['max_wait_seconds'],'Admission guard timeout; no automatic retry'
        time.sleep(g['poll_seconds'])

def main():
    p=read(ROOT/'PROFILE.json');b=read(ROOT/'INPUT_BINDING.json');freeze=read(ROOT/'SOURCE_FREEZE.json');pub=read(ROOT/'RUN_PUBLICATION.json')
    assert ROOT==Path(p['execution_root']) and p['launch_enabled'] and not p['local_receiver_launch_enabled'] and list(sys.version_info[:3])==p['python_version']
    assert pub['state']=='published_actual_endpoint_archive_integrity_before_execution' and pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    for n,h in freeze['files'].items():assert sha(ROOT/n)==h,n
    for meta in b.values():assert sha(meta['path'])==meta['sha256'] and Path(meta['path']).stat().st_size==meta['bytes']
    result=read(b['export_result']['path']);done=read(b['export_completion']['path']);terminal=read(b['export_terminal']['path']);manifest=read(b['exported_manifest']['path']);seal=read(b['exported_seal']['path'])
    assert result['state']=='completed_four_endpoint_and_scalar_epoch_review_export_only' and done['state']=='completed_remote_endpoint_review_packet_export'
    assert done['result_sha256']==b['export_result']['sha256'] and done['exit_code']==terminal['foreground_exit_code']==terminal['root_native_processes']==terminal['failure_count']==0
    assert result['archive']==p['archive'] and result['manifest_sha256']==p['manifest_sha256']==b['exported_manifest']['sha256'] and result['seal_sha256']==p['seal_sha256']==b['exported_seal']['sha256']
    assert manifest['models']==p['expected_models'] and manifest['new_tensor_loads']==manifest['new_CPU_model_checks']==0 and not result['performance_success']
    archive=Path(p['archive']['path']);assert archive.stat().st_size==p['archive']['bytes'] and not archive.stat().st_mode&stat.S_IWRITE
    exclusive('ONCE.json',{'pid':os.getpid(),'unix':time.time(),'profile_sha256':sha(ROOT/'PROFILE.json')});exclusive('ADMISSION.json',guard(p))
    assert sha(archive)==p['archive']['sha256']
    packet=p['packet_name'];files=manifest['files'];assert len(files)==p['expected_hashed_files']==14
    manifest_name=packet+'/ENDPOINT_MANIFEST.json';seal_name=packet+'_SEAL.json'
    expected={packet+'/'+n:v for n,v in files.items()}
    expected[manifest_name]={'sha256':p['manifest_sha256'],'bytes':b['exported_manifest']['bytes']};expected[seal_name]={'sha256':p['seal_sha256'],'bytes':b['exported_seal']['bytes']}
    assert len(expected)==p['expected_archive_entries']==16 and {n for n in files if n.endswith('.pt')}=={v['file'] for v in p['expected_models'].values()}
    captures={};members=[]
    with zipfile.ZipFile(archive,'r') as z:
        infos=z.infolist();assert len(infos)==len({i.filename for i in infos})==16 and set(i.filename for i in infos)==set(expected)
        assert sum(i.file_size for i in infos)<=p['maximum_uncompressed_bytes']
        for info in infos:
            path=PurePosixPath(info.filename)
            assert not path.is_absolute() and '..' not in path.parts and path.as_posix()==info.filename and ':' not in info.filename and chr(92) not in info.filename
            assert not info.is_dir() and not info.flag_bits&1 and stat.S_IFMT(info.external_attr>>16)!=stat.S_IFLNK
            meta=expected[info.filename];assert info.file_size==meta['bytes']<=p['maximum_member_bytes']
            capture=info.filename.endswith('.json') or info.filename.endswith('.jsonl');data=bytearray();total=crc=0;h=hashlib.sha256()
            with z.open(info) as stream:
                for block in iter(lambda:stream.read(p['stream_chunk_bytes']),b''):
                    h.update(block);crc=zlib.crc32(block,crc);total+=len(block)
                    if capture:
                        data.extend(block);assert len(data)<=p['maximum_captured_metadata_bytes']
            assert total==info.file_size and crc&0xffffffff==info.CRC and h.hexdigest()==meta['sha256'],info.filename
            if capture:captures[info.filename]=bytes(data)
            members.append({'name':info.filename,'bytes':total,'sha256':h.hexdigest(),'CRC32_hex':format(crc&0xffffffff,'08x'),'CRC_and_hash_exact':True})
    assert json.loads(captures[manifest_name])==manifest and json.loads(captures[seal_name])==seal and seal['manifest_sha256']==p['manifest_sha256']
    scope=json.loads(captures[packet+'/SCOPE.json']);assert scope==manifest['scope'] and scope['diagnostic_only'] and not scope['local_delivery_complete'] and not scope['local_CPU_verification_completed'] and not scope['whole_prior_packet_delivered']
    assert scope['raw_pretraining_and_full_role_history_optimizer_RNG_and_queries_remain_on_DISLAB'] and scope['new_model_or_tensor_loads']==scope['new_CPU_forwards']==0
    log_rows={}
    for branch in ['benign','minus','plus']:
        rows=[json.loads(line) for line in captures[packet+'/epoch_logs/'+branch+'.jsonl'].decode('utf-8').splitlines()];seen=set()
        assert len(rows)==p['expected_epoch_rows_per_branch']==1000
        for item in rows:
            assert set(item)==set(p['epoch_keys'])
            for k in p['epoch_keys'][:-1]:assert type(item[k]) is int
            assert type(item['loss']) in [int,float] and math.isfinite(item['loss'])
            assert 1<=item['round']<=20 and 0<=item['client']<20 and 1<=item['epoch']<=5 and item['examples']>0 and item['batches']>0 and item['cumulative_role_batches']>0
            key=(item['round'],item['client'],item['epoch']);assert key not in seen;seen.add(key)
        log_rows[branch]={'rows':len(rows),'columns':p['epoch_keys'],'scalar_schema_finite_and_keys_exact':True,'loss_recomputed':False}
    assert sha(archive)==p['archive']['sha256'] and not archive.stat().st_mode&stat.S_IWRITE and 'torch' not in sys.modules and 'numpy' not in sys.modules
    for meta in b.values():assert sha(meta['path'])==meta['sha256']
    out={'state':'passed_full_endpoint_archive_CRC_member_SHA_and_scalar_log_schema','source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'source_commit':pub['commit'],'archive':p['archive'],'archive_unchanged_readonly':True,'archive_SHA_checks':2,'member_stream_passes':1,'CRC_checked_entries':16,'exact_member_SHA_and_bytes':16,'manifest_hashed_entries':14,'models_present_as_bytes_only':4,'manifest_sha256':p['manifest_sha256'],'external_seal_sha256':p['seal_sha256'],'members':members,'scalar_epoch_logs':log_rows,'original_exporter_reinvoked':False,'source_snapshot_guards_rerun':0,'payloads_extracted_or_copied':0,'new_tensor_model_loads':0,'new_CPU_model_or_inference_calls':0,'new_training_or_optimizer':False,'local_runtime_verified':False,'local_receiver_or_transfer_started':False,'new_case_registration':False,'performance_success':False,'overall_goal_complete':False}
    exclusive('RESULT.json',out);exclusive('COMPLETION.json',{'state':'completed_archive_transport_integrity_only','exit_code':0,'finished_unix':time.time(),'result_sha256':sha(ROOT/'RESULT.json'),'local_delivery_complete':False,'overall_goal_complete':False});print(json.dumps({'state':out['state'],'CRC_entries':16,'manifest_hashed_entries':14,'new_model_loads':0}))
if __name__=='__main__':
    try:main()
    except BaseException:
        exclusive('FAILURE.json',{'state':'failed_preserved_no_retry','pid':os.getpid(),'traceback':traceback.format_exc()});raise
