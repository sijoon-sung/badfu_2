"""Observed wrong-class-collapse counterexample must never pass the new gate."""
import hashlib,json
from pathlib import Path
import torch
from attack_quality import metrics

torch.set_num_threads(2)
y=torch.arange(1,10).repeat_interleave(100);mask=torch.ones(len(y),dtype=torch.bool)
def logits(pred):return torch.nn.functional.one_hot(pred,10).float()*10
good=metrics(logits(y),y,mask,y,0)
collapse=metrics(logits(torch.full_like(y,5)),y,mask,y,0)
target=metrics(logits(torch.zeros_like(y)),y,mask,y,0)
localized=y.clone();localized[torch.where(y==7)[0][:10]]=5
local=metrics(logits(localized),y,mask,y,0)
assert good['original_label_robustness_gate'] and good['heldout_original_label_correct_n']==900
assert collapse['ASR_pct']==0 and collapse['heldout_original_label_correct_n']==100 and not collapse['original_label_robustness_gate']
assert target['ASR_pct']==100 and not target['original_label_robustness_gate']
assert local['original_label_drop_from_paired_clean_pp']<2 and local['worst_original_class_drop_from_paired_clean_pp']==10 and not local['original_label_robustness_gate']
assert not torch.cuda.is_initialized()
r=Path(__file__).resolve().parent
result={'state':'passed','synthetic_evaluator_fixture_only':True,'no_model_training_or_inference':True,
    'correct_classification_passes':True,'ASR_zero_wrong_class_collapse_rejected':True,
    'target_collapse_rejected':True,'small_overall_but_large_single_class_damage_rejected':True,
    'source_sha256':hashlib.sha256((r/'attack_quality.py').read_bytes()).hexdigest()}
with (r/'POST_ANCHOR_QUALITY_CONTRACT.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
