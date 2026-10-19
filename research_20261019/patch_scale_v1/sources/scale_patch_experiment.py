"""Locked large validation of the existing paired patch detector on DISLAB.

Ten fresh training seeds, three client label-skew levels, seven requests per
cell. All candidate decisions are locked before their future endpoint exists.
Failures stay in the status/report. No threshold or detector adaptation.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import time
import traceback

import numpy as np
import torch
import torch.nn.functional as F
from torchvision.datasets import CIFAR10

SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE/'reference'))
from train_factorial import model, norm, patch, cpu, statehash
from probe_information import bank, stats


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


def save_state(path, value):
    path = Path(path)
    temp = path.with_name(path.name+'.tmp')
    torch.save(value, temp)
    os.replace(temp, path)


class Experiment:
    def __init__(self, args):
        self.repo, self.out = args.repo, args.out
        self.protocol = json.loads((self.out/'protocol.json').read_text(encoding='utf-8'))
        self.protocol_hash = sha(self.out/'protocol.json')
        for relative, expected in self.protocol['source_hashes'].items():
            assert sha(self.out/relative) == expected, ('Source changed', relative)
        self.weights = Path(self.protocol['initial_weights'])
        assert sha(self.weights) == self.protocol['initial_weights_sha256']
        assert torch.cuda.is_available()
        torch.set_num_threads(4)
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        self.train = CIFAR10(self.protocol['data_root'], train=True, download=False)
        self.test = CIFAR10(self.protocol['data_root'], train=False, download=False)
        self.labels = np.asarray(self.train.targets)
        self.test_labels = np.asarray(self.test.targets)
        self.patterns = bank()
        assert len(self.patterns) == 32
        self.names = [p[0] for p in self.patterns]
        self.started = utc()
        self.status = dict(pid=os.getpid(), state='initializing', started_utc=self.started,
                           protocol_sha256=self.protocol_hash, planned_cells=30, planned_requests=210)

    def update(self, **fields):
        self.status.update(fields)
        self.status['updated_utc'] = utc()
        write_json(self.out/'status.json', self.status)

    def images(self, ids, test=False):
        data = self.test.data if test else self.train.data
        return torch.from_numpy(data[ids].copy()).permute(0, 3, 1, 2).cuda().float()/255

    def prepare(self, seed, fraction, cell):
        rng = np.random.default_rng(seed)
        labels = self.labels
        base, pool, dev, val, tests = [], [], [], [], []
        clients = [[] for _ in range(5)]
        primary = int(round(600*fraction))
        assert (600-primary) % 4 == 0
        for c in range(10):
            ix = rng.permutation(np.flatnonzero(labels == c))
            base.extend(ix[:600]); pool.extend(ix[600:900])
            dev.extend(ix[900:920]); val.extend(ix[920:940])
            tests.extend(rng.permutation(np.flatnonzero(self.test_labels == c))[:200])
            owner = c//2
            clients[owner].extend(ix[:primary])
            for cid, chunk in zip([j for j in range(5) if j != owner], np.array_split(ix[primary:600], 4)):
                clients[cid].extend(chunk)
        base, pool, dev, val, tests = map(np.asarray, (base, pool, dev, val, tests))
        poison = rng.choice(pool[labels[pool] != 0], 180, replace=False)
        cover = rng.choice(np.setdiff1d(pool, poison), 720, replace=False)
        prior = rng.choice(np.setdiff1d(pool[labels[pool] == 0], cover), 180, replace=False)
        used = set(base.tolist()+poison.tolist()+cover.tolist()+prior.tolist()+dev.tolist()+val.tolist())
        anchors = []
        anchor_rng = np.random.default_rng(881000+seed)
        for c in range(10):
            possible = np.array([int(i) for i in np.flatnonzero(labels == c) if int(i) not in used])
            anchors.extend(anchor_rng.choice(possible, 50, replace=False).tolist())
        assert all(len(ids) == 1200 for ids in clients)
        assert len(set(base)) == 6000 and not(set(dev)&set(val))
        assert not(set(anchors)&used)
        assert not(set(base)&set(poison) or set(base)&set(cover) or set(poison)&set(cover))
        meta = dict(seed=seed, dominant_class_fraction=fraction,
                    base=base.tolist(), poison=poison.tolist(), cover=cover.tolist(), prior=prior.tolist(),
                    development=dev.tolist(), validation=val.tolist(), test=tests.tolist(), anchors=anchors,
                    clients=[list(map(int, ids)) for ids in clients],
                    client_label_histograms=[np.bincount(labels[ids], minlength=10).tolist() for ids in clients])
        write_json(cell/'splits.json', meta)
        trigger = torch.rand(1, 3, 4, 4, generator=torch.Generator().manual_seed(20261018))
        save_state(cell/'evaluation_trigger.pt', trigger)
        clean = [(self.images(ids), torch.tensor(labels[ids], device='cuda')) for ids in clients]
        source_p = self.images(poison)
        cover_x = patch(self.images(cover), trigger)
        zero_y = torch.zeros(180, dtype=torch.long, device='cuda')
        data = dict(clean=clean, poison=(patch(source_p, trigger), zero_y),
                    noise=(source_p, zero_y), prior=(self.images(prior), zero_y),
                    cover=(cover_x, torch.tensor(labels[cover], device='cuda')),
                    anchor=self.images(anchors),
                    probes=dict(development=(self.images(dev), labels[dev]), validation=(self.images(val), labels[val])),
                    test=(self.images(tests, test=True), torch.tensor(self.test_labels[tests], device='cuda')),
                    trigger=trigger, meta=meta)
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
        initial = cpu(model(str(self.weights)).state_dict())
        save_state(cell/'initial.pt', initial)
        data['initial'] = initial
        data['initial_hash'] = statehash(initial)
        return data

    @staticmethod
    def cat(*pairs):
        return torch.cat([p[0] for p in pairs]), torch.cat([p[1] for p in pairs])

    def world(self, data, phase):
        result = list(data['clean'])
        b, p, c, q, n = data['clean'][0], data['poison'], data['cover'], data['prior'], data['noise']
        mapping = dict(badfu_pre=self.cat(b, p, c), prior_pre=self.cat(b, q, c),
                       noise_pre=self.cat(b, n, c), cover_only=self.cat(b, c),
                       danger_future=self.cat(b, p), safe_future=self.cat(b, (c[0][:180], c[1][:180])),
                       base_future=b, prior_future=self.cat(b, q), noise_future=self.cat(b, n))
        result[0] = mapping[phase]
        return result

    @torch.inference_mode()
    def evaluate(self, m, data):
        x, y = data['test']
        m.eval()
        clean = torch.cat([m(norm(z)) for z in x.split(128)])
        xx = patch(x, data['trigger'])
        attack = torch.cat([m(norm(z)) for z in xx.split(128)])
        assert torch.isfinite(clean).all() and torch.isfinite(attack).all()
        eligible = y != 0
        metrics = dict(clean_accuracy=float((clean.argmax(1) == y).float().mean()),
                       actual_trigger_asr=float((attack.argmax(1)[eligible] == 0).float().mean()),
                       triggered_accuracy=float((attack.argmax(1)[eligible] == y[eligible]).float().mean()),
                       eligible_test_records=int(eligible.sum()))
        return metrics, dict(clean_logits=clean.cpu().numpy(), trigger_logits=attack.cpu().numpy(), labels=y.cpu().numpy())

    def train_phase(self, data, cell, phase, seed, rounds=None):
        dest = cell/'models'/phase
        dest.mkdir(parents=True, exist_ok=True)
        checkpoint, done = dest/'model.pt', dest/'complete.json'
        if done.exists():
            met = json.loads(done.read_text(encoding='utf-8'))
            assert met['protocol_sha256'] == self.protocol_hash and sha(checkpoint) == met['checkpoint_sha256']
            assert met['rounds'] == (rounds or self.protocol['training']['rounds'])
            return checkpoint, met
        world = self.world(data, phase)
        counts = [len(y) for _, y in world]
        gm, local = model().cuda(), model().cuda()
        gm.load_state_dict(data['initial'])
        start_round = 0
        resume = dest/'resume.pt'
        if resume.exists():
            saved = torch.load(resume, weights_only=True, map_location='cpu')
            assert saved['protocol_sha256'] == self.protocol_hash
            gm.load_state_dict(saved['state']); start_round = saved['round']
        rounds = rounds or self.protocol['training']['rounds']
        start = time.time()
        for rnd in range(start_round, rounds):
            global_state = {k:v.detach().clone() for k,v in gm.state_dict().items()}
            aggregated = {k:torch.zeros_like(v, dtype=torch.float32) for k,v in global_state.items()}
            for cid, (xx, yy) in enumerate(world):
                local.load_state_dict(global_state); local.train()
                optimizer = torch.optim.SGD(local.parameters(), lr=.01)
                gen = torch.Generator(device='cuda').manual_seed(seed*100000+rnd*10+cid)
                order = torch.randperm(len(yy), generator=gen, device='cuda')
                for ids in order.split(64):
                    optimizer.zero_grad(set_to_none=True)
                    loss = F.cross_entropy(local(norm(xx[ids])), yy[ids])
                    assert torch.isfinite(loss)
                    loss.backward(); optimizer.step()
                for key, value in local.state_dict().items():
                    aggregated[key].add_(value.float(), alpha=counts[cid]/sum(counts))
            for key, value in global_state.items():
                if not value.is_floating_point():
                    aggregated[key] = aggregated[key].round().to(value.dtype)
            gm.load_state_dict(aggregated)
            self.update(state='running', phase=phase, round=rnd+1, rounds=rounds)
            if (rnd+1) % 5 == 0:
                save_state(resume, dict(state=cpu(gm.state_dict()), round=rnd+1, protocol_sha256=self.protocol_hash))
            print(json.dumps(dict(event='round', cell=cell.name, phase=phase, round=rnd+1, seconds=time.time()-start)), flush=True)
        save_state(checkpoint, cpu(gm.state_dict()))
        met, logits = self.evaluate(gm, data)
        np.savez_compressed(dest/'test_logits.npz', **logits)
        met.update(seed=seed, phase=phase, counts=counts, initial_state_sha256=data['initial_hash'],
                   checkpoint_sha256=sha(checkpoint), protocol_sha256=self.protocol_hash, rounds=rounds, finished_utc=utc())
        write_json(done, met)
        del gm, local
        torch.cuda.empty_cache()
        return checkpoint, met

    @torch.inference_mode()
    def collect(self, m, probes):
        out = {}
        m.eval()
        for split, (x, y) in probes.items():
            baseline = torch.cat([m(norm(b)).cpu() for b in x.split(128)]).numpy()
            patched = []
            for _, r, c, pattern in self.patterns:
                xx = x.clone(); xx[:, :, r:r+4, c:c+4] = pattern.to(x)
                patched.append(torch.cat([m(norm(b)).cpu() for b in xx.split(128)]).numpy())
            z = np.stack(patched)
            assert np.isfinite(z).all() and np.isfinite(baseline).all()
            out[split+'_labels'] = y
            out[split+'_clean'] = baseline
            out[split+'_blind'] = z
        return out

    @staticmethod
    def delta(obs, split):
        y = obs[split+'_labels']
        baseline, _ = stats(obs[split+'_clean'][None], y)
        patched, _ = stats(obs[split+'_blind'], y)
        return patched-baseline

    def decide(self, observations):
        delta = {split:{role:self.delta(obs, split) for role, obs in observations.items()}
                 for split in ('development', 'validation')}
        a = delta['development']['retained']-delta['development']['pre']
        i, t = np.unravel_index(a.argmax(), a.shape)
        val = delta['validation']
        gain = float(val['retained'][i,t]-val['pre'][i,t])
        contrast = float(val['retained'][i,t]-val['forget'][i,t])
        score = max(0., min(gain, contrast))
        return dict(pattern=self.names[i], pattern_index=int(i), target=int(t),
                    retained_gain=gain, branch_contrast=contrast, score=score,
                    threshold=.006, flag=score > .006, retained_gain_flag=gain > .006)

    def shadow(self, initial, teacher, public, pair, seed, dest):
        if dest.exists():
            m = model().cuda().eval()
            m.load_state_dict(torch.load(dest, map_location='cpu', weights_only=True))
            return m
        m = model().cuda().eval(); m.load_state_dict(initial)
        for name, parameter in m.named_parameters():
            parameter.requires_grad_(name.startswith('layer4.'))
        optimizer = torch.optim.SGD([p for p in m.parameters() if p.requires_grad], lr=.01)
        generator = torch.Generator(device='cuda').manual_seed(771000+seed)
        xx, yy = pair
        losses = []
        for step in range(100):
            ix = torch.randint(len(yy), (32,), generator=generator, device='cuda')
            ip = torch.randint(len(public), (32,), generator=generator, device='cuda')
            optimizer.zero_grad(set_to_none=True)
            lp = m(norm(public[ip]))
            local_loss = F.cross_entropy(m(norm(xx[ix])), yy[ix])
            anchor = 2*F.kl_div(lp.log_softmax(1), teacher[ip], reduction='batchmean')
            loss = local_loss+anchor
            assert torch.isfinite(loss)
            loss.backward()
            torch.nn.utils.clip_grad_norm_([p for p in m.parameters() if p.requires_grad], 1., error_if_nonfinite=True)
            optimizer.step()
            losses.append(dict(step=step+1, local_ce=float(local_loss.detach()), anchor=float(anchor.detach())))
        state = cpu(m.state_dict())
        assert all(torch.equal(state[key], value) for key, value in initial.items() if not key.startswith('layer4.'))
        assert all(torch.equal(state[key], value) for key, value in initial.items() if key.endswith(('running_mean','running_var','num_batches_tracked')))
        assert any(not torch.equal(state[key], value) for key, value in initial.items() if key.startswith('layer4.'))
        save_state(dest, state)
        write_json(dest.with_suffix('.losses.json'), losses)
        return m

    def request_pairs(self, data):
        b, p, c, q, n = data['clean'][0], data['poison'], data['cover'], data['prior'], data['noise']
        return dict(
            attack_delete_cover=('badfu_pre', 'danger_future', self.cat(b,p), c),
            equal_size_safe=('badfu_pre', 'safe_future', self.cat(b,(c[0][:180],c[1][:180])), self.cat(p,(c[0][180:],c[1][180:]))),
            delete_poison=('badfu_pre', 'cover_only', self.cat(b,c), p),
            delete_both=('badfu_pre', 'base_future', b, self.cat(p,c)),
            benign_class_prior=('prior_pre', 'prior_future', self.cat(b,q), c),
            label_noise=('noise_pre', 'noise_future', self.cat(b,n), c),
            normal_cover=('cover_only', 'base_future', b, c))

    def predict_requests(self, data, cell, seed, pre_phase, pre_path, pre_metrics):
        requests = [(name, *details) for name, details in self.request_pairs(data).items() if details[0] == pre_phase]
        for name, *_ in requests:
            prediction_path = cell/'requests'/name/'prediction.json'
            if prediction_path.exists():
                stored = json.loads(prediction_path.read_text(encoding='utf-8'))
                assert stored['protocol_sha256'] == self.protocol_hash
                assert stored['pre_checkpoint_sha256'] == sha(pre_path)
        pending = [r for r in requests if not (cell/'requests'/r[0]/'prediction.json').exists()]
        if not pending:
            return
        initial = torch.load(pre_path, map_location='cpu', weights_only=True)
        original = model().cuda().eval(); original.load_state_dict(initial); original.requires_grad_(False)
        with torch.no_grad():
            teacher = original(norm(data['anchor'])).softmax(1).detach()
        pre_observation = self.collect(original, data['probes'])
        del original
        for name, _, future_phase, retained, forget in pending:
            self.update(phase='detector', request=name, round=None)
            dest = cell/'requests'/name; dest.mkdir(parents=True, exist_ok=True)
            future = cell/'models'/future_phase/'model.pt'
            assert not future.exists(), 'A future checkpoint exists before this request prediction is locked'
            observations = dict(pre=pre_observation)
            for role, pair in [('retained', retained), ('forget', forget)]:
                m = self.shadow(initial, teacher, data['anchor'], pair, seed, dest/f'{role}.pt')
                observations[role] = self.collect(m, data['probes'])
                del m; torch.cuda.empty_cache()
            prediction = self.decide(observations)
            prediction.update(request=name, pre_phase=pre_phase, future_phase=future_phase,
                              seed=seed, dominant_class_fraction=data['meta']['dominant_class_fraction'],
                              retained_records=len(retained[1]), forget_records=len(forget[1]),
                              retained_histogram=torch.bincount(retained[1], minlength=10).cpu().tolist(),
                              forget_histogram=torch.bincount(forget[1], minlength=10).cpu().tolist(),
                              pre_checkpoint_sha256=sha(pre_path), protocol_sha256=self.protocol_hash,
                              future_checkpoint_existed_at_prediction=False, locked_utc=utc(),
                              pre_actual_trigger_asr=pre_metrics['actual_trigger_asr'],
                              pre_clean_accuracy=pre_metrics['clean_accuracy'])
            for role, obs in observations.items():
                np.savez_compressed(dest/f'{role}_probes.npz', **obs)
            write_json(dest/'prediction.json', prediction)
            print(json.dumps(dict(event='prediction_locked', cell=cell.name, request=name, score=prediction['score'], flag=prediction['flag'])), flush=True)

    def finish_cell(self, data, cell, seed):
        # badfu requests are all locked before cover_only is trained, even
        # though cover_only is also a pre-model for the normal-cover control.
        for phase in ('badfu_pre', 'prior_pre', 'noise_pre', 'cover_only'):
            path, metrics = self.train_phase(data, cell, phase, seed)
            self.predict_requests(data, cell, seed, phase, path, metrics)
        assert len(list((cell/'requests').glob('*/prediction.json'))) == 7
        for phase in ('danger_future', 'safe_future', 'base_future', 'prior_future', 'noise_future'):
            self.train_phase(data, cell, phase, seed)
        rows = []
        for name in self.request_pairs(data):
            path = cell/'requests'/name/'prediction.json'
            prediction = json.loads(path.read_text(encoding='utf-8'))
            future = cell/'models'/prediction['future_phase']
            met = json.loads((future/'complete.json').read_text(encoding='utf-8'))
            assert sha(future/'model.pt') == met['checkpoint_sha256']
            pre, post = prediction['pre_actual_trigger_asr'], met['actual_trigger_asr']
            row = dict(**prediction, post_actual_trigger_asr=post, actual_asr_increase=post-pre,
                       post_clean_accuracy=met['clean_accuracy'], future_checkpoint_sha256=met['checkpoint_sha256'],
                       prediction_file_sha256=sha(path),
                       realized_latent_activation=(pre <= .10 and post >= .50 and post-pre >= .30),
                       construction_attack=(name == 'attack_delete_cover'))
            rows.append(row)
            write_json(cell/'requests'/name/'evaluation.json', row)
        write_json(cell/'complete.json', dict(protocol_sha256=self.protocol_hash, rows=rows, completed_utc=utc()))
        return rows

    def summarize(self):
        cells = list((self.out/'cells').glob('*/complete.json')) if (self.out/'cells').exists() else []
        rows = [row for path in cells for row in json.loads(path.read_text(encoding='utf-8'))['rows']]
        errors = list((self.out/'cells').glob('*/error.json')) if (self.out/'cells').exists() else []
        failed = [p for p in errors if not (p.parent/'complete.json').exists()]
        locked = list((self.out/'cells').glob('*/requests/*/prediction.json')) if (self.out/'cells').exists() else []
        def counts(values):
            attacks = [r for r in values if r['construction_attack']]
            controls = [r for r in values if not r['construction_attack']]
            realized = [r for r in values if r['realized_latent_activation']]
            return dict(requests=len(values), attempted_attack_requests=len(attacks),
                        attempted_attack_flagged=sum(r['flag'] for r in attacks),
                        construction_controls=len(controls), construction_controls_flagged=sum(r['flag'] for r in controls),
                        realized_latent_requests=len(realized), realized_latent_flagged=sum(r['flag'] for r in realized),
                        retained_gain_only_controls_flagged=sum(r['retained_gain_flag'] for r in controls))
        summary = dict(updated_utc=utc(), protocol_sha256=self.protocol_hash, completed_cells=len(cells),
                       planned_cells=30, completed_requests=len(rows), planned_requests=210,
                       failed_cells=len(failed), historical_error_records=len(errors),
                       locked_predictions=len(locked), overall=counts(rows),
                       by_non_iid={str(level):counts([r for r in rows if r['dominant_class_fraction'] == level])
                                   for level in self.protocol['non_iid_dominant_fractions']},
                       by_request={name:counts([r for r in rows if r['request'] == name]) for name in self.protocol['requests']},
                       note='Cells share ten seed clusters; counts are not 210 independent training seeds. Intent labels and realized trigger activation are reported separately.')
        write_json(self.out/'summary.json', summary)
        if rows:
            keys = [k for k in rows[0] if not isinstance(rows[0][k], list)]
            with (self.out/'results.csv').open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=keys, extrasaction='ignore')
                writer.writeheader(); writer.writerows(rows)
        lines = ['기존 패치 검사 대형 검증', '갱신 UTC: '+utc(),
                 f"완료 {len(cells)}/30조건, {len(rows)}/210요청, 실패 조건 {len(failed)}개", '임계값0.006 고정. 결과를 보고 조정하지 않음.',
                 '공격 의도로 구성한 요청과 실제 잠재 백도어 활성화는 별도로 집계한다.', '']
        for level, value in summary['by_non_iid'].items():
            lines += [f"Non-IID 지배 클래스 비중 {level}: {value['requests']}건 완료",
                      f"공격 구성 요청 탐지 {value['attempted_attack_flagged']}/{value['attempted_attack_requests']}",
                      f"대조 요청 위험 판정 {value['construction_controls_flagged']}/{value['construction_controls']}",
                      f"실제 잠재 활성화 탐지 {value['realized_latent_flagged']}/{value['realized_latent_requests']}", '']
        lines += ['0/0은 아직 평가 사례가 없다는 뜻이다.', '고정 타겟0·동일4x4 트리거·CIFAR-10/ResNet18 범위의 검증이다.',
                  '순차 실행 중인 중간 결과를 최종 성공률로 해석하지 않는다.']
        (self.out/'REPORT_KO.txt').write_text('\n'.join(lines), encoding='utf-8')
        return summary

    def self_check(self):
        expected = [
            ('local_witness_confirm74', 'seed_74_attack', .014216192066669464),
            ('local_witness_confirm74_safe', 'seed_74_equal_size_safe', 0.),
            ('local_witness_benign_prior74', 'seed_74_benign_prior', .00061788409948349),
            ('local_witness_label_noise74', 'seed_74_label_noise', .003588162362575531)]
        replay = []
        for folder, case, value in expected:
            dest = self.repo/'research_20261018/fl_information'/folder/case
            obs = {role:dict(np.load(dest/f'{role}_probes.npz')) for role in ('pre','retained','forget')}
            score = self.decide(obs)
            assert abs(score['score']-value) < 1e-10, (case, score, value)
            replay.append(dict(case=case, score=score['score'], reproduced=True))
        cell = self.out/'smoke'
        cell.mkdir(parents=True, exist_ok=True)
        data = self.prepare(1001, .7, cell)
        self.update(state='self_check', cell='smoke')
        path, met = self.train_phase(data, cell, 'badfu_pre', 1001, rounds=1)
        initial = torch.load(path, map_location='cpu', weights_only=True)
        m = model().cuda().eval(); m.load_state_dict(initial); m.requires_grad_(False)
        with torch.no_grad():
            teacher = m(norm(data['anchor'])).softmax(1).detach()
        b = data['clean'][0]
        shadow = self.shadow(initial, teacher, data['anchor'], self.cat(b,data['poison']), 1001, cell/'smoke_shadow.pt')
        obs = self.collect(shadow, data['probes'])
        assert all(np.isfinite(value).all() for value in obs.values())
        write_json(self.out/'self_check.json', dict(passed=True, replay=replay, one_federated_round=met,
                                                   one_hundred_step_shadow_finite=True, protocol_sha256=self.protocol_hash, utc=utc()))
        self.update(state='self_check_passed')
        print(json.dumps(dict(event='self_check_passed', replay=replay)), flush=True)

    def run(self):
        assert json.loads((self.out/'self_check.json').read_text(encoding='utf-8'))['passed']
        lock = self.out/'worker.lock'
        with lock.open('x', encoding='utf-8') as stream:
            json.dump(dict(pid=os.getpid(), started_utc=utc(), protocol_sha256=self.protocol_hash), stream)
        failures = 0
        try:
            for spec in self.protocol['cell_order']:
                seed, fraction = spec['seed'], spec['dominant_fraction']
                cell = self.out/'cells'/f"seed_{seed}_skew_{int(fraction*100):02d}"
                cell.mkdir(parents=True, exist_ok=True)
                if (cell/'complete.json').exists():
                    continue
                self.update(state='running', cell=cell.name, seed=seed, dominant_fraction=fraction, phase='preparing', round=None)
                try:
                    data = self.prepare(seed, fraction, cell)
                    self.finish_cell(data, cell, seed)
                    del data
                    torch.cuda.empty_cache()
                except Exception:
                    failures += 1
                    error = dict(utc=utc(), cell=cell.name, error=traceback.format_exc(), protocol_sha256=self.protocol_hash)
                    write_json(cell/'error.json', error)
                    print(json.dumps(dict(event='cell_failed', **error)), flush=True)
                    torch.cuda.empty_cache()
                summary = self.summarize()
                self.update(completed_cells=summary['completed_cells'], completed_requests=summary['completed_requests'], failed_cells=summary['failed_cells'])
            summary = self.summarize()
            final = 'completed' if summary['completed_cells'] == 30 else 'completed_with_failures'
            self.update(state=final, phase=None, round=None, **{k:summary[k] for k in ('completed_cells','completed_requests','failed_cells')})
            write_json(self.out/'complete.json', dict(state=final, utc=utc(), protocol_sha256=self.protocol_hash, summary=summary))
        finally:
            lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--self-check', action='store_true')
    args = parser.parse_args()
    experiment = Experiment(args)
    try:
        if args.self_check:
            experiment.self_check()
        else:
            experiment.run()
    except Exception:
        experiment.update(state='failed', fatal_error=traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
