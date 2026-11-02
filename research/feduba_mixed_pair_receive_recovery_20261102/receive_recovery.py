"""One first local extraction/storage check using frozen original helpers."""
import os,sys,time,datetime,traceback,shutil,zipfile
from pathlib import Path
os.environ['CUDA_VISIBLE_DEVICES']='-1'
os.environ['OMP_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
sys.dont_write_bytecode=True
from receive_ops import ROOT,OLD,now,read,write,digest,state,event,frozen,old_module,own_processes,absence
def main():
    p=frozen()
    assert Path(sys.executable).resolve()==Path(p['python']).resolve(),'Unexpected Python executable'
    assert not (ROOT/'RECEIVE_FAILURE.json').exists()
    assert not (ROOT/'private_run/PAIR_REVIEW_LOCAL_COMPLETE.json').exists()
    write(ROOT/'RECEIVE_ONCE.json',{'state':'receive_only_attempt_claimed_before_resource_wait',
          'utc':now(),'pid':os.getpid(),'parent_pid':os.getppid(),
          'source_freeze_sha256':digest(ROOT/'SOURCE_FREEZE.json'),
          'publication_sha256':digest(ROOT/'RECEIVE_PUBLICATION.json'),
          'archive_sha256':p['archive_sha256'],'archive_retransferred':False})
    rows=own_processes()
    assert len(rows)==1 and rows[0]['ProcessId']==os.getpid(),'Old/duplicate receiver found'
    identity=rows[0]
    assert identity['ParentProcessId']==os.getppid() and identity['Name'].lower()=='python.exe'
    write(ROOT/'ACTUAL_PROCESS.json',{'utc':now(),'process':identity})
    absence(p)
    c=old_module();original_profile=c.freeze()
    assert p['memory_guard']==original_profile['memory_guard']
    assert p['case_ids']==c.CASES and Path(p['local_packet'])==c.LOCAL_PACKET
    guard=p['memory_guard']
    assert guard=={'available_min_bytes':8589934592,'commit_headroom_min_bytes':17179869184,
                   'wait_max_seconds':86400,'poll_seconds':15}
    from native_memory import memory_information
    start=time.monotonic()
    deadline_utc=(datetime.datetime.now(datetime.timezone.utc)+datetime.timedelta(seconds=guard['wait_max_seconds'])).isoformat()
    write(ROOT/'RESOURCE_WAIT_BEGIN.json',{'utc':now(),'deadline_utc':deadline_utc,'guard':guard})
    index=0
    while True:
        m=memory_information()
        ok=m['availableBytes']>=guard['available_min_bytes'] and m['commitLimit']-m['committedBytes']>=guard['commit_headroom_min_bytes']
        current={'state':'resource_guard_passed' if ok else 'waiting_fixed_memory_guard',
                 'memory':m,'elapsed_seconds':time.monotonic()-start,'deadline_utc':deadline_utc,
                 'guard':guard,'sample':index,'extraction_started':False,'CPU_payloads_checked':0}
        state(current);event('resource_guard',**current)
        if ok:break
        assert time.monotonic()-start<guard['wait_max_seconds'],'Fixed CPU storage memory wait exhausted; no automatic retry'
        time.sleep(guard['poll_seconds']);index+=1
    # Recheck identity, original receipts and source after the bounded wait, before mutation.
    frozen();absence(p)
    assert [v['ProcessId'] for v in own_processes()]==[os.getpid()]
    r=c.read(OLD/'PAIR_REVIEW_DELIVERY_REMOTE.json');archive=OLD/'PAIR_REVIEW_DELIVERY.zip'
    assert r['state']=='exported_verified_diagnostic_pair_review' and r['case_ids']==c.CASES
    for key in ['archive_sha256','archive_bytes','manifest_sha256','seal_sha256','packet_total_files','tensor_payload_count']:
        assert r[key]==p[key],key
    state({'state':'validating_existing_archive','extraction_started':False,'CPU_payloads_checked':0})
    assert c.digest(archive)==r['archive_sha256'] and archive.stat().st_size==r['archive_bytes']
    write(ROOT/'EXTRACTION_ONCE.json',{'utc':now(),'archive_sha256':r['archive_sha256'],'archive_bytes':r['archive_bytes']})
    c.LOCAL_PACKET.mkdir(parents=True,exist_ok=False)
    state({'state':'extracting_first_local_packet','extraction_started':True,'CPU_payloads_checked':0})
    with zipfile.ZipFile(archive) as zipped:
        items=zipped.infolist();names=[v.filename for v in items]
        assert len(names)==len(set(names))==r['packet_total_files']
        assert len({x.casefold() for x in names})==len(names)
        for item in items:
            target=c.safe(c.LOCAL_PACKET,item.filename)
            assert not item.is_dir() and (item.external_attr>>16)&0o170000!=0o120000
            target.parent.mkdir(parents=True,exist_ok=True)
            with zipped.open(item) as source,target.open('xb') as out:shutil.copyfileobj(source,out)
    assert c.digest(c.LOCAL_PACKET/'DELIVERY_MANIFEST.json')==r['manifest_sha256']
    assert c.digest(c.LOCAL_PACKET/'DELIVERY_SEAL.json')==r['seal_sha256']
    for path in c.LOCAL_PACKET.rglob('*'):
        if path.is_file():path.chmod(0o444)
    state({'state':'verifying_readonly_exact_tree','extraction_started':True,'CPU_payloads_checked':0})
    checked_guard=c.verify(c.LOCAL_PACKET,r['manifest_sha256'])
    manifest=c.read(c.LOCAL_PACKET/'DELIVERY_MANIFEST.json')
    progress=0
    def on_check(row):
        nonlocal progress
        progress+=1
        current={'state':'first_local_strict_CPU_storage_check','extraction_started':True,
                 'CPU_payloads_checked':progress,'payload_kind':row['kind']}
        state(current);event('CPU_storage_checked',**current)
    checks=c.cpu_check(c.LOCAL_PACKET,manifest['payloads'],on_check=on_check)
    assert checks['payload_count']==r['tensor_payload_count']==672
    complete={'state':'local_delivery_complete','utc':now(),'case_ids':c.CASES,
        'packet_root':str(c.LOCAL_PACKET),'archive_sha256':r['archive_sha256'],'archive_bytes':r['archive_bytes'],
        'manifest_sha256':r['manifest_sha256'],'seal_sha256':r['seal_sha256'],
        'packet_total_files':r['packet_total_files'],'tensor_payload_count':r['tensor_payload_count'],
        'guard':checked_guard,'CPU_checks':checks,'local_delivery_complete':True,'catalogue_registered':False,
        'original_export_receipt_modified':False,'overall_goal_complete':False,
        'recovery_source_freeze_sha256':digest(ROOT/'SOURCE_FREEZE.json'),
        'old_receiver_termination_cause':'unproved'}
    write(ROOT/'private_run/PAIR_REVIEW_LOCAL_COMPLETE.json',complete)
    write(ROOT/'LOCAL_STORAGE_COMPLETION_SUMMARY.json',{k:v for k,v in complete.items() if k!='CPU_checks'} |
          {'CPU_checks':{k:v for k,v in checks.items() if k!='checks'},
           'authoritative_local_ledger':'private_run/PAIR_REVIEW_LOCAL_COMPLETE.json',
           'local_ledger_sha256':digest(ROOT/'private_run/PAIR_REVIEW_LOCAL_COMPLETE.json')})
    frozen()
    state({'state':'local_delivery_complete','extraction_started':True,'CPU_payloads_checked':672})
    event('local_delivery_complete',CPU_payloads_checked=672)
    write(ROOT/'RECEIVE_TERMINAL.json',{'state':'completed','utc':now(),'pid':os.getpid(),'exit_code':0,
          'local_ledger_sha256':digest(ROOT/'private_run/PAIR_REVIEW_LOCAL_COMPLETE.json'),
          'original_receive_receipts_written':False,'overall_goal_complete':False})
if __name__=='__main__':
    try:main()
    except BaseException as exc:
        trace=ROOT/'private_run/FAILURE_TRACE.json'
        write(trace,{'utc':now(),'traceback':traceback.format_exc()})
        failed={'state':'failed_preserved_no_retry','utc':now(),'pid':os.getpid(),
                'exception_type':type(exc).__name__,'trace_sha256':digest(trace),'automatic_retry':False}
        write(ROOT/'RECEIVE_FAILURE.json',failed)
        state(failed)
        write(ROOT/'RECEIVE_TERMINAL.json',{**failed,'exit_code':1})
        raise
