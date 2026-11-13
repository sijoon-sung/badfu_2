"""One metadata-only terminal prefix preservation, no torch or model loads."""
import base64, hashlib, json, os, subprocess, sys, time, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=Path('D:/FEDUBA_MIXED_PAIR_20261101')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256();buffer=bytearray(65536);view=memoryview(buffer)
    with Path(p).open('rb',buffering=0) as stream:
        while (n:=stream.readinto(buffer)):h.update(view[:n])
    return h.hexdigest()
def once(name,value):
    with (ROOT/name).open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
def main():
    assert ROOT==Path('D:/FEDUBA_MIXED_PAIR_MEMORY_RECOVERY_20261101')
    frozen=read(ROOT/'SOURCE_FREEZE.json')
    for n,h in frozen['files'].items():assert sha(ROOT/n)==h,n
    pub=read(ROOT/'PUBLICATION.json')
    assert pub['state']=='published_memory_failure_preservation_and_exact_own_observer_stop_before_execution'
    assert pub['source_freeze_sha256']==sha(ROOT/'SOURCE_FREEZE.json')
    assert read(ROOT/'OPS_RESULT.json')['state']=='completed_exact_own_historical_readonly_observer_stop'
    query="$rows=@(Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object {$_.CommandLine -like '*FEDUBA_MIXED_PAIR_20261101*'} | Select-Object -ExpandProperty ProcessId);ConvertTo-Json -InputObject $rows -Compress"
    encoded=base64.b64encode(query.encode('utf-16le')).decode()
    ids=json.loads(subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-EncodedCommand',encoded],text=True,encoding='utf-8'))
    assert not ids,ids
    assert read(OLD/'FU_attack_FAILURE.json')['state']=='failed_preserved'
    assert read(OLD/'PAIR_CONTROLLER_FAILURE.json')['state']=='failed_preserved'
    once('PREFIX_ONCE.json',{'pid':os.getpid(),'time_unix':time.time()})
    manifest=read(OLD/'fu/attack/MANIFEST.json')
    assert [r['round'] for r in manifest['rounds']]==[1,2,3,4]
    assert manifest['rounds'][-1]['actual_cumulative_batches']==4000
    files=list((OLD/'fu/attack').rglob('*'))
    files=[p for p in files if p.is_file()]
    names=['SOURCE_FREEZE.json','PAIR_RUN_FREEZE.json','FU_RUN_FREEZE.json','PAIR_PUBLICATION.json','FU_LAUNCH_PROFILE.json','PAIR_LAUNCH_PROFILE.json','PAIR_EVAL_LAUNCH_PROFILE.json','TRIGGER_SOURCE_BINDING.json','FU_attack_FAILURE.json','PAIR_CONTROLLER_FAILURE.json','FU_attack_STATE.json','PAIR_CONTROLLER_STATE.json','FU_attack_ONCE.json','PAIR_CONTROLLER_ONCE.json','SSS_ONCE.json','SSS_RESULT.json','SSS_VERIFIED.json','FU_benign_RESULT.json','FU_benign_VERIFIED.json','pair_console.log']
    source=read(OLD/'SOURCE_FREEZE.json')['files']
    files.extend(OLD/n for n in set(names)|set(source))
    files=sorted(set(files))
    hashes={}
    for i,p in enumerate(files,1):
        n=p.relative_to(OLD).as_posix();digest=sha(p)
        if n in source:assert digest==source[n],n
        hashes[n]={'sha256':digest,'bytes':p.stat().st_size}
        if i%10==0:
            (ROOT/'PREFIX_STATE.json').write_text(json.dumps({'state':'hashing_terminal_original_prefix','pid':os.getpid(),'checked':i,'total':len(files)}),encoding='utf-8')
    trained=[p for p in files if p.parent==OLD/'fu/attack/trained']
    assert len(trained)==46
    result={'state':'passed_terminal_original_attack_prefix_hash_preservation','original_root':str(OLD),'committed_rounds':4,'committed_batches':4000,'trained_files':46,'committed_trained_files':40,'uncommitted_round5_saved_trained_files':6,'round5_client10_bundle_exists':(OLD/'fu/attack/trained/round05_client10.pt').exists(),'all_original_prefix_files':hashes,'model_loads':0,'model_forwards':0,'torch_imported':'torch' in sys.modules,'original_files_modified':False,'numerical_job_relaunched':False}
    assert not result['round5_client10_bundle_exists'] and not result['torch_imported']
    once('PREFIX_PRESERVED.json',result)
    (ROOT/'PREFIX_STATE.json').write_text(json.dumps({'state':result['state'],'pid':os.getpid(),'checked':len(files),'total':len(files)}),encoding='utf-8')
    print(json.dumps({'state':result['state'],'files':len(files),'trained_files':46,'committed_rounds':4}),flush=True)
if __name__=='__main__':
    try:main()
    except BaseException:
        once('PREFIX_FAILURE.json',{'state':'failed_preserved','pid':os.getpid(),'traceback':traceback.format_exc()})
        raise
