"""Train normal MNIST FedAvg and measure a benign participant deletion."""

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import struct
import time

import torch
from torch import nn
from torch.nn import functional as F


@dataclass(frozen=True)
class Profile:
    rounds: int
    local_epochs: int
    kd_epochs: int
    seed: int = 20261023
    partition_seed: int = 20261020
    clients: int = 20
    per_round: int = 8
    batch_size: int = 64
    deleted: int = 4
    recovery: int = 5
    local_lr: float = 0.001
    kd_lr: float = 0.01
    temperature: float = 30.0


PROFILES = {"baseline": Profile(20, 2, 10), "paper-scale": Profile(100, 50, 10)}
RAW_FILES = (
    "train-images-idx3-ubyte", "train-labels-idx1-ubyte",
    "t10k-images-idx3-ubyte", "t10k-labels-idx1-ubyte",
)


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 6, 5)
        self.conv2 = nn.Conv2d(6, 16, 5)
        self.fc1 = nn.Linear(256, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, 10)

    def forward(self, images):
        hidden = F.max_pool2d(F.relu(self.conv1(images)), 2)
        hidden = F.max_pool2d(F.relu(self.conv2(hidden)), 2)
        hidden = F.relu(self.fc1(hidden.flatten(1)))
        return self.fc3(F.relu(self.fc2(hidden)))


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path, data):
    pending = path.with_suffix(".tmp")
    pending.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    pending.replace(path)


def read_split(raw, image_name, label_name, expected):
    images = bytearray((raw / image_name).read_bytes())
    labels = bytearray((raw / label_name).read_bytes())
    if (len(images) != 16 + expected * 784 or len(labels) != 8 + expected
            or struct.unpack_from(">4I", images) != (2051, expected, 28, 28)
            or struct.unpack_from(">2I", labels) != (2049, expected)):
        raise ValueError(f"Invalid MNIST IDX files: {image_name}, {label_name}")
    x = torch.frombuffer(images, dtype=torch.uint8, offset=16).reshape(expected, 1, 28, 28)
    y = torch.frombuffer(labels, dtype=torch.uint8, offset=8).long()
    if y.max().item() >= 10:
        raise ValueError(f"Invalid MNIST label: {label_name}")
    return x, y


@torch.inference_mode()
def clean_counts(model, images, labels, device):
    model.eval()
    confusion = torch.zeros((10, 10), dtype=torch.int64, device=device)
    for x, y in zip(images.split(256), labels.split(256), strict=True):
        logits = model(x.to(device=device, dtype=torch.float32).div_(255))
        if not torch.isfinite(logits).all().item():
            raise ValueError("Nonfinite evaluation logits")
        pred = logits.argmax(1)
        confusion += torch.bincount(y.to(device) * 10 + pred, minlength=100).reshape(10, 10)
    correct = int(confusion.trace().item())
    total = int(confusion.sum().item())
    if total != labels.numel():
        raise ValueError("Incomplete clean evaluation")
    return {"clean_correct": correct, "N": total, "CA_pct": 100 * correct / total,
            "class_confusion": confusion.cpu().tolist()}


def generator(seed):
    return torch.Generator().manual_seed(seed)


def local_train(model, incoming, x, y, profile, seed):
    model.load_state_dict(incoming, strict=True)
    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=profile.local_lr)
    order_rng = generator(seed)
    for _ in range(profile.local_epochs):
        for index in torch.randperm(len(y), generator=order_rng).split(profile.batch_size):
            optimizer.zero_grad(set_to_none=True)
            loss = F.cross_entropy(model(x[index]), y[index])
            loss.backward()
            optimizer.step()
    if not torch.isfinite(loss).item():
        raise ValueError("Nonfinite local loss")
    return loss.item()


def emit(output, event):
    event = {**event, "elapsed_s": round(time.monotonic() - START, 3)}
    with (output / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, allow_nan=False) + "\n")
    print(json.dumps(event, allow_nan=False), flush=True)


def fedavg(model, initial, shards, schedule, profile, output, retained_only=False):
    phase = "retained_retrain" if retained_only else "before_fl"
    incoming = initial
    delta = {name: torch.zeros_like(value, dtype=torch.float64)
             for name, value in initial.items()}
    deleted_rounds = []
    for number, drawn in enumerate(schedule, 1):
        participants = [client for client in drawn if not retained_only or client != profile.deleted]
        summed = {name: torch.zeros_like(value, dtype=torch.float64)
                  for name, value in incoming.items()}
        sizes = {client: len(shards[client][1]) for client in participants}
        n_samples = sum(sizes.values())
        losses = []
        for client in participants:
            x, y = shards[client]
            losses.append(local_train(model, incoming, x, y, profile,
                                      profile.seed + number * profile.clients + client))
            weight = sizes[client] / n_samples
            if client == profile.deleted:
                deleted_rounds.append(number)
            for name, local in model.state_dict().items():
                summed[name].add_(local, alpha=weight)
                if client == profile.deleted:
                    delta[name].add_(local.double() - incoming[name].double(), alpha=weight)
        incoming = {name: summed[name].to(value.dtype) for name, value in incoming.items()}
        if not all(torch.isfinite(value).all().item() for value in incoming.values()):
            raise ValueError(f"Nonfinite global state in {phase} round {number}")
        emit(output, {"stage": phase, "round": number, "participants": participants,
                      "samples_per_epoch": n_samples, "mean_last_batch_loss": sum(losses) / len(losses)})
    return incoming, delta, deleted_rounds


