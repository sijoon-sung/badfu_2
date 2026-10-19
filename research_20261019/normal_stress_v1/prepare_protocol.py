from pathlib import Path
import ast
import hashlib
import json
import numpy as np

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
SOURCE=ROOT/'research_20261019/patch_scale_v1'
GRADIENT=ROOT/'research_20261019/gradient_scale_v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (OUT/'protocol.json').exists(),'Refusing to replace frozen protocol'
    original=json.loads((GRADIENT/'protocol.json').read_text(encoding='utf-8'))
    snapshot=json.loads((GRADIENT/'summary_remote.json').read_text(encoding='utf-8'))
    (OUT/'original_benchmark_at_start.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
    source_code=(OUT/'sources/normal_stress.py').read_text(encoding='utf-8')
    tree=ast.parse(source_code)
    selection_code=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('quotas','select')],type_ignores=[])
    namespace={'np':np};exec(compile(selection_code,'selection_self_check','exec'),namespace)
    rng=np.random.default_rng(20261019);checks=0
    modes=['stratified_random','class_focused','matched_easy','matched_hard']
    for dominant in (.2,.7,.9):
        for owner in (0,2,4):
            counts=np.full(10,int((1200-1200*dominant)/8))
            counts[2*owner:2*owner+2]=int(600*dominant)
            labels=np.repeat(np.arange(10),counts)
            assert len(labels)==1200
            losses=rng.lognormal(size=1200)
            for count in (120,360,720):
                masks={mode:namespace['select'](labels,losses,count,mode,1001+owner) for mode in modes}
                for mask in masks.values():
                    assert mask.sum()==count and (~mask).sum()==1200-count
                    checks+=1
                for mode in ('matched_easy','matched_hard'):
                    assert np.array_equal(np.bincount(labels[masks[mode]],minlength=10),np.bincount(labels[masks['stratified_random']],minlength=10))
                assert losses[masks['matched_easy']].mean()<=losses[masks['stratified_random']].mean()+1e-12
                assert losses[masks['stratified_random']].mean()<=losses[masks['matched_hard']].mean()+1e-12
    (OUT/'selection_self_check.json').write_text(json.dumps(dict(passed=True,partition_checks=checks,
        label_quotas_matched_for_random_easy_hard=True,easy_random_hard_loss_order_verified=True,
        training_or_new_model_scoring=False),indent=2),encoding='utf-8')
    requests=[dict(name=f'{mode}_n{count}',mode=mode,forget_count=count) for count in (120,360,720) for mode in modes]
    remote='C:/Users/DISLAB/Documents/antigravity/dazzling-lovelace/research_20261019'
    protocol=dict(name='Additional correct-label Non-IID deletion stress test',version='normal_stress_v1',created_date_kst='2026-10-19',
        source_experiment=remote+'/patch_scale_v1',gradient_experiment=remote+'/gradient_scale_v1',
        source_protocol_sha256=sha(SOURCE/'protocol.json'),gradient_protocol_sha256=sha(GRADIENT/'protocol.json'),
        gradient_scorer_sha256=sha(GRADIENT/'sources/gradient_experiment.py'),
        model_helper_sha256=sha(SOURCE/'sources/reference/train_factorial.py'),
        data_root=original['data_root'],cell_order=original['cell_order'],
        planned_normal_requests=360,original_requests=210,planned_combined_requests=570,
        source_model='base_future: FedAvg trained exclusively on correctly labeled unmodified B records from all five clients.',
        client_selection='(seed-1001) modulo 5; each of five clients used for two of the ten seeds; same client across three skew levels.',
        source_client_records=1200,forget_counts=[120,360,720],forget_fractions=[.1,.3,.6],modes=modes,requests=requests,
        strata='Random, easy and hard deletions have identical class counts, using largest-remainder proportional quotas. Easy/hard ranking uses current clean-model CE within each class.',
        class_focused='Take classes by descending client label frequency, ties by class index; uniform random order within each class.',
        input_policy='Only source base/client image IDs and true CIFAR labels. Never reads poison, suppression, trigger, anchor, dev, validation or test image tensors.',
        virtual_learning_rate=original['virtual_learning_rate'],thresholds=original['thresholds'],primary_metrics=original['primary_metrics'],
        threshold_rule='Exact unchanged thresholds of gradient_scale_v1; no tuning or layer selection on expanded outcomes.',
        objective=original['objective'],optimizer_steps=0,additional_clean_reference_images=0,detector_patch_probes=0,
        device='CPU',threads=2,microbatch_size=64,minimum_available_memory_bytes=int(1.2*1024**3),
        runtime='Low priority follower. Wait before each request while original gradient worker is computing; wait for source clean models and sufficient memory.',
        analytic_fc_relative_tolerance=.001,
        validation='Every new R/F FC update compared to an independent analytic mean-CE gradient using cached clean-model features. Record identities/histograms, complementary partitions and CE means.',
        actual_post_deletion_training=False,
        interpretation='Additional cases test alarm behavior on correctly labeled normal deletion requests. They do not add actual post-deletion ASR outcomes or new attack seeds.',
        statistical_scope='Deliberately selected stress cases; ten shared seed clusters; do not report a natural-request population FPR or 570 independent training seeds.',
        prior_observations='Designed after observing the initial gradient benchmark: one missed constructed attack and one label-noise false alarm among 28 completed requests. Preserve that result; do not retune.',
        source_hashes={str(p.relative_to(OUT)).replace('\\','/'):sha(p) for p in sorted(list((OUT/'sources').glob('*.py'))+[Path(__file__)])})
    (OUT/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'normal_requests':360,'combined_requests':570,'selection_partition_checks':checks,'protocol_sha256':sha(OUT/'protocol.json')},indent=2))


if __name__=='__main__':main()
