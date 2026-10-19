"""CPU-only, fixed one-point gradient diagnostics on patch_scale_v1 requests.

Never modifies the source experiment or trains a model. Original private
records are reconstructed for this simulation; no detector patches, public
anchors, development, validation or test images are loaded by the detector.
"""
import argparse
import datetime as dt
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

import numpy as np
import torch
import torch.nn.functional as F
from torchvision.datasets import CIFAR10


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    os.replace(temporary, path)


def save(path, value):
    temporary = path.with_name(path.name+'.tmp')
    torch.save(value, temporary)
    os.replace(temporary, path)


def metrics(a, b):
    a, b = a.double(), b.double()
    r2, f2, dot = float(a.square().sum()), float(b.square().sum()), float((a*b).sum())
    result = dict(retained_norm=math.sqrt(r2), forget_norm=math.sqrt(f2),
                  inner_product=dot, norm_ratio=None, orthogonal_ratio=None, cosine=None)
    if not f2:
        result['undefined_reason'] = 'Exactly zero forget gradient; no denominator epsilon or safe label.'
        return result
    result['norm_ratio'] = math.sqrt(r2/f2)
    alpha = dot/f2
    residual = a-alpha*b
    residual2 = float(residual.square().sum())
    result['orthogonal_ratio'] = math.sqrt(residual2/f2)
    result['projection_coefficient'] = alpha
    if r2:
        cosine = max(-1., min(1., dot/math.sqrt(r2*f2)))
        result['cosine'] = cosine
        identity = result['norm_ratio']*math.sqrt(max(0., 1-cosine*cosine))
        assert abs(identity-result['orthogonal_ratio']) < 1e-8*max(1., identity)
    if residual2:
        error = abs(float((residual*b).sum()))/math.sqrt(residual2*f2)
        assert error < 1e-8
        result['relative_orthogonality_error'] = error
    return result


