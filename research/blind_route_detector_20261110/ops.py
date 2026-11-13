"""Local transport only. Actual scientific code runs on DISLAB."""
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = Path('C:/Users/sijoo/Documents/ChatGPT/badFU')
sys.path.insert(0, str(WORKSPACE/'research/00_trajectories'))
from dislab_audit import FLAGS, REMOTE, remote, run

DEST = 'D:/BLIND_ROUTE_DETECTOR_20261110'
PYTHON = 'C:/Users/DISLAB/AppData/Local/Programs/Python/Python312/python.exe'


def python(code):
    b = base64.b64encode(code.encode('utf-8')).decode()
    return remote("$env:PYTHONIOENCODING='utf-8'\n& '"+PYTHON+"' -c \"import base64;exec(base64.b64decode('"+b+"'))\"\nexit $LASTEXITCODE")


def main(action):
    if action == 'upload':
        print(remote("if (Test-Path '"+DEST+"') { throw 'New experiment destination already exists' }\nNew-Item -ItemType Directory '"+DEST+"' | Out-Null"))
        freeze = json.loads((ROOT/'FREEZE.json').read_text())
        for name in list(freeze['files'])+['FREEZE.json','PUBLICATION.json']:
            run(['scp.exe','-q',*FLAGS,str(ROOT/name),REMOTE+':'+DEST+'/'+name])
        print('source uploaded once')
    elif action == 'prepare':
        print(remote("if (Test-Path '"+DEST+"/PREPARE_ONCE') { throw 'Existing preparation marker' }\n$p=Start-Process -FilePath '"+PYTHON+"' -ArgumentList '-u','"+DEST+"/prepare.py' -WorkingDirectory '"+DEST+"' -WindowStyle Hidden -PassThru -RedirectStandardOutput '"+DEST+"/prepare.stdout.txt' -RedirectStandardError '"+DEST+"/prepare.stderr.txt'\n$p.Id"))
    elif action == 'start':
        print(remote("if (Test-Path '"+DEST+"/CONTROLLER_ONCE') { throw 'Existing controller marker' }\n$p=Start-Process -FilePath '"+PYTHON+"' -ArgumentList '-u','"+DEST+"/controller.py' -WorkingDirectory '"+DEST+"' -WindowStyle Hidden -PassThru -RedirectStandardOutput '"+DEST+"/controller.stdout.txt' -RedirectStandardError '"+DEST+"/controller.stderr.txt'\n$p.Id"))
    elif action == 'status':
        print(python("import json,pathlib,subprocess; r=pathlib.Path('"+DEST+"'); out={};\nfor n in ['CONTROLLER_STATE.json','STATE.json','SEARCH_FAILURE.txt','VERIFY_FAILURE.txt']:\n p=r/n\n if p.exists():out[n]=p.read_text(encoding='utf-8')\nout['processes']=subprocess.check_output(['powershell','-NoProfile','-Command',\"@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^(python|pythonw|mpiexec)\\\\.exe$'} | Select-Object ProcessId,ParentProcessId,CommandLine)|ConvertTo-Json -Compress\"],text=True)\nprint(json.dumps(out,ensure_ascii=True))"))
    elif action == 'fetch':
        local = ROOT/'remote_results'; local.mkdir(exist_ok=True)
        listing = json.loads(python("import pathlib,json; r=pathlib.Path('"+DEST+"'); print(json.dumps([p.name for p in r.iterdir() if p.is_file() and p.suffix in ['.json','.txt'] and not p.name.startswith('controller.')]))"))
        for name in listing:
            run(['scp.exe','-q',*FLAGS,REMOTE+':'+DEST+'/'+name,str(local/name)])
        print('fetched '+str(len(listing))+' metadata files')
    else: raise ValueError(action)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='strict')
    main(sys.argv[1])
