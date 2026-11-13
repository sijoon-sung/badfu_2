"""Read the finite DISLAB run and verify a consistent result snapshot."""
import hashlib
import json
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from verify_summary import check

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'research' / '00_trajectories'))
from dislab_audit import FLAGS, REMOTE, remote, run

REMOTE_ROOT = 'D:/FOUR_ROUTE_LARGE_BENIGN_VALIDATION_20261113'
TASK = 'Codex-BadFU-four-route-new-benign-20261113'


def main():
    state = json.loads(remote(f"""
$r='{REMOTE_ROOT}'
$n='{TASK}'
$task=Get-ScheduledTask -TaskName $n
$info=Get-ScheduledTaskInfo -TaskName $n
$owned=@(Get-CimInstance Win32_Process | Where-Object {{
  $_.Name -eq 'python.exe' -and $_.CommandLine -match 'FOUR_ROUTE_LARGE_BENIGN_VALIDATION_20261113'
}})
$commits=@(Get-ChildItem "$r/commits" -Filter '*.json' -ErrorAction SilentlyContinue)
$hashes=[ordered]@{{}}
foreach($name in @('STATE.json','SCORES.json','COMPARISON.json','DATA_AUDIT.json','FAILURE.txt')) {{
    $file=Join-Path $r $name
    if(Test-Path -LiteralPath $file){{$hashes[$name]=(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower()}}
}}
[ordered]@{{task=[string]$task.State;exit=$info.LastTaskResult;owned=@($owned.ProcessId);commits=$commits.Count;files=$hashes}} |
  ConvertTo-Json -Depth 5 -Compress
"""))
    print(json.dumps(state, ensure_ascii=False))
    done = state['task'] == 'Ready' and state['exit'] == 0 and not state['owned']
    with TemporaryDirectory(dir=ROOT) as folder:
        staged = Path(folder)
        for name, expected in state['files'].items():
            file = staged / name
            run(['scp.exe', '-q', *FLAGS, REMOTE + ':' + REMOTE_ROOT + '/' + name, str(file)])
            actual = hashlib.sha256(file.read_bytes()).hexdigest()
            if actual != expected:
                raise SystemExit('Remote files advanced during transfer. Read back again.')
        if 'FAILURE.txt' in state['files']:
            print((staged / 'FAILURE.txt').read_text(encoding='utf-8'))
        if {'SCORES.json','COMPARISON.json'}.issubset(state['files']):
            print(json.dumps(check(staged, done), ensure_ascii=False))
        if done:
            assert state['commits'] == 160
            for name in state['files']:
                shutil.copyfile(staged / name, ROOT / name)
            (ROOT / 'TERMINAL.json').write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
