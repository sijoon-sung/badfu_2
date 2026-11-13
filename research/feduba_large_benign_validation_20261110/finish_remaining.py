"""Continue only pending phases after a completed FU/audit publication timeout."""
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from bindings import ROOT,read,write,sha,require_publication
from controller import child


def main():
    (ROOT/'FINISH_REMAINING_ONCE').open('x').write(str(os.getpid()))
    cfg=require_publication()
    assert read(ROOT/'FINISH_PUBLICATION.json')['all_raw_blob_bytes_verified']
    freeze=read(ROOT/'FINISH_FREEZE.json')
    for name,digest in freeze['files'].items():assert sha(ROOT/name)==digest,name
    for name,digest in freeze['completed_binding'].items():assert sha(ROOT/name)==digest,name
    failure=read(ROOT/'CONTROLLER_FAILURE.json')
    assert 'Bounded publication wait expired' in failure['traceback']
    assert read(ROOT/'CONTROLLER_STATE.json')['state']=='failed_preserved'
    assert read(ROOT/'FU_balanced5000_VERIFIED.json')['state']=='passed'
    assert not (ROOT/'detector/n00/SEARCH_ONCE').exists()
    ps=subprocess.check_output(['powershell','-NoProfile','-Command',
       "@(Get-CimInstance Win32_Process|Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -like '*FEDUBA_LARGE_BENIGN_VALIDATION_20261110*'}|Select-Object ProcessId)|ConvertTo-Json -Compress"],text=True)
    peers=json.loads(ps) if ps.strip() else []
    if isinstance(peers,dict):peers=[peers]
    assert not [p for p in peers if p['ProcessId']!=os.getpid()]
    archive=ROOT/'incidents/publication_timeout';archive.mkdir(parents=True,exist_ok=False)
    for name in ['CONTROLLER_STATE.json','CONTROLLER_FAILURE.json']:
        source=ROOT/name;target=archive/name
        assert target.resolve().is_relative_to(archive.resolve());source.rename(target)
    results=[]
    for index,branch in enumerate(cfg['branch_order']):
        if index==0:
            ready=read(ROOT/'DETECTOR_READY_n00.json');out=Path(ready['root'])
        else:
            child('train_fu.py',branch);child('verify_fu.py',branch)
            from setup_detector import main as setup
            out=setup(branch,index)
        opaque=f'n{index:02d}'
        write(ROOT/'CONTROLLER_STATE.json',dict(state='waiting_detector_publication',pid=os.getpid(),branch=branch,opaque=opaque,time=time.time()))
        start=time.monotonic()
        while not (out/'PUBLICATION.json').exists():
            assert time.monotonic()-start<7200,'Bounded publication wait expired'
            time.sleep(2)
        assert read(out/'PUBLICATION.json')['all_raw_blob_bytes_verified']
        for name,digest in read(out/'FREEZE.json')['files'].items():assert sha(out/name)==digest
        child('run_search.py',cwd=out);child('verify_nonempty.py',cwd=out)
        assert read(out/'VERIFIED.json')['all_counts_exact']
        rows=read(out/'RESULT.json')['results'];route=next(r for r in rows if r['arm']=='route')
        assert len(rows)==2 and route['n']==cfg['stopping_n']==900
        child('clean_evaluate.py',branch)
        verdict=dict(branch=branch,opaque=opaque,results=rows,route_overlap=route['witness']>=cfg['stopping_route_witness'],
                     clean_utility=read(ROOT/('CLEAN_'+branch+'.json')),native_independent_counts_exact=True)
        write(ROOT/('VERDICT_'+branch+'.json'),verdict);results.append(verdict)
        if verdict['route_overlap']:
            write(ROOT/'COMPLETION.json',dict(state='bounded_claim_falsified',results=results,
                 unstarted_branches=cfg['branch_order'][index+1:],calibration_required=True,all_claims_validated=False))
            break
    else:
        write(ROOT/'COMPLETION.json',dict(state='bounded_controls_below_frozen_reference',results=results,
                 unstarted_branches=[],calibration_required=True,universal_detection_validated=False))
    write(ROOT/'CONTROLLER_STATE.json',dict(state='complete',pid=os.getpid(),time=time.time(),continuation='finish_remaining.py'))


if __name__=='__main__':
    try:main()
    except BaseException:
        write(ROOT/'FINISH_FAILURE.json',dict(traceback=traceback.format_exc(),time=time.time()));raise
