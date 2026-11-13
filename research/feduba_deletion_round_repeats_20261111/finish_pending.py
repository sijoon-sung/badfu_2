"""One bounded sequential task. Old trainers and verifiers are never invoked."""
import os
import subprocess
import sys
import time
import traceback

from bindings import ROOT, read, write, sha, require_publication


def run(filename, *args):
    label = filename.removesuffix('.py') + ('_'+ '_'.join(args) if args else '')
    with (ROOT/(label+'.stdout.txt')).open('xb') as out, (ROOT/(label+'.stderr.txt')).open('xb') as err:
        p = subprocess.Popen([sys.executable, '-B', '-u', str(ROOT/filename), *args], cwd=ROOT, stdout=out, stderr=err)
        write(ROOT/'PENDING_STATE.json',dict(state='running',pid=os.getpid(),child_pid=p.pid,script=filename,args=args,time=time.time()))
        rc=p.wait()
    if rc:
        raise RuntimeError(f'{label} stopped with exit {rc}; preserve the phase outputs')


def main():
    cfg=require_publication()
    (ROOT/'PENDING_ONCE').open('x').write(str(os.getpid()))
    f=read(ROOT/'PENDING_FREEZE.json')
    assert read(ROOT/'PENDING_PUBLICATION.json')['freeze_sha256']==sha(ROOT/'PENDING_FREEZE.json')
    for n,d in f['files'].items():assert sha(ROOT/n)==d,n
    assert not any((ROOT/'fu'/b).exists() for b in cfg['branch_order'])
    assert not (ROOT/'STATE.json').exists()
    run('validate_training_imports.py')
    assert read(ROOT/'DEPENDENCY_CHECK.json')['state']=='passed'
    assert read(ROOT/'PANEL_stored_RESULT.json')['endpoint_checks']==10
    for branch in cfg['branch_order']:
        run('train_fu_pending.py',branch)
        run('verify_fu.py',branch)
        v=read(ROOT/('FU_'+branch+'_VERIFIED.json'))
        assert v['state']=='passed' and v['rounds']==cfg['rounds']
    from prepare import prepare_new
    prepare_new()
    run('panel.py','new')
    assert len(read(ROOT/'PANEL_new_RESULT.json')['rows'])==12
    write(ROOT/'COMPLETION.json',dict(state='complete',stored_rows=30,new_rows=12,new_FU_rounds=30,
          new_branches=cfg['branch_order'],stored_sha256=sha(ROOT/'PANEL_stored_RESULT.json'),
          new_sha256=sha(ROOT/'PANEL_new_RESULT.json'),new_binding_sha256=sha(ROOT/'PANEL_new_BINDING.json'),
          old_finite_jobs_repeated=False))
    write(ROOT/'PENDING_STATE.json',dict(state='complete',pid=os.getpid(),time=time.time()))


if __name__=='__main__':
    try:main()
    except BaseException:
        write(ROOT/'PENDING_FAILURE.json',dict(traceback=traceback.format_exc()))
        raise SystemExit(1)
