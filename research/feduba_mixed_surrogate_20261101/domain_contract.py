"""One genuinely new synthetic overlap/domain/tail contract, zero model calls."""
import os
os.environ.update(CUDA_VISIBLE_DEVICES='-1', PYTHONDONTWRITEBYTECODE='1')
import sys
import traceback
sys.dont_write_bytecode = True
import torch
from torch.utils.data import DataLoader
from mixed_common import ROOT, once, frozen, MixedImages


def main():
    frozen(); torch.set_num_threads(2)
    once('DOMAIN_CONTRACT_ONCE.json', {'pid': os.getpid(), 'real_data_reads': 0, 'model_forward_calls': 0})
    # Expanded synthetic arrays have the real cardinalities without loading real images.
    tiny = {'images_HWC_uint8': torch.full((1, 32, 32, 3), 12, dtype=torch.uint8).expand(100000, -1, -1, -1)}
    target = {'images_HWC_uint8': torch.full((1, 32, 32, 3), 128, dtype=torch.uint8).expand(200, -1, -1, -1)}
    labels, ids = torch.arange(100000) % 200, torch.arange(400, 600)
    mixed = MixedImages(tiny, target, labels, ids, augment=False)
    warm = MixedImages(tiny, target, labels, ids, warmup=True, augment=False)
    expected = [(mixed, 0, (0, 0, 0, 0), 12), (mixed, 400, (0, 400, 0, 400), 12),
                (mixed, 99999, (199, 99999, 0, 99999), 12),
                (mixed, 100000, (200, 100000, 1, 400), 128),
                (mixed, 100199, (200, 100199, 1, 599), 128),
                (warm, 0, (200, 100000, 1, 400), 128), (warm, 199, (200, 100199, 1, 599), 128)]
    checked = []
    for data, index, metadata, pixel in expected:
        x, *actual = data[index]
        assert tuple(actual) == metadata
        checked.append(tuple(actual))
        normalized = torch.tensor(float(pixel)).div(255).sub(.5).div(.5)
        assert x.dtype == torch.float32 and x.is_contiguous() and torch.equal(x, torch.full((3, 32, 32), float(normalized)))
    assert checked[1][2:] == (0, 400) and checked[3][2:] == (1, 400)
    assert checked[1][2:] != checked[3][2:]
    tails = []
    for n, batches, tail in [(100200, 783, 104), (200, 2, 72)]:
        rows = list(DataLoader(torch.arange(n), batch_size=128, shuffle=True,
                              generator=torch.Generator().manual_seed(1000), num_workers=0))
        assert len(rows) == batches and len(rows[-1]) == tail
        assert torch.equal(torch.cat(rows).sort().values, torch.arange(n)); tails.append(tail)
    assert not torch.cuda.is_initialized()
    once('DOMAIN_CONTRACT_RESULT.json', {'state': 'passed', 'CPU_only': True, 'CPU_threads': 2,
         'synthetic_image_getitems': 7, 'sampler_passes': 2, 'tails': tails,
         'raw_ID400_preserved_in_two_distinct_domains': True, 'real_data_reads': 0,
         'model_forward_calls': 0, 'optimizer_steps': 0, 'completed_old_fixture_repeated': False})


if __name__ == '__main__':
    try: main()
    except BaseException:
        once('DOMAIN_CONTRACT_FAILURE.json', {'state': 'failed_preserved', 'pid': os.getpid(), 'traceback': traceback.format_exc()})
        raise
