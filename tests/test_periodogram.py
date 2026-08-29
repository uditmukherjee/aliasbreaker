"""Periodogram, candidate construction, basin refinement, and support
normalisation (charter sections 2-3)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from aliasbreaker.world import truth_rv
from aliasbreaker.fitting import (candidate_periods, fit_basin, fit_circular,
                                  periodogram, support_from_chi2)

from helpers import get_case


class TestPeriodogram(unittest.TestCase):

    PARAMS = {"P": 7.3, "K": 15.0, "phi": 1.1, "gamma": 2.0}

    def setUp(self):
        self.t = np.linspace(0.0, 40.0, 400)
        # Small deterministic perturbation: keeps the periodogram from being
        # exactly degenerate while leaving the true peak dominant.
        self.y = truth_rv(self.PARAMS, self.t) + 0.05 * np.cos(11.0 * self.t)

    def test_grid_step_matches_declared_rule(self):
        freqs, chi2s, df = periodogram(self.t, self.y, 1.0)
        span = float(self.t.max() - self.t.min())
        self.assertAlmostEqual(df, 1.0 / (4.0 * span), places=12)
        self.assertEqual(len(freqs), len(chi2s))
        self.assertGreaterEqual(float(freqs.min()), 0.01)
        self.assertLess(float(freqs.max()), 1.2)
        np.testing.assert_allclose(np.diff(freqs), df, atol=1e-12)

    def test_periodogram_chi2_matches_fit_circular(self):
        freqs, chi2s, _df = periodogram(self.t, self.y, 2.0)
        for i in (0, len(freqs) // 3, len(freqs) - 1):
            self.assertAlmostEqual(
                chi2s[i], fit_circular(self.t, self.y, 2.0, 1.0 / freqs[i])["chi2"],
                places=9)

    def test_periodogram_minimum_is_at_the_true_frequency(self):
        freqs, chi2s, df = periodogram(self.t, self.y, 1.0)
        f_best = float(freqs[int(np.argmin(chi2s))])
        self.assertLessEqual(abs(f_best - 1.0 / self.PARAMS["P"]), 2.0 * df)

    def test_candidate_periods_contain_the_truth_basin(self):
        periods, df = candidate_periods(self.t, self.y, 1.0)
        self.assertGreater(len(periods), 0)
        f_true = 1.0 / self.PARAMS["P"]
        hits = [P for P in periods if abs(1.0 / P - f_true) <= 2.0 * df]
        self.assertTrue(
            hits, f"no candidate within 2*df of f_true; periods={periods}")

    def test_candidate_periods_are_separated_and_capped(self):
        periods, df = candidate_periods(self.t, self.y, 1.0)
        self.assertLessEqual(len(periods), 6)
        freqs = sorted(1.0 / P for P in periods)
        for a, b in zip(freqs, freqs[1:]):
            self.assertGreaterEqual(b - a, 4.0 * df - 1e-12)

    def test_candidate_periods_are_truth_blind(self):
        # Same (t, y, sigma) with different hidden truths cannot be
        # distinguished: identical inputs must give identical candidates.
        p1, df1 = candidate_periods(self.t, self.y, 1.0)
        p2, df2 = candidate_periods(self.t, self.y.copy(), 1.0)
        self.assertEqual(p1, p2)
        self.assertEqual(df1, df2)

    def test_candidates_on_a_generated_case_are_ordered_by_fit_quality(self):
        case = get_case(1)
        chi2s = [fit_circular(case.init_t, case.init_y, case.sigma, P)["chi2"]
                 for P in case.candidates]
        self.assertEqual(chi2s, sorted(chi2s),
                         "candidates should be ordered best-fit first")


class TestSupport(unittest.TestCase):

    def test_sums_to_one(self):
        for chi2s in ([1.0], [10.0, 12.0, 30.0], [0.0, 0.0], [5.5, 5.5, 5.6]):
            with self.subTest(chi2s=chi2s):
                s = support_from_chi2(chi2s)
                self.assertAlmostEqual(float(s.sum()), 1.0, places=12)
                self.assertTrue(np.all(s >= 0.0))
                self.assertTrue(np.all(s <= 1.0))

    def test_orders_inversely_with_chi2(self):
        chi2s = np.array([30.0, 10.0, 22.0, 12.5])
        s = support_from_chi2(chi2s)
        self.assertEqual(int(np.argmax(s)), int(np.argmin(chi2s)))
        # Ranking of support is exactly the reverse ranking of chi2.
        self.assertEqual(list(np.argsort(-s)), list(np.argsort(chi2s)))
        for i in range(len(chi2s)):
            for j in range(len(chi2s)):
                if chi2s[i] < chi2s[j]:
                    self.assertGreater(s[i], s[j])

    def test_equal_chi2_gives_uniform_support(self):
        s = support_from_chi2([7.0, 7.0, 7.0, 7.0])
        np.testing.assert_allclose(s, np.full(4, 0.25), atol=1e-12)

    def test_shift_invariance(self):
        base = np.array([4.0, 9.0, 11.0])
        np.testing.assert_allclose(support_from_chi2(base),
                                   support_from_chi2(base + 1000.0),
                                   atol=1e-12)

    def test_large_gap_is_numerically_stable(self):
        s = support_from_chi2([0.0, 500.0, 900.0])
        self.assertAlmostEqual(float(s.sum()), 1.0, places=12)
        self.assertAlmostEqual(float(s[0]), 1.0, places=9)
        self.assertTrue(np.all(np.isfinite(s)))


class TestFitBasin(unittest.TestCase):

    def test_refined_chi2_never_worse_than_basin_center(self):
        case = get_case(1)
        t, y = case.init_t, case.init_y
        for P in case.candidates:
            with self.subTest(P=P):
                center = fit_circular(t, y, case.sigma, P)["chi2"]
                refined = fit_basin(t, y, case.sigma, P, case.freq_df)["chi2"]
                self.assertLessEqual(refined, center + 1e-12)

    def test_refined_chi2_never_worse_with_follow_up_data(self):
        case = get_case(1)
        idx = list(range(0, min(len(case.slot_t), 30), 6))[:6]
        t = np.concatenate([case.init_t, case.slot_t[idx]])
        y = np.concatenate([case.init_y, case.slot_y[idx]])
        for P in case.candidates:
            with self.subTest(P=P):
                center = fit_circular(t, y, case.sigma, P)["chi2"]
                refined = fit_basin(t, y, case.sigma, P, case.freq_df)["chi2"]
                self.assertLessEqual(refined, center + 1e-12)

    def test_refined_period_stays_inside_its_basin(self):
        case = get_case(1)
        t, y = case.init_t, case.init_y
        for P in case.candidates:
            with self.subTest(P=P):
                fit = fit_basin(t, y, case.sigma, P, case.freq_df)
                self.assertLessEqual(abs(1.0 / fit["P"] - 1.0 / P),
                                     2.0 * case.freq_df + 1e-12)

    def test_fit_basin_is_deterministic(self):
        case = get_case(1)
        a = fit_basin(case.init_t, case.init_y, case.sigma,
                      case.candidates[0], case.freq_df)
        b = fit_basin(case.init_t, case.init_y, case.sigma,
                      case.candidates[0], case.freq_df)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
