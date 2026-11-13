"""Literal/hash-checked compact invocation, using the proven V3 transport."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'00_trajectories'))
import dislab_audit as t

def main():
    p=json.loads((HERE/'SOURCE_PROFILE.json').read_text());pub=json.loads((HERE/'RUN_PUBLICATION.json').read_text())
    sha=lambda b:hashlib.sha256(b).hexdigest()
    assert pub['source_freeze_sha256']==sha((HERE/'SOURCE_FREEZE.json').read_bytes())
    assert pub['run_freeze_sha256']==sha((HERE/'RUN_FREEZE.json').read_bytes())
    raw=(HERE/'launch_once.ps1').read_text(encoding='utf-8')
    assert raw.count('$r=$PSScriptRoot')==1
    replacement="$r='"+p['execution_root']+"'"
    expected=sha(raw.replace('$r=$PSScriptRoot',replacement).encode('utf-8'))
    digest=sha((HERE/'launch_once.ps1').read_bytes())
    literal=base64.b64encode(replacement.encode()).decode()
    command=("$f='"+p['execution_root']+"/launch_once.ps1';if((Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash.ToLowerInvariant() -ne '"+digest+"'){throw 'Launcher hash mismatch'};"
        "$b=[IO.File]::ReadAllText($f);$v=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+literal+"'));$b=$b.Replace('$r=$PSScriptRoot',$v);"
        "$a=[Security.Cryptography.SHA256]::Create();$x=([BitConverter]::ToString($a.ComputeHash([Text.Encoding]::UTF8.GetBytes($b)))).Replace('-','').ToLowerInvariant();if($x -ne '"+expected+"'){throw 'Invocation-body hash mismatch'}; & ([ScriptBlock]::Create($b))")
    with (HERE/'LOCAL_LAUNCH_ONCE.json').open('x',encoding='utf-8') as f:
        json.dump({'pid':os.getpid(),'run_publication_sha256':sha((HERE/'RUN_PUBLICATION.json').read_bytes()),'transformed_body_sha256':expected},f);f.flush();os.fsync(f.fileno())
    result=t.remote(command)
    with (HERE/'LOCAL_LAUNCH_RESULT.json').open('x',encoding='utf-8') as f:json.dump({'state':'first_launch_returned','stdout':result},f)
    print(result)

if __name__=='__main__':
    try:main()
    except BaseException:
        with (HERE/'LOCAL_LAUNCH_FAILURE.json').open('x',encoding='utf-8') as f:json.dump({'state':'failed_preserved','traceback':traceback.format_exc()},f)
        raise
