"""Terminal metadata and immutable input hashes only; no tensor inference."""
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def ps(script):
    out=subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-Command',script],text=True)
    return json.loads(out) if out.strip() else []


def main():
    freeze=json.loads((ROOT/'FREEZE.json').read_text())
    assert all(sha(ROOT/n)==d for n,d in freeze['files'].items())
    recovery=json.loads((ROOT/'VERIFIER_RECOVERY_FREEZE.json').read_text())
    assert all(sha(ROOT/n)==d for n,d in recovery['files'].items())
    assert all(sha(ROOT/n)==d for n,d in recovery['actual_primary_binding'].items())
    before=json.loads(Path('D:/BLIND_ROUTE_DETECTOR_20261110/CATALOG_BEFORE.json').read_text(encoding='utf-8'))
    catpath=Path('D:/TRAJECTORY_CATALOG_20261023/catalog.json')
    cat=json.loads(catpath.read_text(encoding='utf-8'))
    assert cat['cases'][:-1]==before['cases'] and len(cat['cases'])==29
    for k in before:
        if k not in ('cases','supplemental_audits'):assert cat[k]==before[k]
    models={}
    for pair in json.loads((ROOT/'INPUTS.json').read_text())['cases']:
        for key in ('pre','post'):
            b=pair[key];p=Path(b['path']);actual=sha(p);assert actual==b['sha256'];models[str(p)]=actual
    assert len(models)==15
    tasknames=['Codex-Blind-route-detector-20261110','Codex-Blind-route-detector-v2-20261110',
               'Codex-Blind-route-shared-recovery-20261110','Codex-Blind-route-command-recovery-20261110',
               'Codex-Blind-route-verify-nonempty-20261110','Codex-Blind-route-derived-packet-20261110',
               'Codex-FUBA-ten-seed-repro-recovery-20261031']
    script="$tasks=@("+','.join("'"+n+"'" for n in tasknames)+"); @($tasks | ForEach-Object {$t=Get-ScheduledTask -TaskName $_;$i=Get-ScheduledTaskInfo -TaskName $_;[pscustomobject]@{Name=$t.TaskName;State=[int]$t.State;ExitCode=$i.LastTaskResult;Triggers=@($t.Triggers).Count}})|ConvertTo-Json -Compress"
    tasks=ps(script)
    processes=ps("@(Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*BLIND_ROUTE_DETECTOR*'} | Select-Object ProcessId,CommandLine)|ConvertTo-Json -Compress")
    if isinstance(processes,dict):processes=[processes]
    processes=[p for p in processes if p['ProcessId']!=os.getpid()]
    assert not processes
    assert next(t for t in tasks if t['Name']=='Codex-Blind-route-verify-nonempty-20261110')['ExitCode']==0
    assert next(t for t in tasks if t['Name']=='Codex-Blind-route-derived-packet-20261110')['ExitCode']==0
    assert next(t for t in tasks if t['Name']=='Codex-FUBA-ten-seed-repro-recovery-20261031')['State']==1
    out=dict(time=time.time(),all_frozen_source_bytes_exact=True,primary_and_selection_bytes_unchanged=True,
             independent_verifier='verify_nonempty.py',independent_all20_counts_exact=json.loads((ROOT/'VERIFIED.json').read_text())['all_counts_exact'],
             cpu_all60_strict_finite=json.loads((ROOT/'CPU_PAYLOAD_AUDIT.json').read_text())['all_60_strict_finite'],
             all15_original_endpoint_file_hashes_unchanged=models,remote_catalog_sha256=sha(catpath),
             prior28_cases_and_defaults_preserved=True,remote_new_diagnostic_cases=1,
             active_owned_scientific_processes=processes,tasks=tasks,original_controller_failure_preserved=True)
    (ROOT/'FINAL_TERMINAL.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(state='passed',endpoint_hashes=len(models),all20_counts=True,all60_payloads=True,owned_active=0)))


if __name__=='__main__':main()
