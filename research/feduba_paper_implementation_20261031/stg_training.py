"""Explicit canonical paper STG helpers; no victim parameters/data are accepted."""
import numpy as np
from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms
import core


class ExternalImages(Dataset):
    def __init__(self, images_HWC_uint8, labels, augment=True):
        assert images_HWC_uint8.device.type == labels.device.type == 'cpu'
        assert images_HWC_uint8.dtype == torch.uint8 and images_HWC_uint8.shape[1:] == (32, 32, 3)
        assert len(images_HWC_uint8) == len(labels)
        self.images, self.labels = images_HWC_uint8, labels
        ops = [transforms.RandomCrop(32, padding=4), transforms.RandomHorizontalFlip()] if augment else []
        self.transform = transforms.Compose(ops + [transforms.ToTensor(), transforms.Normalize((.5,) * 3, (.5,) * 3)])

    def __len__(self):
        return len(self.images)

    def __getitem__(self, index):
        image = Image.fromarray(self.images[index].numpy())
        return self.transform(image), int(self.labels[index])


def freeze_trigger_surrogate(model):
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
        parameter.grad = None


def projected_sgd_batch(model, x, targets, delta, optimizer, epsilon_model):
    assert not model.training and not any(parameter.requires_grad for parameter in model.parameters())
    assert isinstance(optimizer, torch.optim.SGD)
    assert len(optimizer.param_groups) == 1 and optimizer.param_groups[0]['params'] == [delta]
    assert optimizer.param_groups[0]['momentum'] == 0 and optimizer.param_groups[0]['weight_decay'] == 0
    return core.trigger_step(model, x, targets, delta, optimizer, epsilon_model)
