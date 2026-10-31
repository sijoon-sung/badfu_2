"""Once-only deleted-sample feature audit; do not run while FedUBA trains."""
import hashlib
import json
import os
import time
import traceback

import numpy as np
from PIL import Image
import torch
import stage05_common as s
core=s.core


def data():
    info=core.read(s.HERE/'STAGE03_INPUTS.json')
    extra=core.read(s.HERE/'STAGE05_INPUTS.json')
    for entry in extra.values():assert core.sha(entry['path'])==entry['sha256']
    assert core.sha(info['record_path'])==info['record_path_sha256']
    assert core.sha(info['clean_path'])==info['clean_path_sha256']
    train=torch.load(extra['train']['path'],map_location='cpu',weights_only=True)
    clean=torch.load(info['clean_path'],map_location='cpu',weights_only=True)
    split=core.read(extra['split']['path']);alignment=core.read(extra['alignment']['path'])
    record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    cover=[];cidx=[];cy=[]
    for idx,entry in record['bd_train']['cv_data_container']['data_dict'].items():
        parts=str(entry['path']).replace('\\','/').split('/')
        rel='/'.join(parts[parts.index('cv_train_dataset'):])
        path=s.Path(info['record_root'])/rel
        assert core.sha(path)==alignment['plain_cover_file_sha256'][rel]
        cover.append(np.asarray(Image.open(path).convert('RGB')).copy())
        cidx.append(int(idx));cy.append(int(entry['other_info'][0]))
    assert cidx==split['cover_cifar10_indices'] and len(cidx)==850
    cy=torch.tensor(cy);assert torch.equal(cy,train['train_y'][cidx].long())
    tidx=[int(i) for i in record['bd_test']['bd_data_container']['data_dict']]
    assert len(tidx)==9000 and sorted(tidx)==torch.where(clean['test_y']!=0)[0].tolist()
    big=split['clean_cifar10_indices'][4]
    sets={'benign_big19336':(train['train_x'][big],train['train_y'][big].long(),big,'big_complete',clean['test_y'].long()),
          'benign_same850':(train['train_x'][cidx],cy,cidx,'same_complete',clean['test_y'].long()),
          'attack_cover850':(torch.from_numpy(np.stack(cover)),cy,cidx,'attack_complete',clean['test_y'][tidx].long())}
    return sets,extra


def main():
    s.OUT.mkdir(exist_ok=True);s.verify_sources()
    fitreceipt=core.read(s.OUT/'FIT_COMPLETED.json')
    assert core.sha(s.OUT/'FIT_RESULT.json')==fitreceipt['result_sha256']
    assert core.sha(s.OUT/'CANDIDATES_BEFORE_EVALUATION.json')==fitreceipt['files']['CANDIDATES_BEFORE_EVALUATION.json']
    # A failed entry guard does not consume the once-only inference stage.
    core.resource_guard()
    with (s.OUT/'DELETE_STARTED.json').open('x',encoding='utf8') as f:
        json.dump({'pid':os.getpid(),'time':time.time()},f)
    selected,sealed,states=s.snapshot()
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.cuda.set_per_process_memory_fraction(.25)
    datasets,extra=data()
    model=sealed.model_class(selected['source_root'])().cuda().eval()
    result={'state':'running','cases':{},'evaluator':'class_conditional_deleted_member_rank_v1',
            'fit_receipt_sha256':core.sha(s.OUT/'FIT_COMPLETED.json'),'formal_deletion_certificate':False,
            'privacy_inputs_publicly_exported':False}
    for pair,a,b in core.PAIRS:
        raw,y,ids,complete_key,nonmember_y=datasets[pair]
        complete=core.read(extra[complete_key]['path'])
        removed_hash=hashlib.sha256(np.asarray(sorted(ids),dtype=np.int64).tobytes()).hexdigest()
        assert removed_hash==complete['audit']['removed_indices_sha256']
        assert len(ids)==complete['audit']['removed_n']
        assert complete['checkpoint_sha256']==selected['server_inputs'][b]['sha256']
        member_features={}
        for use_pre,role in [(True,a),(False,b)]:
            model.load_state_dict(states[role],strict=True)
            core.CURRENT_VARIANT=pair+'_deleted_'+role
            member_features[use_pre]=core.extract(model,raw)
            assert core.tensor_digest(model.cpu().state_dict())==core.tensor_digest(states[role])
            model.cuda()
        private=s.OUT/('private_'+pair+'_member_features.pt')
        torch.save({'pre':member_features[True],'post':member_features[False],'labels':y},private)
        before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
        key='attack' if pair.startswith('attack') else 'clean'
        reports={}
        for name,(use_pre,h) in s.heads(pair,a,b,states).items():
            nonmember=(before if use_pre else after)[key]
            reports[name]=s.membership(s.logits(member_features[use_pre],h),y,s.logits(nonmember,h),nonmember_y)
        baseline=reports['native_post']
        for name,row in reports.items():
            gaps={score:{measure:row['scores'][score][measure]-baseline['scores'][score][measure]
                    for measure in ['advantage','weighted_class_advantage']} for score in baseline['scores']}
            gap_increase=abs(row['weighted_accuracy_gap'])-abs(baseline['weighted_accuracy_gap'])
            row['increase_over_post']=gaps;row['absolute_accuracy_gap_increase']=gap_increase
            row['necessary_deletion_audit_gate']=all(v<=.04+1e-12 for vals in gaps.values() for v in vals.values()) and gap_increase<=.02+1e-12
        result['cases'][pair]={'removed_n':len(ids),'removed_hash_matches_original_training':True,
                              'private_features_sha256':core.sha(private),'variants':reports}
        core.write('DELETE_RESULT.json',result)
        print(json.dumps({'pair':pair,'H5_deletion_gate':reports['H5']['necessary_deletion_audit_gate']}),flush=True)
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    fit=core.read(s.OUT/'FIT_RESULT.json')
    result['H5_combined_necessary_gates']=all(fit['cases'][p]['H5']['CA_necessary_gate'] and
        result['cases'][p]['variants']['H5']['necessary_deletion_audit_gate'] for p,_,_ in core.PAIRS) and fit['cases']['attack_cover850']['H5']['ASR_pct']<=10
    result.update(state='completed',finished_unix=time.time(),gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated())
    core.write('DELETE_RESULT.json',result)
    core.write('DELETE_COMPLETED.json',{'result_sha256':core.sha(s.OUT/'DELETE_RESULT.json'),
        'files':{p.name:core.sha(p) for p in s.OUT.iterdir() if p.is_file() and p.name!='DELETE_COMPLETED.json'}})
    print('STAGE05_DELETE_COMPLETED',flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        s.OUT.mkdir(exist_ok=True);core.write('DELETE_FAILURE.json',{'traceback':traceback.format_exc()});raise
