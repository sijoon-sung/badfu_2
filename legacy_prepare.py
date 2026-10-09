"""Run the trusted, pinned upstream data preparation with modern PyTorch compatibility."""
import os
import runpy
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent
torch.hub.set_dir(str(ROOT / "data/torch"))
torch.set_num_threads(4)
original_load = torch.load


def trusted_load(*args, **kwargs):
    # Only use this wrapper for artifacts produced locally by the pinned upstream.
    kwargs.setdefault("weights_only", False)
    return original_load(*args, **kwargs)


if __name__ == "__main__":
    torch.load = trusted_load
    stage = sys.argv[1]
    relative = {"base": "attack/badnet.py", "cover": "uba/uba_inf_cover.py"}[stage]
    script = ROOT / "upstream/data_prepare" / relative
    sys.argv = [str(script), *sys.argv[2:]]
    sys.path[0] = str(script.parent)
    os.chdir(script.parent)
    runpy.run_path(str(script), run_name="__main__")
