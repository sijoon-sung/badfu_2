"""Report task exits, verified case append and final byte bindings; no model calls."""
import json
import os
from pathlib import Path
import subprocess
from bindings import ROOT, CAT, read, write, sha, require_publication


def ps(command):
    s=subprocess.check_output(['powershell','-NoProfile','-NonInteractive','-Command',command],text=True)
    return json.loads(s) if s.strip() else []


def main():
    cfg=require_publication();done=read(ROOT/'COMPLETION.json')
    assert done['state']=='complete' and done['new_branches']==cfg['branch_order']
    for n,k in [('PANEL_stored_RESULT.json','stored_sha256'),('PANEL_new_RESULT.json','new_sha256'),('PANEL_new_BINDING.json','new_binding_sha256')]:
        assert sha(ROOT/n)==done[k]
    before=read(ROOT/'CATALOG_BEFORE.json');after=read(CAT/'catalog.json')
    assert after['cases'][:len(before['cases'])]==before['cases']
    assert after['supplemental_audits'][:len(before['supplemental_audits'])]==before['supplemental_audits']
    assert all(after[k]==v for k,v in before.items() if k not in ('cases','supplemental_audits'))
    assert len(after['cases'])==len(before['cases'])+2
    totals=dict(rounds=0,roles=0,epochs=0,batches=0)
    for b in cfg['branch_order']:
        f=ROOT/('FU_'+b+'_RESULT.json');v=read(ROOT/('FU_'+b+'_VERIFIED.json'));r=read(f)
        assert v['state']=='passed' and v['result_sha256']==sha(f)
        assert v['calibration_and_aggregation_exact']
        for n in totals:totals[n]+=r[n]
        assert sha(Path(r['after']['path']))==r['after']['sha256']
    assert totals==dict(rounds=30,roles=300,epochs=1500,batches=24000)
    names=['Codex-FedUBA-deletion-round-repeats-prepare-20261111','Codex-FedUBA-deletion-round-repeats-20261111',
           'Codex-FedUBA-deletion-round-repeats-pending-20261111','Codex-FedUBA-deletion-round-review-20261111',
           'Codex-FUBA-ten-seed-repro-recovery-20261031']
    tasks=ps('$names=@('+','.join("'"+n+"'" for n in names)+
        ');@($names|ForEach-Object {$t=Get-ScheduledTask -TaskName $_;$i=Get-ScheduledTaskInfo -TaskName $_;'+
        '[pscustomobject]@{name=$t.TaskName;state=[int]$t.State;exit=$i.LastTaskResult}})|ConvertTo-Json -Compress')
    assert [t['exit'] for t in tasks[:4]]==[0,1,0,0] and tasks[-1]['state']==1
    processes=ps("@(Get-CimInstance Win32_Process|Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*FEDUBA_DELETION_ROUND_REPEATS_20261111*'}|Select-Object ProcessId)|ConvertTo-Json -Compress")
    if isinstance(processes,dict):processes=[processes]
    other=[p for p in processes if p['ProcessId']!=os.getpid()];assert not other
    assert (ROOT/'CONTROLLER_FAILURE.json').exists() and (ROOT/'FU_balanced_b_FAILURE.json').exists()
    write(ROOT/'TERMINAL_AUDIT.json',dict(state='passed',totals=totals,stored_checkpoints=30,new_checkpoints=12,
        previous_cases=len(before['cases']),current_cases=len(after['cases']),prior_catalogue_cases_and_defaults_unchanged=True,
        active_owned=other,tasks=tasks,stored_panel_sha256=done['stored_sha256'],new_panel_sha256=done['new_sha256'],
        original_failure_preserved=True,review=read(ROOT/'ROUND_REVIEW_SEAL.json')))
    print(json.dumps(dict(state='passed',totals=totals,active_owned=len(other))))


if __name__=='__main__':main()
