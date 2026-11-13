"""Exercise the real dependency chain, with no data or checkpoints opened."""
import importlib.metadata
import torch
from torchvision.datasets import CIFAR10
from torchvision import transforms
from fu_core import owned_selection, branch_dataset, local_schedule, calibration_round
from fu_training import train_role
from runtime_common import save
import model_reference
from bindings import ROOT, read, write

cfg = read(ROOT / 'PROFILE.json')
assert all(importlib.metadata.version(n) == v for n,v in cfg['packages'].items())
assert all(callable(f) for f in (CIFAR10,transforms.Compose,owned_selection,branch_dataset,local_schedule,
           calibration_round,train_role,save,model_reference.ResNet18))
assert not torch.cuda.is_initialized()
write(ROOT/'DEPENDENCY_CHECK.json',dict(state='passed',CUDA_initialized=False,tensor_loads=0,training_steps=0))
