"""One bounded stdlib-only review of a newly discovered pinned public ZIP."""
import ast,collections,hashlib,io,json,os,shutil,subprocess,sys,time,tokenize,traceback,urllib.request,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parent
TARGETS={'poison_image','poison_image_label','concoct_dataset','sur_target_dataset','apply_noise_patch','ResNet18','ResNet18_201'}
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def exclusive(n,v):
    with (ROOT/n).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(v,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
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
def definitions(tree,member):
    out=[]
    def visit(n,scope):
        for c in ast.iter_child_nodes(n):
            if isinstance(c,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                if c.name in TARGETS:
                    item={'member':member,'name':c.name,'kind':type(c).__name__,'line':c.lineno,'end_line':c.end_lineno,'scope':scope}
                    if isinstance(c,ast.ClassDef):
                        init=next((v for v in c.body if isinstance(v,(ast.FunctionDef,ast.AsyncFunctionDef)) and v.name=='__init__'),None)
                        item['constructor_arguments']=ast.unparse(init.args) if init else None
                        item['bases']=[ast.unparse(v) for v in c.bases]
                    else:item['arguments']=ast.unparse(c.args)
                    out.append(item)
                visit(c,scope+[c.name])
            else:visit(c,scope)
    visit(tree,[]);return out
def main():
    p=read(ROOT/'PROFILE.json');b=read(ROOT/'INPUT_BINDING.json');pub=read(ROOT/'RUN_PUBLICATION.json')
    assert ROOT==Path(p['execution_root']) and p['launch_enabled']
    assert list(sys.version_info[:3])==p['python_version']
    assert pub['state']=='published_actual_ity92_source_archive_review_before_execution' and len(pub['commit'])==40
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    freeze=read(ROOT/'SOURCE_FREEZE.json')
    for n,h in freeze['files'].items():assert sha(ROOT/n)==h,n
    exclusive('ONCE.json',{'pid':os.getpid(),'unix':time.time(),'profile_sha256':sha(ROOT/'PROFILE.json'),'publication_commit':pub['commit']})
    admission=guard(p);exclusive('ADMISSION.json',admission)
    req=urllib.request.Request(p['download_url'],headers={'User-Agent':'FedUBA-source-provenance-review'})
    with urllib.request.urlopen(req,timeout=60) as r:raw=r.read(p['expected_bytes']+1)
    with (ROOT/'archive.zip').open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
    archive_sha=hashlib.sha256(raw).hexdigest()
    git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()
    exclusive('DOWNLOAD_RECEIPT.json',{'url':p['download_url'],'bytes':len(raw),'sha256':archive_sha,'git_blob':git_blob,'urlopen_calls':1,'retry_count':0})
    assert len(raw)==p['expected_bytes']==b['archive_expected_bytes']
    assert git_blob==p['expected_git_blob']==b['archive_expected_blob']
    os.chmod(ROOT/'archive.zip',0o444)
    inventory=[];sources=[];found=[];matches={n:[] for n in b['paperlinked_nine_bodies']};skipped=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        infos=z.infolist();assert len(infos)<=p['max_members']
        assert len({i.filename for i in infos})==len(infos),'Duplicate archive member name'
        total=sum(i.file_size for i in infos);assert total<=p['max_total_uncompressed_bytes']
        for i in infos:
            name=i.filename;path=PurePosixPath(name)
            assert not path.is_absolute() and '..' not in path.parts and chr(92) not in name and ':' not in name,name
            assert not i.flag_bits&1,'Encrypted archive member'
            mode=(i.external_attr>>16)&0o170000;assert mode!=0o120000,'Symbolic link archive member'
            row={'member':name,'bytes':i.file_size,'compressed_bytes':i.compress_size,'extension':path.suffix.lower(),'CRC32_declared':format(i.CRC,'08x'),'is_directory':i.is_dir()}
            inventory.append(row)
            if i.is_dir():row['review']='directory_metadata_only';continue
            is_source=path.suffix.lower() in p['source_only_extensions'];is_readme=path.name.lower()=='readme.md'
            if not (is_source or is_readme):row['review']='non_source_contents_not_read';skipped.append(row);continue
            assert i.file_size<=p['max_source_member_bytes'],name
            body=z.read(i);assert len(body)==i.file_size
            applepath='__MACOSX' in path.parts or path.name.startswith('._')
            if applepath and body[:4]==bytes.fromhex('00051607'):
                row['review']='AppleDouble_path_and_magic_verified_source_AST_skipped';row['sha256']=hashlib.sha256(body).hexdigest();continue
            assert not applepath,'Resource-looking source missing AppleDouble magic'
            h=hashlib.sha256(body).hexdigest();row.update({'sha256':h,'source_CRC_read_passed':True})
            if path.name in matches:
                expected=b['paperlinked_nine_bodies'][path.name]
                matches[path.name].append({'member':name,'sha256':h,'bytes':len(body),'exact_raw_body_match':h==expected['sha256'] and len(body)==expected['bytes']})
            if is_readme:row['review']='README_raw_body_only';continue
            encoding,_=tokenize.detect_encoding(io.BytesIO(body).readline)
            text=body.decode(encoding);tree=ast.parse(text,filename=name)
            d=definitions(tree,name);found.extend(d)
            source={'member':name,'sha256':h,'bytes':len(body),'encoding':encoding,'AST_passed':True,'target_definition_count':len(d),'top_level_imports':[ast.unparse(v) for v in tree.body if isinstance(v,(ast.Import,ast.ImportFrom))]}
            sources.append(source);row['review']='Python_source_CRC_and_AST_only'
    exclusive('SOURCE_INVENTORY.json',{'archive_sha256':archive_sha,'members':inventory,'Python_sources':sources,'target_definitions':found,'paperlinked_nine_body_comparison':matches,'all_nine_uniquely_exact':all(len(v)==1 and v[0]['exact_raw_body_match'] for v in matches.values()),'skipped_non_source_payload_contents':len(skipped),'skipped_payload_CRC_verified':False})
    assert 'torch' not in sys.modules and 'numpy' not in sys.modules
    for n,h in freeze['files'].items():assert sha(ROOT/n)==h,n
    counts=dict(collections.Counter(d['name'] for d in found))
    result={'state':'completed_new_ity92_historical_archive_source_review','repository':'ity92/FedUBA','pinned_parent_commit':'0b0601dd88f465b799fc580624a386bba6759647','archive_bytes':len(raw),'archive_sha256':archive_sha,'archive_git_blob':git_blob,'archive_members':len(inventory),'total_declared_uncompressed_bytes':total,'Python_sources_AST_and_CRC_checked':len(sources),'target_definition_counts':counts,'target_definitions':found,'paperlinked_nine_body_comparison':matches,'all_nine_uniquely_exact':all(len(v)==1 and v[0]['exact_raw_body_match'] for v in matches.values()),'inventory_sha256':sha(ROOT/'SOURCE_INVENTORY.json'),'owner_identity_certified':False,'missing_paperlinked_helper_semantics_certified':False,'new_code_adopted':False,'new_training_launched':False,'upstream_code_executions':0,'torch_imports':0,'RNG_executions':0,'model_tensor_data_loads':0,'forward_calls':0,'optimizer_steps':0,'download_calls':1,'overall_goal_complete':False}
    exclusive('RESULT.json',result)
    exclusive('COMPLETION.json',{'state':'completed_bounded_source_only_review','exit_code':0,'finished_unix':time.time(),'result_sha256':sha(ROOT/'RESULT.json'),'source_freeze_sha256':sha(ROOT/'SOURCE_FREEZE.json'),'publication_commit':pub['commit'],'old_finite_jobs_rerun':0,'overall_goal_complete':False})
    print(json.dumps({'state':result['state'],'archive_sha256':archive_sha,'Python_sources':len(sources),'definitions':counts,'all_nine_exact':result['all_nine_uniquely_exact']}))
if __name__=='__main__':
    try:main()
    except BaseException:
        exclusive('FAILURE.json',{'state':'failed_preserved_no_retry','pid':os.getpid(),'traceback':traceback.format_exc()});raise
