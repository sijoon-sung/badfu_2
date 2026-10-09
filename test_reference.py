import ast
import tempfile
import unittest
from pathlib import Path

import torch
from torch import nn

from reference_runner import ROOT, DiskHistory, build_tree, rng_state, pause_at_checkpoint, TrainingPaused


class ExampleModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(3, 2)
        self.register_buffer("counter", torch.tensor(7, dtype=torch.long))


class ReferenceChecks(unittest.TestCase):
    def test_pause_requires_marker_and_records_saved_round(self):
        root = ROOT / "results/reference_tests"
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            path = Path(temporary)
            metrics = {"phase": "global_model_bd", "round": 8}
            pause_at_checkpoint(path, metrics)
            self.assertFalse((path / "paused.json").exists())
            (path / "PAUSE").touch()
            with self.assertRaises(TrainingPaused):
                pause_at_checkpoint(path, metrics)
            self.assertIn('"round": 8', (path / "paused.json").read_text())

    def test_source_definitions_and_default_experiment_preserved(self):
        tree, _, names = build_tree(ROOT / "input.pt", ROOT / "results/test")
        self.assertIn("unlearning_step_once", names)
        self.assertIn("local_train", names)
        constants = {n.targets[0].id: n.value.value for n in tree.body if isinstance(n, ast.Assign)
                     and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                     and isinstance(n.value, ast.Constant)}
        self.assertEqual(constants["num_clients"], 5)
        self.assertEqual(constants["num_rounds"], 40)
        self.assertEqual(constants["local_epochs"], 5)
        self.assertEqual(constants["dominant_ratio"], .7)
        self.assertEqual(constants["seed"], 42)

    def test_disk_history_bitwise_state_and_rng_roundtrip(self):
        root = ROOT / "results/reference_tests"
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            # Validate the cleanup target remains within the explicitly designated test directory.
            self.assertTrue(Path(temporary).resolve().is_relative_to(root.resolve()))
            namespace = {"ExampleModel": ExampleModel, "device": "cpu"}
            history = DiskHistory("old", temporary, namespace)
            m = ExampleModel()
            history.append([m])
            before = rng_state()
            loaded = history[0][0]
            after = rng_state()
            for k, value in m.state_dict().items():
                self.assertTrue(torch.equal(value, loaded.state_dict()[k]))
            self.assertTrue(torch.equal(before["torch"], after["torch"]))
            self.assertEqual(before["python"], after["python"])
            for a, b in zip(before["cuda"], after["cuda"]):
                self.assertTrue(torch.equal(a, b))
            reloaded = DiskHistory("old", temporary, namespace)
            self.assertEqual(len(reloaded), 1)
            self.assertTrue(torch.equal(reloaded[0][0].fc.weight, m.fc.weight))
            namespace["r"] = 0
            history.append([m])
            self.assertEqual(len(history), 1)


if __name__ == "__main__":
    unittest.main()
