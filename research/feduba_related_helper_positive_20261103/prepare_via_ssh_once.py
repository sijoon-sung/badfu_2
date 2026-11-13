"""One metadata prepare; check four original tasks, do not invoke their jobs."""
import json,sys,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'00_trajectories'))
import dislab_audit as t
REMOTE='D:/FEDUBA_RELATED_HELPER_POSITIVE_20261103'
PUBLIC=['PREPARE_ONCE.json','BASELINE_INPUT_BINDING.json','FU_LAUNCH_PROFILE.json','LAUNCH_PROFILE.json','PREPARATION_RESULT.json','RUN_FREEZE.json','FU_RUN_FREEZE.json']
def main():
    assert not (HERE/'LOCAL_PREPARE_ONCE.json').exists()
    terminal=json.loads(t.remote(r"""
$out=@()
foreach($v in @(@('Codex-FedUBA-public-fixed10-cleanFL20-20261103','d:/feduba_fixed10_foundation_20261103/'),@('Codex-FedUBA-public-fixed10-clean-review-export-CPU-20261103','d:/feduba_fixed10_clean_delivery_20261103/'),@('Codex-FedUBA-public-fixed10-newSSS5000-20261103','d:/feduba_fixed10_sss_20261103/'),@('Codex-FedUBA-public-fixed10-targetclass125-pairedFU20-20261103','d:/feduba_fixed10_pair_20261103/'))){
 $task=Get-ScheduledTask -TaskName $v[0];$i=$task|Get-ScheduledTaskInfo
 $root=$v[1];$count=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"|Where-Object{([string]$_.CommandLine).Replace([char]92,[char]47).ToLowerInvariant().Contains($root)}).Count
 if(([string]$task.State) -ne 'Ready' -or $i.LastTaskResult -ne 0 -or $count -ne 0){throw 'Upstream task not actually terminated cleanly'}
 $out+=[pscustomobject]@{task_name=$v[0];state=[string]$task.State;last_result=$i.LastTaskResult;native_process_count=$count;execute=$task.Actions.Execute;arguments=$task.Actions.Arguments;level=[string]$task.Principal.RunLevel}
}
[pscustomobject]@{observed_utc=[DateTime]::UtcNow.ToString('o');tasks=$out}|ConvertTo-Json -Depth 5 -Compress
"""))
    for n,v in [('LOCAL_PREPARE_ONCE.json',{'state':'first_positive_sign_metadata_prepare'}),('UPSTREAM_TERMINAL_CHECK.json',terminal)]:
        with (HERE/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
    t.run(['scp.exe','-q',*t.FLAGS,str(HERE/'SOURCE_PUBLICATION.json'),str(HERE/'UPSTREAM_TERMINAL_CHECK.json'),t.REMOTE+':'+REMOTE+'/'])
    print(t.remote("& 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -B '"+REMOTE+"/prepare_run.py';if($LASTEXITCODE -ne 0){throw 'Positive sign metadata preparation failed'}"))
    for n in PUBLIC:
        assert not (HERE/n).exists();t.run(['scp.exe','-q',*t.FLAGS,t.REMOTE+':'+REMOTE+'/'+n,str(HERE/n)])
if __name__=='__main__':
    try:main()
    except BaseException:
        with (HERE/'LOCAL_PREPARE_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f)
        raise
