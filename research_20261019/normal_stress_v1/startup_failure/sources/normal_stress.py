"""Additional correct-label Non-IID deletion stress tests; CPU only.

Read-only follower of the existing clean base models. Reuses the exact frozen
gradient scorer and thresholds. No poisoned records or trigger files are read.
"""
import argparse
import ctypes
import datetime as dt
import gc
import hashlib
import importlib.util
import json
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
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    os.replace(temporary,path)


def save(path,value):
    temporary=path.with_name(path.name+'.tmp');torch.save(value,temporary);os.replace(temporary,path)


def available_memory():
    class Memory(ctypes.Structure):
        _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(k,ctypes.c_ulonglong) for k in
            ('total_physical','available_physical','total_page','available_page','total_virtual','available_virtual','available_extended')]
    status=Memory();status.length=ctypes.sizeof(status)
    assert ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    return status.available_physical


def quotas(labels,count):
    raw=np.bincount(labels,minlength=10)*count/len(labels)
    result=np.floor(raw).astype(int)
    order=np.argsort(-(raw-result),kind='stable')
    result[order[:count-int(result.sum())]]+=1
    assert result.sum()==count
    return result


def select(labels,losses,count,mode,seed):
    rng=np.random.default_rng(seed+count*100003)
    groups={c:np.flatnonzero(labels==c) for c in range(10)}
    shuffled={c:rng.permutation(ids) for c,ids in groups.items()}
    if mode=='class_focused':
        selected=[]
        for c in sorted(groups,key=lambda c:(-len(groups[c]),c)):
            selected.extend(shuffled[c][:count-len(selected)].tolist())
            if len(selected)==count:break
    else:
        per_class=quotas(labels,count)
        selected=[]
        for c,ids in groups.items():
            if mode=='stratified_random':order=shuffled[c]
            elif mode=='matched_easy':order=ids[np.argsort(losses[ids],kind='stable')]
            else:
                assert mode=='matched_hard'
                order=ids[np.argsort(-losses[ids],kind='stable')]
            selected.extend(order[:per_class[c]].tolist())
        assert np.array_equal(np.bincount(labels[selected],minlength=10),per_class)
    mask=np.zeros(len(labels),dtype=bool);mask[selected]=True
    assert mask.sum()==count and len(set(selected))==count
    return mask


