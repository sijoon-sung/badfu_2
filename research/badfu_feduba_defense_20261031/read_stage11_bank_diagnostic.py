"""Summarize already-saved H11 float-bank logits; never changes selection."""
import hashlib,json
from pathlib import Path
import torch

ROOT=Path(__file__).resolve().parent/'stage11'/'benign_big19336'
torch.set_num_threads(2)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    # Selection is already fixed: this observation is not an algorithm input.
    declaration=ROOT/'SELECTION_BEFORE_PRIVATE_EVALUATION.json'
    meta=json.loads((ROOT/'QUERYBANKS_BEFORE_TRAINING.json').read_text())
    result={'state':'observed_saved_bank_diagnostic','fresh_model_inference':False,
            'case':'benign_big19336','selection_sha256':sha(declaration),
            'script_sha256':sha(__file__),'arms':{},'actual_attack_efficacy_evaluated':False}
    for arm in ['matched_kl','all_class_disjoint']:
        p=ROOT/('private_'+arm+'_querybank.pt');d=ROOT/('private_'+arm+'_bank_diagnostic.pt')
        assert sha(p)==meta[arm]['sha256']
        bank=torch.load(p,map_location='cpu',weights_only=True)
        z=torch.load(d,map_location='cpu',weights_only=True)['query_logits']
        assert z.shape==(240,10) and torch.isfinite(z).all()
        tp=bank['teacher_prob_T2'].argmax(1);pp=bank['post_logits'].argmax(1)
        pred=z.argmax(1);k=bank['requested_classes'];found=(pp==k)&(tp!=k)
        rows=[];teacherrows=[]
        for c in range(10):
            mask=k==c;discovered=mask&found;truth=tp==c
            rows.append({'requested_class':c,'n':int(mask.sum()),'teacher_agreement_n':int((mask&(pred==tp)).sum()),
                         'discovered_post_k_teacher_not_k_n':int(discovered.sum()),
                         'raw_student_still_k_on_discovered_n':int((discovered&(pred==k)).sum())})
            teacherrows.append({'teacher_predicted_class':c,'n':int(truth.sum()),
                                'raw_student_agreement_n':int((truth&(pred==tp)).sum())})
        result['arms'][arm]={'bank_sha256':sha(p),'saved_logit_sha256':sha(d),
            'raw_teacher_agreement_pct':100*float((pred==tp).double().mean()),
            'nativepost_teacher_agreement_pct':100*float((pp==tp).double().mean()),
            'raw_predicted_class_counts':torch.bincount(pred,minlength=10).tolist(),
            'per_requested_output':rows,'per_teacher_predicted_output':teacherrows}
    assert not torch.cuda.is_initialized() and sha(declaration)==result['selection_sha256']
    dest=ROOT/'BANK_DIAGNOSTIC_OBSERVATION.json'
    with dest.open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
