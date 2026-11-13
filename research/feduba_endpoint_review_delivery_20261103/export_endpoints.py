"""New bounded endpoint/scalar-log projection. No tensor or model imports."""
import hashlib,json,math,os,shutil,stat,subprocess,sys,time,traceback,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def exclusive(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
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
    p=read(ROOT/'EXPORT_PROFILE.json');b=read(ROOT/'EXPORT_INPUT_BINDING.json');pub=read(ROOT/'RUN_PUBLICATION.json');freeze=read(ROOT/'SOURCE_FREEZE.json')
    assert ROOT==Path(p['execution_root']) and p['launch_enabled'] and not p['local_receiver_launch_enabled'] and list(sys.version_info[:3])==p['python_version']
    assert pub['state']=='published_actual_endpoint_review_export_before_execution' and pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    for n,h in freeze['files'].items():assert sha(ROOT/n)==h,n
    for m in b.values():assert sha(m['path'])==m['sha256'] and Path(m['path']).stat().st_size==m['bytes']
    registered=read(b['registered']['path']);assert registered['state']=='registered_three_DISLAB_only_diagnostic_endpoint_pairs' and registered['new_case_count']==28 and registered['new_catalog_sha256']==p['expected_catalog_sha256']
    positive=read(b['positive_recovery']['path']);baseline=read(b['baseline_evaluation']['path'])
    assert positive['state']==baseline['state']=='passed' and not positive['minimum_operational_gate']['passed'] and not positive['original_verifier_completed_successfully']
    catroot=Path(p['catalog_root']);catpath=catroot/'catalog.json';assert sha(catpath)==p['expected_catalog_sha256'] and sha(catroot/'select_case.py')==p['expected_selector_source_sha256']
    cat=read(catpath);assert len(cat['cases'])==28
    for cid in p['case_ids'].values():assert next(v for v in cat['cases'] if v['id']==cid)['allowed_purposes']==['diagnostic']
    packet=Path(p['packet_root']);outer=packet.with_name(packet.name+'_SEAL.json');archive=ROOT/'ENDPOINT_REVIEW.zip'
    assert not packet.exists() and not outer.exists() and not archive.exists()
    exclusive('EXPORT_ONCE.json',{'pid':os.getpid(),'unix':time.time(),'profile_sha256':sha(ROOT/'EXPORT_PROFILE.json')});exclusive('ADMISSION.json',guard(p))
    env=os.environ.copy();env.update(PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='-1')
    selected={};sources={}
    for branch,cid in p['case_ids'].items():
        out=json.loads(subprocess.check_output([sys.executable,'-B',str(catroot/'select_case.py'),cid,'--purpose','diagnostic','--location','dislab'],text=True,encoding='utf-8',env=env))
        assert out['guard_state']=='all_snapshot_files_verified_on_this_host' and out['server_inputs']==p['expected_server_inputs'][branch]
        selected[branch]=out
        if sources:assert sources['pre']==out['server_inputs']['pre']
        else:sources['pre']=out['server_inputs']['pre']
        sources[branch]=out['server_inputs']['post']
    assert set(sources)=={'pre','benign','minus','plus'} and sha(catpath)==p['expected_catalog_sha256']
    bindings=read(ROOT/'PACKET_BINDING.json');manifests={k:read(Path(v['root'])/v['manifest']) for k,v in bindings.items()}
    packet.mkdir(parents=True,exist_ok=False);models={}
    def write_packet(rel,value):
        dest=packet/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
    for name,meta in sources.items():
        expected=p['endpoints'][name];src=Path(meta['path']);source_root=Path(bindings[expected['packet']]['root']).resolve()
        assert src.resolve().is_relative_to(source_root) and meta['sha256']==expected['sha256'] and meta['payload_key'] is None and meta['bytes']==expected['bytes']==44770315
        assert not src.stat().st_mode&stat.S_IWRITE and sha(src)==expected['sha256']
        dest=packet/'models'/(name+'.pt');dest.parent.mkdir(exist_ok=True);assert not dest.exists();shutil.copyfile(src,dest)
        assert sha(dest)==sha(src)==expected['sha256'] and dest.stat().st_size==expected['bytes']
        models[name]={'file':dest.relative_to(packet).as_posix(),'sha256':expected['sha256'],'bytes':44770315,'payload_key':None,'prior_DISLAB_strict_CPU_receipt_reused':True,'new_model_check':False}
    for src,name in [(Path(b['architecture']['path']),'model_reference.py'),(ROOT/'load_checkpoint.py','load_checkpoint.py')]:
        shutil.copyfile(src,packet/name);assert sha(src)==sha(packet/name)
    log_summary={}
    for branch,origin in p['epoch_log_projection'].items():
        source=Path(bindings[origin['packet']]['root'])/origin['member'];sealed=manifests[origin['packet']]['files'][origin['member']]
        assert sha(source)==sealed['sha256'] and source.stat().st_size==sealed['bytes']
        rows=[];seen=set()
        for line in source.read_text(encoding='utf-8').splitlines():
            row=json.loads(line)
            if row.get('kind')!='local_epoch':continue
            item={k:row[k] for k in p['epoch_whitelist']};assert math.isfinite(item['loss'])
            assert 1<=item['round']<=20 and 0<=item['client']<20 and 1<=item['epoch']<=5 and item['examples']>0 and item['batches']>0
            key=(item['round'],item['client'],item['epoch']);assert key not in seen;seen.add(key);rows.append(item)
        assert len(rows)==p['expected_epoch_rows_per_log']==1000
        dest=packet/'epoch_logs'/(branch+'.jsonl');dest.parent.mkdir(exist_ok=True)
        with dest.open('x',encoding='utf-8',newline='\n') as f:
            for row in rows:f.write(json.dumps(row,allow_nan=False)+'\n')
        restored=[json.loads(line) for line in dest.read_text(encoding='utf-8').splitlines()];assert restored==rows and sha(source)==sealed['sha256']
        log_summary[branch]={'file':dest.relative_to(packet).as_posix(),'rows':len(rows),'source_packet':origin['packet'],'source_member':origin['member'],'source_sha256':sealed['sha256'],'columns':p['epoch_whitelist'],'all_scalar_epoch_values_copied_unchanged':True,'raw_per_sample_fields_copied':False}
    eval_summary={'scope':'Evaluator-only aggregate standard-route reuse; never pass to a server method. No new inference and delta is not included.','baseline':baseline['models'],'positive':positive['models'],'positive_minimum_operational_gate':positive['minimum_operational_gate'],'original_positive_writer_failed_preserved':True,'separate_positive_recovery_passed':True,'performance_success':False}
    write_packet('EVALUATOR_ONLY_SUMMARY.json',eval_summary)
    write_packet('CASE_SELECTIONS.json',selected)
    write_packet('SOURCE_PROVENANCE.json',{'source_inputs':b,'source_publication_commit':pub['commit'],'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'source_case_ids':p['case_ids'],'source_packet_anchors':bindings,'source_catalogue_sha256':p['expected_catalog_sha256'],'source_code_author_unique_certified':False,'declared_interpretation_only':True,'old_source_and_failure_overwritten':False})
    scope={'models':list(models),'model_count':4,'new_model_or_tensor_loads':0,'new_CPU_forwards':0,'epoch_log_projection':log_summary,'excluded':p['excluded_payloads'],'raw_pretraining_and_full_role_history_optimizer_RNG_and_queries_remain_on_DISLAB':True,'full_original_epoch_logs_remain_on_DISLAB':True,'diagnostic_only':True,'local_receiver_launched':False,'local_CPU_verification_completed':False,'local_delivery_complete':False,'whole_prior_packet_delivered':False,'performance_success':False,'overall_goal_complete':False}
    write_packet('SCOPE.json',scope)
    (packet/'README.txt').write_text('Four existing FedUBA endpoints for diagnostic review only.\nSame shared pre and benign/minus/plus after weights, no new training or attack success. Exactly3000 scalar FU epoch rows are projected unchanged; raw role/RNG/query/per-sample data, trigger delta and full histories remain on DISLAB.\nVerify the externally supplied ENDPOINT_MANIFEST SHA and sibling seal before using load_checkpoint.py. Select an explicit registered diagnostic case and consume only pre/post server inputs. Local CPU/receipt/catalogue approval requires a separate receiver contract; this export does not establish it. Preserve original failed performance and writer failure.\n',encoding='utf-8',newline='\n')
    files={x.relative_to(packet).as_posix():{'sha256':sha(x),'bytes':x.stat().st_size} for x in sorted(packet.rglob('*')) if x.is_file()}
    assert set(n for n in files if n.endswith('.pt'))=={v['file'] for v in models.values()}
    assert len(files)<=p['maximum_packet_files'] and sum(v['bytes'] for v in files.values())<=p['maximum_packet_uncompressed_bytes'] and all(v['bytes']<=p['maximum_member_bytes'] for v in files.values())
    manifest={'state':'sealed_four_diagnostic_endpoints_and_scalar_FU_epoch_logs','files':files,'models':models,'scope':scope,'new_tensor_loads':0,'new_CPU_model_checks':0,'origin_strict_CPU_receipts_reused':True}
    write_packet('ENDPOINT_MANIFEST.json',manifest)
    with outer.open('x',encoding='utf-8',newline='\n') as f:json.dump({'packet_name':packet.name,'manifest_sha256':sha(packet/'ENDPOINT_MANIFEST.json'),'hashed_files':len(files),'model_files':4,'new_CPU_model_checks':0},f,indent=2);f.write('\n')
    for x in packet.rglob('*'):
        if x.is_file():x.chmod(0o444)
    outer.chmod(0o444)
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for x in sorted(packet.rglob('*')):
            if x.is_file():z.write(x,packet.name+'/'+x.relative_to(packet).as_posix())
        z.write(outer,outer.name)
    with zipfile.ZipFile(archive) as z:assert len(z.infolist())==len(files)+2
    archive.chmod(0o444)
    assert sha(catpath)==p['expected_catalog_sha256'] and 'torch' not in sys.modules and 'numpy' not in sys.modules
    for m in bindings.values():assert sha(Path(m['root'])/m['manifest'])==m['manifest_sha256'] and sha(m['seal'])==m['seal_sha256']
    result={'state':'completed_four_endpoint_and_scalar_epoch_review_export_only','packet_root':str(packet),'manifest_sha256':sha(packet/'ENDPOINT_MANIFEST.json'),'seal_sha256':sha(outer),'hashed_files':len(files),'model_files':4,'scalar_epoch_rows':3000,'source_case_ids':p['case_ids'],'source_guard_passes':3,'source_packet_file_hash_checks':2427,'models':models,'archive':{'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive)},'source_catalogue_unchanged':True,'source_packets_seals_and_original_failures_preserved':True,'model_files_copied':4,'new_model_tensor_loads':0,'new_CPU_or_inference_calls':0,'new_training':False,'local_receiver_started':False,'local_delivery_complete':False,'performance_success':False,'overall_goal_complete':False}
    exclusive('EXPORT_RESULT.json',result);exclusive('COMPLETION.json',{'state':'completed_remote_endpoint_review_packet_export','exit_code':0,'finished_unix':time.time(),'result_sha256':sha(ROOT/'EXPORT_RESULT.json'),'local_delivery_complete':False,'overall_goal_complete':False});print(json.dumps({'state':result['state'],'models':4,'epoch_rows':3000,'archive_bytes':result['archive']['bytes'],'new_model_loads':0}))
if __name__=='__main__':
    try:main()
    except BaseException:
        exclusive('EXPORT_FAILURE.json',{'state':'failed_preserved_no_retry','pid':os.getpid(),'traceback':traceback.format_exc()});raise
