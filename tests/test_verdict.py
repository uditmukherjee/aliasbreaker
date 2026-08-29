"""Verdict-rule consistency (charter section 3): the flags the whole benchmark
is scored on must be internally coherent for every case and every observation
subset."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from aliasbreaker.evaluator import THETA_DEFAULT, verdict
from aliasbreaker.fitting import support_from_chi2

from helpers import dev_cases, get_case


def _subsets(case):
    n = len(case.slot_t)
    return [
        [],
        [0],
        [0, 1],
        sorted({0, n // 4, n // 2, 3 * n // 4, n - 1}),
        sorted({1, 2, 3, n // 3, n - 2}),
    ]


class TestVerdictConsistency(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = dev_cases(8)

    def test_flags_are_internally_consistent(self):
        for case in self.cases:
            for idx in _subsets(case):
                with self.subTest(case=case.case_id, idx=tuple(idx)):
                    obs_t = [float(case.slot_t[i]) for i in idx]
                    obs_y = [float(case.slot_y[i]) for i in idx]
                    v = verdict(case, obs_t, obs_y)

                    self.assertEqual(v["abstained"], not v["resolved"])
                    if v["correct"]:
                        self.assertTrue(v["resolved"])
                    self.assertEqual(v["false_resolution"],
                                     v["resolved"] and not v["correct"])
                    self.assertGreaterEqual(v["max_support"], 0.0)
                    self.assertLessEqual(v["max_support"], 1.0)
                    self.assertGreaterEqual(v["truth_support"], 0.0)
                    self.assertLessEqual(v["truth_support"], 1.0)
                    self.assertEqual(v["n_obs"], len(idx))
                    self.assertEqual(len(v["chi2s"]), len(case.candidates))
                    self.assertIn(v["pred"], range(len(case.candidates)))

    def test_resolved_matches_the_threshold_rule(self):
        for case in self.cases:
            for idx in _subsets(case):
                with self.subTest(case=case.case_id, idx=tuple(idx)):
                    obs_t = [float(case.slot_t[i]) for i in idx]
                    obs_y = [float(case.slot_y[i]) for i in idx]
                    v = verdict(case, obs_t, obs_y)
                    self.assertEqual(v["resolved"],
                                     v["max_support"] >= THETA_DEFAULT)

    def test_max_support_is_the_argmax_of_the_support_table(self):
        for case in self.cases[:3]:
            idx = [0, 3, 7]
            obs_t = [float(case.slot_t[i]) for i in idx]
            obs_y = [float(case.slot_y[i]) for i in idx]
            v = verdict(case, obs_t, obs_y)
            support = support_from_chi2(v["chi2s"])
            self.assertEqual(v["pred"], int(np.argmax(support)))
            self.assertAlmostEqual(v["max_support"], float(support.max()), 12)
            self.assertAlmostEqual(v["truth_support"],
                                   float(support[case.true_basin_index]), 12)

    def test_correct_requires_pred_to_equal_the_truth_basin(self):
        for case in self.cases:
            for idx in _subsets(case):
                obs_t = [float(case.slot_t[i]) for i in idx]
                obs_y = [float(case.slot_y[i]) for i in idx]
                v = verdict(case, obs_t, obs_y)
                if v["correct"]:
                    self.assertEqual(v["pred"], case.true_basin_index)

    def test_verdict_is_deterministic(self):
        case = self.cases[0]
        idx = [1, 5, 9]
        obs_t = [float(case.slot_t[i]) for i in idx]
        obs_y = [float(case.slot_y[i]) for i in idx]
        self.assertEqual(verdict(case, obs_t, obs_y),
                         verdict(case, obs_t, obs_y))

    def test_higher_theta_never_resolves_more(self):
        case = get_case(1)
        idx = [0, 4, 8, 12]
        obs_t = [float(case.slot_t[i]) for i in idx]
        obs_y = [float(case.slot_y[i]) for i in idx]
        strict = verdict(case, obs_t, obs_y, theta=0.999)
        loose = verdict(case, obs_t, obs_y, theta=0.5)
        if strict["resolved"]:
            self.assertTrue(loose["resolved"])
        self.assertEqual(strict["pred"], loose["pred"])

    def test_theta_zero_always_resolves(self):
        case = get_case(1)
        v = verdict(case, [], [], theta=0.0)
        self.assertTrue(v["resolved"])
        self.assertFalse(v["abstained"])

    def test_accepts_numpy_observation_arrays(self):
        case = get_case(1)
        idx = [2, 6]
        a = verdict(case, [float(case.slot_t[i]) for i in idx],
                    [float(case.slot_y[i]) for i in idx])
        b = verdict(case, case.slot_t[idx], case.slot_y[idx])
        self.assertEqual(a["pred"], b["pred"])
        np.testing.assert_allclose(a["chi2s"], b["chi2s"], atol=1e-12)

    def test_more_data_never_shrinks_the_fitted_sample(self):
        case = get_case(1)
        v0 = verdict(case, [], [])
        v1 = verdict(case, [float(case.slot_t[0])], [float(case.slot_y[0])])
        self.assertEqual(v0["n_obs"], 0)
        self.assertEqual(v1["n_obs"], 1)


if __name__ == "__main__":
    unittest.main()
