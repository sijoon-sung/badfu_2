"""Compare the prototype against the unchanged upstream unlearning function."""
import ast
import copy
import json
from pathlib import Path

import torch
from torch import nn

from experiment import aggregate, calibrated_state, resolve_image

ROOT = Path(__file__).resolve().parent


def original_function():
    tree = ast.parse((ROOT / "upstream/badfu.py").read_text(encoding="utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "unlearning_step_once")
    namespace = {"torch": torch, "copy": copy}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "upstream/badfu.py", "exec"), namespace)
    return namespace["unlearning_step_once"]


class TinyState(nn.Module):
    def __init__(self, w, buffer):
        super().__init__()
        self.w = nn.Parameter(torch.tensor([float(w)]))
        self.register_buffer("bn", torch.tensor([float(buffer)]))


if __name__ == "__main__":
    reference = original_function()
    old = [TinyState(2, 8), TinyState(4, 12)]
    new = [TinyState(2, 11), TinyState(6, 15)]
    before, current = TinyState(0, 0), TinyState(1, 10)
    expected = reference(old, new, before, current).state_dict()
    old_mean = aggregate([m.state_dict() for m in old], [1, 3])
    fresh = aggregate([m.state_dict() for m in new], [1, 3])
    changed = calibrated_state(current.state_dict(), fresh,
                               {"w": float(torch.norm(old_mean["w"] - before.w))}, {"w"})
    assert expected["w"].item() == 4 and expected["bn"].item() == 20
    assert changed["w"].item() == 4.5 and changed["bn"].item() == 14
    artifact = torch.load(ROOT / "upstream/data_prepare/record/badnet_seed0/pert_result.pt",
                          weights_only=False, map_location="cpu")
    bd = artifact["bd_train"]["bd_data_container"]["data_dict"]
    cv = artifact["cv_pert"]["data_dict"]
    bd_paths = {int(k): resolve_image(v["path"]) for k, v in bd.items()}
    # Dry simulation only: upstream shell script deletes pert/* then moves bd class 1..9.
    moved_destinations = {(p.parent.name, p.name) for p in bd_paths.values() if p.parent.name in list("123456789")}
    valid_after_shell = sum((resolve_image(v["path"]).parent.name, resolve_image(v["path"]).name)
                            in moved_destinations for v in cv.values())
    report = {
        "prototype_valid_for_original_reproduction": False,
        "numeric_counterexample": {"original": {k: v.item() for k, v in expected.items()},
                                     "prototype": {k: v.item() for k, v in changed.items()}},
        "confirmed_changes": [
            "40 rounds -> 10; 5 local epochs -> 1; full data -> approximately 10k",
            "5 regular clients with dominant ratio 0.7 -> 20 Dirichlet clients",
            "FU starts at old_GMs[0] -> fresh initialization",
            "Historical reference old_GMs[r+1] -> state before round r",
            "FU client means are uniform in upstream -> data-size-weighted means",
            "Upstream calibrates all state tensors -> prototype calibrates parameters and replaces BN buffers",
            "Upstream postprocessing shell steps were not executed"],
        "data_postprocess_check": {"cover_records": len(cv), "poison_records": len(bd),
                                   "poison_cover_index_overlap": len(set(bd) & set(cv)),
                                   "cover_paths_surviving_literal_shell_move": valid_after_shell,
                                   "actually_moved_or_deleted": False},
        "conclusion": "Prototype ASR decrease cannot diagnose upstream attack success. "
                      "Changes are experimentally material. The literal upstream shell postprocess "
                      "would also invalidate cover image references in the artifact generated here."}
    path = ROOT / "results/audit"
    path.mkdir(parents=True, exist_ok=True)
    (path / "changes.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
