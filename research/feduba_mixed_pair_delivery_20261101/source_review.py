"""Once new delivery source and completed-metadata review. No torch/model/OS probe."""
import ast
import json
import os
import sys
import traceback
from pathlib import Path
from pair_review_common import ROOT,read,write,digest,input_receipts

def main():
    assert ROOT==Path('D:/FEDUBA_MIXED_PAIR_DELIVERY_20261101')
    assert sys.version_info[:3]==(3,12,10)
    write(ROOT/'SOURCE_REVIEW_ONCE.json',{'pid':os.getpid(),'model_loads':0,'model_forwards':0})
    f=read(ROOT/'SOURCE_FREEZE.json')
    for n,sha in f['files'].items():assert digest(ROOT/n)==sha,n
    for n in ROOT.glob('*.py'):ast.parse(n.read_text(encoding='utf-8'))
    p=input_receipts();roots={k:Path(v) for k,v in p['roots'].items()}
    for n,v in read(ROOT/'COPY_PROVENANCE.json')['unchanged_helpers'].items():assert digest(ROOT/n)==v['sha256']
    assert not (ROOT/'DELIVERY_PUBLICATION.json').exists()
    assert not (Path('D:/CHECKPOINTS_FOR_REVIEW')/p['packet_name']).exists()
    clean=read(roots['foundation']/'clean_fl/MANIFEST.json')
    histories={b:read(roots['attack' if b=='attack' else 'pair']/f'fu/{b}/MANIFEST.json') for b in p['case_ids']}
    roles=[]
    for owner in [5,7]:
        original=next(v for v in reversed(clean['rounds']) if owner in v['clients']);rn=original['round']
        for branch,h in histories.items():
            assert len(h['rounds'])==20 and [v['clients'] for v in h['rounds']]==[v['clients'] for v in clean['rounds']]
            tr=next(v for v in h['rounds'][rn-1]['trained_roles'] if v['client']==owner)
            ca=next(v for v in h['rounds'][rn-1]['calibrated_roles'] if v['client']==owner)
            assert tr['source_N']>0 and tr['batches']>0 and ca['checkpoint']['payload_key'] is None
            roles.append({'branch':branch,'owner':owner,'round':rn,'source_N':tr['source_N'],'batches':tr['batches']})
    sss=read(roots['pair']/'SSS_RESULT.json');ev=read(roots['eval']/'PAIR_EVAL_RESULT.json')
    assert len(sss['query_packets'])==40 and len(ev['input_packets'])==79
    assert all(len(v)==79 for v in ev['logit_packets'].values())
    assert len(read(roots['trigger']/'TRIGGER_VERIFIED.json')['history_hashes'])==300
    assert read(roots['eval']/'PAIR_EVAL_VERIFIED.json')['state']=='passed'
    assert not ev['minimum_operational_gate']['passed']
    assert 'torch' not in sys.modules
    write(ROOT/'SOURCE_REVIEW_RESULT.json',{'state':'passed_new_delivery_source_and_completed_metadata_review',
        'Python_AST_files':len(list(ROOT.glob('*.py'))),'frozen_file_count':len(f['files']),'input_receipts':len(p['input_receipts']),
        'representative_roles':roles,'SSS_query_packets':40,'evaluation_input_packets':79,'evaluation_logit_packets':237,
        'new_CPU_trigger_records':300,'model_loads':0,'model_forwards':0,'torch_imported':False,'old_finite_called':False})
    print(json.dumps({'state':'passed_new_delivery_source_and_completed_metadata_review','model_loads':0,'model_forwards':0,'roles':roles}))

if __name__=='__main__':
    try:main()
    except BaseException:
        write(ROOT/'SOURCE_REVIEW_FAILURE.json',{'state':'failed_preserved','traceback':traceback.format_exc()});raise
