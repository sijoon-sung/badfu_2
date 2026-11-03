"""Bounded read-only status; JSON event rows never carry PowerShell ETS providers."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
QUERY = r"""+$r='D:/FEDUBA_MIXED_PAIR_20261101'
$states=@{}
foreach($name in @('PAIR_CONTROLLER_STATE.json','PAIR_CONTROLLER_FAILURE.json',
  'FU_benign_STATE.json','FU_benign_FAILURE.json','FU_benign_AUDIT_STATE.json','FU_benign_AUDIT_FAILURE.json',
  'FU_attack_STATE.json','FU_attack_FAILURE.json','FU_attack_AUDIT_STATE.json','FU_attack_AUDIT_FAILURE.json',
  'PAIR_EVAL_STATE.json','PAIR_EVAL_FAILURE.json','PAIR_EVAL_AUDIT_FAILURE.json')) {
  if(Test-Path -LiteralPath "$r/$name") {
    $value=Get-Content -LiteralPath "$r/$name" -Raw -Encoding UTF8 | ConvertFrom-Json
    $row=$value | Select-Object state,pid,step,branch,child_pid,round,rounds,client,epoch,examples,cumulative_role_batches,checked_roles,actual_epochs,actual_batches
    if($value.traceback) {$row | Add-Member -NotePropertyName traceback_preview -NotePropertyValue ([string]$value.traceback).Substring(0,[Math]::Min(4000,([string]$value.traceback).Length))}
    $states[$name]=$row
  }
}
$s=$states['PAIR_CONTROLLER_STATE.json'];$processes=@()
if($s.pid) {
  $filter='ProcessId='+[int]$s.pid
  if($s.child_pid) {$filter+=' OR ProcessId='+[int]$s.child_pid}
  $processes=@(Get-CimInstance Win32_Process -Filter $filter | Select-Object ProcessId,ParentProcessId,CommandLine)
}
$rounds=@{};$events=@{}
foreach($branch in @('benign','attack')) {
  if(Test-Path -LiteralPath "$r/fu/$branch/MANIFEST.json") {
    $m=Get-Content -LiteralPath "$r/fu/$branch/MANIFEST.json" -Raw -Encoding UTF8 | ConvertFrom-Json
    $rounds[$branch]=@($m.rounds).Count
  }
  if(Test-Path -LiteralPath "$r/fu/$branch/events.jsonl") {
    # Parse before embedding. A raw Get-Content string has ETS PSDrive/Provider properties.
    $line=Get-Content -LiteralPath "$r/fu/$branch/events.jsonl" -Tail 1 -Encoding UTF8
    if($line) {$events[$branch]=([string]$line | ConvertFrom-Json | Select-Object kind,branch,round,client,epoch,examples,batches,cumulative_role_batches)}
  }
}
$completed=@{}
foreach($name in @('FU_benign_RESULT.json','FU_benign_VERIFIED.json','FU_attack_RESULT.json','FU_attack_VERIFIED.json','PAIR_EVAL_VERIFIED.json')) {
  if(Test-Path -LiteralPath "$r/$name") {
    $value=Get-Content -LiteralPath "$r/$name" -Raw -Encoding UTF8 | ConvertFrom-Json
    $completed[$name]=$value | Select-Object state,branch,rounds,new_trained_roles,actual_local_epochs,actual_batches
  }
}
[pscustomobject]@{utc=(Get-Date).ToUniversalTime().ToString('o');root=$r;states=$states;processes=$processes;committed_rounds=$rounds;last_events=$events;completed=$completed} | ConvertTo-Json -Depth 6 -Compress
"""


def observe():
    frozen = json.loads((HERE / 'FREEZE.json').read_text(encoding='utf-8'))
    for name, digest in frozen['files'].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name
    sys.path.insert(0, str(HERE.parent / '00_trajectories'))
    import dislab_audit
    raw = dislab_audit.remote(QUERY)
    if len(raw) > 50000:
        raise RuntimeError('Observer output exceeded the fixed character bound; raw output withheld')
    value = json.loads(raw)
    assert value['root'] == 'D:/FEDUBA_MIXED_PAIR_20261101'
    assert set(value) == {'utc', 'root', 'states', 'processes', 'committed_rounds', 'last_events', 'completed'}
    # Explicit schemas also reject accidental ETS expansion within a short output.
    for event in value['last_events'].values():
        assert set(event) == {'kind', 'branch', 'round', 'client', 'epoch', 'examples', 'batches', 'cumulative_role_batches'}
    assert 'torch' not in sys.modules
    return {'state': 'passed_bounded_readonly_metadata_observation', 'output_characters': len(raw),
            'source_freeze_sha256': hashlib.sha256((HERE / 'FREEZE.json').read_bytes()).hexdigest(),
            'query_sha256': hashlib.sha256(QUERY.encode()).hexdigest(),
            'new_model_queries': 0, 'training_or_audit_reexecuted': False, 'observation': value}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--save', type=Path)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8')
    result = observe()
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.save:
        with args.save.open('x', encoding='utf-8', newline='\n') as stream: stream.write(output)
    print(output)
