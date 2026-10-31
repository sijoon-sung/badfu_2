"""Source-bank transfer diagnostics and a strict convex-output repair lower bound."""
import hashlib,json,os,time,traceback
from pathlib import Path
import numpy as np
import torch
import stage05_common as s
from sourcepair_pilot import cpu_guard
core=s.core;ROOT=s.HERE/'post_anchor_run';OUT=s.HERE/'post_anchor_diagnosis'
ARMS=['teacher_query','post_anchor']


def pixel(v):return hashlib.sha256(v.contiguous().numpy().tobytes()).hexdigest()


def matrix(truth,pred,classes=10):
    m=np.zeros((classes,classes),dtype=np.int64)
    for t,p in zip(truth,pred):m[int(t),int(p)]+=1
    return m.tolist()


def main():
    OUT.mkdir(exist_ok=True);s.verify_sources()
    freeze=core.read(s.HERE/'POST_ANCHOR_DIAGNOSIS_FREEZE.json')
    for n,h in freeze['files'].items():assert core.sha(s.HERE/n)==h,n
    top=core.read(ROOT/'COMPLETED.json');summary=core.read(ROOT/'RESULT.json')
    assert top['result_sha256']==core.sha(ROOT/'RESULT.json')
    assert top['source_freeze_sha256']==core.sha(s.HERE/'POST_ANCHOR_FREEZE.json')
    audit=core.read(ROOT/'INDEPENDENT_VERIFICATION.json')
    assert audit['state']=='passed' and audit['scope']=='finished_pipeline' and audit['root_result_sha256']==core.sha(ROOT/'RESULT.json')
    assert audit['verifier_sha256']==core.sha(s.HERE/'verify_post_anchor.py')
    cpu=cpu_guard();assert not torch.cuda.is_initialized()
    with (OUT/'STARTED.json').open('x',encoding='utf8') as f:json.dump({'pid':os.getpid(),'time':time.time(),'CPU':cpu},f)
    selected,sealed,states=s.snapshot();info=core.read(s.HERE/'STAGE03_INPUTS.json')
    assert core.sha(info['clean_path'])==info['clean_path_sha256']
    data=torch.load(info['clean_path'],map_location='cpu',weights_only=True);labels=data['test_y'].numpy()
    split=core.read(s.HERE/'PROXY_SPLIT.json');held=np.asarray(split['heldout_ids'])
    public=data['test_x'][split['fit_ids']].permute(0,3,1,2).float().div(255).contiguous()
    lookup={pixel(v):i for i,v in enumerate(public)}
    assert core.sha(info['record_path'])==info['record_path_sha256']
    record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    tids=np.asarray([int(i) for i in record['bd_test']['bd_data_container']['data_dict']])
    mask=np.isin(tids,held);truth=labels[tids];assert int(mask.sum())==8542 and len(tids)==9000
    result={'state':'passed_saved_output_diagnosis','cases':{},'fresh_model_inference':False,'model_or_query_updates':False,
        'new_model_selected':False,'unique_cause_proved':False,'full_objective_achieved':False,
        'parent_result_sha256':core.sha(ROOT/'RESULT.json'),'parent_audit_sha256':core.sha(ROOT/'INDEPENDENT_VERIFICATION.json')}
    for pair in ['benign_big19336','attack_cover850']:
        folder=ROOT/pair;receipt=core.read(folder/'COMPLETED.json')
        for n,h in receipt['files'].items():assert core.sha(folder/n)==h,(pair,n)
        assert receipt['result_sha256']==core.sha(folder/'RESULT.json')
        dec=core.read(folder/'SELECTION_BEFORE_PRIVATE_EVALUATION.json');bm=core.read(folder/'BANK_BEFORE_TRAINING.json')
        bp=Path(bm['bank_path']);ip=Path(bm['initial_path'])
        assert core.sha(bp)==bm['bank_sha256'] and core.sha(ip)==bm['initial_sha256']
        bank=torch.load(bp,map_location='cpu',weights_only=True);initial=torch.load(ip,map_location='cpu',weights_only=True)
        src=bank['sources'].numpy();valid=bank['teacher_logits'].numpy().argmax(1)==src
        indices=np.asarray([lookup[pixel(v)] for v in initial['starts']]);rows={}
        if pair=='attack_cover850':native=s.logits(s.feature_cache(pair,False)['attack'],s.head(states['post'])).numpy()
        for arm in ARMS:
            diag=torch.load(folder/('private_'+arm+'_bank_diagnostic.pt'),map_location='cpu',weights_only=True)
            qpred=diag['query_logits'].numpy().argmax(1);tpred=bank['teacher_logits'].numpy().argmax(1)
            proxy=torch.load(folder/('private_'+arm+'_proxy.pt'),map_location='cpu',weights_only=True)
            raw_at=proxy['alphas'].index(1.) if 1. in proxy['alphas'] else 0
            selected_at=proxy['alphas'].index(dec['models'][arm]['alpha'])
            npred=proxy['teacher_logits'].numpy()[indices].argmax(1)
            rp=proxy['candidate_logits'][raw_at].numpy()[indices].argmax(1)
            sp=proxy['candidate_logits'][selected_at].numpy()[indices].argmax(1)
            assert np.array_equal(npred,src)
            row={'bank_valid_n':int(valid.sum()),'raw_bank_assigned_source_correct_n':int((qpred[valid]==src[valid]).sum()),
                'raw_bank_assigned_source_agreement_pct':100*float((qpred[valid]==src[valid]).mean()),
                'raw_full_bank_teacher_agreement_n':int((qpred==tpred).sum()),
                'raw_valid_bank_source_prediction_counts':matrix(src[valid],qpred[valid]),
                'original_anchor_n':len(indices),'raw_anchor_source_correct_n':int((rp==src).sum()),
                'selected_anchor_source_correct_n':int((sp==src).sum()),'alpha':dec['models'][arm]['alpha']}
            if pair=='attack_cover850':
                raw=torch.load(folder/('private_'+arm+'_raw_attack.pt'),map_location='cpu',weights_only=True)['attack_logits'].numpy()
                chosen=torch.load(folder/('private_'+arm+'_selected_attack.pt'),map_location='cpu',weights_only=True)['attack_logits'].numpy()
                rawpred=raw.argmax(1);chosenpred=chosen.argmax(1)
                # Strict margins: excluding target from the competitor maximum.
                nmargin=native[:,0]-native[:,1:].max(1);rmargin=raw[:,0]-raw[:,1:].max(1)
                unanimous=(nmargin>0)&(rmargin>0);lower=100*float(unanimous.mean());hlower=100*float(unanimous[mask].mean())
                rc=rawpred[mask]==truth[mask];sc=chosenpred[mask]==truth[mask]
                row['actual']={'raw_source_prediction_counts':matrix(truth[mask],rawpred[mask]),
                    'selected_source_prediction_counts':matrix(truth[mask],chosenpred[mask]),
                    'raw_source_correct_n':int(rc.sum()),'selected_source_correct_n':int(sc.sum()),
                    'raw_correct_selected_wrong_n':int((rc&~sc).sum()),'raw_wrong_selected_correct_n':int((~rc&sc).sum()),
                    'both_correct_n':int((rc&sc).sum()),'both_wrong_n':int((~rc&~sc).sum()),
                    'strict_shared_target_n':int(unanimous.sum()),'strict_shared_target_held_n':int(unanimous[mask].sum()),
                    'target_tie_or_boundary_n_native':int((nmargin==0).sum()),'target_tie_or_boundary_n_raw':int((rmargin==0).sum()),
                    'convex_logit_or_probability_blend_ASR_lower_bound_pct':lower,
                    'convex_blend_heldout_ASR_lower_bound_pct':hlower,
                    'park_this_output_blending_candidate':lower>10 or hlower>10}
            rows[arm]=row
        result['cases'][pair]=rows
    assert not torch.cuda.is_initialized();sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    with (OUT/'RESULT.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    with (OUT/'COMPLETED.json').open('x',encoding='utf8') as f:json.dump({'result_sha256':core.sha(OUT/'RESULT.json'),
        'source_freeze_sha256':core.sha(s.HERE/'POST_ANCHOR_DIAGNOSIS_FREEZE.json')},f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException:
        OUT.mkdir(exist_ok=True)
        with (OUT/'FAILURE.json').open('x',encoding='utf8') as f:json.dump({'traceback':traceback.format_exc()},f,indent=2);f.write('\n')
        raise
