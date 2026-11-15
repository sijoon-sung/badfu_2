"""Register only the delivered diagnostic pair, without changing any global default."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from verify_payload import digest,verify


CASE='fuba.reference.mnist.dba.s20261023.pre100.post.retrain100.20261115'


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--local-payload',type=Path)
    parser.add_argument('--selector',type=Path,required=True)
    parser.add_argument('--selector-sha256',required=True)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent;remote=Path('D:/FUBA_RETRAIN_FU_20261115')
    if args.local_payload:
        payload=args.local_payload.resolve();manifest=payload/'MANIFEST.json';seal=root/'delivery/SEAL.json'
    else:
        assert root==remote.resolve();payload=root;manifest=root/'delivery/MANIFEST.json';seal=root/'delivery/SEAL.json'
    bound=json.loads(seal.read_text());proof=verify(manifest.parent,bound['manifest_sha256'])
    result=json.loads((payload/'RESULT.json').read_text());cpu=json.loads((payload/'CPU_AUDIT.json').read_text());ind=json.loads((payload/'INDEPENDENT_RESULT.json').read_text())
    assert result['state']=='complete' and cpu['state']==ind['state']=='passed'
    assert result['rounds']==100 and result['erased_client']==4 and not result['original_pre_suppression_passed']
    assert digest(args.selector)==args.selector_sha256
    out=root/'catalog';out.mkdir(exist_ok=False)
    shutil.copyfile(args.selector,out/'select_case.py')
    audit={'state':'verified_diagnostic_pair','case_id':CASE,'proof':proof,'CPU_sha256':digest(payload/'CPU_AUDIT.json'),
           'independent_sha256':digest(payload/'INDEPENDENT_RESULT.json'),'seal_sha256':digest(seal),
           'selector_sha256':args.selector_sha256,'original_pre_suppression_failed':True,'full_paper_reproduced':False}
    put(out/'audit/AUDIT.json',audit)
    def location(base,man,seal_path):
        return {'root':str(base),'server_inputs':{k:{'path':str(base/name),'sha256':digest(payload/name),'payload_key':None}
                   for k,name in [('pre','inputs/before.pt'),('post','after.pt')]},
                'checkpoint_guard':{'manifest_path':str(man),'manifest_sha256':bound['manifest_sha256'],
                   'seal_path':str(seal_path),'seal_sha256':digest(seal),'loader_path':str(base/'verify_payload.py')}}
    registered=location(remote,remote/'delivery/MANIFEST.json',remote/'delivery/SEAL.json')
    case={'id':CASE,'title':'Actual MNIST DBA retained-client Retrain100 FU; failed original pre suppression',
          'source_root':str(remote),'allowed_purposes':['diagnostic'],'post_type':'actual_retained_client_retrain100_gamma1',**registered}
    if args.local_payload:case['local_copy']=location(payload,manifest,seal)
    put(out/'catalog.json',{'schema':'experiment-scoped-input-catalog-v1','audit_sha256':digest(out/'audit/AUDIT.json'),
                          'cases':[case],'supplemental_audits':[],'global_defaults_changed':False})
    cmd=[sys.executable,'-B',str(out/'select_case.py'),CASE,'--purpose','diagnostic']
    if args.local_payload:cmd+=['--location','local']
    selected=json.loads(subprocess.check_output(cmd,text=True,encoding='utf-8'))
    assert selected['guard_state']=='all_snapshot_files_verified_on_this_host'
    put(root/'SELECTION_CHECK.json',selected)
    print(json.dumps({'state':'registered','case_id':CASE,'location':'local' if args.local_payload else 'dislab','files':proof['files']}))


if __name__=='__main__':main()
