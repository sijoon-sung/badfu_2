"""Explicit optimizer choice for a declared FUBA interpretation."""
import torch


def make_reweighted_optimizer(parameters, *, interpretation, learning_rate):
    if interpretation == 'algorithm_sgd':
        return torch.optim.SGD(parameters, lr=learning_rate)
    if interpretation == 'experimental_adam':
        return torch.optim.Adam(parameters, lr=learning_rate)
    raise ValueError('Choose algorithm_sgd or experimental_adam explicitly')


def apply_weights(model, weights):
    if dict(model.named_parameters()).keys() != weights.keys():
        raise ValueError('Gradient weight names do not match model')
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            if parameter.grad is not None:
                parameter.grad.mul_(weights[name])
