"""Fixed, complete intermediate-round evaluation; terminal counts are reused."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import traceback
from run import ROOT, setup, inputs, read, write, sha, save, load, begin, resource_guard


def evaluate(p, route):
    import numpy as np
    import torch
    from torchvision.datasets import CIFAR10
    import model_reference
    assert read(ROOT / 'CONTROLLER.json')['state'] == 'completed'
    assert read(ROOT / 'RESULT.json')['state'] == 'completed_comparison'
    resource_guard(p)
    begin('curve_' + route)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.set_float32_matmul_precision('highest')
    torch.use_deterministic_algorithms(True)
    selection, _, _ = inputs(p)
    delta = load(selection['delta']).cuda()
    if delta.ndim == 4:
        delta = delta[0]
    data = CIFAR10(p['data_root'], train=False, download=False)
    labels = torch.tensor(data.targets)
    model = model_reference.ResNet18().cuda().eval()
    rows = []
    with torch.inference_mode():
        for branch in (['benign', 'attack'] if route == 'primary' else ['attack', 'benign']):
            history_path = ROOT / 'fu' / branch / 'MANIFEST.json'
            assert sha(history_path) == read(ROOT / ('TRAINED_' + branch + '.json'))['manifest_sha256']
            for record in read(history_path)['rounds'][:-1]:
                r = record['round']
                model.load_state_dict(load(record['after'], ROOT), strict=True)
                outputs, hashes = [], []
                for start in range(0, 10000, 128):
                    if route == 'primary':
                        x = torch.as_tensor(data.data[start:start+128]).permute(0,3,1,2).contiguous().float().div_(255).sub_(.5).div_(.5)
                    else:
                        a = np.ascontiguousarray(data.data[start:start+128].transpose(0,3,1,2), dtype=np.float32)
                        x = torch.from_numpy((a / np.float32(255) - np.float32(.5)) / np.float32(.5))
                    hashes.append(hashlib.sha256(x.numpy().tobytes()).hexdigest())
                    x = x.cuda()
                    logits = torch.stack([model(x), model((x + 1.5 * delta).clamp(-1, 1))]).cpu()
                    assert bool(torch.isfinite(logits).all())
                    outputs.append(logits)
                logits = torch.cat(outputs, dim=1)
                correct = int((logits[0].argmax(1) == labels).sum())
                hits = int((logits[1].argmax(1)[labels != 2] == 2).sum())
                packet = save(ROOT / 'curve' / route / f'{branch}_{r:02d}.pt',
                              {'logits': logits, 'labels': labels, 'input_hashes': hashes, 'model': record['after']})
                rows.append({'branch': branch, 'round': r, 'correct': correct, 'target_hits': hits,
                             'CA': correct / 100, 'ASR': hits / 90, 'packet': packet})
                write(ROOT / ('CURVE_' + route + '_STATE.json'), {'state': 'running', 'branch': branch,
                      'round': r, 'models_completed': len(rows), 'pid': os.getpid(), 'time': time.time()})
    write(ROOT / ('CURVE_' + route + '.json'), {'state': 'completed', 'rows': rows, 'new_sample_forwards': 760000})


def finalize():
    import torch
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    begin('curve_finalize')
    routes = [read(ROOT / ('CURVE_' + route + '.json')) for route in ['primary', 'independent']]
    by_key = [{(r['branch'], r['round']): r for r in data['rows']} for data in routes]
    assert set(by_key[0]) == set(by_key[1]) == {(b, r) for b in ['benign','attack'] for r in range(1,20)}
    max_error, rows = 0., []
    for key in sorted(by_key[0]):
        a, b = (table[key] for table in by_key)
        assert all(a[k] == b[k] for k in ['correct','target_hits','CA','ASR'])
        x, y = load(a['packet'], ROOT), load(b['packet'], ROOT)
        assert x['model'] == y['model'] and x['input_hashes'] == y['input_hashes']
        assert torch.equal(x['labels'], y['labels']) and torch.equal(x['logits'].argmax(-1), y['logits'].argmax(-1))
        torch.testing.assert_close(x['logits'], y['logits'], rtol=1e-5, atol=1e-6)
        max_error = max(max_error, float((x['logits'] - y['logits']).abs().max()))
        rows.append({k:v for k,v in a.items() if k != 'packet'})
    final = read(ROOT / 'RESULT.json')
    for branch in ['benign','attack']:
        m = final['metrics'][branch]
        rows.append({'branch':branch,'round':20, **{k:m[k] for k in ['correct','target_hits','CA','ASR']}, 'reused_terminal_counts':True})
    lookup = {(r['branch'],r['round']): r for r in rows}
    stable = all(lookup['attack',r]['ASR'] >= 80 and lookup['attack',r]['CA'] >= 80 and
                 lookup['attack',r]['ASR'] - lookup['benign',r]['ASR'] >= 50 for r in range(16,21))
    write(ROOT / 'CURVE_RESULT.json', {'state':'passed_integrity', 'rows':rows,'last5_sustained_activation':stable,
          'independent_max_logit_error':max_error,'pre':final['metrics']['pre'],'independent_training_seeds':1,
          'new_model_training':0,'full_paper_reproduced':False,'full_raw_packets':str(ROOT/'curve')})
    fig, axes = plt.subplots(1,2,figsize=(11,4),layout='constrained')
    for branch,color,label in [('benign','#2463a4','Normal deletion'),('attack','#c53d43','Minus request (Eq.7 all classes)')]:
        for axis,metric in zip(axes,['ASR','CA']):
            axis.plot(range(1,21),[lookup[branch,r][metric] for r in range(1,21)],color=color,marker='o',markersize=3,label=label)
    axes[0].axhline(90.61,color='#777777',linestyle='--',linewidth=1,label='Paper Table IV endpoint: 90.61%')
    for axis,label in zip(axes,['Attack success rate (%)','Clean accuracy (%)']):
        axis.set(xlabel='FU calibration round',ylabel=label,xlim=(1,20),ylim=(0,100))
        axis.set_xticks([1,5,10,15,20]);axis.grid(alpha=.2)
    axes[0].legend(fontsize=7,loc='upper left')
    fig.suptitle('FedUBA declared fixed10 comparison | CIFAR-10 IID | seed 42\nFull round evaluation; no best-round selection',fontsize=11)
    fig.savefig(ROOT/'FU_CURVES.png',dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
    parser = argparse.ArgumentParser()
    parser.add_argument('stage',choices=['primary','independent','finalize'])
    args = parser.parse_args()
    try:
        for name,digest in read(ROOT/'CURVE_FREEZE.json').items():
            assert sha(ROOT/name)==digest, name
        p=setup()
        if args.stage=='finalize':finalize()
        else:evaluate(p,args.stage)
    except BaseException:
        write(ROOT/('CURVE_FAILURE_'+args.stage+'.json'),{'time':time.time(),'traceback':traceback.format_exc()})
        raise
