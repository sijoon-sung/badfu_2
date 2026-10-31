"""Read-only source/state/optimizer and independent metric audit of the bounded pilot."""
import json
import numpy as np
import torch
import stage05_common as s
from verify_stage05_results import independent_auc


def finite_tree(value):
    if isinstance(value,torch.Tensor):assert torch.isfinite(value).all()
    elif isinstance(value,dict):
        for v in value.values():finite_tree(v)
    elif isinstance(value,(list,tuple)):
        for v in value:finite_tree(v)


def main():
    s.verify_sources();selected,sealed,states=s.snapshot();out=s.HERE/'stage08'
    frozen=s.core.read(s.HERE/'STAGE08_FREEZE.json')
    for name,digest in frozen['files'].items():assert s.core.sha(s.HERE/name)==digest,name
    receipt=s.core.read(out/'COMPLETED.json')
    for name,digest in receipt['files'].items():assert s.core.sha(out/name)==digest,name
    result=s.core.read(out/'RESULT.json');assert s.core.sha(out/'RESULT.json')==receipt['result_sha256']
    assert result['state']=='completed' and result['CUDA_initialized'] is False
    candidates=s.core.read(out/'MODELS_BEFORE_PRIVATE_EVALUATION.json')
    query_receipt=s.core.read(out/'QUERYBANK_BEFORE_TRAINING.json')
    assert s.core.sha(out/'private_querybank.pt')==query_receipt['sha256']
    bank=torch.load(out/'private_querybank.pt',map_location='cpu',weights_only=True)
    finite_tree(bank)
    assert bank['queries'].shape==(256,3,32,32)
    assert float(bank['queries'].min())>=0 and float(bank['queries'].max())<=1
    assert torch.allclose(bank['teacher_prob_T2'].sum(1),torch.ones(256),atol=2e-6)
    assert len(query_receipt['logs'])==32
    info=s.core.read(s.HERE/'STAGE03_INPUTS.json')
    assert s.core.sha(info['clean_path'])==info['clean_path_sha256']
    labels=torch.load(info['clean_path'],map_location='cpu',weights_only=True)['test_y'].numpy()
    old_receipt=s.core.read(s.HERE/'stage07_cpu_v2/COMPLETED.json')
    old_path=s.HERE/'stage07_cpu_v2/private_benign_big19336_member_features.pt'
    assert s.core.sha(old_path)==old_receipt['files'][old_path.name]
    member_labels=torch.load(old_path,map_location='cpu',weights_only=True)['labels'].numpy()
    held=np.array(s.core.read(s.HERE/'PROXY_SPLIT.json')['heldout_ids'])
    pre=s.feature_cache('benign_big19336',True)
    post=s.feature_cache('benign_big19336',False)
    a=s.logits(pre['clean'],s.head(states['clean_pre'])).argmax(1).numpy()
    b=s.logits(post['clean'],s.head(states['clean_big_post'])).argmax(1).numpy()
    baseline=s.core.read(s.HERE/'stage07_cpu_v2/RESULT.json')['cases']['benign_big19336']['variants']['native_post']
    report={'state':'passed','arms':{},'source_and_all_output_hashes':'passed','querybank_contract':'passed',
            'verifier_sha256':s.core.sha(__file__),'new_model_inference':False}
    for arm in ['clean_only','query_transfer']:
        entry=candidates[arm];assert s.core.sha(out/entry['path'])==entry['sha256']
        st=torch.load(out/entry['path'],map_location='cpu',weights_only=True);finite_tree(st)
        model=sealed.model_class(s.Path(selected['source_root']))()
        model.load_state_dict(st,strict=True)
        for k in st:
            if s.core.is_buffer(k):assert torch.equal(st[k],states['clean_big_post'][k]),k
        logs=[json.loads(line) for line in (out/(arm+'_steps.jsonl')).read_text(encoding='utf8').splitlines()]
        assert [r['step'] for r in logs]==list(range(1,101))
        assert all(np.isfinite([r['clean_loss'],r['query_loss'],r['seconds']]).all() for r in logs)
        opt=torch.load(out/(arm+'_optimizer_rng.pt'),map_location='cpu',weights_only=True);finite_tree(opt)
        assert len(opt['optimizer']['state'])==len(list(model.parameters()))
        assert all(float(v['step'])==100 for v in opt['optimizer']['state'].values())
        data=torch.load(out/('private_'+arm+'_logits.pt'),map_location='cpu',weights_only=True);finite_tree(data)
        assert np.array_equal(data['member_labels'].numpy(),member_labels)
        cz=data['clean_logits'];mz=data['member_logits'];pred=cz.argmax(1).numpy()
        saved=result['cases'][arm];clean=saved['clean']
        assert int((pred[held]==labels[held]).sum())==clean['correct']
        for c in range(10):
            v=float((pred[held][labels[held]==c]==c).mean()*100)
            assert abs(v-clean['class_CA_pct'][c])<1e-10
        benefit=(a[held]!=labels[held])&(b[held]==labels[held])
        assert int(benefit.sum())==clean['beneficial_n']
        assert int(((pred[held]==labels[held])&benefit).sum())==clean['beneficial_kept_n']
        ml=mz.log_softmax(1).numpy();nl=cz.log_softmax(1).numpy()
        weights=np.bincount(member_labels,minlength=10)/len(member_labels)
        scores={};checks=0
        for name,ms,ns in [('true_label_logprob',ml[np.arange(len(ml)),member_labels],nl[np.arange(len(nl)),labels]),
                           ('max_logprob',ml.max(1),nl.max(1))]:
            aucs=[]
            for c in range(10):
                auc=independent_auc(ms[member_labels==c],ns[labels==c])
                assert abs(auc-saved['deletion_audit']['scores'][name]['class_rows'][c]['AUC'])<1e-12
                aucs.append(auc);checks+=1
            wa=float(weights@np.asarray(aucs))
            scores[name]={'weighted_AUC':wa,'advantage':2*abs(wa-.5),
                          'weighted_class_advantage':float(weights@(2*np.abs(np.asarray(aucs)-.5)))}
            for key,value in scores[name].items():assert abs(value-saved['deletion_audit']['scores'][name][key])<1e-12
        mp=mz.argmax(1).numpy()
        gap=float(sum(weights[c]*((mp[member_labels==c]==c).mean()-(pred[labels==c]==c).mean()) for c in range(10)))
        assert abs(gap-saved['deletion_audit']['weighted_accuracy_gap'])<1e-12
        base_clean=s.core.metrics(s.logits(post['clean'],s.head(states['clean_big_post'])),torch.from_numpy(labels),
                    s.logits(pre['clean'],s.head(states['clean_pre'])),s.logits(post['clean'],s.head(states['clean_big_post'])),torch.from_numpy(held))
        overall=base_clean['CA_pct']-clean['CA_pct']
        worst=max(x-y for x,y in zip(base_clean['class_CA_pct'],clean['class_CA_pct']))
        privacy=all(scores[n][key]-baseline['scores'][n][key]<=.04+1e-12 for n in scores for key in ['advantage','weighted_class_advantage']) and abs(gap)-abs(baseline['weighted_accuracy_gap'])<=.02+1e-12
        passed=overall<=.5+1e-10 and worst<=2+1e-10 and privacy
        assert passed==saved['necessary_gate']
        report['arms'][arm]={'optimizer_steps':100,'independent_class_AUC_checks':checks,'gate_matches':True,
                            'necessary_gate':passed,'strict_prior_correction_fraction':clean['beneficial_kept_fraction']}
    sealed.verify(selected['source_root'],selected['checkpoint_guard']['manifest_sha256'])
    s.core.OUT=out;s.core.write('INDEPENDENT_VERIFICATION.json',report)
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
