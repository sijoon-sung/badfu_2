"""Shared actual paired-FU local SGD engine; synthetic wiring checks use CPU only."""
import math
import torch
from torch.utils.data import DataLoader, Dataset
from runtime_common import seed, rng, cpu


class TracedDataset(Dataset):
    def __init__(self, dataset, source_ids):
        assert len(dataset) == len(source_ids) == len(set(source_ids))
        self.dataset, self.source_ids = dataset, list(source_ids)

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, index):
        x, y = self.dataset[index]
        return x, y, self.source_ids[index]


def train_role(model, dataset, source_ids, schedule, device, on_epoch):
    assert schedule['epochs'] == 5 and schedule['batch_size'] == 128
    assert schedule['expected_batches'] == math.ceil(len(dataset) / 128) * 5
    device = torch.device(device)
    seed(schedule['seed']); model.train()
    for parameter in model.parameters():
        parameter.requires_grad_(True)
    optimizer = torch.optim.SGD(model.parameters(), lr=schedule['lr'], momentum=.9, weight_decay=0)
    generator = torch.Generator().manual_seed(schedule['seed'])
    loader = DataLoader(TracedDataset(dataset, source_ids), batch_size=128, shuffle=True,
                        generator=generator, num_workers=0, pin_memory=device.type == 'cuda')
    epochs, total_batches, edge_batches = [], 0, []
    for epoch in range(1, 6):
        rng_before, loader_before = rng(), generator.get_state()
        count = batches = 0; loss_sum = 0.; ids_seen = []
        for x, y, ids in loader:
            # Preserve the two fixed edge inputs for later source/label/BEA diagnosis.
            if (epoch == 1 and batches == 0) or (epoch == 5 and batches == len(loader) - 1):
                edge_batches.append({'epoch': epoch, 'batch': batches + 1, 'x': x.clone(), 'labels': y.clone(), 'source_ids': ids.clone()})
            ids_seen.append(ids)
            x, y = x.to(device).contiguous(), y.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = torch.nn.functional.cross_entropy(model(x), y)
            assert bool(torch.isfinite(loss))
            loss.backward(); optimizer.step()
            loss_sum += float(loss.detach()) * len(y); count += len(y); batches += 1
        assert count == len(dataset) and batches == math.ceil(len(dataset) / 128) and math.isfinite(loss_sum)
        total_batches += batches
        record = {'epoch': epoch, 'examples': count, 'batches': batches, 'cumulative_role_batches': total_batches,
                  'loss': loss_sum / count, 'source_ids': torch.cat(ids_seen),
                  'rng_before_epoch': rng_before, 'rng': rng(), 'loader_rng_before_epoch': loader_before,
                  'loader_rng': generator.get_state()}
        epochs.append(record)
        on_epoch({k: v for k, v in record.items() if k not in ['source_ids', 'rng_before_epoch', 'rng', 'loader_rng_before_epoch', 'loader_rng']})
    assert total_batches == schedule['expected_batches']
    assert all(bool(torch.isfinite(v).all()) for v in model.state_dict().values())
    return cpu({'model': model.state_dict(), 'optimizer': optimizer.state_dict(), 'epochs': epochs,
                'batches': total_batches, 'source_indices': source_ids, 'schedule': schedule,
                'edge_batches': edge_batches, 'rng': rng(), 'loader_rng': generator.get_state()})
