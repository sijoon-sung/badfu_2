"""Recompute deletion audits with truly heldout reference records, no inference."""
import json,os,time
from pathlib import Path
import numpy as np
import torch
import stage05_common as s
from verify_stage05_results import independent_auc
core=s.core
OUT=s.HERE/'heldout_reference_audit'


def independent(audit,mz,my,nz,ny):
    ml=mz.log_softmax(1).numpy();nl=nz.log_softmax(1).numpy();checks=0
    mlabels=my.numpy();nlabels=ny.numpy()
    for name,ms,ns in [('true_label_logprob',ml[np.arange(len(my)),mlabels],nl[np.arange(len(ny)),nlabels]),
                       ('max_logprob',ml.max(1),nl.max(1))]:
        for c in range(10):
            v=independent_auc(ms[mlabels==c],ns[nlabels==c]) if (mlabels==c).any() else .5
            assert abs(v-audit['scores'][name]['class_rows'][c]['AUC'])<1e-12,(name,c)
            checks+=1
    return checks


def compare(a,b):
    assert a['member_n']==b['member_n'] and a['nonmember_n']==b['nonmember_n']
    assert abs(a['weighted_accuracy_gap']-b['weighted_accuracy_gap'])<1e-10
    for score in a['scores']:
        for key in ['weighted_AUC','advantage','weighted_class_advantage']:
            assert abs(a['scores'][score][key]-b['scores'][score][key])<1e-10,(score,key,a['scores'][score][key],b['scores'][score][key])


def gate(audit,baseline):
    increases={n:{key:audit['scores'][n][key]-baseline['scores'][n][key] for key in ['advantage','weighted_class_advantage']} for n in audit['scores']}
    gap=abs(audit['weighted_accuracy_gap'])-abs(baseline['weighted_accuracy_gap'])
    return {'increase_over_post':increases,'absolute_accuracy_gap_increase':gap,
            'necessary_deletion_gate':gap<=.02+1e-12 and all(v<=.04+1e-12 for values in increases.values() for v in values.values())}


