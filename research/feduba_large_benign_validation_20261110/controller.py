"""Finite sequential control: FU -> CPU audit -> publication -> blind discovery."""
import json
import os
import subprocess
import sys
import time
import traceback
from bindings import ROOT,read,write,sha,require_publication


def child(script,*args,cwd=ROOT):
    tag=script.removesuffix('.py')+('_'+'_'.join(args) if args else '')
    with (cwd/(tag+'.stdout.txt')).open('xb') as out,(cwd/(tag+'.stderr.txt')).open('xb') as err:
        process=subprocess.Popen([sys.executable,'-u',str(cwd/script),*args],cwd=cwd,stdout=out,stderr=err,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        write(ROOT/'CONTROLLER_STATE.json',dict(state='running',pid=os.getpid(),child_pid=process.pid,script=script,args=args,time=time.time()))
        code=process.wait()
    assert code==0,(script,args,code)


def main():
    (ROOT/'CONTROLLER_ONCE').open('x').write(str(os.getpid()))
    cfg=require_publication();results=[]
    for index,branch in enumerate(cfg['branch_order']):
        child('train_fu.py',branch);child('verify_fu.py',branch)
        from setup_detector import main as setup
        out=setup(branch,index);opaque=f'n{index:02d}'
        write(ROOT/'CONTROLLER_STATE.json',dict(state='waiting_detector_publication',pid=os.getpid(),branch=branch,opaque=opaque,time=time.time()))
        started=time.monotonic()
        while not (out/'PUBLICATION.json').exists():
            assert time.monotonic()-started<7200,'Bounded publication wait expired'
            time.sleep(2)
        pub=read(out/'PUBLICATION.json');assert pub['all_raw_blob_bytes_verified']
        for name,digest in read(out/'FREEZE.json')['files'].items():assert sha(out/name)==digest
        child('run_search.py',cwd=out);child('verify_nonempty.py',cwd=out)
        assert read(out/'VERIFIED.json')['all_counts_exact']
        rows=read(out/'RESULT.json')['results'];assert len(rows)==2
        route=next(row for row in rows if row['arm']=='route')
        assert route['n']==cfg['stopping_n']==900
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
    write(ROOT/'CONTROLLER_STATE.json',dict(state='complete',pid=os.getpid(),time=time.time()))


if __name__=='__main__':
    try:main()
    except BaseException:
        write(ROOT/'CONTROLLER_FAILURE.json',dict(traceback=traceback.format_exc(),time=time.time()))
        write(ROOT/'CONTROLLER_STATE.json',dict(state='failed_preserved',pid=os.getpid(),time=time.time()));raise
