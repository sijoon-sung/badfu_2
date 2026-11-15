"""Full raw history stays remote; deliver actual pair, all logs and selected states."""
import json
import zipfile
from run import ROOT,read,sha,write,frozen


def main():
    frozen()
    assert read(ROOT/'STATE.json')['state']=='complete'
    assert read(ROOT/'CPU_AUDIT.json')['state']=='passed'
    assert read(ROOT/'INDEPENDENT_RESULT.json')['state']=='passed'
    for name,digest in read(ROOT/'EXPORT_FREEZE.json')['files'].items():assert sha(ROOT/name)==digest
    out=ROOT/'delivery';out.mkdir(exist_ok=False)
    full={p.relative_to(ROOT).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}
          for p in sorted(ROOT.rglob('*')) if p.is_file() and not p.is_relative_to(out)
          and '__pycache__' not in p.parts and p.suffix!='.tmp'}
    write('delivery/FULL_REMOTE_RAW_MANIFEST.json',{'remote_root':str(ROOT),'files':full})
    chosen={}
    for name,item in full.items():
        keep=not name.endswith('.pt') or name.startswith('inputs/') or name=='after.pt'
        keep=keep or name in ['rounds/round0001.pt','rounds/round0100.pt']
        keep=keep or name.startswith('phases/round0100_')
        if keep:chosen[name]=item
    chosen['delivery/FULL_REMOTE_RAW_MANIFEST.json']={'sha256':sha(out/'FULL_REMOTE_RAW_MANIFEST.json'),'bytes':(out/'FULL_REMOTE_RAW_MANIFEST.json').stat().st_size}
    manifest={'schema':'fuba-retrain-pair-review-v1','remote_root':str(ROOT),'files':chosen,
              'scope':'Actual original before, original initial, new retained-client FU100 after; all epoch and role logs; first/final round and final-round phases. All intermediate tensors remain in full remote manifest.',
              'full_paper_reproduced':False,'pre_suppression_failed':True,'FU':'Retained-client Retrain100, gamma1'}
    assert 'REVIEW_MANIFEST.json' not in chosen
    write('delivery/REVIEW_MANIFEST.json',manifest)
    archive=out/'FUBA_RETRAIN_FU_RECOVERY_20261115.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as z:
        for name,item in chosen.items():
            assert sha(ROOT/name)==item['sha256'];z.write(ROOT/name,name)
        z.write(out/'REVIEW_MANIFEST.json','REVIEW_MANIFEST.json')
    seal={'manifest_sha256':sha(out/'REVIEW_MANIFEST.json'),'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
          'files':len(chosen),'full_remote_files':len(full),'full_paper_reproduced':False}
    write('delivery/SEAL.json',seal);print(json.dumps(seal),flush=True)


if __name__=='__main__':main()
