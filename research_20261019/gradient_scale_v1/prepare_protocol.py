"""Freeze thresholds using only the old 16 cases, before any new scores."""
from pathlib import Path
import hashlib
import json
import math
import shutil
import numpy as np

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
OLD=ROOT/'research_20261018/all_or_nothing'
SOURCE=ROOT/'research_20261019/patch_scale_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (OUT/'protocol.json').exists():
        assert (OUT/'initial_selfcheck_failure/protocol.json').exists()
        assert not list((OUT/'cells').glob('*/requests/*/prediction.json'))
    (OUT/'calibration').mkdir(exist_ok=True)
    for name in ('pure_layer4_result.json','orthogonal_fc_result.json'):
        shutil.copyfile(OLD/name,OUT/'calibration'/name)
    old=json.loads((OLD/'pure_layer4_result.json').read_text(encoding='utf-8'))['rows']
    fc={r['case']:r for r in json.loads((OLD/'orthogonal_fc_result.json').read_text(encoding='utf-8'))['rows']}
    archive=np.load(OLD/'pure_layer4_arrays.npz')
    np.savez_compressed(OUT/'calibration/selfcheck_fc.npz',**{r:archive['attack74/fc/'+r] for r in ('retained','forget')})
    values={}
    for row in old:
        case=row['case']
        for block,item in [('fc',row['fc']),('conv_all',row['conv'])]+[(r['layer'],r) for r in row['layers']]:
            for quantity in ('norm_ratio','orthogonal_ratio'):
                if block=='fc':
                    value=fc[case]['norm_ratio' if quantity=='norm_ratio' else 'residual_frobenius_over_forget']
                else:
                    value=item['ratio'] if quantity=='norm_ratio' else item['ratio']*math.sqrt(max(0.,1-item['cosine']**2))
                key={'fc':'fc','conv_all':'conv'}.get(block,block)+('_norm' if quantity=='norm_ratio' else '_residual')
                record=values.setdefault(key,dict(block=block,quantity=quantity,attacks=[],controls=[]))
                record['attacks' if case.startswith('attack') else 'controls'].append(value)
    thresholds={}
    for key,item in values.items():
        amin,cmax=min(item['attacks']),max(item['controls'])
        assert amin>cmax
        thresholds[key]=dict(block=item['block'],quantity=item['quantity'],
            threshold=(amin+cmax)/2,calibration_attack_range=[amin,max(item['attacks'])],
            calibration_control_range=[min(item['controls']),cmax],direction='>')
    source=json.loads((SOURCE/'protocol.json').read_text(encoding='utf-8'))
    remote='C:/Users/DISLAB/Documents/antigravity/dazzling-lovelace'
    protocol=dict(name='Fixed no-probe-patch one-point gradient comparison',version='gradient_scale_v1',
        created_date_kst='2026-10-19',source_experiment=remote+'/research_20261019/patch_scale_v1',
        source_protocol_sha256=sha(SOURCE/'protocol.json'),
        model_helper_sha256=sha(SOURCE/'sources/reference/train_factorial.py'),
        data_root=source['data_root'],cell_order=source['cell_order'],planned_requests=210,
        requests=dict(attack_delete_cover=dict(pre_phase='badfu_pre',future_phase='danger_future'),
            equal_size_safe=dict(pre_phase='badfu_pre',future_phase='safe_future'),
            delete_poison=dict(pre_phase='badfu_pre',future_phase='cover_only'),
            delete_both=dict(pre_phase='badfu_pre',future_phase='base_future'),
            benign_class_prior=dict(pre_phase='prior_pre',future_phase='prior_future'),
            label_noise=dict(pre_phase='noise_pre',future_phase='noise_future'),
            normal_cover=dict(pre_phase='cover_only',future_phase='base_future')),
        primary_metrics=['fc_norm','fc_residual','conv_norm','conv_residual'],thresholds=thresholds,
        threshold_rule='Midpoint of old 16-case control maximum and attack minimum; fixed before any new gradient scores. Not fitted to new outcomes.',
        virtual_learning_rate=.01,objective='Full-subset mean CE at the same original checkpoint; both branches descend their own CE.',
        optimizer_steps=0,device='CPU',threads=2,microbatch_size=64,BN='eval/frozen',
        additional_clean_reference_images=0,KL=0,clipping=False,momentum=False,weight_decay=0,
        detector_patch_probes=0,detector_input_optimization=False,
        original_training_records='Reconstructed from the saved experiment splits; original poisoned/suppression patterns remain part of private records. Pattern and target are not arguments of the scoring function.',
        fc_matrix='10x513 weight and bias',conv_blocks='Same five layer4 Conv tensors as old experiment, excluding BN affine parameters.',
        conv_all='Joint Frobenius product over all five tensors; one projection coefficient for conv_residual.',
        undefined_denominator='Exactly zero B yields undefined, never safe zero. Store absolute norms for small-denominator inspection.',
        comparison='Pair with the same checkpoint hash, R/F record counts and label histograms before joining actual ASR and original patch decisions.',
        retrospective_source_note='Some source future models and their ASRs existed and were inspected before this experiment. Record future existence for every new gradient score; do not claim all decisions are prospective.',
        statistics='Ten seed clusters, not 210 independent training seeds. All failed/missing/undefined cases retained separately.',
        self_check_source=remote+'/research_20261018/fl_information/fedavg_confirm74/seed_74',
        self_check='CPU recomputation of old attack74; checkpoint/split hashes, FC arrays and FC/Conv scalar metrics checked against old GPU reference (relative tolerance .005). CPU microbatch 64 versus 128 invariance checked with relative tolerance .0001. Initial .001 cross-device tolerance failure (maximum .003052 error) preserved before scoring any new request.',
        runtime='Read-only follower of the source experiment. CPU only; saves gradients and decisions in this separate folder; waits for future source models.',
        source_hashes={str(p.relative_to(OUT)).replace('\\','/'):sha(p) for p in
                       sorted(list((OUT/'sources').glob('*.py'))+list((OUT/'calibration').glob('*'))+[Path(__file__)])})
    (OUT/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    rng=np.random.default_rng(20261019)
    errors=[]
    for _ in range(20):
        a,b=rng.normal(size=(10,513)),rng.normal(size=(10,513))
        f2=np.sum(b*b);r=a-np.sum(a*b)/f2*b
        q=np.linalg.norm(a)/np.linalg.norm(b)
        cosine=np.sum(a*b)/(np.linalg.norm(a)*np.linalg.norm(b))
        errors.append(abs(np.linalg.norm(r)/np.linalg.norm(b)-q*math.sqrt(1-cosine*cosine)))
        assert abs(np.sum(r*b))/(np.linalg.norm(r)*np.linalg.norm(b))<1e-12
    prob=1/(1+math.exp(-2))
    label_gradient=np.array([prob-1,1-prob])
    a=np.outer(label_gradient,[0.,10.,1.]);b=np.outer(label_gradient,[1.,0.,1.])
    residual=a-np.sum(a*b)/np.sum(b*b)*b
    counter=float(np.linalg.norm(residual)/np.linalg.norm(b))
    assert abs(counter-math.sqrt(50.25))<1e-12
    math_report=dict(identity='s=q*sqrt(1-cos(A,B)^2); residual orthogonal to B; 0<=s<=q',
        random_identity_max_absolute_error=max(errors),
        benign_counterexample=dict(both_labels=0,both_predictions=0,probability=prob,
            retained_augmented_feature=[0,10,1],forget_augmented_feature=[1,0,1],
            norm_ratio=float(np.linalg.norm(a)/np.linalg.norm(b)),orthogonal_ratio=counter),
        conclusion='Valid update statistics; neither score alone is a mathematical certificate of backdoor presence or complete Non-IID removal.')
    (OUT/'math_check.json').write_text(json.dumps(math_report,indent=2),encoding='utf-8')
    print(json.dumps({'protocol_sha256':sha(OUT/'protocol.json'),'primary_thresholds':{k:thresholds[k]['threshold'] for k in protocol['primary_metrics']},'math_check':math_report},indent=2))


if __name__=='__main__':main()
