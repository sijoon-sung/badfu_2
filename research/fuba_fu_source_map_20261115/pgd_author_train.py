"""Entire IBM notebook ascent loop; no implicit FUBA history or source choice."""
import copy
import torch
from torch import nn
from pgd_author_kernel import squared_distance, project_author_, stop_author


def unlearn_author(reference, deleted_client, loader, *, radius_squared,
                   distance_threshold, epochs=5, lr=.01, momentum=.9, clip_grad=5., capture=None):
    if epochs <= 0 or lr <= 0 or clip_grad <= 0:
        raise ValueError('Positive declared iteration and optimization settings required')
    model = copy.deepcopy(reference).train()
    optimizer = torch.optim.SGD(model.parameters(), lr=lr, momentum=momentum)
    records = []
    for epoch in range(epochs):
        count = 0
        for batch, (x, y) in enumerate(loader):
            optimizer.zero_grad()
            loss = nn.functional.cross_entropy(model(x), y)
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError('Nonfinite ascent loss')
            (-loss).backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), clip_grad)
            optimizer.step()
            before = float(squared_distance(model, reference))
            project_author_(model, reference, radius_squared=radius_squared)
            stop = stop_author(model, deleted_client, distance_threshold=distance_threshold)
            record = {'epoch': epoch+1, 'batch': batch+1, 'loss': float(loss.detach()),
                      'projected': before > radius_squared,
                      'squared_reference_distance': float(squared_distance(model, reference)),
                      'squared_deleted_distance': float(squared_distance(model, deleted_client)),
                      'stop': stop}
            records.append(record)
            count += 1
            if capture:
                capture(model, optimizer, record)
            if stop:
                return model, optimizer, records
        if not count:
            raise ValueError('Empty deletion loader')
    return model, optimizer, records
