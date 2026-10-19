$ErrorActionPreference = 'Stop'
$taskReader = @'
import json,pathlib,subprocess
root=pathlib.Path('C:/Users/DISLAB/Documents/antigravity/dazzling-lovelace/research_20261019/gradient_scale_v1')
source=root.parent/'patch_scale_v1'
reply={}
for key in ('launch','self_check','status','summary','complete','results'):
    path=root/(key+'.json')
    if path.exists():reply[key]=json.loads(path.read_text(encoding='utf-8'))
for name in ('worker.stdout.log','worker.stderr.log'):
    path=root/name
    if path.exists():reply[name]=path.read_text(encoding='utf-8',errors='replace')[-6000:]
for key in ('status','summary'):
    path=source/(key+'.json')
    if path.exists():reply['patch_'+key]=json.loads(path.read_text(encoding='utf-8'))
path=root/'REPORT_KO.txt'
if path.exists():reply['report_ko']=path.read_text(encoding='utf-8')
pid=reply.get('launch',{}).get('pid')
if pid:reply['process']=subprocess.run(['tasklist','/FI','PID eq '+str(pid),'/FO','CSV','/NH'],capture_output=True,text=True).stdout.strip()
reply['gpu']=subprocess.run(['nvidia-smi','--query-gpu=name,memory.used,utilization.gpu','--format=csv,noheader'],capture_output=True,text=True).stdout.strip()
print(json.dumps(reply,ensure_ascii=True))
'@
$taskLines=$taskReader | & ssh.exe -T -o BatchMode=yes -o ConnectTimeout=10 -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes -i "$env:USERPROFILE\.ssh\id_ed25519_dislab" DISLAB@100.75.90.126 'python -'
if($LASTEXITCODE -ne 0){throw 'Gradient experiment status read failed'}
$taskText=$taskLines -join [Environment]::NewLine
$taskResult=$taskText | ConvertFrom-Json
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'remote_status.json'),$taskText,(New-Object Text.UTF8Encoding($false)))
foreach($taskName in @('summary','results','self_check')){
    if($taskResult.$taskName){[IO.File]::WriteAllText((Join-Path $PSScriptRoot ($taskName+'_remote.json')),($taskResult.$taskName | ConvertTo-Json -Depth 50),(New-Object Text.UTF8Encoding($false)))}
}
if($taskResult.report_ko){[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'REPORT_REMOTE_KO.txt'),[string]$taskResult.report_ko,(New-Object Text.UTF8Encoding($false)))}
$taskResult.status | ConvertTo-Json -Depth 10
$taskResult.process
$taskResult.gpu
if($taskResult.summary){
    $taskResult.summary | Select-Object scored_requests,evaluated_requests,failed_requests,prospective_scores | ConvertTo-Json
    foreach($taskLevel in @('0.2','0.7','0.9')){
        $taskLevel
        $taskResult.summary.by_non_iid.$taskLevel | Select-Object fc_norm,fc_residual,conv_norm,conv_residual,patch | ConvertTo-Json -Depth 10
    }
}
$taskResult.'worker.stderr.log'
