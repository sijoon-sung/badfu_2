"""Local transport only; no local model computation."""
import base64
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'C:/Users/sijoo/Documents/ChatGPT/badFU/research/00_trajectories')
from dislab_audit import remote,run,FLAGS,REMOTE
DEST='D:/FEDUBA_LARGE_BENIGN_VALIDATION_20261110'
PYTHON='C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe'


def python(code):
    b=base64.b64encode(code.encode('utf-8')).decode()
    return remote("$env:PYTHONIOENCODING='utf-8'\n& '"+PYTHON+"' -c \"import base64;exec(base64.b64decode('"+b+"'))\"\nexit $LASTEXITCODE")


def upload(names):
    for name in names:run(['scp.exe','-q',*FLAGS,str(ROOT/name),REMOTE+':'+DEST+'/'+name])


def task(name,script,limit=4):
    command="$name='"+name+"'\nif(Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue){throw 'Existing one-shot task'}\n"
    command+="$a=New-ScheduledTaskAction -Execute '"+PYTHON+"' -Argument '-u "+DEST+'/'+script+"' -WorkingDirectory '"+DEST+"'\n"
    command+="$p=New-ScheduledTaskPrincipal -UserId 'DISLAB' -LogonType Interactive -RunLevel Highest\n"
    command+="$s=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours "+str(limit)+") -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries\n"
    command+="Register-ScheduledTask -TaskName $name -Action $a -Principal $p -Settings $s -Description 'New bounded legitimate deletion validation; no triggers/retries'|Out-Null\nStart-ScheduledTask -TaskName $name\nGet-ScheduledTask -TaskName $name|Select-Object TaskName,State|ConvertTo-Json -Compress"
    return remote(command)


def main(action):
    if action=='upload':
        print(remote("if(Test-Path '"+DEST+"'){throw 'Experiment destination exists'}\nNew-Item -ItemType Directory '"+DEST+"'|Out-Null"))
        upload(list(json.loads((ROOT/'SOURCE_FREEZE.json').read_text(encoding='utf-8'))['files'])+['SOURCE_FREEZE.json','SOURCE_PUBLICATION.json'])
        print('New source uploaded once')
    elif action=='prepare':print(task('Codex-FedUBA-large-normal-prepare-20261110','prepare.py'))
    elif action=='start':print(task('Codex-FedUBA-large-normal-FU20-20261110','controller.py'))
    elif action=='status':
        print(python("import pathlib,json; r=pathlib.Path('"+DEST+"'); print(json.dumps({n:json.loads((r/n).read_text(encoding='utf-8')) for n in ['PREPARED.json','PREPARE_FAILURE.json','CONTROLLER_STATE.json','STATE.json','AUDIT_STATE.json','CONTROLLER_FAILURE.json','COMPLETION.json'] if (r/n).exists()}))"))
    elif action=='fetch':
        out=ROOT/'remote_results';out.mkdir(exist_ok=True)
        names=json.loads(python("import pathlib,json; r=pathlib.Path('"+DEST+"'); print(json.dumps([p.name for p in r.iterdir() if p.is_file() and p.suffix in ['.json','.txt'] and p.name not in ['PRIVATE_REQUESTS.json','CATALOG_BEFORE.json']]))"))
        for name in names:run(['scp.exe','-q',*FLAGS,REMOTE+':'+DEST+'/'+name,str(out/name)])
        print('Metadata fetched: '+str(len(names)))
    else:raise ValueError(action)


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8',errors='strict');main(sys.argv[1])
