# Original BadFU reproduction and resume

Upstream: https://github.com/BingguangLu/BadFU at
`0a2117feab58faf5b7e2a1e5e1759112087d6049`.

On Windows with NVIDIA GPU and Conda-enabled PowerShell:

```powershell
./setup_reference.ps1
./resume_reference.ps1
```

The first command is for a fresh installation. On the existing experiment PC,
only `./resume_reference.ps1` is needed. It appends to `reference.log` and restores
saved model weights, buffers and Python/NumPy/CPU/CUDA RNG states; completed rounds
are skipped. The original configuration remains seed 42, 5 regular clients,
dominant ratio 0.7, 40 communication rounds and 5 local epochs.

From another PowerShell in this folder, request a pause:

```powershell
./pause_reference.ps1
```

The updated runner finishes the current round, saves an atomic checkpoint, and
exits normally. Wait for `REFERENCE_PAUSED` in the log and `results/reference/paused.json`
before shutting down. An interrupted unsaved round is repeated on restart.
Never run two experiments against the same result directory.

Keep these directories for continuation:

- `results/reference/`, including checkpoints, manifest, metrics and `history/`.
- `upstream/data_prepare/record/badnet_original/`, including all generated images.
- `upstream/data_prepare/data/cifar10/` and `data/torch/`.
- `envs/badfu-original/` on this PC, or recreate it with the setup script elsewhere.

Large data, environments and trained checkpoints are excluded from Git. **Cloning
this repository alone starts a fresh experiment, not a continuation of a trained run.**
To move PCs, transfer the result/data directories too. Absolute image references
are regenerated from the original artifact; retain its relative directory layout.

All upstream training, aggregation, evaluation and unlearning function/class
definitions are protected by AST equality assertions. The wrapper changes file
paths, Windows worker count and history storage, and adds checkpoint/pause hooks.
Tests verify original defaults, bitwise historical model state, RNG preservation
and the pause marker behavior.

Preparation exception: the public preparation shell script's final delete/move
commands invalidate generated image references. They are omitted; official
generated images, labels, indices and ratios are retained. This is original
training/unlearning execution with that documented exception.

On completion, `results/reference/REPORT.md` and `summary.json` contain the six
original phases and the auxiliary cover-client deletion ASR change. The earlier
modified prototype is not evidence of original reproduction.
