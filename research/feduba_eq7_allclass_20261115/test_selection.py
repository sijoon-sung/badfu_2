"""Known counterexamples for class restriction, ties, ownership and budgets."""
import unittest
from selection import select_all_classes


class SelectionTests(unittest.TestCase):
    def test_top_score_survives_even_when_its_class_is_not_target(self):
        # Source 12 would be discarded by the old class-2-only filter.
        labels = {12: 8, 1: 2, 7: 2, 3: 6}
        ranks = {'5': [[12, 9.], [1, 2.]], '7': [[7, 3.], [3, 3.]]}
        result = select_all_classes(ranks, {'5': [1, 12], '7': [3, 7]}, 2)
        self.assertEqual(result, {'5': [12], '7': [3]})
        self.assertEqual(sum(len(v) for v in result.values()), 2)
        self.assertEqual(labels[12], 8)

    def test_ownership_and_duplicate_rejection(self):
        for ranks, ownership in [({'5': [[1, 2]]}, {'5': [2]}),
                                  ({'5': [[1, 2], [1, 3]]}, {'5': [1]}),
                                  ({'5': [[1, 2]], '7': [[1, 3]]}, {'5': [1], '7': [1]})]:
            with self.assertRaises(ValueError):
                select_all_classes(ranks, ownership, 1)

    def test_invalid_budget_and_nonfinite(self):
        for budget in [0, -1, 2, True]:
            with self.assertRaises(ValueError):
                select_all_classes({'5': [[1, 2.]]}, {'5': [1]}, budget)
        with self.assertRaises(ValueError):
            select_all_classes({'5': [[1, float('nan')]]}, {'5': [1]}, 1)


if __name__ == '__main__':
    unittest.main()