def recover(student, before, delta, data, profile, output):
    student.load_state_dict(
        {name: (value.double() - delta[name]).to(value.dtype) for name, value in before.items()},
        strict=True,
    )
    teacher = Net().to(data.device).eval()
    teacher.load_state_dict(before, strict=True)
    with torch.no_grad():
        soft_labels = torch.cat([
            F.softmax(teacher(batch) / profile.temperature, dim=1)
            for batch in data.split(profile.batch_size)
        ])
    student.train()
    optimizer = torch.optim.SGD(student.parameters(), lr=profile.kd_lr, momentum=0.9)
    order_rng = generator(profile.seed + 10000)
    for epoch in range(1, profile.kd_epochs + 1):
        loss_sum = 0.0
        for index in torch.randperm(len(data), generator=order_rng).split(profile.batch_size):
            optimizer.zero_grad(set_to_none=True)
            log_probs = F.log_softmax(student(data[index]) / profile.temperature, dim=1)
            loss = F.kl_div(log_probs, soft_labels[index], reduction="batchmean")
            loss.backward()
            optimizer.step()
            loss_sum += loss.item() * len(index)
        emit(output, {"stage": "benign_kd", "epoch": epoch, "samples": len(data),
                      "mean_kl": loss_sum / len(data)})
    return student.state_dict()


def endpoint(model, state, output, name, test, device):
    model.load_state_dict(state, strict=True)
    model_file = output / f"{name}.pt"
    cpu_state = {key: value.detach().cpu().clone() for key, value in state.items()}
    if not all(torch.isfinite(value).all().item() for value in cpu_state.values()):
        raise ValueError(f"Nonfinite endpoint {name}")
    torch.save(cpu_state, model_file)
    return {**clean_counts(model, *test, device), "file": model_file.name, "sha256": digest(model_file)}


def run(profile_name, raw, output, device):
    profile = PROFILES[profile_name]
    raw_hashes = {name: digest(raw / name) for name in RAW_FILES}
    train_x, train_y = read_split(raw, *RAW_FILES[:2], 60000)
    test = read_split(raw, *RAW_FILES[2:], 10000)
    torch.manual_seed(profile.seed)
    model = Net().to(device)
    initial = {key: value.detach().clone() for key, value in model.state_dict().items()}
    order = torch.randperm(len(train_y), generator=generator(profile.partition_seed))
    shards = [(train_x[i].to(device=device, dtype=torch.float32).div_(255), train_y[i].to(device))
              for i in order.tensor_split(profile.clients)]
    client_rng = generator(profile.seed)
    schedule = [torch.randperm(profile.clients, generator=client_rng)[:profile.per_round].tolist()
                for _ in range(profile.rounds)]
    if not any(profile.deleted in drawn for drawn in schedule):
        raise ValueError("Deletion candidate had no recorded participation")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "profile.json", {
        "profile": profile_name, **asdict(profile), "device": str(device),
        "torch": str(torch.__version__), "source_sha256": digest(Path(__file__)),
        "dataset_sha256": raw_hashes, "schedule": schedule,
        "partition_sha256": hashlib.sha256(order.numpy().tobytes()).hexdigest(),
    })
    try:
        before, delta, deleted_rounds = fedavg(model, initial, shards, schedule, profile, output)
        results = {"before": endpoint(model, before, output, "before", test, device)}
        after = recover(model, before, delta, shards[profile.recovery][0], profile, output)
        results["benign_kd"] = endpoint(model, after, output, "benign_kd", test, device)
        retained, _, _ = fedavg(model, initial, shards, schedule, profile, output, retained_only=True)
        results["retained_retrain"] = endpoint(model, retained, output, "retained_retrain", test, device)
        gap = results["benign_kd"]["CA_pct"] - results["retained_retrain"]["CA_pct"]
        write_json(output / "result.json", {"profile": profile_name, "deleted_rounds": deleted_rounds,
                   **results, "kd_minus_retrain_CA_pp": gap, "utility_within_2pp": abs(gap) <= 2})
    except BaseException as error:
        write_json(output / "failure.json", {"type": type(error).__name__, "message": str(error)})
        raise


START = time.monotonic()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default="baseline")
    parser.add_argument("--mnist-raw", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = parser.parse_args()
    torch.set_num_threads(2)
    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA requested but unavailable")
    run(args.profile, args.mnist_raw, args.output, torch.device(args.device))
