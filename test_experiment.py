import unittest

import numpy as np
import pandas as pd
import torch

from analysis import BASE, XAI, compare
from experiment import aggregate, attr_distribution, calibrated_state, jsd, partition


class Checks(unittest.TestCase):
    def test_calibration_zero_norm_and_buffer_handling(self):
        current = {"w": torch.tensor([1., 2.]), "bn": torch.tensor([3.]), "n": torch.tensor(1)}
        fresh = {"w": torch.tensor([1., 2.]), "bn": torch.tensor([4.]), "n": torch.tensor(2)}
        out = calibrated_state(current, fresh, {"w": 10.}, {"w"})
        self.assertTrue(torch.isfinite(out["w"]).all())
        torch.testing.assert_close(out["w"], current["w"])
        torch.testing.assert_close(out["bn"], fresh["bn"])
        self.assertEqual(out["n"].item(), 2)
        fresh["w"] = torch.tensor([4., 6.])
        out = calibrated_state(current, fresh, {"w": 10.}, {"w"})
        self.assertAlmostEqual(torch.linalg.vector_norm(out["w"] - current["w"]).item(), 10.)
    def test_partition_has_no_loss_or_overlap(self):
        y = np.repeat(np.arange(10), 100)
        parts = partition(y, 20, .1, np.random.default_rng(11))
        np.testing.assert_array_equal(np.sort(np.concatenate(parts)), np.arange(len(y)))
        self.assertGreaterEqual(min(map(len, parts)), 2)

    def test_aggregation_and_integer_buffers(self):
        a = {"w": torch.tensor([1.]), "n": torch.tensor(1)}
        b = {"w": torch.tensor([3.]), "n": torch.tensor(3)}
        result = aggregate([a, b], [1, 3])
        self.assertAlmostEqual(result["w"].item(), 2.5)
        self.assertEqual(result["n"].dtype, torch.int64)

    def test_same_model_attribution_is_repeatable(self):
        from argparse import Namespace
        model = torch.nn.Sequential(torch.nn.Flatten(), torch.nn.Linear(12, 10))
        x = torch.ones(3, 2, 2)
        baseline = torch.zeros(2, 3, 2, 2)
        args = Namespace(shap_samples=16)
        p, m = attr_distribution(model, x, 0, baseline, 10, args, "cpu")
        q, n = attr_distribution(model, x, 0, baseline, 10, args, "cpu")
        self.assertAlmostEqual(jsd(p, q), 0.)
        self.assertAlmostEqual(float(p.sum()), 1., places=6)
        self.assertEqual(m, n)

    def test_grouped_prediction_is_unaffected_by_heldout_labels(self):
        rng = np.random.default_rng(1)
        df = pd.DataFrame(rng.normal(size=(60, len(BASE + XAI))), columns=BASE + XAI)
        df["seed"] = np.repeat([11, 22, 33], 20)
        df["condition"] = "test"
        df["client"] = np.tile(np.arange(20), 3)
        df["delta_asr"] = .1 * df.jsd_clean_target + rng.normal(0, .001, 60)
        _, first = compare(df)
        altered = df.copy()
        altered.loc[altered.seed == 11, "delta_asr"] += 100
        _, second = compare(altered)
        np.testing.assert_array_equal(first.loc[df.seed == 11, "with_xai"],
                                      second.loc[df.seed == 11, "with_xai"])
        self.assertFalse(any("trigger" in k or "asr" in k for k in BASE + XAI))


if __name__ == "__main__":
    unittest.main()
