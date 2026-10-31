"""Evaluator-only target suppression AND paired-original classification quality."""
import torch


def metrics(z,truth,mask,clean_prediction,target):
    assert len(z)==len(truth)==len(mask)==len(clean_prediction) and z.ndim==2
    assert torch.isfinite(z).all() and bool(mask.any())
    pred=z.argmax(1);classes=z.shape[1]
    ref=100*float((clean_prediction[mask]==truth[mask]).double().mean())
    ca=100*float((pred[mask]==truth[mask]).double().mean())
    per=[100*float((pred[mask][truth[mask]==c]==c).double().mean()) if bool((truth[mask]==c).any()) else None for c in range(classes)]
    base=[100*float((clean_prediction[mask][truth[mask]==c]==c).double().mean()) if bool((truth[mask]==c).any()) else None for c in range(classes)]
    worst=max(a-b for a,b in zip(base,per) if a is not None)
    return {'target_n':int((pred==target).sum()),'n':len(pred),'ASR_pct':100*float((pred==target).double().mean()),
        'heldout_target_n':int((pred[mask]==target).sum()),'heldout_n':int(mask.sum()),
        'heldout_ASR_pct':100*float((pred[mask]==target).double().mean()),
        'original_label_correct_n':int((pred==truth).sum()),'original_label_CA_pct':100*float((pred==truth).double().mean()),
        'heldout_original_label_correct_n':int((pred[mask]==truth[mask]).sum()),'heldout_original_label_CA_pct':ca,
        'heldout_original_class_CA_pct':per,'original_label_drop_from_paired_clean_pp':ref-ca,
        'worst_original_class_drop_from_paired_clean_pp':worst,
        'original_label_robustness_gate':ref-ca<=2+1e-10 and worst<=5+1e-10}
