"""Separate explicit AppleDouble packaging recovery; immutable original inspector remains failed."""
import ast,hashlib,io,json,posixpath,sys,traceback,urllib.request,zipfile
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def write(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
def main():
    p=json.loads((ROOT/'REVIEW_PROFILE.json').read_text(encoding='utf-8'))
    freeze=json.loads((ROOT/'SOURCE_FREEZE_V2.json').read_text(encoding='utf-8'))
    for n,d in freeze['files'].items():assert sha((ROOT/n).read_bytes())==d,n
    assert p['review_enabled'] and not p['launch_enabled'] and not p['numerical_compute_allowed']
    pub=json.loads((ROOT/'SOURCE_PUBLICATION_V2.json').read_text(encoding='utf-8'))
    assert pub['source_freeze_sha256']==sha((ROOT/'SOURCE_FREEZE_V2.json').read_bytes())
    write('REVIEW_RECOVERY_ONCE.json',{'state':'started_model_free_archive_review','utc':datetime.now(timezone.utc).isoformat(),'source_publication_sha256':sha((ROOT/'SOURCE_PUBLICATION_V2.json').read_bytes())})
    recovery=json.loads((ROOT/'RECOVERY_PROFILE.json').read_text(encoding='utf-8'))
    assert sha((ROOT/'REVIEW_FAILURE.json').read_bytes())==recovery['original_failure_sha256']
    data=(ROOT/recovery['source_archive_reused']).read_bytes()
    assert len(data)==p['archive_expected_bytes'] and blob(data)==p['archive_git_blob_sha1']
    members=[];defs=[];imports=[];bybase={};source_count=0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=z.infolist();assert len(infos)<=p['max_members']
        assert sum(x.file_size for x in infos)<=p['max_uncompressed_bytes']
        for info in infos:
            name=info.filename.replace('\\','/');path=PurePosixPath(name)
            assert not path.is_absolute() and '..' not in path.parts and ':' not in name,name
            meta={'path':info.filename,'bytes':info.file_size,'compressed_bytes':info.compress_size,'directory':info.is_dir()}
            if not info.is_dir() and path.suffix.lower() in ['.py','.md','.txt']:
                b=z.read(info);meta.update(sha256=sha(b),git_blob_sha1=blob(b),CRC_checked_by_zip_read=True)
                if path.parts[0]=='__MACOSX' and path.name.startswith('._'):
                    assert b[:4]==bytes.fromhex('00051607'),name
                    meta['kind']='AppleDouble_resource_metadata_not_Python_source';meta['magic_hex']=b[:4].hex()
                    members.append(meta);continue
                bybase.setdefault(path.name,[]).append({'path':info.filename,'git_blob_sha1':blob(b)})
                if path.suffix.lower()=='.py':
                    tree=ast.parse(b,filename=info.filename);source_count+=1
                    for node in ast.walk(tree):
                        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                            defs.append({'path':info.filename,'name':node.name,'kind':type(node).__name__,'line':node.lineno})
                        if isinstance(node,ast.Import):imports.extend({'path':info.filename,'module':a.name,'line':node.lineno} for a in node.names)
                        if isinstance(node,ast.ImportFrom):imports.append({'path':info.filename,'module':node.module,'names':[a.name for a in node.names],'line':node.lineno})
            members.append(meta)
    root_comparison={n:{'expected_blob':d,'archive_candidates':bybase.get(n,[]),'has_exact_match':any(v['git_blob_sha1']==d for v in bybase.get(n,[]))} for n,d in p['expected_root_blobs'].items()}
    found={n:[d for d in defs if d['name']==n] for n in p['required_missing_symbols']}
    result={'state':'completed_model_free_alternative_publisher_archive_packaging_recovery','utc':datetime.now(timezone.utc).isoformat(),'repository':p['repository'],'commit':p['commit'],'url':p['url'],'archive':{'bytes':len(data),'sha256':sha(data),'git_blob_sha1':blob(data)},'source_freeze_sha256':sha((ROOT/'SOURCE_FREEZE_V2.json').read_bytes()),'members':members,'parsed_Python_files':source_count,'definitions':defs,'imports':imports,'root_comparison':root_comparison,'missing_helper_definitions':found,'all_required_helper_definitions_present':all(found.values()),'model_loads':0,'tensor_payload_reads':0,'torch_imports':0,'forward_calls':0,'optimizer_steps':0,'archive_code_executed':False,'old_finite_jobs_replayed':False,'existing_source_or_profile_changed':False,'paper_performance_or_detection_success_implied':False}
    write('REVIEW_RECOVERY_RESULT.json',result)
    print(json.dumps({'state':result['state'],'members':len(members),'python_files':source_count,'helpers_found':{k:len(v) for k,v in found.items()},'root_exact_matches':sum(v['has_exact_match'] for v in root_comparison.values()),'archive_sha256':sha(data),'model_loads':0}))
if __name__=='__main__':
    try:main()
    except BaseException:
        write('REVIEW_RECOVERY_FAILURE.json',{'state':'failed_preserved_no_retry','traceback':traceback.format_exc()});raise
