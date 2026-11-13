"""First metadata prepare only after the new attack training and CPU task terminate."""
import json,sys,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'00_trajectories'));import dislab_audit as t
REMOTE='D:/FEDUBA_RELATED_HELPER_POSITIVE_EVALUATION_20261103'
def main():
    assert not (HERE/'LOCAL_PREPARE_ONCE.json').exists()
    terminal=json.loads(t.remote(r"""
$n='Codex-FedUBA-related-helper-positive-FU20-20261103';$t=Get-ScheduledTask -TaskName $n;$i=$t|Get-ScheduledTaskInfo
$c=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"|Where-Object{([string]$_.CommandLine).Replace([char]92,[char]47).ToLowerInvariant().Contains('d:/feduba_related_helper_positive_20261103/')}).Count
if([string]$t.State -ne 'Ready' -or $i.LastTaskResult -ne 0 -or $c -ne 0){throw 'New FU20/CPU task not actually completed'}
@{utc=[DateTime]::UtcNow.ToString('o');task=@{name=$n;state=[string]$t.State;last_result=$i.LastTaskResult;native_process_count=$c;execute=$t.Actions.Execute;arguments=$t.Actions.Arguments;level=[string]$t.Principal.RunLevel}}|ConvertTo-Json -Depth 4 -Compress
"""))
    for n,v in [('LOCAL_PREPARE_ONCE.json',{'state':'first_new_attack_only_eval_metadata_prepare'}),('UPSTREAM_TERMINAL_CHECK.json',terminal)]:
        with (HERE/n).open('x',encoding='utf-8',newline='\n') as f:json.dump(v,f,indent=2);f.write('\n')
    t.run(['scp.exe','-q',*t.FLAGS,str(HERE/'SOURCE_PUBLICATION.json'),str(HERE/'UPSTREAM_TERMINAL_CHECK.json'),t.REMOTE+':'+REMOTE+'/'])
    print(t.remote("& 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -B '"+REMOTE+"/prepare_eval.py';if($LASTEXITCODE -ne 0){throw 'New attack only eval preparation failed'}"))
    for n in ['PREPARE_ONCE.json','INPUT_BINDING.json','EVAL_LAUNCH_PROFILE.json','PREPARATION_RESULT.json','EVAL_RUN_FREEZE.json']:
        assert not (HERE/n).exists();t.run(['scp.exe','-q',*t.FLAGS,t.REMOTE+':'+REMOTE+'/'+n,str(HERE/n)])
if __name__=='__main__':
    try:main()
    except BaseException:
        with (HERE/'LOCAL_PREPARE_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f)
        raise
