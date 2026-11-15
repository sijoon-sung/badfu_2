"""Explicit diagnostic optimizers; never substitutes Adam for the paper Algorithm 1."""
import torch
from torch import nn


def learn(model, x, y, settings, *, phase_seed, phase, gradient_weights=None, reference=None, log=None, optimizer_policy=None):
    assert gradient_weights is not None and reference is None
    assert optimizer_policy in ['algorithm_sgd','experimental_adam']
    literal = optimizer_policy == 'algorithm_sgd'
    optimizer = (torch.optim.SGD(model.parameters(), lr=settings.lr, foreach=True) if literal
                 else torch.optim.Adam(model.parameters(), lr=settings.lr, foreach=True))
    model.train()
    ref = torch.nn.utils.parameters_to_vector(reference.parameters()).detach() if reference is not None else None
    device = x.device
    generator = torch.Generator(device=device).manual_seed(phase_seed)
    batches = 0
    for epoch in range(settings.epochs):
        order = torch.randperm(len(y), generator=generator, device=device)
        total = torch.zeros((), device=device)
        finite = torch.ones((), dtype=torch.bool, device=device)
        for idx in order.split(settings.batch):
            optimizer.zero_grad(set_to_none=True)
            loss = nn.functional.cross_entropy(model(x[idx]), y[idx])
            if ref is not None:
                vector = torch.nn.utils.parameters_to_vector(model.parameters())
                loss = loss + settings.consistency * (vector - ref).square().sum()
            finite.logical_and_(torch.isfinite(loss.detach()))
            loss.backward()
            if gradient_weights is not None:
                with torch.no_grad():
                    for name, parameter in model.named_parameters():
                        parameter.grad.mul_(gradient_weights[name])
            optimizer.step()
            total.add_(loss.detach() * len(idx))
            batches += 1
        state_finite = torch.stack([torch.isfinite(v).all() for v in model.state_dict().values()]).all()
        if not bool(finite & state_finite):
            raise FloatingPointError('Nonfinite epoch; role is not submitted')
        if log:
            import hashlib
            order_hash=hashlib.sha256(order.detach().cpu().numpy().astype('<i8',copy=False).tobytes()).hexdigest()
            log(order_sha256=order_hash,phase=phase, epoch=epoch + 1, epochs=settings.epochs, batches=batches,
                examples=len(y), loss=float(total) / len(y), optimizer=type(optimizer).__name__)
    return model, optimizer, generator.get_state(), batches
