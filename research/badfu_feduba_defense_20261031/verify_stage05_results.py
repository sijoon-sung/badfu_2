"""Independent NumPy SVD and all-pairs/tie-rank verification of saved results."""
import json
import numpy as np
import torch
import stage05_common as s


def independent_auc(m,n):
    # Sort both populations together; average ranks are computed from tie groups.
    joined=np.concatenate([m,n]);order=np.argsort(joined,kind='stable')
    values=joined[order];member=order<len(m)
    starts=np.r_[0,1+np.flatnonzero(values[1:]!=values[:-1])];ends=np.r_[starts[1:],len(values)]
    rank_sum=0.
    for left,right in zip(starts,ends):rank_sum+=member[left:right].sum()*(left+1+right)/2
    return float((rank_sum-len(m)*(len(m)+1)/2)/(len(m)*len(n)))


def verify_fit(states):
    ids=np.asarray(s.core.read(s.HERE/'PROXY_SPLIT.json')['fit_ids'])
    receipt=s.core.read(s.OUT/'FIT_COMPLETED.json');rows={}
    assert s.core.sha(s.OUT/'FIT_RESULT.json')==receipt['result_sha256']
    for pair,a,b in s.core.PAIRS:
        x=s.original_cache('features_'+a+'.pt').double().numpy()[ids]
        y=s.original_cache('features_'+b+'.pt').double().numpy()[ids]
        mx=x.mean(0);my=y.mean(0);xc=x-mx;yc=y-my;d=x.shape[1]
        lam=.01*((xc*xc).sum()+(yc*yc).sum())/(2*d)
        u,_,vh=np.linalg.svd(xc.T@yc+lam*np.eye(d),full_matrices=False);rot=u@vh
        wp=states[b]['model.fc.weight'].double().numpy();bp=states[b]['model.fc.bias'].double().numpy()
        w=(rot@wp.T).T.astype(np.float32);bias=(bp+my@wp.T-mx@rot@wp.T).astype(np.float32)
        saved=torch.load(s.OUT/(pair+'_aligned_head.pt'),weights_only=True)
        error=max(float(np.max(np.abs(w-saved['weight'].numpy()))),float(np.max(np.abs(bias-saved['bias'].numpy()))))
        assert error<2e-6,(pair,error)
        f=s.feature_cache(pair,True);reference=s.core.read(s.OUT/'FIT_RESULT.json')['cases'][pair]['H5']
        pred=(f['attack'].double().numpy()@w.astype(np.float64).T+bias.astype(np.float64)).argmax(1)
        assert int((pred==0).sum())==reference['attack_target_n']
        labels=s.original_cache('clean_predictions.pt')['labels'].numpy()
        held=s.core.read(s.HERE/'PROXY_SPLIT.json')['heldout_ids']
        pc=(f['clean'].double().numpy()@w.astype(np.float64).T+bias.astype(np.float64)).argmax(1)
        assert int((pc[held]==labels[held]).sum())==reference['clean']['correct']
        rows[pair]={'numpy_SVD_head_max_error':error,'clean_correct':reference['clean']['correct'],
                    'attack_target_n':reference['attack_target_n'],'integer_counts_match':True}
    return rows


def verify_delete(states):
    result=s.core.read(s.OUT/'DELETE_RESULT.json');receipt=s.core.read(s.OUT/'DELETE_COMPLETED.json')
    assert s.core.sha(s.OUT/'DELETE_RESULT.json')==receipt['result_sha256']
    # Recover nonmember original labels without opening images or fresh inference.
    info=s.core.read(s.HERE/'STAGE03_INPUTS.json')
    assert s.core.sha(info['clean_path'])==info['clean_path_sha256']
    raw=torch.load(info['clean_path'],weights_only=True);y=raw['test_y'].long().numpy()
    assert s.core.sha(info['record_path'])==info['record_path_sha256']
    record=torch.load(info['record_path'],weights_only=False)
    tidx=[int(i) for i in record['bd_test']['bd_data_container']['data_dict']]
    nchecks=0;max_error=0.
    for pair,a,b in s.core.PAIRS:
        path=s.OUT/('private_'+pair+'_member_features.pt')
        assert s.core.sha(path)==receipt['files'][path.name]
        mem=torch.load(path,weights_only=True);my=mem['labels'].numpy()
        ny=y[tidx] if pair.startswith('attack') else y
        before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
        for name,(pre,h) in s.heads(pair,a,b,states).items():
            w=h['weight'].double().numpy();bias=h['bias'].double().numpy()
            m=mem['pre' if pre else 'post'].double().numpy()@w.T+bias
            n=(before if pre else after)['attack' if pair.startswith('attack') else 'clean'].double().numpy()@w.T+bias
            def logsoft(z):
                v=z-z.max(1,keepdims=True);return v-np.log(np.exp(v).sum(1,keepdims=True))
            ml=logsoft(m);nl=logsoft(n)
            for score,ms,ns in [('true_label_logprob',ml[np.arange(len(my)),my],nl[np.arange(len(ny)),ny]),
                                ('max_logprob',ml.max(1),nl.max(1))]:
                rows=result['cases'][pair]['variants'][name]['scores'][score]['class_rows']
                for c in range(10):
                    if not (my==c).any():continue
                    auc=independent_auc(ms[my==c],ns[ny==c]);err=abs(auc-rows[c]['AUC'])
                    max_error=max(max_error,err);assert err<1e-10,(pair,name,score,c,err)
                    nchecks+=1
    return {'class_AUC_checks':nchecks,'max_error':max_error,'fresh_forward':False}


if __name__=='__main__':
    s.verify_sources();selected,sealed,states=s.snapshot()
    report={'fit':verify_fit(states),'delete':verify_delete(states) if (s.OUT/'DELETE_COMPLETED.json').exists() else 'pending'}
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    name='INDEPENDENT_FULL_VERIFICATION.json' if isinstance(report['delete'],dict) else 'INDEPENDENT_FIT_VERIFICATION.json'
    s.core.write(name,report);print(json.dumps(report),flush=True)
