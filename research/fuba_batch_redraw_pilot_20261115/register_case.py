"""Register the sealed bounded trajectory for diagnostics only; no defaults change."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from receive_packet import verify, sha

ROOT=Path(__file__).resolve().parent
REMOTE=Path('D:/FUBA_BATCH_REDRAW_PILOT_20261115')
CASE='fuba.reference.mnist.dba.s20261023.redraw.round21_30.20261115'
SELECTOR_SHA='bac9f7ed02fd5adce93dc904ad369939f180e8258292c5333dcf97a0f1c649bf'


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--local',action='store_true')
    parser.add_argument('--selector',type=Path,required=True);args=parser.parse_args()
    assert sha(args.selector)==SELECTOR_SHA
    seal_path=ROOT/'delivery/SEAL.json';seal=json.loads(seal_path.read_text())
    if args.local:payload=ROOT/'delivery/payload'
    else:
        assert ROOT==REMOTE.resolve()
        payload=ROOT
        with (ROOT/'REVIEW_MANIFEST.json').open('xb') as f:f.write((ROOT/'delivery/REVIEW_MANIFEST.json').read_bytes())
    files=verify(payload,seal['manifest_sha256'])
    for name in ['CPU_AUDIT.json','INDEPENDENT_RESULT.json','GAMMA_AUDIT.json']:
        assert json.loads((payload/name).read_text())['state']=='passed'
    assert not json.loads((payload/'RESULT.json').read_text())['behavioral_hypothesis_supported']
    out=ROOT/'catalog';out.mkdir(exist_ok=False)
    shutil.copyfile(args.selector,out/'select_case.py')
    audit={'case_id':CASE,'state':'verified_bounded_diagnostic_trajectory','files':len(files),
           'manifest_sha256':seal['manifest_sha256'],'performance_failed':True,'unlearning':False}
    write(out/'audit/AUDIT.json',audit)
    def location(base,manifest):
        inputs={label:{'path':str(base/name),'sha256':files[name]['sha256'],'payload_key':key}
                for label,name,key in [('pre','inputs/round0020.pt','after'),
                    ('post','rounds/round0030.pt','after'),('round23_incoming','rounds/round0023.pt','incoming')]}
        return {'root':str(base),'server_inputs':inputs,'checkpoint_guard':{
            'manifest_path':str(manifest),'manifest_sha256':seal['manifest_sha256'],
            'seal_path':str(ROOT/'delivery/SEAL.json') if args.local and base==payload else str(REMOTE/'delivery/SEAL.json'),
            'seal_sha256':sha(seal_path),'loader_path':str(base/'receive_packet.py')}}
    case={'id':CASE,'title':'Failed bounded per-batch redraw21-30R; no FU pair',
          'source_root':str(REMOTE),'allowed_purposes':['diagnostic'],
          'post_type':'bounded_FL_trajectory_no_unlearning',**location(REMOTE,REMOTE/'REVIEW_MANIFEST.json')}
    if args.local:case['local_copy']=location(payload,payload/'REVIEW_MANIFEST.json')
    write(out/'catalog.json',{'schema':'experiment-scoped-input-catalog-v1',
        'audit_sha256':sha(out/'audit/AUDIT.json'),'cases':[case],
        'supplemental_audits':[],'global_defaults_changed':False})
    cmd=[sys.executable,'-B',str(out/'select_case.py'),CASE,'--purpose','diagnostic']
    if args.local:cmd+=['--location','local']
    selected=json.loads(subprocess.check_output(cmd,text=True,encoding='utf-8'))
    assert selected['guard_state']=='all_snapshot_files_verified_on_this_host'
    write(ROOT/('LOCAL_SELECTION_CHECK.json' if args.local else 'REMOTE_SELECTION_CHECK.json'),selected)
    print(json.dumps({'state':'passed','case_id':CASE,'files':len(files)}))


if __name__=='__main__':main()
