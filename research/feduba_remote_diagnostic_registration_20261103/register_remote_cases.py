"""One host-owned diagnostic-only catalogue append. Never loads model tensors."""
import copy,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time,traceback
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
    p=read(ROOT/'REGISTRATION_PROFILE.json');b=read(ROOT/'REGISTRATION_INPUT_BINDING.json');freeze=read(ROOT/'REGISTRATION_SOURCE_FREEZE.json');pub=read(ROOT/'REGISTRATION_RUN_PUBLICATION.json')
    assert ROOT==Path(p['execution_root']) and p['registration_enabled'] and list(sys.version_info[:3])==p['python_version']
    assert pub['state']=='published_actual_remote_diagnostic_registration_before_execution' and pub['source_freeze_sha256']==sha(ROOT/'REGISTRATION_SOURCE_FREEZE.json')
    for n,h in freeze['files'].items():assert sha(ROOT/n)==h,n
    for m in b.values():assert sha(m['path'])==m['sha256'] and Path(m['path']).stat().st_size==m['bytes']
    baseline=read(b['baseline_eval']['path']);positive=read(b['positive_recovery']['path'])
    assert baseline['state']=='passed' and positive['state']=='passed' and positive['independent_counts_exactly_equal'] and positive['all_sample_predictions_exactly_equal']
    assert not positive['minimum_operational_gate']['passed'] and not positive['original_verifier_completed_successfully'] and positive['original_independent_VERIFIED_absent'] and positive['original_failure_preserved']
    assert read(b['metadata_completion']['path'])['state']=='completed_registration_metadata_preparation_only'
    catroot=Path(p['catalog_root']);catpath=catroot/'catalog.json';original_bytes=catpath.read_bytes();assert sha(catpath)==p['expected_catalog_sha256']
    assert sha(catroot/'select_case.py')==p['expected_selector_source_sha256']
    old=json.loads(original_bytes.decode('utf-8'));assert len(old['cases'])==p['expected_case_count'] and {k:old[k] for k in p['expected_defaults']}==p['expected_defaults']
    assert len(set(p['case_ids'].values()))==3 and not any(c['id'] in p['case_ids'].values() for c in old['cases'])
    exclusive('REGISTRATION_ONCE.json',{'pid':os.getpid(),'unix':time.time(),'original_catalog_sha256':sha(catpath)});exclusive('REGISTRATION_ADMISSION.json',guard(p))
    private=ROOT/'private_ledger';private.mkdir(exist_ok=False);(private/'catalog_before.json').write_bytes(original_bytes);(private/'catalog_before.json').chmod(0o444)
    prior_audits={x.relative_to(catroot).as_posix():sha(x) for x in (catroot/'audit').rglob('*') if x.is_file()}
    packets=read(ROOT/'PACKET_BINDING.json');capsule=Path(p['guard_capsule_root']);capsule.mkdir(exist_ok=False)
    shutil.copyfile(ROOT/'checkpoint_guard.py',capsule/'checkpoint_guard.py');assert sha(capsule/'checkpoint_guard.py')==freeze['files']['checkpoint_guard.py']
    cmanifest={'state':'DISLAB_diagnostic_endpoint_guard_only','files':{'checkpoint_guard.py':{'sha256':sha(capsule/'checkpoint_guard.py'),'bytes':(capsule/'checkpoint_guard.py').stat().st_size}},'packets':packets,'endpoints':p['endpoints'],'scope':'Hash and existing stored CPU receipt guard only; no new tensors/forwards/performance validation. Local delivery incomplete.'}
    with (capsule/'GUARD_MANIFEST.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(cmanifest,f,indent=2);f.write('\n')
    with (capsule/'GUARD_SEAL.json').open('x',encoding='utf-8',newline='\n') as f:json.dump({'manifest_sha256':sha(capsule/'GUARD_MANIFEST.json'),'model_files_copied':0,'old_packets_modified':False},f,indent=2);f.write('\n')
    for x in capsule.iterdir():x.chmod(0o444)
    spec=importlib.util.spec_from_file_location('new_diagnostic_endpoint_guard',capsule/'checkpoint_guard.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    before_guard=module.verify(capsule,sha(capsule/'GUARD_MANIFEST.json'));assert before_guard['hashed_files']==809
    guard_meta={'manifest_path':str(capsule/'GUARD_MANIFEST.json'),'manifest_sha256':sha(capsule/'GUARD_MANIFEST.json'),'seal_path':str(capsule/'GUARD_SEAL.json'),'seal_sha256':sha(capsule/'GUARD_SEAL.json'),'loader_path':str(capsule/'checkpoint_guard.py')}
    def inputs(branch):
        out={}
        for key,name in [('pre','pre'),('post',branch)]:
            e=p['endpoints'][name];out[key]={'path':str(Path(packets[e['packet']]['root'])/e['member']),'sha256':e['sha256'],'bytes':e['bytes'],'payload_key':e['payload_key']}
        return out
    audit_name=p['external_audit_name'];audit=catroot/'audit'/audit_name;assert not audit.exists()
    audit_record={'state':'remote_only_three_diagnostic_endpoint_pairs_stored_and_guarded_performance_failed','related_cards':p['related_cards'],'case_ids':p['case_ids'],'host_label':'dislab','prior_catalog_sha256':p['expected_catalog_sha256'],'prior_case_count':25,'source_freeze_sha256':sha(ROOT/'REGISTRATION_SOURCE_FREEZE.json'),'source_publication_commit':pub['commit'],'guard':guard_meta,'first_guard_result':before_guard,'existing_baseline_evaluation_sha256':b['baseline_eval']['sha256'],'existing_separate_positive_recovery_sha256':b['positive_recovery']['sha256'],'original_positive_verifier_failed_and_absent_receipt_preserved':True,'all_prior_audit_file_hashes':prior_audits,'models_or_tensors_loaded':0,'CPU_or_evaluation_forward_calls':0,'model_files_copied':0,'local_delivery_complete':False,'verified_stealth_latent_pair':False,'detection_success_implied':False,'overall_goal_complete':False}
    with audit.open('x',encoding='utf-8',newline='\n') as f:json.dump(audit_record,f,indent=2);f.write('\n')
    audit.chmod(0o444);cat=copy.deepcopy(old);cat.setdefault('supplemental_audits',[]).append({'path':'audit/'+audit_name,'sha256':sha(audit)})
    for branch,cid in p['case_ids'].items():
        folder='05_diagnostic/'+cid;view=catroot/folder;view.mkdir(parents=True,exist_ok=False)
        (view/'README.md').write_text('DISLAB-only diagnostic endpoint pair from fixed10 FedUBA SSS125/FedEraser20.\n\nStored strict CPU evidence and independent standard evaluation are complete, but latent activation performance gates failed. Only diagnostic use is approved. The guard references both unchanged sealed packets and checks all declared hashes. No full-history use, activation/purification approval or local delivery is implied. All older cases/defaults/failures remain.\n',encoding='utf-8',newline='\n')
        cat['cases'].append({'id':cid,'folder':folder,'title':'FedUBA fixed10 SSS125/FedEraser20 stored endpoint diagnostic: '+branch,'family':'feduba_declared_fixed10_diagnostic_endpoints','source_root':str(ROOT),'integrity':'existing_strict_CPU_receipts_and_independent_standard_evaluation_with_both_external_packet_seals','reproduction':'failed_minimum_latent_activation_performance_gates','seed':42,'post_type':'actual_FedEraser20_endpoint','allowed_purposes':['diagnostic'],'related_cards':p['related_cards'],'server_inputs':inputs(branch),'checkpoint_guard':guard_meta,'history_scope':{'endpoint_only_for_selection':True,'full_history_use_approved':False,'local_delivery_complete':False},'evaluator_only':{'verified_stealth_latent_pair':False,'performance_gate_passed':False,'original_positive_writer_failure_preserved':True},'evidence':['audit/'+audit_name]})
    assert cat['cases'][:-3]==old['cases'] and cat['supplemental_audits'][:-1]==old.get('supplemental_audits',[])
    for k in old:
        if k not in ['cases','supplemental_audits']:assert cat[k]==old[k],k
    text=original_bytes.decode('utf-8');match=re.search(r'\n( +)"',text);indent=len(match[1]) if match else 2
    rendered=json.dumps(cat,ensure_ascii=not any(ord(c)>127 for c in text),indent=indent,allow_nan=False)
    if text.endswith('\n'):rendered+='\n'
    if '\r\n' in text:rendered=rendered.replace('\n','\r\n')
    temp=catpath.with_name('catalog.feduba_fixed10_diagnostic_append.tmp');assert not temp.exists();temp.write_bytes(rendered.encode('utf-8'))
    assert sha(catpath)==p['expected_catalog_sha256'];os.replace(temp,catpath)
    selections={};denied=[];env=os.environ.copy();env.update(PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='-1')
    for branch,cid in p['case_ids'].items():
        cmd=[sys.executable,'-B',str(catroot/'select_case.py'),cid,'--location','dislab']
        selected=json.loads(subprocess.check_output(cmd+['--purpose','diagnostic'],env=env,text=True,encoding='utf-8'))
        assert selected['guard_state']=='all_snapshot_files_verified_on_this_host' and selected['server_inputs']==inputs(branch) and selected['post_type']=='actual_FedEraser20_endpoint'
        assert set(selected['server_inputs'])=={'pre','post'} and all(set(v)=={'path','sha256','bytes','payload_key'} for v in selected['server_inputs'].values())
        selections[branch]=selected
        for purpose in ['retrain_activation','global_history','client_history','purification_pilot','approximate_FU']:
            r=subprocess.run(cmd+['--purpose',purpose],env=env,capture_output=True);assert r.returncode!=0;denied.append({'case_id':cid,'purpose':purpose,'exit_code':r.returncode})
    assert len(denied)==15 and all(sha(catroot/n)==h for n,h in prior_audits.items())
    after=read(catpath);assert len(after['cases'])==28 and after['cases'][:-3]==old['cases']
    for k in old:
        if k not in ['cases','supplemental_audits']:assert after[k]==old[k]
    assert 'torch' not in sys.modules and 'numpy' not in sys.modules
    result={'state':'registered_three_DISLAB_only_diagnostic_endpoint_pairs','case_ids':p['case_ids'],'old_case_count':25,'new_case_count':28,'prior_catalog_sha256':p['expected_catalog_sha256'],'new_catalog_sha256':sha(catpath),'external_audit_sha256':sha(audit),'external_audit_path':str(audit),'guard':guard_meta,'guard_passes':4,'declared_packet_file_hash_checks':4*809,'selections':selections,'forbidden_purposes_denied':denied,'all_prior_cases_defaults_audit_bytes_preserved':True,'local_catalogues_modified':False,'local_model_delivery_complete':False,'new_model_or_tensor_loads':0,'CPU_forward_calls':0,'new_training_or_evaluation':False,'performance_gates_passed':False,'overall_goal_complete':False}
    exclusive('REGISTERED.json',result);exclusive('REGISTRATION_COMPLETION.json',{'state':'completed_remote_only_diagnostic_registration_and_guards','exit_code':0,'finished_unix':time.time(),'registered_sha256':sha(ROOT/'REGISTERED.json'),'catalogue_sha256':sha(catpath),'overall_goal_complete':False});print(json.dumps({'state':result['state'],'old':25,'new':28,'guard_passes':4,'forbidden_purposes_denied':15,'model_loads':0}))
if __name__=='__main__':
    try:main()
    except BaseException:
        exclusive('REGISTRATION_FAILURE.json',{'state':'failed_preserved_no_retry','pid':os.getpid(),'traceback':traceback.format_exc()});raise