def pinned_torch(path,receipt):
    assert core.sha(path)==receipt['files'][path.name],str(path)
    return torch.load(path,map_location='cpu',weights_only=True)


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources();core.OUT=OUT
    frozen=core.read(s.HERE/'HELDOUT_REFERENCE_FREEZE.json')
    for n,h in frozen['files'].items():assert core.sha(s.HERE/n)==h,n
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'new_inference':False},f)
    selected,sealed,states=s.snapshot()
    split=core.read(s.HERE/'PROXY_SPLIT.json');held=torch.tensor(split['heldout_ids'])
    assert len(held)==9500 and len(set(split['fit_ids'])&set(split['heldout_ids']))==0
    info=core.read(s.HERE/'STAGE03_INPUTS.json')
    assert core.sha(info['clean_path'])==info['clean_path_sha256'] and core.sha(info['record_path'])==info['record_path_sha256']
    y=torch.load(info['clean_path'],map_location='cpu',weights_only=True)['test_y'].long()
    record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    tids=[int(i) for i in record['bd_test']['bd_data_container']['data_dict']]
    assert len(tids)==9000 and sorted(tids)==torch.where(y!=0)[0].tolist()
    held_set=set(split['heldout_ids']);mask=torch.tensor([i in held_set for i in tids],dtype=torch.bool)
    oldroot=s.HERE/'stage07_cpu_v2';oldreceipt=core.read(oldroot/'COMPLETED.json');oldresult=core.read(oldroot/'RESULT.json')
    assert core.sha(oldroot/'RESULT.json')==oldreceipt['result_sha256']
    result={'state':'running','new_inference':False,'source_freeze_sha256':core.sha(s.HERE/'HELDOUT_REFERENCE_FREEZE.json'),
            'nonmember_clean_n':9500,'nonmember_trigger_n':int(mask.sum()),'removed_public_clean_n':500,
            'removed_public_trigger_n':int((~mask).sum()),'original_interventions':{},'students':{},'independent_AUC_checks':0}
    for pair,a,b in core.PAIRS:
        mem=pinned_torch(oldroot/('private_'+pair+'_member_features.pt'),oldreceipt);my=mem['labels'].long()
        before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
        refs='attack' if pair.startswith('attack') else 'clean';ny=y[tids] if refs=='attack' else y
        keep=mask if refs=='attack' else held
        methods=s.heads(pair,a,b,states)
        hp=s.HERE/'stage06'/(pair+'_head.pt')
        assert core.sha(hp)==core.read(s.HERE/'stage06/CANDIDATES_BEFORE_EVALUATION.json')[pair]['head_sha256']
        methods['H6']=(False,torch.load(hp,map_location='cpu',weights_only=True))
        rows={}
        for name,(pre,h) in methods.items():
            mz=s.logits(mem['pre' if pre else 'post'],h);nz=s.logits((before if pre else after)[refs],h)
            old=s.membership(mz,my,nz,ny);compare(old,oldresult['cases'][pair]['variants'][name])
            corrected=s.membership(mz,my,nz[keep],ny[keep])
            result['independent_AUC_checks']+=independent(corrected,mz,my,nz[keep],ny[keep])
            rows[name]={'old_all_reference':old,'corrected_heldout_reference':corrected}
        baseline=rows['native_post']['corrected_heldout_reference']
        for name,row in rows.items():row.update(gate(row['corrected_heldout_reference'],baseline))
        result['original_interventions'][pair]=rows
        core.write('RESULT.json',result)
    baseline=result['original_interventions']['benign_big19336']['native_post']['corrected_heldout_reference']
    for stage,suffix in [('stage08','_logits.pt'),('stage09','_evaluation.pt')]:
        folder=s.HERE/stage;receipt=core.read(folder/'COMPLETED.json');old=core.read(folder/'RESULT.json')
        assert core.sha(folder/'RESULT.json')==receipt['result_sha256'];rows={}
        for arm in ['clean_only','query_transfer']:
            data=pinned_torch(folder/('private_'+arm+suffix),receipt)
            mz=data['member_logits'];my=data['member_labels'].long();nz=data['clean_logits']
            assert torch.equal(my,pinned_torch(oldroot/'private_benign_big19336_member_features.pt',oldreceipt)['labels'])
            all_audit=s.membership(mz,my,nz,y);compare(all_audit,old['cases'][arm]['deletion_audit'])
            corrected=s.membership(mz,my,nz[held],y[held]);n=independent(corrected,mz,my,nz[held],y[held])
            result['independent_AUC_checks']+=n
            row={'old_all_reference':all_audit,'corrected_heldout_reference':corrected,**gate(corrected,baseline)}
            prior=old['cases'][arm]
            drop=prior.get('overall_drop_pp',prior.get('overall_CA_drop_pp'));worst=prior.get('worst_class_drop_pp',prior.get('worst_class_CA_drop_pp'))
            row['unchanged_CA_necessary_gate']=drop<=.5+1e-10 and worst<=2+1e-10
            row['corrected_necessary_gate']=row['necessary_deletion_gate'] and row['unchanged_CA_necessary_gate']
            rows[arm]=row
        result['students'][stage]=rows;core.write('RESULT.json',result)
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    result.update(state='completed',corrected_H9_eligible_arms=[a for a,v in result['students']['stage09'].items() if v['corrected_necessary_gate']],
                  finished_unix=time.time(),formal_deletion_certificate=False)
    core.write('RESULT.json',result);core.write('COMPLETED.json',{'result_sha256':core.sha(OUT/'RESULT.json'),
                'files':{p.name:core.sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='COMPLETED.json'}})
    print(json.dumps({'state':'completed','independent_AUC_checks':result['independent_AUC_checks'],
        'heldout_trigger_n':result['nonmember_trigger_n'],'H9_eligible':result['corrected_H9_eligible_arms'],
        'H9_corrected_adv':{a:v['corrected_heldout_reference']['scores']['true_label_logprob']['advantage'] for a,v in result['students']['stage09'].items()}}),flush=True)


if __name__=='__main__':main()