class Experiment:
    def __init__(self,out):
        self.out=out;self.protocol=read(out/'protocol.json');self.protocol_hash=sha(out/'protocol.json')
        self.source=Path(self.protocol['source_experiment'])
        self.gradient=Path(self.protocol['gradient_experiment'])
        assert sha(self.source/'protocol.json')==self.protocol['source_protocol_sha256']
        assert sha(self.gradient/'protocol.json')==self.protocol['gradient_protocol_sha256']
        assert sha(self.gradient/'sources/gradient_experiment.py')==self.protocol['gradient_scorer_sha256']
        for name,value in self.protocol['source_hashes'].items():assert sha(out/name)==value,name
        check=read(self.gradient/'self_check.json')
        assert check['passed'] and check['protocol_sha256']==self.protocol['gradient_protocol_sha256']
        spec=importlib.util.spec_from_file_location('frozen_gradient',self.gradient/'sources/gradient_experiment.py')
        baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
        helper=self.source/'sources/reference/train_factorial.py'
        assert sha(helper)==self.protocol['model_helper_sha256']
        sys.path.insert(0,str(helper.parent))
        from train_factorial import model,norm
        # Only the unchanged scoring function is inherited. Its source loader,
        # poisoned-record preparation and benchmark follower are not invoked.
        class Scorer(baseline.Experiment):
            def __init__(self,protocol):
                self.protocol=protocol;self.make_model=model;self.norm=norm
        self.scorer=Scorer(self.protocol);self.make_model=model;self.norm=norm
        torch.set_num_threads(2);torch.set_num_interop_threads(1)
        self.private=CIFAR10(self.protocol['data_root'],train=True,download=False)
        self.labels=np.asarray(self.private.targets)
        self.status=dict(pid=os.getpid(),state='initializing',started_utc=utc(),protocol_sha256=self.protocol_hash,
                         planned_normal_requests=360,planned_combined_requests=570,device='cpu',threads=2)

    def update(self,**values):
        self.status.update(values);self.status['updated_utc']=utc();write(self.out/'status.json',self.status)

    def cooperate(self):
        while True:
            old_status=read(self.gradient/'status.json') if (self.gradient/'status.json').exists() else {}
            busy=old_status.get('state') in ('running','self_check','self_check_cpu_batch_invariance','initializing')
            memory=available_memory()
            if not busy and memory>=self.protocol['minimum_available_memory_bytes']:return
            self.update(state='waiting_for_existing_gradient_worker' if busy else 'waiting_for_memory',available_memory_bytes=memory)
            time.sleep(15)

    def prepare(self,spec,source_cell,dest):
        pre=source_cell/'models/base_future'
        met=read(pre/'complete.json');checkpoint=pre/'model.pt'
        assert met['protocol_sha256']==self.protocol['source_protocol_sha256']
        assert met['counts']==[1200]*5 and sha(checkpoint)==met['checkpoint_sha256']
        split_path=source_cell/'splits.json';split=read(split_path)
        client=(spec['seed']-1001)%5
        ids=np.asarray(split['clients'][client],dtype=np.int64)
        assert len(ids)==1200 and len(set(ids.tolist()))==1200
        assert set(ids.tolist()).issubset(set(split['base']))
        assert not set(ids.tolist()).intersection(split['poison']+split['cover']+split['prior'])
        labels=self.labels[ids]
        x=torch.from_numpy(self.private.data[ids].copy()).permute(0,3,1,2).float()/255
        y=torch.tensor(labels,dtype=torch.long)
        state=torch.load(checkpoint,map_location='cpu',weights_only=True)
        cache=dest/'selection.pt'
        if cache.exists():
            selection=torch.load(cache,map_location='cpu',weights_only=True)
            assert selection['checkpoint_sha256']==met['checkpoint_sha256']
            assert torch.equal(selection['source_ids'],torch.tensor(ids))
        else:
            m=self.make_model().eval();m.load_state_dict(state);m.fc=torch.nn.Identity();m.requires_grad_(False)
            with torch.inference_mode():
                features=torch.cat([m(self.norm(batch)) for batch in x.split(64)]).double()
                logits=F.linear(features,state['fc.weight'].double(),state['fc.bias'].double())
                losses=F.cross_entropy(logits,y,reduction='none')
                probabilities=logits.softmax(1)
            assert torch.isfinite(features).all() and torch.isfinite(losses).all()
            selection=dict(checkpoint_sha256=met['checkpoint_sha256'],source_ids=torch.tensor(ids),
                           features=features,losses=losses,probabilities=probabilities)
            save(cache,selection);del m
        write(dest/'selection.json',dict(seed=spec['seed'],dominant_class_fraction=spec['dominant_fraction'],client=client,
            source_phase='base_future',source_training='Only correctly labeled, unmodified base records of all five clients',
            checkpoint_sha256=met['checkpoint_sha256'],splits_sha256=sha(split_path),private_records=len(ids),
            label_histogram=np.bincount(labels,minlength=10).tolist(),selection_sha256=sha(cache)))
        return dict(x=x,y=y,state=state,selection=selection,client=client,ids=ids,labels=labels,
                    checkpoint_sha256=met['checkpoint_sha256'],splits_sha256=sha(split_path))

    def compute(self,data,spec,cell,request,dest):
        start=time.monotonic();count=request['forget_count'];mode=request['mode']
        mask=select(data['labels'],data['selection']['losses'].numpy(),count,mode,spec['seed'])
        mask=torch.from_numpy(mask)
        retained=(data['x'][~mask],data['y'][~mask]);forget=(data['x'][mask],data['y'][mask])
        self.update(state='running',cell=cell,request=request['name'],client=data['client'])
        result,gradients=self.scorer.gradients(data['state'],retained,forget,progress=self.update)
        features=data['selection']['features'];probs=data['selection']['probabilities']
        residual=probs-F.one_hot(data['y'],num_classes=10).double()
        augmented=torch.cat([features,torch.ones(len(features),1,dtype=torch.float64)],1)
        errors={}
        for role,role_mask in [('retained',~mask),('forget',mask)]:
            expected=-self.protocol['virtual_learning_rate']*(residual[role_mask].T@augmented[role_mask])/int(role_mask.sum())
            actual=gradients['fc_virtual_updates'][role]
            denominator=float(expected.norm())
            error=float((actual-expected).norm())/denominator if denominator else float((actual-expected).norm())
            errors[role]=error
        assert max(errors.values())<self.protocol['analytic_fc_relative_tolerance'],errors
        dest.mkdir(parents=True,exist_ok=True)
        save(dest/'gradients.pt',gradients)
        result.update(cell=cell,request=request['name'],mode=mode,forget_count=count,
            seed=spec['seed'],dominant_class_fraction=spec['dominant_fraction'],client=data['client'],
            construction_normal=True,source_phase='base_future',normal_future_retraining_performed=False,
            pre_checkpoint_sha256=data['checkpoint_sha256'],splits_sha256=data['splits_sha256'],
            forgotten_source_ids=data['ids'][mask.numpy()].tolist(),
            forget_mean_selection_ce=float(data['selection']['losses'][mask].mean()),
            retain_mean_selection_ce=float(data['selection']['losses'][~mask].mean()),
            selection_sha256=sha(dest.parent.parent/'selection.pt'),analytic_fc_relative_errors=errors,
            gradients_sha256=sha(dest/'gradients.pt'),protocol_sha256=self.protocol_hash,
            locked_utc=utc(),elapsed_seconds=time.monotonic()-start)
        write(dest/'prediction.json',result)
        print(json.dumps(dict(event='normal_stress_scored',cell=cell,request=request['name'],
            seconds=result['elapsed_seconds'],primary_scores={k:result['scores'][k] for k in self.protocol['primary_metrics']},
            primary_flags={k:result['flags'][k] for k in self.protocol['primary_metrics']})),flush=True)

    def summarize(self):
        rows=[read(p) for p in (self.out/'cells').glob('*/requests/*/prediction.json')]
        errors=list((self.out/'cells').glob('*/requests/*/error.json'))
        def counts(items):
            result={}
            for name in self.protocol['thresholds']:
                values=[r['scores'][name] for r in items if r['scores'][name] is not None]
                result[name]=dict(normal_requests=len(items),flagged=sum(r['flags'][name] is True for r in items),
                    undefined=sum(r['flags'][name] is None for r in items),score_range=[min(values),max(values)] if values else None)
            return result
        original=read(self.gradient/'summary.json') if (self.gradient/'summary.json').exists() else {}
        summary=dict(updated_utc=utc(),protocol_sha256=self.protocol_hash,planned_normal_requests=360,
            scored_normal_requests=len(rows),failed_requests=len(errors),planned_combined_requests=570,
            original_scored_requests=original.get('scored_requests',0),original_evaluated_requests=original.get('evaluated_requests',0),
            combined_scored_requests=len(rows)+original.get('scored_requests',0),
            original_benchmark=original,overall=counts(rows),
            by_non_iid={str(f):counts([r for r in rows if r['dominant_class_fraction']==f]) for f in (.2,.7,.9)},
            by_mode={m:counts([r for r in rows if r['mode']==m]) for m in self.protocol['modes']},
            by_forget_count={str(n):counts([r for r in rows if r['forget_count']==n]) for n in self.protocol['forget_counts']},
            note='Deliberately selected correct-label stress requests; no new attack requests or post-deletion retraining. Ten shared seed clusters; not a population false-positive estimate.')
        write(self.out/'summary.json',summary);write(self.out/'results.json',dict(rows=rows,protocol_sha256=self.protocol_hash))
        lines=['正常 Non-IID 삭제 요청 추가 검증'.replace('正常','정상'),
            f"추가 정상 요청 계산 {len(rows)}/360, 오류 {len(errors)}건",
            f"기존 검사 계산 {original.get('scored_requests',0)}/210, 실제 삭제 후 평가 연결 {original.get('evaluated_requests',0)}건",
            '임계값·지표·레이어 정의 고정. 새 결과를 보고 조정하지 않음.',
            '기존210건과 추가 정상360건은 서로 다른 실험군으로 집계한다.','']
        for mode,values in summary['by_mode'].items():
            lines.append(mode)
            for name in self.protocol['primary_metrics']:
                value=values[name]
                lines.append(f"{name}: 정상 요청 위험 판정 {value['flagged']}/{value['normal_requests']}, 미정의 {value['undefined']}")
            lines.append('')
        lines+=['추가 요청의 실제 삭제 후 모델은 재학습하지 않았다. 정상 구성 요청의 경보 성향을 검사한다.',
                '의도적으로 고른 난이도·클래스 편향 조건이며 자연 발생 오탐률로 해석하지 않는다.']
        (self.out/'REPORT_KO.txt').write_text('\n'.join(lines),encoding='utf-8')
        return summary

    def run(self):
        lock=self.out/'worker.lock'
        with lock.open('x',encoding='utf-8') as stream:json.dump(dict(pid=os.getpid(),protocol_sha256=self.protocol_hash),stream)
        try:
            while True:
                work=False
                for spec in self.protocol['cell_order']:
                    cell=f"seed_{spec['seed']}_skew_{int(spec['dominant_fraction']*100):02d}"
                    source_cell=self.source/'cells'/cell;dest=self.out/'cells'/cell
                    pending=[r for r in self.protocol['requests'] if not any((dest/'requests'/r['name']/f).exists() for f in ('prediction.json','error.json'))]
                    if not pending or not (source_cell/'models/base_future/complete.json').exists():continue
                    self.cooperate();self.update(state='preparing',cell=cell)
                    data=self.prepare(spec,source_cell,dest)
                    for request in pending:
                        self.cooperate();request_dest=dest/'requests'/request['name']
                        try:self.compute(data,spec,cell,request,request_dest)
                        except Exception:
                            write(request_dest/'error.json',dict(error=traceback.format_exc(),utc=utc(),protocol_sha256=self.protocol_hash))
                            print(traceback.format_exc(),file=sys.stderr,flush=True)
                        work=True
                        summary=self.summarize()
                        self.update(scored_normal_requests=summary['scored_normal_requests'],failed_requests=summary['failed_requests'])
                        gc.collect()
                    del data;gc.collect()
                summary=self.summarize()
                if summary['scored_normal_requests']+summary['failed_requests']==360:
                    self.update(state='completed' if not summary['failed_requests'] else 'completed_with_failures')
                    write(self.out/'complete.json',self.status);break
                if not work and (self.source/'complete.json').exists():
                    self.update(state='completed_with_unavailable_source_models');write(self.out/'complete.json',self.status);break
                if not work:self.update(state='waiting_for_clean_source_models');time.sleep(30)
        finally:lock.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    experiment=Experiment(args.out)
    try:experiment.run()
    except Exception:
        experiment.update(state='failed',error=traceback.format_exc());raise


if __name__=='__main__':main()
