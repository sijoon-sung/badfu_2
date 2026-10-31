"""Independently recompute all saved member-audit AUCs using tie ranks."""
import json
import numpy as np
import torch
import stage05_common as s
from verify_stage05_results import independent_auc


def main():
    s.verify_sources();selected,sealed,states=s.snapshot()
    out=s.HERE/'stage07_cpu_v2';receipt=s.core.read(out/'COMPLETED.json')
    assert s.core.sha(out/'RESULT.json')==receipt['result_sha256']
    result=s.core.read(out/'RESULT.json')
    info=s.core.read(s.HERE/'STAGE03_INPUTS.json')
    assert s.core.sha(info['clean_path'])==info['clean_path_sha256']
    raw=torch.load(info['clean_path'],map_location='cpu',weights_only=True);labels=raw['test_y'].numpy()
    assert s.core.sha(info['record_path'])==info['record_path_sha256']
    record=torch.load(info['record_path'],map_location='cpu',weights_only=False)
    tidx=[int(i) for i in record['bd_test']['bd_data_container']['data_dict']]
    nchecks=0;max_error=0.;max_numpy_error=0.;max_ambiguous_bound=0.;case_reports={}
    for pair,a,b in s.core.PAIRS:
        p=out/('private_'+pair+'_member_features.pt');assert s.core.sha(p)==receipt['files'][p.name]
        members=torch.load(p,map_location='cpu',weights_only=True);my=members['labels'].numpy()
        ny=labels[tidx] if pair.startswith('attack') else labels
        before=s.feature_cache(pair,True);after=s.feature_cache(pair,False)
        methods=s.heads(pair,a,b,states)
        hp=s.HERE/'stage06'/(pair+'_head.pt')
        assert s.core.sha(hp)==s.core.read(s.HERE/'stage06/CANDIDATES_BEFORE_EVALUATION.json')[pair]['head_sha256']
        methods['H6']=(False,torch.load(hp,map_location='cpu',weights_only=True))
        computed={}
        for name,(pre,h) in methods.items():
            w=h['weight'].double().numpy();bias=h['bias'].double().numpy()
            m=members['pre' if pre else 'post'].double().numpy()@w.T+bias
            nonmember=(before if pre else after)['attack' if pair.startswith('attack') else 'clean']
            n=nonmember.double().numpy()@w.T+bias
            def logsoft(z):
                v=z-z.max(1,keepdims=True);return v-np.log(np.exp(v).sum(1,keepdims=True))
            ml=logsoft(m);nl=logsoft(n);report=result['cases'][pair]['variants'][name]
            tm=s.logits(members['pre' if pre else 'post'],h).log_softmax(1).numpy()
            tn=s.logits(nonmember,h).log_softmax(1).numpy()
            scored={};weights=np.bincount(my,minlength=10)/len(my)
            for score,ms,ns in [('true_label_logprob',ml[np.arange(len(my)),my],nl[np.arange(len(ny)),ny]),
                                ('max_logprob',ml.max(1),nl.max(1))]:
                aucs=[]
                for c in range(10):
                    if (my==c).any():
                        exact_m=(tm[np.arange(len(my)),my] if score=='true_label_logprob' else tm.max(1))[my==c]
                        exact_n=(tn[np.arange(len(ny)),ny] if score=='true_label_logprob' else tn.max(1))[ny==c]
                        auc=independent_auc(exact_m,exact_n)
                        numpy_auc=independent_auc(ms[my==c],ns[ny==c])
                        eps=float(np.max(np.abs(ms[my==c]-exact_m))+np.max(np.abs(ns[ny==c]-exact_n)))
                        sorted_n=np.sort(exact_n)
                        near=np.searchsorted(sorted_n,exact_m+eps,side='right')-np.searchsorted(sorted_n,exact_m-eps,side='left')
                        bound=float(near.sum()/(len(exact_m)*len(exact_n)))
                        drift=abs(numpy_auc-auc)
                        assert drift<=bound+1e-12,(pair,name,score,c,drift,bound)
                        max_numpy_error=max(max_numpy_error,drift);max_ambiguous_bound=max(max_ambiguous_bound,bound)
                    else:auc=.5
                    error=abs(auc-report['scores'][score]['class_rows'][c]['AUC'])
                    max_error=max(max_error,error);assert error<1e-10,(pair,name,score,c,error)
                    aucs.append(auc);nchecks+=1
                weighted=float(weights@np.asarray(aucs))
                scored[score]={'weighted_AUC':weighted,'advantage':2*abs(weighted-.5),
                               'weighted_class_advantage':float(weights@(2*np.abs(np.asarray(aucs)-.5)))}
                for key,value in scored[score].items():assert abs(value-report['scores'][score][key])<1e-10
            mp=m.argmax(1);npred=n.argmax(1)
            gap=sum(weights[c]*((mp[my==c]==c).mean()-(npred[ny==c]==c).mean()) for c in range(10) if (my==c).any())
            assert abs(gap-report['weighted_accuracy_gap'])<1e-12
            computed[name]={'scores':scored,'weighted_accuracy_gap':float(gap)}
        case_reports[pair]=computed
    s.core.OUT=out
    report={'state':'passed','independent_class_AUC_checks':nchecks,'max_AUC_error':max_error,'max_Numpy_score_pipeline_AUC_drift':max_numpy_error,
            'max_measured_near_tie_bound':max_ambiguous_bound,'all_Numpy_drifts_within_measured_ambiguous_pair_bounds':True,
            'all_aggregate_advantages_and_accuracy_gaps_match':True,'new_inference':False,
            'verifier_sha256':s.core.sha(__file__),'cases':case_reports}
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    s.core.write('INDEPENDENT_VERIFICATION_V2.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}),flush=True)


if __name__=='__main__':main()
