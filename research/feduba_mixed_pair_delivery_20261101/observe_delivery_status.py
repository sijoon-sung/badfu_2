import sys,json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,'research/00_trajectories');import dislab_audit as t
raw=t.remote(r"""
$r='D:/FEDUBA_MIXED_PAIR_DELIVERY_20261101'
$name='Codex-FedUBA-mixed105-pairedFU20-review-export-CPU-20261101'
$task=Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue;$i=$null;if($task){$i=$task|Get-ScheduledTaskInfo}
$alive=@(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" | Where-Object {([string]$_.CommandLine).Contains('FEDUBA_MIXED_PAIR_DELIVERY_20261101')} | Select-Object ProcessId,ParentProcessId,CommandLine)
$files=[ordered]@{}
foreach($n in @('PAIR_REVIEW_EXPORT_ONCE.json','PAIR_REVIEW_EXPORT_FAILURE.json','PAIR_REVIEW_DELIVERY_REMOTE.json')){
 if(Test-Path -LiteralPath "$r/$n"){
  try{$v=Get-Content -LiteralPath "$r/$n" -Raw -Encoding UTF8 | ConvertFrom-Json
   $files[$n]=[ordered]@{state=[string]$v.state;pid=$v.pid;packet_total_files=$v.packet_total_files;tensor_payload_count=$v.tensor_payload_count;archive_bytes=$v.archive_bytes;traceback=[string]$v.traceback}
  }catch{$files[$n]=@{metadata_read_error=[string]$_.Exception.Message}}
 }
}
$last=$null;if(Test-Path -LiteralPath "$r/PAIR_REVIEW_EXPORT_EVENTS.jsonl"){
 [string]$line=Get-Content -LiteralPath "$r/PAIR_REVIEW_EXPORT_EVENTS.jsonl" -Tail 1 -Encoding UTF8
 try{$v=ConvertFrom-Json -InputObject $line;$last=[ordered]@{event_type=[string]$v.event_type;file=[string]$v.file;bytes=$v.bytes;kind=[string]$v.kind}}catch{$last=@{metadata_read_error=[string]$_.Exception.Message}}
}
[ordered]@{utc=[DateTime]::UtcNow.ToString('o');task_state=[string]$task.State;last_result=$i.LastTaskResult;processes=$alive;files=$files;last_event=$last;model_queries=0;finite_reexecution=$false} | ConvertTo-Json -Depth 5 -Compress
""")
assert len(raw)<25000,'Response exceeded fixed bound'
print(json.dumps(json.loads(raw),ensure_ascii=False,indent=2))
