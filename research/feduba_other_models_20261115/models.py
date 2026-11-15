"""Explicitly recovered model dependencies for the other FedUBA datasets."""
import hashlib
import importlib.util
from pathlib import Path

PINNED = {'mobilenetv2.py':'7e5ee0d8d9ecd923fb9acb28499d44554d57091f5f81375e1a731d8624d928b0',
          'vgg.py':'4a3701fa9d21f8e8cd3fb3e4b732092dfe93ba898388eaed6164e969149bbdf9'}


def create_model(dataset, recovered_root):
    configs = {'PATHMNIST':('mobilenetv2.py',9), 'PATHMNIST_outter':('mobilenetv2.py',8),
               'GTSRB':('vgg.py',43), 'GTSRB_outter':('vgg.py',59)}
    if dataset not in configs:
        raise ValueError('unsupported dataset; CIFAR uses the separately pinned ResNet')
    name, classes = configs[dataset]
    path = Path(recovered_root)/name
    assert hashlib.sha256(path.read_bytes()).hexdigest()==PINNED[name]
    spec=importlib.util.spec_from_file_location('recovered_'+path.stem,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.MobileNetV2(classes) if name=='mobilenetv2.py' else module.VGG('VGG11',classes)
