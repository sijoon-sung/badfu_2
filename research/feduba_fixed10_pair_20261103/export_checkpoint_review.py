"""Seal the actual new pre/normal/attack pair on DISLAB, regardless of performance."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1')
import json
import math
from pathlib import Path
import shutil
import stat
import traceback
import zipfile
from pair_binding import require_published_run
from runtime_common import ROOT, read, write, sha, guard


def main():
    source, launch = require_published_run(); guard()
    with (ROOT / 'EXPORT_ONCE.json').open('x', encoding='utf-8') as stream: json.dump({'pid': os.getpid()}, stream)
    import torch
    import model_reference
    torch.set_num_threads(1)
    result, audit = read(ROOT / 'PAIR_EVAL_RESULT.json'), read(ROOT / 'PAIR_EVAL_VERIFIED.json')
    assert audit['state'] == 'passed' and audit['primary_result_sha256'] == sha(ROOT / 'PAIR_EVAL_RESULT.json')
    assert audit['independent_counts_exactly_equal'] and audit['all_sample_predictions_exactly_equal']
    packet = Path(source['review_packet_root']); packet.mkdir(parents=True, exist_ok=False)
    copied, typed = {}, []
    def copy_file(src, relative):
        src = Path(src); dst = packet / relative
        assert not dst.exists() and dst.resolve().is_relative_to(packet.resolve())
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)
        assert sha(src) == sha(dst)
        copied[relative] = {'sha256': sha(dst), 'bytes': dst.stat().st_size, 'source_path': str(src)}
        return dst
    def finite(value):
        if isinstance(value, torch.Tensor): assert value.device.type == 'cpu' and bool(torch.isfinite(value).all())
        elif isinstance(value, dict):
            for v in value.values(): finite(v)
        elif isinstance(value, (list, tuple)):
            for v in value: finite(v)
        elif isinstance(value, float): assert math.isfinite(value)
    def model_payload(path, classes, key=None):
        value = torch.load(path, map_location='cpu', weights_only=True); finite(value)
        state = value if key is None else value[key]
        model = (model_reference.ResNet18_201() if classes == 201 else model_reference.ResNet18()).cpu().eval()
        model.load_state_dict(state, strict=True)
        with torch.inference_mode(): logits = model(torch.zeros(1, 3, 32, 32))
        assert logits.shape == (1, classes) and bool(torch.isfinite(logits).all())
        typed.append({'file': path.relative_to(packet).as_posix(), 'kind': 'model', 'classes': classes,
                      'payload_key': key, 'strict_CPU': True, 'finite': True, 'zero1_only': True})
        del model, value
    for name, meta in result['source_models'].items():
        path = Path(meta['path']); path = path if path.is_absolute() else ROOT / path
        assert sha(path) == meta['sha256'] and meta['payload_key'] is None
        model_payload(copy_file(path, 'models/' + name + '.pt'), 10)
    teacher = source['inputs']['teacher']; assert sha(teacher['path']) == teacher['sha256']
    model_payload(copy_file(teacher['path'], 'models/teacher201.pt'), 201)
    delta = result['delta']; delta_path = Path(delta['path'])
    if not delta_path.is_absolute(): delta_path = ROOT / delta_path
    target = copy_file(delta_path, 'models/delta.pt')
    d = torch.load(target, map_location='cpu', weights_only=True); finite(d)
    assert d.shape == (1, 3, 32, 32)
    typed.append({'file': 'models/delta.pt', 'kind': 'delta', 'payload_key': None, 'strict_CPU': True, 'finite': True})
    for branch in ['benign', 'attack']:
        manifest = read(ROOT / 'fu' / branch / 'MANIFEST.json')
        for owner in [5, 7]:
            row = next(row for row in reversed(manifest['rounds']) if owner in row['clients'])
            role = next(v for v in row['trained_roles'] if v['client'] == owner)['checkpoint']
            src = Path(role['path']); src = src if src.is_absolute() else ROOT / src
            assert sha(src) == role['sha256']
            model_payload(copy_file(src, f'representative_roles/{branch}/owner{owner}_round{row["round"]:02d}.pt'), 10, 'model')
        for n in ['events.jsonl', 'MANIFEST.json', 'CASE_SELECTION.json']:
            copy_file(ROOT / 'fu' / branch / n, f'logs/{branch}/{n}')
    for path in sorted((ROOT / 'pair_evaluation').rglob('*')):
        if path.is_file():
            dst = copy_file(path, 'evaluation/' + path.relative_to(ROOT / 'pair_evaluation').as_posix())
            if dst.suffix == '.pt':
                finite(torch.load(dst, map_location='cpu', weights_only=True))
                typed.append({'file': dst.relative_to(packet).as_posix(), 'kind': 'evaluation_tensor', 'payload_key': None,
                              'strict_CPU': True, 'finite': True, 'new_model_inference': False})
    previous = read(ROOT / 'SSS_RESULT.json')
    for item in previous['query_packets']:
        meta = item['packet']; src = Path(meta['path'])
        if not src.is_absolute(): src = Path(source['sss_root']) / src
        assert sha(src) == meta['sha256']
        dst = copy_file(src, f'new_fixed10_SSS_queries/owner{item["owner"]}_batch{item["batch"]:02d}.pt')
        finite(torch.load(dst, map_location='cpu', weights_only=True))
        typed.append({'file': dst.relative_to(packet).as_posix(), 'kind': 'new_fixed10_SSS_tensor', 'payload_key': None,
                      'strict_CPU': True, 'finite': True, 'new_model_inference': False})
    # New SSS executed source/profiles/receipts are preserved separately from paired code.
    for path in sorted(Path(source['sss_root']).iterdir()):
        if path.is_file() and path.suffix in ['.py', '.json', '.txt', '.ps1']:
            copy_file(path, 'new_SSS_source_and_receipts/' + path.name)
    for path in sorted(ROOT.iterdir()):
        if path.is_file() and path.suffix in ['.py', '.json', '.txt', '.ps1'] and path.name != 'REMOTE_CHECKPOINT_REVIEW.json':
            copy_file(path, 'source_and_receipts/' + path.name)
    manifest = {'state': 'sealed_new_fixed10_targetclass_pair_remote_review', 'files': copied, 'payloads': typed,
        'models': result['models'], 'operational_gate': result['minimum_operational_gate'],
        'scope': 'Actual endpoints, representative owner contributions/optimizer/RNG, complete epoch logs, private selection, new victim-bound SSS and full evaluation. All raw400 role tensors remain in original new DISLAB root.',
        'full_raw_history_root': str(ROOT), 'local_delivery_complete': False, 'overall_goal_complete': False}
    with (packet / 'DELIVERY_MANIFEST.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(manifest, stream, indent=2, allow_nan=False); stream.write('\n')
    seal = {'manifest_sha256': sha(packet / 'DELIVERY_MANIFEST.json'), 'manifest_bytes': (packet / 'DELIVERY_MANIFEST.json').stat().st_size,
            'hashed_files': len(copied), 'typed_payloads': len(typed)}
    with (packet / 'DELIVERY_SEAL.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(seal, stream, indent=2); stream.write('\n')
    for path in packet.rglob('*'):
        if path.is_file(): path.chmod(stat.S_IREAD)
    archive = ROOT / 'CHECKPOINT_REVIEW.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as stream:
        for path in sorted(packet.rglob('*')):
            if path.is_file(): stream.write(path, path.relative_to(packet).as_posix())
    assert not torch.cuda.is_initialized()
    write(ROOT / 'REMOTE_CHECKPOINT_REVIEW.json', {'state': 'completed_remote_actual_checkpoint_review',
        'packet_root': str(packet), **seal, 'seal_sha256': sha(packet / 'DELIVERY_SEAL.json'),
        'archive': {'path': str(archive), 'bytes': archive.stat().st_size, 'sha256': sha(archive)},
        'local_delivery_complete': False, 'operational_gate': result['minimum_operational_gate'], 'overall_goal_complete': False})


if __name__ == '__main__':
    try: main()
    except BaseException:
        write(ROOT / 'EXPORT_FAILURE.json', {'state': 'failed_preserved', 'traceback': traceback.format_exc()})
        raise
