# BadFU / XAI incremental-value experiment

**Current priority: original reproduction.** The earlier `experiment.py` prototype materially
changed the upstream unlearning computation and is not valid evidence for BadFU reproduction.
Its run was stopped and checkpoints preserved. See `results/audit/changes.json`.

Use `run_reference.ps1` with the dedicated `envs/badfu-original` Conda environment
(Python 3.11, PyTorch 2.4.1+cu118, torchvision 0.19.1, numpy 1.26.4).
Exact installed package versions are in `original-environment-lock.txt`.
To pause after the current round is saved, run `./pause_reference.ps1`.
To continue later, run `./resume_reference.ps1`; completed rounds are skipped and
the model plus Python/NumPy/CPU/CUDA RNG states are restored from checkpoints.
Keep `results/reference` (including `history`), `upstream/data_prepare/record/badnet_original`,
and the downloaded data intact. GitHub code alone cannot restore trained checkpoints.
The one-time `pause_running_legacy.ps1` safely pauses a runner launched before pause support existed.
`reference_runner.py` executes the unchanged function/class definitions from `upstream/badfu.py`.
An AST assertion enforces this, including `local_train`, `fed_avg`, `evaluate_model`,
and `unlearning_step_once`. Original defaults: 5 clients, dominant ratio 0.7,
40 rounds, 5 local epochs, seed 42. All six original training/unlearning phases run.
History is stored on disk and reloaded with bitwise state and RNG preservation;
Windows workers are set to zero. Each round checkpoints state and RNG for resumption.

**Preparation exception:** the final `rm`/`mv` commands in the public shell script
invalidate its saved poison/cover file paths (0/850 cover references would survive in the
generated artifact). They are not executed. Fresh upstream-generated images, labels,
indices and poison/cover ratios are retained; only their path strings become absolute.
Consequently this is original training/unlearning reproduction with a documented data
preparation exception, not a claim that the published shell script runs unchanged end to end.
`--smoke` changes rounds/epochs solely for runtime QA and cannot count as attack reproduction.

Question: do clean-input explanation changes predict post-unlearning ASR changes beyond
accuracy, target probability, margin, confidence, and client class composition on held-out FL seeds?

## Environment

Existing Conda environment: `C:\Users\sijoo\.conda\envs\pytorch`.
Use its Python directly; this still uses the Conda environment and avoids PATH ambiguity.
GPU detected: RTX 4060 Laptop, 8 GiB. Upstream pinned to
`0a2117feab58faf5b7e2a1e5e1759112087d6049` from https://github.com/BingguangLu/BadFU.
Download upstream into `upstream/`. Runtime versions and artifact hash are saved in every run's manifest.

## Data preparation

Run `download_data.py` to download an unchanged MIT mirror archive with torchvision's MD5 verification.
Run `legacy_prepare.py base` with the official `badnet.py` arguments from `prepare_data.sh`,
using `--epochs 0 --device cuda:0 --num_workers 0`.
Use `--save_folder_name badnet_seed0`. Then run `legacy_prepare.py cover --dataset_folder ../record/badnet_seed0 --device cuda:0
--ft_epochs 1 --ap_epochs 1 --num_workers 0`.
The wrapper permits legacy pickle only for locally produced upstream data.
It does not execute the upstream shell script's deletion/move operations.

## Run

`./run_pilot.ps1`: 20 evaluated client distributions, alpha 0.5, 3 seeds,
10 FL rounds, 1 local epoch, stratified approximately 10k training images,
100 explanation images, 16 GradientSHAP samples.

`./run_full.ps1`: 20 distributions, IID and three non-IID levels, 5 seeds,
all CIFAR-10 data, 40 rounds, 5 local epochs, 500 explanation images,
50 GradientSHAP samples. This is much more expensive than the pilot.

The virtual cover client adds one participant, giving **21 actual training participants**.
This adapts the official auxiliary-client branch; it is not literal sample-level deletion
from a single malicious client. Clean data on client 0 are duplicated in the cover client,
as in that upstream branch. Pretrained ImageNet ResNet-18 body follows upstream initialization;
the CIFAR convolution and classifier are fresh. Set `--no-pretrained` for training from scratch.

## Conditions and limitations

1. Clean FL, remove the auxiliary clean client.
2. Clean FL, continue with all clients for matched local update epochs.
3. Poisoned FL, remove the auxiliary influence-crafted cover client.
4. Poisoned FL, continue with all clients for matched local update epochs.
5. Poisoned FL, remove a benign client (client 1).

The fifth condition does **not** match deletion size exactly; report its sample count.
Calibrated deletion restarts from the common initialization and uses every second historical
round's retained-client update norms with data-size-weighted aggregation. Parameter updates
have zero-norm protection; BN buffers use freshly aggregated buffers. These correct/adapt
the legacy implementation's averaging, indexing and zero division, so this is **not an exact
BadFU paper reproduction** and deletion validity is not certified. Hold controls continue
from the pre-unlearning checkpoint for an equal number of local epochs; the optimization
paths differ by design. Local epoch equality is not exact FLOP equality after removing a client.

The influence-crafted artifact is fixed (seed 0); FL initialization, partitions, and selected
poison/cover subsets vary by seed. Results generalize over these seeds conditional on this
one attack artifact. Independently recrafting artifacts is a required follow-up for broader claims.

Test images are separate from training. Client test distributions are disjoint and use
train-derived class allocation probabilities. ASR excludes original target-class examples.
XAI uses a separate fixed stratified test-image subset, identical across pre/post states.
Client XAI values are class-stratified estimates weighted by that client's test class proportions,
not measured explanations for every individual client test image. Client values are dependent.
The final test pool is not used to choose the detector's regularization or features.

## Analysis

Baseline: pre/delta clean accuracy, target probability, target-vs-other logit margin,
maximum confidence, alpha and nine class proportions. XAI additions: clean-input JSD for
fixed target/true class and absolute attribution mass changes. Neither triggered outputs,
trigger masks, post-ASR, nor condition IDs enter the predictors.

Fixed Ridge regularization 10; preprocessing fits only training folds.
Also compare fixed HistGradientBoosting models to check whether an apparent gain is
specific to a linear baseline. Both model families are declared before running outcomes.
Leave-one-seed-out validation holds out every condition/alpha/client for that seed together.
MAE/RMSE/R2, per-seed paired improvement and seed-block bootstrap are saved.
Three seeds and the bootstrap interval are exploratory, not strong inferential evidence.
Predeclared pilot activation gate: attack pre-ASR <= 30%, delta ASR >= 20 percentage points.
If the gate fails, improved regression alone does not demonstrate dormant-backdoor detection.

Outputs: `manifest.json`, per-run configs, splits, checkpoints, attribution caches,
image-level XAI tables, client metrics, global metrics, held-out predictions,
`analysis.json`, `REPORT.md`. Resume with exactly the same command; use a fresh output
directory for changed configuration. `analysis.py results/pilot` recomputes the analysis.
`python -m unittest test_experiment.py` verifies grouping/no label leakage,
partition conservation, aggregation and attribution repeatability.
