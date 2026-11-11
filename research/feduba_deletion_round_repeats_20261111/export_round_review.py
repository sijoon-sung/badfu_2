"""Export the audited actual round endpoints and logs; never imports torch."""
import hashlib
import os
from pathlib import Path
import traceback
import zipfile

from bindings import ROOT, read, write, sha, require_publication


def main():
    cfg = require_publication()
    f = read(ROOT/'DELIVERY_FREEZE.json')
    pub = read(ROOT/'DELIVERY_PUBLICATION.json')
    assert pub['all_raw_blob_bytes_verified'] and pub['freeze_sha256']==sha(ROOT/'DELIVERY_FREEZE.json')
    for name, digest in f['files'].items(): assert sha(ROOT/name)==digest,name
    (ROOT/'DELIVERY_ONCE').open('x').write(str(os.getpid()))
    final=read(ROOT/'COMPLETION.json'); assert final['state']=='complete' and final['new_FU_rounds']==30
    assert sha(ROOT/'PANEL_new_RESULT.json')==final['new_sha256']
    assert sha(ROOT/'PANEL_stored_RESULT.json')==final['stored_sha256']
    panel=read(ROOT/'PANEL_new_BINDING.json')
    assert sha(ROOT/'PANEL_new_BINDING.json')==final['new_binding_sha256']
    files={}; paths={}
    def add(name,p,digest=None):
        assert name not in files
        actual=sha(p)
        assert digest is None or actual==digest, name
        files[name]=dict(sha256=actual,bytes=p.stat().st_size)
        paths[name]=p
    pre=panel['server_inputs']['pre'];add('models/pre.pt',Path(pre['path']),pre['sha256'])
    total_epochs=0;total_batches=0
    for i,branch in enumerate(cfg['branch_order']):
        result=read(ROOT/('FU_'+branch+'_RESULT.json')); audit=read(ROOT/('FU_'+branch+'_VERIFIED.json'))
        assert audit['state']=='passed' and len(audit['roles'])==100
        assert audit['result_sha256']==sha(ROOT/('FU_'+branch+'_RESULT.json'))
        directory=ROOT/'fu'/branch
        mp=directory/'MANIFEST.json'; assert sha(mp)==result['manifest_sha256']
        epoch=directory/'epochs.jsonl'
        import json
        events=[json.loads(line) for line in epoch.read_bytes().splitlines()]
        seen=[(r['round'],r['client'],r['epoch']) for r in events]
        assert seen==[(r,c,e) for r in range(1,11) for c in cfg['fixed_clients'] for e in range(1,6)]
        assert all(r['branch']==branch for r in events)
        assert sum(r['batches'] for r in events)==result['batches']==audit['batches']
        total_epochs+=len(events);total_batches+=result['batches']
        add('logs/'+branch+'_epochs.jsonl',epoch);add('logs/'+branch+'_manifest.json',mp)
        for r in (1,3,5,10):
            k=f'u{i:02d}_r{r:02d}';meta=panel['server_inputs'][k];p=Path(meta['path']).resolve()
            assert p.is_relative_to(directory.resolve())
            assert audit['file_hashes'][p.relative_to(ROOT).as_posix()]==meta['sha256']
            add(f'models/{branch}/round{r:02d}.pt',p,meta['sha256'])
        for t in ('RESULT','VERIFIED'):
            n=f'FU_{branch}_{t}.json';add('metadata/'+n,ROOT/n)
    assert total_epochs==1500 and total_batches==24000
    for n in ('PROTOCOL.txt','PROFILE.json','REQUEST_SUMMARY.json','PANEL_stored_RESULT.json','PANEL_new_RESULT.json',
              'PANEL_new_BINDING.json','COMPLETION.json','RUN_FREEZE.json','RUN_PUBLICATION.json','PENDING_FREEZE.json',
              'PENDING_PROTOCOL.txt','PENDING_PUBLICATION.json','CONTROLLER_FAILURE.json','FU_balanced_b_FAILURE.json',
              'DEPENDENCY_CHECK.json','DELIVERY_PROTOCOL.txt','DELIVERY_FREEZE.json','DELIVERY_PUBLICATION.json'):
        add('metadata/'+n,ROOT/n)
    manifest=ROOT/'ROUND_REVIEW_MANIFEST.json'
    assert not manifest.exists()
    write(manifest,dict(files=files,model_payloads=13,epoch_records=total_epochs,batches=total_batches,
          scope='actual 1/3/5/10 FU endpoints for all 3 new repeats, shared pre and full epoch/manifest/audit logs',
          excludes='original private request IDs, CIFAR data, all role/optimizer/RNG tensors remain on DISLAB'))
    archive=ROOT/'D22_ROUND_REVIEW.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_STORED) as z:
        for name,p in paths.items():z.write(p,name)
        z.write(manifest,manifest.name)
    write(ROOT/'ROUND_REVIEW_SEAL.json',dict(file=archive.name,sha256=sha(archive),bytes=archive.stat().st_size,
         manifest_sha256=sha(manifest),files=len(files),model_payloads=13,model_loads=0,model_forwards=0))


if __name__=='__main__':
    try:main()
    except BaseException:
        write(ROOT/'DELIVERY_FAILURE.json',dict(traceback=traceback.format_exc()));raise