class Experiment:
    def __init__(self, out):
        self.out = out
        self.protocol = read(out/'protocol.json')
        self.protocol_hash = sha(out/'protocol.json')
        self.source = Path(self.protocol['source_experiment'])
        assert sha(self.source/'protocol.json') == self.protocol['source_protocol_sha256']
        for name, expected in self.protocol['source_hashes'].items():
            assert sha(out/name) == expected, name
        ref = self.source/'sources/reference/train_factorial.py'
        assert sha(ref) == self.protocol['model_helper_sha256']
        sys.path.insert(0, str(ref.parent))
        from train_factorial import model, norm, patch
        self.make_model, self.norm, self.apply_original_training_pattern = model, norm, patch
        torch.set_num_threads(2)
        torch.set_num_interop_threads(1)
        self.private = CIFAR10(self.protocol['data_root'], train=True, download=False)
        self.labels = np.asarray(self.private.targets)
        self.status = dict(pid=os.getpid(), state='initializing', protocol_sha256=self.protocol_hash,
                           started_utc=utc(), device='cpu', threads=2, planned_requests=210)
        self.requests = self.protocol['requests']

    def update(self, **values):
        self.status.update(values)
        self.status['updated_utc'] = utc()
        write(self.out/'status.json', self.status)

    def images(self, ids):
        return torch.from_numpy(self.private.data[ids].copy()).permute(0,3,1,2).float()/255

    @staticmethod
    def cat(*pairs):
        return torch.cat([p[0] for p in pairs]), torch.cat([p[1] for p in pairs])

    def private_pairs(self, split, trigger_path, request):
        # Simulation data preparation only. The scoring function below receives
        # the already constructed R/F tensors, not a trigger or target class.
        base, poison, cover = split['clients'][0], split['poison'], split['cover']
        b = self.images(base), torch.tensor(self.labels[base], dtype=torch.long)
        trigger = torch.load(trigger_path, map_location='cpu', weights_only=True)
        c = self.apply_original_training_pattern(self.images(cover), trigger), torch.tensor(self.labels[cover], dtype=torch.long)
        if request == 'normal_cover':
            return b, c
        if request == 'benign_class_prior':
            ids = split['prior']
            q = self.images(ids), torch.tensor(self.labels[ids], dtype=torch.long)
            assert (q[1] == 0).all()
            return self.cat(b,q), c
        p_x = self.images(poison)
        if request != 'label_noise':
            p_x = self.apply_original_training_pattern(p_x, trigger)
        p = p_x, torch.zeros(len(poison), dtype=torch.long)
        if request in ('attack_delete_cover','label_noise'):
            return self.cat(b,p), c
        if request == 'equal_size_safe':
            return self.cat(b,(c[0][:180],c[1][:180])), self.cat(p,(c[0][180:],c[1][180:]))
        if request == 'delete_poison':
            return self.cat(b,c), p
        assert request == 'delete_both'
        return b, self.cat(p,c)

    def gradients(self, state, retained, forget, progress=None, microbatch_size=64):
        m = self.make_model().cpu().eval()
        m.load_state_dict(state)
        m.fc = torch.nn.Identity()
        m.requires_grad_(False)
        m.layer4.requires_grad_(True)
        weight = state['fc.weight'].double().clone().requires_grad_()
        bias = state['fc.bias'].double().clone().requires_grad_()
        conv = {name:p for name,p in m.named_parameters() if name.startswith('layer4.') and p.ndim == 4}
        assert len(conv) == 5
        updates, raw, losses, histograms = {}, {}, {}, {}
        lr = self.protocol['virtual_learning_rate']
        for role, (x,y) in [('retained',retained),('forget',forget)]:
            m.zero_grad(set_to_none=True)
            weight.grad = bias.grad = None
            losses[role] = 0.
            count = len(y)
            histograms[role] = torch.bincount(y,minlength=10).tolist()
            for start in range(0,count,microbatch_size):
                ids = slice(start,start+microbatch_size)
                h = m(self.norm(x[ids]))
                z = F.linear(h.double(),weight,bias)
                loss = F.cross_entropy(z,y[ids],reduction='sum')/count
                assert torch.isfinite(loss)
                loss.backward()
                losses[role] += float(loss.detach())
                if progress:
                    progress(role=role, samples_done=min(start+microbatch_size,count), samples_total=count)
            raw[role] = {name:p.grad.detach().clone() for name,p in conv.items()}
            updates[role] = -lr*torch.cat([weight.grad.detach(),bias.grad.detach()[:,None]],1)
            assert torch.isfinite(updates[role]).all()
            assert all(torch.isfinite(g).all() for g in raw[role].values())
        assert all(torch.equal(value,state[name]) for name,value in m.state_dict().items())
        result = {'fc':metrics(updates['retained'],updates['forget'])}
        total_r2 = total_f2 = total_dot = 0.
        for name in conv:
            a,b = -lr*raw['retained'][name].double(),-lr*raw['forget'][name].double()
            result[name] = metrics(a,b)
            total_r2 += result[name]['retained_norm']**2
            total_f2 += result[name]['forget_norm']**2
            total_dot += result[name]['inner_product']
        # One joint Frobenius product over the five Conv tensors, without
        # concatenating tensors or choosing a favorable reshaping.
        aggregate = dict(retained_norm=math.sqrt(total_r2),forget_norm=math.sqrt(total_f2),
                         inner_product=total_dot,norm_ratio=None,orthogonal_ratio=None,cosine=None)
        if total_f2:
            alpha = total_dot/total_f2
            direct = sum(float((-lr*raw['retained'][name].double()-alpha*(-lr*raw['forget'][name].double())).square().sum()) for name in conv)
            aggregate.update(norm_ratio=math.sqrt(total_r2/total_f2),orthogonal_ratio=math.sqrt(direct/total_f2),projection_coefficient=alpha)
            if total_r2:
                cosine = max(-1.,min(1.,total_dot/math.sqrt(total_r2*total_f2)))
                aggregate['cosine'] = cosine
                expected = aggregate['norm_ratio']*math.sqrt(max(0.,1-cosine*cosine))
                assert abs(expected-aggregate['orthogonal_ratio']) < 1e-8*max(1.,expected)
        result['conv_all'] = aggregate
        scores = {name:result[item['block']][item['quantity']] for name,item in self.protocol['thresholds'].items()}
        flags = {name:(None if value is None else value>self.protocol['thresholds'][name]['threshold']) for name,value in scores.items()}
        saved = dict(conv_mean_ce_gradients=raw,fc_virtual_updates=updates,virtual_learning_rate=lr)
        return dict(metrics=result,scores=scores,flags=flags,mean_ce_losses=losses,
                    histograms=histograms,retained_records=len(retained[1]),forget_records=len(forget[1]),
                    model_and_bn_unchanged=True), saved

    def self_check(self):
        # A genuine CPU recomputation against the old GPU reference, not a
        # replay of already saved scores.
        old = Path(self.protocol['self_check_source'])
        checkpoint, split_path = old/'both.pt',old/'splits.json'
        expected = next(r for r in read(self.out/'calibration/pure_layer4_result.json')['rows'] if r['case']=='attack74')
        assert sha(checkpoint)==expected['checkpoint_sha256'] and sha(split_path)==expected['splits_sha256']
        pairs = self.private_pairs(read(split_path),old/'evaluation_trigger.pt','attack_delete_cover')
        state = torch.load(checkpoint,map_location='cpu',weights_only=True)
        self.update(state='self_check')
        start = time.monotonic()
        computed, saved = self.gradients(state,*pairs,progress=self.update)
        reference = np.load(self.out/'calibration/selfcheck_fc.npz')
        errors = {role:float(np.linalg.norm(saved['fc_virtual_updates'][role].numpy()-reference[role])/np.linalg.norm(reference[role])) for role in ('retained','forget')}
        for block in ('fc','conv_all'):
            source = expected['fc' if block=='fc' else 'conv']
            for key in ('retained_norm','forget_norm','cosine'):
                value = computed['metrics'][block][key]
                errors[block+'.'+key] = abs(value-source[key])/max(abs(source[key]),1e-15)
        write(self.out/'self_check_reference_errors.json',dict(relative_errors=errors,protocol_sha256=self.protocol_hash))
        # Cross-device float32 convolutions can differ. Independently verify
        # that CPU microbatch accumulation at 64 and 128 gives the same result.
        self.update(state='self_check_cpu_batch_invariance')
        repeated, repeated_saved = self.gradients(state,*pairs,progress=self.update,microbatch_size=128)
        cpu_errors = {role:float(torch.linalg.vector_norm(saved['fc_virtual_updates'][role]-repeated_saved['fc_virtual_updates'][role])/torch.linalg.vector_norm(saved['fc_virtual_updates'][role])) for role in ('retained','forget')}
        for block in computed['metrics']:
            for key in ('retained_norm','forget_norm','norm_ratio','orthogonal_ratio','cosine'):
                a,b = computed['metrics'][block][key],repeated['metrics'][block][key]
                if a is not None and b is not None:
                    cpu_errors[block+'.'+key]=abs(a-b)/max(abs(a),1e-15)
        record=dict(passed=max(errors.values())<.005 and max(cpu_errors.values())<.0001,
              utc=utc(),protocol_sha256=self.protocol_hash,reference_case='attack74',
              cpu_seconds=time.monotonic()-start,relative_errors=errors,cpu_batch_relative_errors=cpu_errors,
              cross_device_relative_tolerance=.005,cpu_batch_relative_tolerance=.0001,
              initial_cross_device_tolerance_failure_preserved=True,model_and_bn_unchanged=True)
        write(self.out/'self_check.json',record)
        assert record['passed'],record
        self.update(state='self_check_passed')

    def summarize(self):
        predictions = [read(p) for p in (self.out/'cells').glob('*/requests/*/prediction.json')]
        evaluated = []
        for prediction in predictions:
            original = self.source/'cells'/prediction['cell']/'requests'/prediction['request']/'evaluation.json'
            if not original.exists():
                continue
            truth = read(original)
            assert truth['pre_checkpoint_sha256']==prediction['pre_checkpoint_sha256']
            assert truth['retained_records']==prediction['retained_records'] and truth['forget_records']==prediction['forget_records']
            for role in ('retained','forget'):
                assert truth[role+'_histogram']==prediction['histograms'][role]
            row = dict(**prediction,construction_attack=truth['construction_attack'],
                       realized_latent_activation=truth['realized_latent_activation'],
                       pre_asr=truth['pre_actual_trigger_asr'],post_asr=truth['post_actual_trigger_asr'],
                       pre_clean_accuracy=truth['pre_clean_accuracy'],post_clean_accuracy=truth['post_clean_accuracy'],
                       patch_score=truth['score'],patch_flag=truth['flag'])
            evaluated.append(row)
            write(self.out/'cells'/prediction['cell']/'requests'/prediction['request']/'evaluation.json',row)
        def stats(rows, name):
            def flag(r):
                return r['patch_flag'] if name=='patch' else r['flags'][name]
            a = [r for r in rows if r['construction_attack']]
            b = [r for r in rows if not r['construction_attack']]
            actual = [r for r in rows if r['realized_latent_activation']]
            def ranges(values):
                v = [r['scores'][name] for r in values if r['scores'][name] is not None] if name!='patch' else [r['patch_score'] for r in values]
                return [min(v),max(v)] if v else None
            return dict(attacks=len(a),attack_flagged=sum(flag(r) is True for r in a),
                        controls=len(b),controls_flagged=sum(flag(r) is True for r in b),
                        undefined=sum(flag(r) is None for r in rows),
                        realized_latent=len(actual),realized_latent_flagged=sum(flag(r) is True for r in actual),
                        attack_score_range=ranges(a),control_score_range=ranges(b))
        names = list(self.protocol['thresholds'])+['patch']
        summary = dict(updated_utc=utc(),protocol_sha256=self.protocol_hash,
                       scored_requests=len(predictions),evaluated_requests=len(evaluated),planned_requests=210,
                       failed_requests=len(list((self.out/'cells').glob('*/requests/*/error.json'))),
                       prospective_scores=sum(not r['future_existed_when_scored'] for r in predictions),
                       overall={name:stats(evaluated,name) for name in names},
                       by_non_iid={str(f):{name:stats([r for r in evaluated if r['dominant_class_fraction']==f],name) for name in names} for f in (.2,.7,.9)})
        write(self.out/'summary.json',summary)
        write(self.out/'results.json',dict(protocol_sha256=self.protocol_hash,rows=evaluated))
        lines = ['패치 없는 순수 1스텝 탐지: 중간 결과',
                 f"계산 {len(predictions)}/210건, 삭제 후 평가까지 완료 {len(evaluated)}건",
                 '임계값은 과거 16건으로 정한 뒤 고정. 새 결과에 맞춰 조정하지 않음.',
                 '추가 정상 기준 이미지 0장, 탐지용 패치 0개, 원본 모델 갱신 0회.',
                 '현재 결과는 동일한 10개 시드의 반복 요청이며 독립 210개 시드가 아님.','']
        for f,values in summary['by_non_iid'].items():
            lines.append('기본 자료 두 클래스 비중 '+f)
            for name in self.protocol['primary_metrics']+['patch']:
                v = values[name]
                lines.append(f"{name}: 공격 탐지 {v['attack_flagged']}/{v['attacks']}, 대조 오탐 {v['controls_flagged']}/{v['controls']}, 미정의 {v['undefined']}")
            lines.append('')
        (self.out/'REPORT_KO.txt').write_text('\n'.join(lines),encoding='utf-8')
        return summary

    def run(self):
        check = read(self.out/'self_check.json')
        assert check['passed'] and check['protocol_sha256']==self.protocol_hash
        lock = self.out/'worker.lock'
        with lock.open('x',encoding='utf-8') as stream:
            json.dump(dict(pid=os.getpid(),protocol_sha256=self.protocol_hash),stream)
        try:
            while True:
                work = False
                for spec in self.protocol['cell_order']:
                    cell = f"seed_{spec['seed']}_skew_{int(spec['dominant_fraction']*100):02d}"
                    source_cell = self.source/'cells'/cell
                    for request,details in self.requests.items():
                        dest = self.out/'cells'/cell/'requests'/request
                        if (dest/'prediction.json').exists() or (dest/'error.json').exists():
                            continue
                        pre = source_cell/'models'/details['pre_phase']
                        if not (pre/'complete.json').exists():
                            continue
                        dest.mkdir(parents=True,exist_ok=True)
                        self.update(state='running',cell=cell,request=request)
                        try:
                            start = time.monotonic()
                            checkpoint = pre/'model.pt'
                            checkpoint_hash = sha(checkpoint)
                            assert checkpoint_hash==read(pre/'complete.json')['checkpoint_sha256']
                            future = source_cell/'models'/details['future_phase']/'model.pt'
                            future_before = future.exists()
                            split_path = source_cell/'splits.json'
                            pairs = self.private_pairs(read(split_path),source_cell/'evaluation_trigger.pt',request)
                            state = torch.load(checkpoint,map_location='cpu',weights_only=True)
                            prediction, gradients = self.gradients(state,*pairs,progress=self.update)
                            save(dest/'gradients.pt',gradients)
                            prediction.update(cell=cell,request=request,seed=spec['seed'],
                                dominant_class_fraction=spec['dominant_fraction'],
                                pre_checkpoint_sha256=checkpoint_hash,splits_sha256=sha(split_path),
                                gradients_sha256=sha(dest/'gradients.pt'),protocol_sha256=self.protocol_hash,
                                future_existed_before_scoring=future_before,
                                future_existed_when_scored=future.exists(),locked_utc=utc(),
                                cpu_seconds=time.monotonic()-start)
                            write(dest/'prediction.json',prediction)
                            print(json.dumps(dict(event='gradient_scored',cell=cell,request=request,
                                  seconds=prediction['cpu_seconds'],scores=prediction['scores'],flags=prediction['flags'])),flush=True)
                            del state,pairs,gradients
                            gc.collect()
                        except Exception:
                            write(dest/'error.json',dict(utc=utc(),error=traceback.format_exc(),protocol_sha256=self.protocol_hash))
                            print(traceback.format_exc(),file=sys.stderr,flush=True)
                        work = True
                        summary = self.summarize()
                        self.update(scored_requests=summary['scored_requests'],evaluated_requests=summary['evaluated_requests'],failed_requests=summary['failed_requests'])
                summary = self.summarize()
                if summary['evaluated_requests']==210:
                    self.update(state='completed')
                    write(self.out/'complete.json',self.status)
                    break
                if not work and (self.source/'complete.json').exists():
                    self.update(state='completed_with_unavailable_or_failed_requests')
                    write(self.out/'complete.json',dict(**self.status,summary=summary))
                    break
                if not work:
                    self.update(state='waiting_for_source_models',scored_requests=summary['scored_requests'],evaluated_requests=summary['evaluated_requests'])
                    time.sleep(30)
        finally:
            lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--self-check',action='store_true')
    args = parser.parse_args()
    experiment = Experiment(args.out)
    try:
        experiment.self_check() if args.self_check else experiment.run()
    except Exception:
        experiment.update(state='failed',error=traceback.format_exc())
        raise


if __name__=='__main__':
    main()
