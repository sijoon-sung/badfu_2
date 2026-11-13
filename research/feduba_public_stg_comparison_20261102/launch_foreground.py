"""One-time local transport only. All model computation stays on DISLAB."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
freeze = json.loads((ROOT / 'LAUNCH_RECOVERY_FREEZE.json').read_text(encoding='utf-8'))
for name, digest in freeze['files'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
pub = json.loads((ROOT / 'LAUNCH_RECOVERY_PUBLICATION.json').read_text(encoding='utf-8'))
assert pub['freeze_sha256'] == hashlib.sha256((ROOT / 'LAUNCH_RECOVERY_FREEZE.json').read_bytes()).hexdigest()
script = r"""$ErrorActionPreference='Stop'
$r='D:/FEDUBA_PUBLIC_STG_COMPARISON_20261102'
$live=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match 'python' -and $_.CommandLine -like '*FEDUBA_PUBLIC_STG_COMPARISON_20261102*'})
if($live.Count -ne 0){throw 'Root already has an actual Python process'}
foreach($n in @('CONTROLLER_ONCE.json','CONTROLLER_FAILURE.json','RUN_ONCE.json','RUN_FAILURE.json','RESULT.json','AUDIT_ONCE.json','VERIFIED.json')){
 if(Test-Path -LiteralPath ($r+'/'+$n)){throw ('Existing numeric/controller ledger: '+$n)}
}
$o=[pscustomobject]@{state='first_foreground_launch_after_detached_body0';utc=[DateTime]::UtcNow.ToString('o')}
$stream=[IO.File]::Open($r+'/FOREGROUND_LAUNCH_ONCE.json',[IO.FileMode]::CreateNew)
try{$bytes=[Text.Encoding]::UTF8.GetBytes(($o|ConvertTo-Json));$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
& 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe' -B -u ($r+'/comparison_controller.py')
exit $LASTEXITCODE
"""
encoded = base64.b64encode(script.encode('utf-16le')).decode('ascii')
flags = ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'IdentitiesOnly=yes',
         '-o', 'StrictHostKeyChecking=yes', '-o', 'ServerAliveInterval=15', '-o', 'ServerAliveCountMax=4',
         '-i', str(Path(os.environ['USERPROFILE']) / '.ssh/id_ed25519_dislab')]
raise SystemExit(subprocess.call(['ssh.exe', '-T', *flags, 'DISLAB@100.75.90.126',
                 'powershell -NoProfile -NonInteractive -EncodedCommand ' + encoded]))
