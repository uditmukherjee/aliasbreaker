"""Leakage guard (charter section 6): no arm may condition its SCHEDULING on
hidden truth. Corrupting the evaluator-only fields must not change which slots
an arm chooses. Verdict fields (correct / truth_support / false_resolution) are
evaluator-side and are allowed to depend on truth.
"""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from aliasbreaker.planners import (batch_design, run_batch, run_even_spacing,
                                   run_scripted_adaptive)

from helpers import dev_cases

SENTINEL_PARAMS = {"P": -1.0, "K": -1.0, "phi": -1.0, "gamma": -1.0}
SENTINEL_BASIN = -999


def _corrupt(case):
    """Deep copy with the evaluator-only fields replaced by sentinels."""
    poisoned = copy.deepcopy(case)
    poisoned.true_params = dict(SENTINEL_PARAMS)
    poisoned.true_basin_index = SENTINEL_BASIN
    return poisoned


class TestTruthBlindScheduling(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = dev_cases(10)
        cls.poisoned = [_corrupt(c) for c in cls.cases]

    def test_agent_visible_fields_survive_corruption(self):
        for clean, dirty in zip(self.cases, self.poisoned):
            np.testing.assert_array_equal(clean.slot_t, dirty.slot_t)
            np.testing.assert_array_equal(clean.slot_y, dirty.slot_y)
            np.testing.assert_array_equal(clean.init_y, dirty.init_y)
            self.assertEqual(clean.candidates, dirty.candidates)
            self.assertNotEqual(clean.true_basin_index, dirty.true_basin_index)

    def test_batch_design_is_truth_blind(self):
        for clean, dirty in zip(self.cases, self.poisoned):
            with self.subTest(case=clean.case_id):
                self.assertEqual(batch_design(clean), batch_design(dirty))

    def test_run_batch_slots_are_truth_blind(self):
        for clean, dirty in zip(self.cases, self.poisoned):
            with self.subTest(case=clean.case_id):
                self.assertEqual(run_batch(clean)["slots"],
                                 run_batch(dirty)["slots"])

    def test_run_even_spacing_slots_are_truth_blind(self):
        for clean, dirty in zip(self.cases, self.poisoned):
            with self.subTest(case=clean.case_id):
                self.assertEqual(run_even_spacing(clean)["slots"],
                                 run_even_spacing(dirty)["slots"])

    def test_run_scripted_adaptive_slots_are_truth_blind(self):
        for clean, dirty in zip(self.cases, self.poisoned):
            with self.subTest(case=clean.case_id):
                self.assertEqual(run_scripted_adaptive(clean)["slots"],
                                 run_scripted_adaptive(dirty)["slots"])

    def test_support_and_chi2_are_truth_blind(self):
        # Everything the arms can see must be identical; only the scoring
        # fields may move.
        for clean, dirty in zip(self.cases, self.poisoned):
            with self.subTest(case=clean.case_id):
                a, b = run_batch(clean), run_batch(dirty)
                np.testing.assert_allclose(a["chi2s"], b["chi2s"], atol=1e-12)
                self.assertAlmostEqual(a["max_support"], b["max_support"], 12)
                self.assertEqual(a["pred"], b["pred"])
                self.assertEqual(a["resolved"], b["resolved"])
                self.assertEqual(a["n_obs"], b["n_obs"])

    def test_poisoned_truth_never_scores_as_correct(self):
        # With basin index -999 the evaluator must not credit a correct
        # resolution, proving the scoring path really reads that field.
        for dirty in self.poisoned:
            with self.subTest(case=dirty.case_id):
                out = run_batch(dirty)
                self.assertFalse(out["correct"])
                self.assertEqual(out["truth_support"], 0.0)

    def test_arms_do_not_mutate_the_case(self):
        case = self.cases[0]
        before = (case.slot_t.copy(), case.slot_y.copy(),
                  case.init_t.copy(), case.init_y.copy(),
                  list(case.candidates), case.true_basin_index,
                  dict(case.true_params))
        run_batch(case)
        run_even_spacing(case)
        run_scripted_adaptive(case)
        np.testing.assert_array_equal(before[0], case.slot_t)
        np.testing.assert_array_equal(before[1], case.slot_y)
        np.testing.assert_array_equal(before[2], case.init_t)
        np.testing.assert_array_equal(before[3], case.init_y)
        self.assertEqual(before[4], case.candidates)
        self.assertEqual(before[5], case.true_basin_index)
        self.assertEqual(before[6], case.true_params)


if __name__ == "__main__":
    unittest.main()
