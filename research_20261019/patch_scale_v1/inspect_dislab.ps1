$ErrorActionPreference = 'Stop'
$taskReader = @'
import json,pathlib,subprocess
root=pathlib.Path('C:/Users/DISLAB/Documents/antigravity/dazzling-lovelace/research_20261019/patch_scale_v1')
reply={}
for key in ('launch','self_check','status','summary','complete'):
    path=root/(key+'.json')
    if path.exists(): reply[key]=json.loads(path.read_text(encoding='utf-8'))
for name in ('worker.stdout.log','worker.stderr.log'):
    path=root/name
    if path.exists(): reply[name]=path.read_text(encoding='utf-8',errors='replace')[-5000:]
path=root/'REPORT_KO.txt'
if path.exists(): reply['report_ko']=path.read_text(encoding='utf-8')
cells=root/'cells'
reply['artifact_counts']={
    'locked_predictions':len(list(cells.glob('*/requests/*/prediction.json'))),
    'completed_cells':len(list(cells.glob('*/complete.json'))),
    'completed_federated_models':len(list(cells.glob('*/models/*/complete.json'))),
    'error_records':len(list(cells.glob('*/error.json')))}
current=reply.get('status',{}).get('cell')
if current:
    reply['current_cell_predictions']=[]
    for path in sorted((cells/current/'requests').glob('*/prediction.json')):
        value=json.loads(path.read_text(encoding='utf-8'))
        reply['current_cell_predictions'].append({key:value[key] for key in ('request','score','flag','locked_utc','future_checkpoint_existed_at_prediction')})
reply['gpu']=subprocess.run(['nvidia-smi','--query-gpu=name,memory.used,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True).stdout.strip()
pid=reply.get('launch',{}).get('pid')
if pid: reply['process']=subprocess.run(['tasklist','/FI','PID eq '+str(pid),'/FO','CSV','/NH'],capture_output=True,text=True).stdout.strip()
print(json.dumps(reply,ensure_ascii=True,indent=2))
'@
$taskLines = $taskReader | & ssh.exe -T -o BatchMode=yes -o ConnectTimeout=10 -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -i "$env:USERPROFILE\.ssh\id_ed25519_dislab" DISLAB@100.75.90.126 'python -'
if ($LASTEXITCODE -ne 0) { throw 'DISLAB status read failed' }
$taskText = $taskLines -join [Environment]::NewLine
$taskResult = $taskText | ConvertFrom-Json
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'remote_status.json'),$taskText,(New-Object Text.UTF8Encoding($false)))
if ($taskResult.summary) { [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'remote_summary.json'),($taskResult.summary | ConvertTo-Json -Depth 30),(New-Object Text.UTF8Encoding($false))) }
if ($taskResult.self_check) { [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'self_check_remote.json'),($taskResult.self_check | ConvertTo-Json -Depth 30),(New-Object Text.UTF8Encoding($false))) }
if ($taskResult.report_ko) { [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'REMOTE_REPORT_KO.txt'),[string]$taskResult.report_ko,(New-Object Text.UTF8Encoding($false))) }
$taskResult.status | ConvertTo-Json -Depth 20
$taskResult.artifact_counts | ConvertTo-Json -Depth 10
$taskResult.current_cell_predictions | ConvertTo-Json -Depth 10
$taskResult.gpu
$taskResult.process
$taskResult.'worker.stdout.log'
$taskResult.'worker.stderr.log'
