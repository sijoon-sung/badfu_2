"""Once CPU-only copy/strict storage validation of the newly completed mixed pair."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',PYTHONIOENCODING='utf-8')
import json
import shutil
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path
from pair_review_common import ROOT,REMOTE_PACKET,CASES,read,write,digest,safe,freeze,cpu_check,verify,input_receipts,terminal_process_guard,wait_memory,input_tensor

def main():
    p=freeze();input_receipts();terminal=terminal_process_guard();memory=wait_memory()
    roots={k:Path(v) for k,v in p['roots'].items()}
    E,B,A,F,T=roots['eval'],roots['pair'],roots['attack'],roots['foundation'],roots['trigger']
    result=read(E/'PAIR_EVAL_RESULT.json');audited=read(E/'PAIR_EVAL_VERIFIED.json')
    assert audited['state']=='passed' and audited['primary_result_sha256']==digest(E/'PAIR_EVAL_RESULT.json')
    assert result['models']==audited['models'] and audited['independent_counts_exactly_equal']
    assert audited['all_sample_predictions_exactly_equal'] and audited['independent_sample_forwards']==60000
    assert read(E/'COMPLETION.json')['state']=='completed_new_mixed_pair_evaluation_independently_verified_delivery_pending'
    assert not result['minimum_operational_gate']['passed']
    selected=json.loads(subprocess.check_output([sys.executable,'-B','D:/TRAJECTORY_CATALOG_20261023/select_case.py',
        result['case_id'],'--purpose','diagnostic'],text=True,encoding='utf-8'))
    assert selected['guard_state']=='all_snapshot_files_verified_on_this_host'
    assert selected['server_inputs']['pre']['sha256']==result['source_models']['pre']['sha256']
    verified={b:read((A if b=='attack' else B)/f'FU_{b}_VERIFIED.json') for b in CASES}
    histories={b:read((A if b=='attack' else B)/f'fu/{b}/MANIFEST.json') for b in CASES}
    for b in CASES:
        a=verified[b];root=A if b=='attack' else B;rr=read(root/f'FU_{b}_RESULT.json')
        assert a['state']=='passed' and (a['rounds'],a['new_trained_roles'],a['actual_local_epochs'])==(20,200,1000)
        assert a['actual_batches']==(20000 if b=='attack' else 19955) and len(a['history_hashes'])==420
        assert rr['history_manifest_sha256']==digest(root/f'fu/{b}/MANIFEST.json')
    assert (verified['attack']['reused_original_roles'],verified['attack']['executed_here_roles'])==(46,154)
    assert not REMOTE_PACKET.exists() and not (ROOT/'PAIR_REVIEW_DELIVERY.zip').exists()
    assert not (ROOT/'PAIR_REVIEW_EXPORT_ONCE.json').exists()
    write(ROOT/'PAIR_REVIEW_EXPORT_ONCE.json',{'pid':os.getpid(),'case_ids':CASES,'terminal':terminal,'memory':memory})
    REMOTE_PACKET.mkdir(parents=True,exist_ok=False)
    def event(event_type,**details):
        with (ROOT/'PAIR_REVIEW_EXPORT_EVENTS.jsonl').open('a',encoding='utf-8',newline='\n') as stream:
            stream.write(json.dumps({'event_type':event_type,**details},allow_nan=False)+'\n');stream.flush()
    payloads=[];sources={}
    def copy(source,name,expected=None,**description):
        source=Path(source).resolve()
        assert source.is_file() and not source.is_symlink()
        meta={'sha256':digest(source),'bytes':source.stat().st_size}
        if expected:
            assert meta['sha256']==expected['sha256'],str(source)
            if 'bytes' in expected:assert meta['bytes']==expected['bytes'],str(source)
        target=safe(REMOTE_PACKET,name);target.parent.mkdir(parents=True,exist_ok=True)
        assert not target.exists();shutil.copyfile(source,target)
        assert digest(target)==meta['sha256']
        sources[name]={'original':str(source),**meta}
        if description:payloads.append({'file':name,**meta,**description})
        event('copied',file=name,bytes=meta['bytes'])
    clean=read(F/'clean_fl/MANIFEST.json')
    copy(input_tensor(clean['fresh_initial'],F),'run/initial.pt',clean['fresh_initial'],kind='model',classes=10,payload_key=None)
    for key,meta in result['source_models'].items():
        copy(input_tensor(meta,B),'run/'+('before' if key=='pre' else key+'_after')+'.pt',meta,kind='model',classes=10,payload_key=meta['payload_key'])
    copy(input_tensor(result['delta'],B),'run/delta.pt',result['delta'],kind='delta',payload_key=None)
    trigger=read(T/'TRIGGER_RESULT.json');teacher=trigger['teacher']
    assert teacher['sha256']=='240a2af249a42cd18af4d11513392c94c4c64a279f332e3c27eb17eaf02c8a2f'
    copy(input_tensor(teacher,T),'run/fixed_surrogate201.pt',teacher,kind='model',classes=201,payload_key=None)
    selected_roles={}
    for owner in [5,7]:
        original=next(v for v in reversed(clean['rounds']) if owner in v['clients']);rn=original['round']
        old=next(v for v in original['roles'] if v['client']==owner)
        copy(input_tensor(old['checkpoint'],F),f'roles/old_owner{owner}.pt',old['checkpoint'],kind='model',classes=10,payload_key='model',role_kind='baseline')
        selected_roles[str(owner)]={'round':rn,'client':owner,'original':old['checkpoint']}
        for branch in CASES:
            history=histories[branch]
            assert len(history['rounds'])==20 and [v['clients'] for v in history['rounds']]==[v['clients'] for v in clean['rounds']]
            row=history['rounds'][rn-1]
            trained=next(v for v in row['trained_roles'] if v['client']==owner)
            calibrated=next(v for v in row['calibrated_roles'] if v['client']==owner)
            for role in [trained,calibrated]:assert role['checkpoint']['sha256'] in verified[branch]['history_hashes'].values()
            copy(input_tensor(trained['checkpoint'],B),f'roles/{branch}_owner{owner}_trained.pt',trained['checkpoint'],
                kind='model',classes=10,payload_key='model',role_kind='fu',round=rn,client=owner,source_N=trained['source_N'],batches=trained['batches'])
            copy(input_tensor(calibrated['checkpoint'],B),f'roles/{branch}_owner{owner}_calibrated.pt',calibrated['checkpoint'],kind='model',classes=10,payload_key=None)
    packets=[v['packet'] for v in read(B/'SSS_RESULT.json')['query_packets']]
    assert len(packets)==40 and len(result['input_packets'])==79
    for i,meta in enumerate(packets,1):
        copy(input_tensor(meta,B),f'private_tensor_evidence/SSS/query{i:02d}.pt',meta,kind='tensor_evidence',payload_key=None)
    for group,metas in [('inputs',result['input_packets']),*result['logit_packets'].items()]:
        assert len(metas)==79
        for i,meta in enumerate(metas,1):
            copy(input_tensor(meta,E),f'private_tensor_evidence/evaluation/{group}/batch{i:02d}.pt',meta,kind='tensor_evidence',payload_key=None)
    trigger_hashes=read(T/'TRIGGER_VERIFIED.json')['history_hashes'];assert len(trigger_hashes)==300
    for path,sha in sorted(trigger_hashes.items()):
        source=input_tensor({'path':path},T);rel=source.relative_to(T).as_posix()
        copy(source,'private_tensor_evidence/trigger/'+rel,{'sha256':sha},kind='tensor_evidence',payload_key=None)
    folders={'foundation':['clean_fl','stg','stg_cpu_trigger_recovery'],'teacher':['private_run'],'trigger':['private_run'],
        'pair':['sss','fu/benign','fu/attack'],'attack':['fu/attack','private_inputs'],'eval':['pair_evaluation']}
    suffixes={'.json','.jsonl','.txt','.md','.py','.ps1','.log'}
    for label,root in roots.items():
        paths={v for v in root.iterdir() if v.is_file() and v.suffix in suffixes}
        for folder in folders.get(label,[]):
            paths.update(v for v in (root/folder).rglob('*') if v.is_file() and v.suffix in suffixes)
        for path in sorted(paths):
            assert path.name!='METADATA_PROBE_RAW.json'
            assert path.stat().st_size<=p['metadata_file_max_bytes'],str(path)
            copy(path,'evidence/studies/'+label+'/'+path.relative_to(root).as_posix())
    for branch in CASES:
        root=A if branch=='attack' else B
        copy(root/f'fu/{branch}/MANIFEST.json',f'evidence/fu/{branch}/MANIFEST.json')
    copy(E/'PAIR_EVAL_VERIFIED.json','evidence/root/PAIR_EVAL_VERIFIED.json')
    for path in sorted(ROOT.iterdir()):
        if path.is_file() and path.suffix in ['.json','.txt','.py','.ps1'] and not path.name.startswith('PAIR_REVIEW_'):
            copy(path,'evidence/delivery_source/'+path.name)
    copy(ROOT/'model_reference.py','model_reference.py')
    copy(ROOT/'pair_review_common.py','load_checkpoint.py')
    write(REMOTE_PACKET/'DELIVERY_SCOPE.json',{'case_ids':CASES,'representative_roles':selected_roles,
        'all_original_raw_retained_at':p['roots'],'all400_trained_tensors_in_packet':False,'all400_calibrated_tensors_in_packet':False,
        'local_full_history_use_approved':False,'all_FU_epoch_event_logs_included':True,'all_SSS_queries_and_evaluation_packets_included':True,
        'all_CPU_trigger100_epoch_and200step_records_included':True,'source_map':sources,
        'minimum_latent_pair_performance_passed':False,'original_GPU_STG_audit_failure_preserved':True,'diagnostic_only':True,
        'old46_reused_new154_roles':True,'lost5epoch100batch_not_effective_history':True,'other_projects_raw_CIM_commands_included':False})
    checks=cpu_check(REMOTE_PACKET,payloads,lambda check:event('CPU_checked',**check))
    write(REMOTE_PACKET/'CPU_VERIFIED.json',checks)
    files={v.relative_to(REMOTE_PACKET).as_posix():{'sha256':digest(v),'bytes':v.stat().st_size} for v in sorted(REMOTE_PACKET.rglob('*')) if v.is_file()}
    write(REMOTE_PACKET/'DELIVERY_MANIFEST.json',{'case_ids':CASES,'files':files,'payloads':payloads})
    msha=digest(REMOTE_PACKET/'DELIVERY_MANIFEST.json')
    write(REMOTE_PACKET/'DELIVERY_SEAL.json',{'case_ids':CASES,'manifest_sha256':msha,'hashed_files':len(files)})
    for path in REMOTE_PACKET.rglob('*'):
        if path.is_file():path.chmod(0o444)
    guard=verify(REMOTE_PACKET,msha)
    archive=ROOT/'PAIR_REVIEW_DELIVERY.zip'
    with archive.open('xb') as stream,zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as zipped:
        for path in sorted(REMOTE_PACKET.rglob('*')):
            if path.is_file():zipped.write(path,path.relative_to(REMOTE_PACKET).as_posix())
    write(ROOT/'PAIR_REVIEW_DELIVERY_REMOTE.json',{'state':'exported_verified_diagnostic_pair_review','case_ids':CASES,
        'packet_root':str(REMOTE_PACKET),'archive_path':str(archive),'archive_sha256':digest(archive),'archive_bytes':archive.stat().st_size,
        'manifest_sha256':msha,'seal_sha256':digest(REMOTE_PACKET/'DELIVERY_SEAL.json'),'hashed_files':len(files),
        'packet_total_files':len(files)+2,'tensor_payload_count':len(payloads),'guard':guard,'models':result['source_models'],'delta':result['delta'],
        'local_delivery_complete':False,'catalogue_registered':False,'minimum_latent_pair_performance_passed':False,'overall_goal_complete':False})

if __name__=='__main__':
    try:main()
    except BaseException:
        write(ROOT/'PAIR_REVIEW_EXPORT_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
