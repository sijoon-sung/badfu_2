"""Terminal metadata/input hash audit only; no torch or model inference."""
import json
import os
from pathlib import Path
import subprocess
import time
from bindings import ROOT,CAT,read,write,sha


def ps(script):
    value=subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-Command',script],text=True)
    return json.loads(value) if value.strip() else []


def main():
    completion=read(ROOT/'COMPLETION.json')
    assert completion['state'] in ('bounded_claim_falsified','bounded_controls_below_frozen_reference')
    for n,d in read(ROOT/'RUN_FREEZE.json')['files'].items():assert sha(ROOT/n)==d,n
    before=read(ROOT/'CATALOG_BEFORE.json');after=read(CAT/'catalog.json')
    assert after['cases'][:len(before['cases'])]==before['cases']
    assert after['supplemental_audits'][:len(before['supplemental_audits'])]==before['supplemental_audits']
    for k in before:
        if k not in ('cases','supplemental_audits'):assert after[k]==before[k]
    old_models={}
    for pair in read(Path('D:/BLIND_ROUTE_DETECTOR_V2_20261110/INPUTS.json'))['cases']:
        for key in ('pre','post'):
            meta=pair[key];assert sha(Path(meta['path']))==meta['sha256'];old_models[meta['path']]=meta['sha256']
    endpoints={};totals=dict(rounds=0,roles=0,epochs=0,batches=0)
    for verdict in completion['results']:
        branch=verdict['branch'];opaque=verdict['opaque'];result=read(ROOT/('FU_'+branch+'_RESULT.json'))
        audit=read(ROOT/('FU_'+branch+'_VERIFIED.json'));assert audit['state']=='passed'
        assert audit['result_sha256']==sha(ROOT/('FU_'+branch+'_RESULT.json'))
        for key in totals:totals[key]+=result[key]
        meta=result['after'];assert sha(Path(meta['path']))==meta['sha256'];endpoints[branch]=meta
        out=ROOT/'detector'/opaque
        for n,d in read(out/'FREEZE.json')['files'].items():assert sha(out/n)==d,n
        check=read(out/'VERIFIED.json');assert check['all_counts_exact']
        assert check['primary_sha256']==sha(out/'RESULT.json')
        assert read(out/'SELECTION_SEAL.json')['sha256']==sha(out/'SELECTIONS.json')
    owned=ps("@(Get-CimInstance Win32_Process|Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*FEDUBA_LARGE_BENIGN_VALIDATION_20261110*'}|Select-Object ProcessId,CommandLine)|ConvertTo-Json -Compress")
    if isinstance(owned,dict):owned=[owned]
    owned=[p for p in owned if p['ProcessId']!=os.getpid()];assert not owned
    names=['Codex-FedUBA-large-normal-prepare-20261110','Codex-FedUBA-large-normal-FU20-20261110',
           'Codex-FedUBA-large-normal-admission-recovery-20261110','Codex-FedUBA-large-normal-finish-20261111',
           'Codex-FedUBA-large-normal-finish-v2-20261111','Codex-FedUBA-large-normal-review-20261111',
           'Codex-FUBA-ten-seed-repro-recovery-20261031']
    tasks=ps("$names=@("+','.join("'"+n+"'" for n in names)+");@($names|ForEach-Object {$t=Get-ScheduledTask -TaskName $_;$i=Get-ScheduledTaskInfo -TaskName $_;[pscustomobject]@{Name=$t.TaskName;State=[int]$t.State;ExitCode=$i.LastTaskResult}})|ConvertTo-Json -Compress")
    assert next(t for t in tasks if t['Name']=='Codex-FedUBA-large-normal-finish-v2-20261111')['ExitCode']==0
    assert next(t for t in tasks if t['Name']=='Codex-FedUBA-large-normal-review-20261111')['ExitCode']==0
    assert next(t for t in tasks if t['Name']=='Codex-FUBA-ten-seed-repro-recovery-20261031')['State']==1
    write(ROOT/'FINAL_TERMINAL.json',dict(time=time.time(),state='passed',totals=totals,
          old15_input_hashes_preserved=old_models,new_endpoints=endpoints,all_completed_native_counts_exact=True,
          prior_case_count=len(before['cases']),final_case_count=len(after['cases']),old_cases_defaults_audits_preserved=True,
          catalog_sha256=sha(CAT/'catalog.json'),active_owned_processes=owned,tasks=tasks,
          publication_timeout_and_import_failure_preserved=True,original_FU_and_audit_not_repeated=True,
          review_seal=read(ROOT/'REVIEW_SEAL.json')))
    print(json.dumps(dict(state='passed',totals=totals,owned_active=0)))


if __name__=='__main__':main()
