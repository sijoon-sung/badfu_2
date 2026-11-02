"""Metadata preparation only, after all three actual upstream tasks terminate cleanly."""
import json
from pathlib import Path
import sys
import traceback
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'00_trajectories'))
import dislab_audit as t
def main():
    assert not (HERE/'LOCAL_PREPARE_ONCE.json').exists()
    terminal=json.loads(t.remote(r"""
$out=@()
foreach($v in @(@('Codex-FedUBA-public-fixed10-cleanFL20-20261103','d:/feduba_fixed10_foundation_20261103/'),@('Codex-FedUBA-public-fixed10-clean-review-export-CPU-20261103','d:/feduba_fixed10_clean_delivery_20261103/'),@('Codex-FedUBA-public-fixed10-newSSS5000-20261103','d:/feduba_fixed10_sss_20261103/'))){
 $task=Get-ScheduledTask -TaskName $v[0];$i=$task|Get-ScheduledTaskInfo
 $root=$v[1];$count=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"|Where-Object{([string]$_.CommandLine).Replace('\','/').ToLowerInvariant().Contains($root)}).Count
 if(([string]$task.State) -ne 'Ready' -or $i.LastTaskResult -ne 0 -or $count -ne 0){throw 'Upstream task not actually terminated cleanly'}
 $out+=[pscustomobject]@{task_name=$v[0];state=[string]$task.State;last_result=$i.LastTaskResult;native_process_count=$count;execute=$task.Actions.Execute;arguments=$task.Actions.Arguments}
}
if(-not(Test-Path -LiteralPath 'D:/FEDUBA_FIXED10_SSS_20261103/COMPLETION.json')){throw 'New SSS not completed'}
[pscustomobject]@{observed_utc=[DateTime]::UtcNow.ToString('o');tasks=$out}|ConvertTo-Json -Depth 5 -Compress
"""))
    for n,v in [('LOCAL_PREPARE_ONCE.json',{'state':'first_closed_fixed10_upstream_metadata_prepare'}),('UPSTREAM_TERMINAL_CHECK.json',terminal)]:
        with (HERE/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
    remote='D:/FEDUBA_FIXED10_PAIR_20261103'
    t.run(['scp.exe','-q',*t.FLAGS,str(HERE/'SOURCE_PUBLICATION.json'),str(HERE/'UPSTREAM_TERMINAL_CHECK.json'),t.REMOTE+':'+remote+'/'])
    print(t.remote("& 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -B '"+remote+"/prepare_pair.py';if($LASTEXITCODE -ne 0){throw 'Fixed10 pair preparation failed'}"))
    for n in ['PREPARE_ONCE.json','FOUNDATION_INPUT_BINDING.json','FU_LAUNCH_PROFILE.json','PAIR_EVAL_LAUNCH_PROFILE.json','LAUNCH_PROFILE.json','PREPARATION_RESULT.json','RUN_FREEZE.json','FU_RUN_FREEZE.json','PAIR_EVAL_RUN_FREEZE.json','NORMAL_CASE_SELECTION.json','CLEAN_FL_RESULT.json','CLEAN_FL_VERIFIED.json','CLEAN_FL_READY.json','CLEAN_FL_PROFILE.json','SSS_RESULT.json','SSS_VERIFIED.json']:
        assert not (HERE/n).exists()
        t.run(['scp.exe','-q',*t.FLAGS,t.REMOTE+':'+remote+'/'+n,str(HERE/n)])
if __name__=='__main__':
    try:main()
    except BaseException:
        with (HERE/'LOCAL_PREPARE_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f)
        raise
