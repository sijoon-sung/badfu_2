"""Metadata-only preparation, callable only after actual foundation taskReady/exit0."""
import json
from pathlib import Path
import sys
import traceback
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'00_trajectories'))
import dislab_audit as t
def main():
    assert not (HERE/'LOCAL_PREPARE_ONCE.json').exists()
    value=json.loads(t.remote(r"""
$name='Codex-FedUBA-public-fixed10-cleanFL20-20261103'
$task=Get-ScheduledTask -TaskName $name
$i=$task|Get-ScheduledTaskInfo
$count=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"|Where-Object{([string]$_.CommandLine).Replace('\','/').ToLowerInvariant().Contains('d:/feduba_fixed10_foundation_20261103/')}).Count
if(([string]$task.State) -ne 'Ready' -or $i.LastTaskResult -ne 0 -or $count -ne 0){throw 'Foundation not actually terminated cleanly'}
[pscustomobject]@{task_name=$name;state=[string]$task.State;last_result=$i.LastTaskResult;native_process_count=$count;observed_utc=[DateTime]::UtcNow.ToString('o');execute=$task.Actions.Execute;arguments=$task.Actions.Arguments}|ConvertTo-Json -Compress
"""))
    with (HERE/'LOCAL_PREPARE_ONCE.json').open('x',encoding='utf-8') as f:json.dump({'state':'first_closed_foundation_metadata_prepare','terminal':value},f)
    with (HERE/'FOUNDATION_TERMINAL_CHECK.json').open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
    remote='D:/FEDUBA_FIXED10_CLEAN_DELIVERY_20261103'
    t.run(['scp.exe','-q',*t.FLAGS,str(HERE/'SOURCE_PUBLICATION.json'),str(HERE/'FOUNDATION_TERMINAL_CHECK.json'),t.REMOTE+':'+remote+'/'])
    print(t.remote("& 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -B '"+remote+"/prepare_actual.py';if($LASTEXITCODE -ne 0){throw 'Clean review preparation failed'}"))
    for n in ['PREPARE_ONCE.json','FOUNDATION_INPUT_BINDING.json','LAUNCH_PROFILE.json','RUN_FREEZE.json','CLEAN_EXPORT_FREEZE.json','CLEAN_REGISTRATION_FREEZE.json']:
        assert not (HERE/n).exists()
        t.run(['scp.exe','-q',*t.FLAGS,t.REMOTE+':'+remote+'/'+n,str(HERE/n)])
if __name__=='__main__':
    try:main()
    except BaseException:
        with (HERE/'LOCAL_PREPARE_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f)
        raise
