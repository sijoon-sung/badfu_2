"""Pack derived transforms and receipts, never original endpoint model payloads."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def main():
    (ROOT/'PACKET_ONCE').open('x').write('derived transforms only\n')
    assert json.loads((ROOT/'VERIFIED.json').read_text())['all_counts_exact']
    import torch
    torch.set_num_threads(2)
    from probe_reference import Transform
    cfg = json.loads((ROOT/'PROFILE.json').read_text())
    payload_checks = []
    schedules = {}
    def finite(value):
        if isinstance(value,torch.Tensor): assert torch.isfinite(value).all()
        elif isinstance(value,dict):
            for v in value.values(): finite(v)
        elif isinstance(value,(tuple,list)):
            for v in value: finite(v)
    for p in sorted((ROOT/'artifacts').rglob('*.pt')):
        family,arm = p.stem.split('_')
        data = torch.load(p,map_location='cpu',weights_only=True);finite(data)
        model = Transform(family,cfg);model.load_state_dict(data['transform'],strict=True)
        assert len(data['schedule']) == 400 and all(len(ids) == 20 and min(ids) >= 0 and max(ids) < 320 for ids in data['schedule'])
        assert all(float(s['step']) == 400 for s in data['optimizer']['state'].values())
        if family == 'mask':
            assert model.mask.min() >= 0 and model.mask.max() <= 1 and model.pattern.min() >= 0 and model.pattern.max() <= 1
            assert model.mask.flatten(1).sum(1).max() <= cfg['mask_mass']+1e-4
        elif family == 'additive': assert model.delta.abs().max() <= cfg['epsilon']+1e-7
        schedule_sha = hashlib.sha256(json.dumps(data['schedule']).encode()).hexdigest()
        schedules.setdefault(p.parent.name,set()).add(schedule_sha)
        payload_checks.append(dict(file=p.relative_to(ROOT).as_posix(),sha256=sha(p),strict_cpu_load=True,
                                   finite_all_tensors=True,actual_adam_steps=400,schedule_sha256=schedule_sha))
    assert len(payload_checks) == 60 and all(len(s) == 1 for s in schedules.values())
    (ROOT/'CPU_PAYLOAD_AUDIT.json').write_text(json.dumps(dict(payload_checks=payload_checks,
                    all_60_strict_finite=True,same_case_arm_and_family_schedules_exact=True),indent=2)+'\n',encoding='utf-8')
    files = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in ('.py','.json','.txt') and
             not p.name.startswith(('recovery_controller','controller.','prepare.')) and p.name != 'FINAL_FILES.json']
    files += [p for p in (ROOT/'artifacts').rglob('*') if p.is_file()]
    files += [p for d in ('admission_blocked','admission_blocked_command_identity') for p in (ROOT/d).rglob('*') if p.is_file()]
    manifest = {p.relative_to(ROOT).as_posix():dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(files)}
    (ROOT/'PACKET_MANIFEST.json').write_text(json.dumps(dict(scope='derived transforms, all arm schedules/optimizer/RNG/calibration, source and receipts; original endpoints/raw public data excluded',files=manifest),indent=2)+'\n',encoding='utf-8')
    packet = ROOT/'DERIVED_REVIEW_PACKET.zip'
    with zipfile.ZipFile(packet,'x',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
        for p in files+[ROOT/'PACKET_MANIFEST.json']:z.write(p,p.relative_to(ROOT).as_posix())
    (ROOT/'PACKET_SEAL.json').write_text(json.dumps(dict(file=packet.name,sha256=sha(packet),bytes=packet.stat().st_size,files=len(manifest)),indent=2)+'\n',encoding='utf-8')
    print('Derived review packet sealed: '+str(len(manifest))+' files')


if __name__ == '__main__': main()
