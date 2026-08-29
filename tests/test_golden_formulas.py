"""Golden numerical locks on the charter's exact formulas — codex diff-gate 1,
findings 10 and 11.

The existing periodogram/verdict tests check ordering, normalization and
determinism; every one of them would still pass with the wrong softmax
temperature, a different fine-grid size, or a relaxed candidate rule. These
tests pin the literal constants:

  * support = exp(-0.5 * dchi2) / sum(...)          (the -0.5 coefficient)
  * fit_basin scans exactly 25 frequencies over f0 +- 2*df
  * candidate_periods: local minima only, dchi2_keep = 12, separation >= 5
    grid steps, at most 6 candidates, initial-observations-only
  * basins are disjoint: candidate centers are > 4*df apart (finding 10)
"""

import inspect
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from aliasbreaker import fitting
from aliasbreaker.fitting import (candidate_periods, fit_basin, periodogram,
                                  support_from_chi2)

from helpers import dev_cases

SIGMA = 3.0


def _dense_two_sinusoid():
    """Deterministic dense data with two strong periodicities and many
    spurious periodogram minima."""
    rng = np.random.default_rng(0)
    t = np.arange(0.0, 30.0, 0.25) + 0.05 * rng.random(120)
    y = (12.0 * np.cos(2.0 * np.pi * 0.12 * t + 0.4)
         + 9.0 * np.cos(2.0 * np.pi * 0.37 * t - 1.1) + 1.5
         + SIGMA * rng.standard_normal(len(t)))
    return t, y


def _local_minima(chi2s):
    is_peak = np.zeros(len(chi2s), dtype=bool)
    is_peak[1:-1] = (chi2s[1:-1] < chi2s[:-2]) & (chi2s[1:-1] < chi2s[2:])
    return is_peak


def _grid_indices(periods, freqs):
    """Map returned periods back to periodogram grid indices."""
    idx = []
    for P in periods:
        f = 1.0 / P
        k = int(np.argmin(np.abs(freqs - f)))
        assert abs(freqs[k] - f) < 1e-9, "candidate is not a grid frequency"
        idx.append(k)
    return idx


class TestSupportSoftmaxCoefficient(unittest.TestCase):
    """support_from_chi2 must be exp(-0.5 * dchi2), not any other temperature."""

    def test_golden_two_candidate_value(self):
        got = support_from_chi2([0.0, 2.0])
        e = math.exp(-1.0)          # exp(-0.5 * (2 - 0))
        want = [1.0 / (1.0 + e), e / (1.0 + e)]
        self.assertEqual(len(got), 2)
        for g, w in zip(got, want):
            self.assertAlmostEqual(float(g), w, delta=1e-12)

    def test_golden_value_is_temperature_sensitive(self):
        """A wrong coefficient (-1.0 or -0.25) must not reproduce the golden."""
        got = float(support_from_chi2([0.0, 2.0])[1])
        for wrong in (-1.0, -0.25, -2.0):
            s = np.exp(wrong * (np.array([0.0, 2.0])))
            self.assertGreater(abs(got - float((s / s.sum())[1])), 1e-6)

    def test_golden_three_candidate_value(self):
        chi2s = [10.0, 13.0, 17.0]
        got = support_from_chi2(chi2s)
        raw = [math.exp(-0.5 * (c - 10.0)) for c in chi2s]
        tot = sum(raw)
        for g, r in zip(got, raw):
            self.assertAlmostEqual(float(g), r / tot, delta=1e-12)

    def test_shift_invariant_and_normalized(self):
        a = np.array([4.0, 7.5, 9.0])
        s1 = support_from_chi2(a)
        s2 = support_from_chi2(a + 1234.5)
        np.testing.assert_allclose(s1, s2, rtol=0, atol=1e-12)
        self.assertAlmostEqual(float(s1.sum()), 1.0, delta=1e-12)


class TestFitBasinFineGrid(unittest.TestCase):
    """The refit basin is exactly 25 points spanning f0 +- 2*df."""

    @classmethod
    def setUpClass(cls):
        rng = np.random.default_rng(0)
        cls.t = np.sort(rng.uniform(0.0, 30.0, 40))
        cls.df = 1.0 / (4.0 * (cls.t.max() - cls.t.min()))
        cls.f0 = 0.1
        # Optimum deliberately off-center, 1.4 coarse grid steps up.
        cls.f_true = cls.f0 + 1.4 * cls.df
        cls.y = 10.0 * np.cos(2.0 * np.pi * cls.f_true * cls.t) + 2.0
        cls.grid = np.linspace(cls.f0 - 2.0 * cls.df, cls.f0 + 2.0 * cls.df, 25)

    def test_declared_defaults(self):
        sig = inspect.signature(fit_basin).parameters
        self.assertEqual(sig["half_width_steps"].default, 2.0)
        self.assertEqual(sig["n_fine"].default, 25)

    def test_scans_exactly_25_frequencies_on_the_declared_grid(self):
        seen = []
        real = fitting.fit_circular

        def spy(t, y, sigma, P):
            seen.append(1.0 / P)
            return real(t, y, sigma, P)

        fitting.fit_circular = spy
        try:
            fit_basin(self.t, self.y, 1.0, 1.0 / self.f0, self.df)
        finally:
            fitting.fit_circular = real

        self.assertEqual(len(seen), 25,
                         f"fit_basin scanned {len(seen)} frequencies, not 25")
        np.testing.assert_allclose(np.array(seen), self.grid,
                                   rtol=0, atol=1e-12)
        self.assertAlmostEqual(seen[0], self.f0 - 2.0 * self.df, delta=1e-12)
        self.assertAlmostEqual(seen[-1], self.f0 + 2.0 * self.df, delta=1e-12)

    def test_best_lands_on_the_grid_point_nearest_the_true_optimum(self):
        best = fit_basin(self.t, self.y, 1.0, 1.0 / self.f0, self.df)
        f_best = 1.0 / best["P"]
        k = int(np.argmin(np.abs(self.grid - f_best)))
        self.assertLess(abs(self.grid[k] - f_best), 1e-12,
                        "refined frequency is off the 25-point basin grid")
        expected = int(np.argmin(np.abs(self.grid - self.f_true)))
        self.assertEqual(k, expected)
        # 8.4 fine steps above center -> index 12 + 8, i.e. NOT the center.
        self.assertEqual(k, 20)
        self.assertNotEqual(k, 12)

    def test_stays_inside_its_own_basin(self):
        """Refinement never escapes +-2*df, even with a far-off optimum."""
        y = 10.0 * np.cos(2.0 * np.pi * (self.f0 + 9.0 * self.df) * self.t)
        best = fit_basin(self.t, y, 1.0, 1.0 / self.f0, self.df)
        f_best = 1.0 / best["P"]
        self.assertLessEqual(abs(f_best - self.f0), 2.0 * self.df + 1e-12)


class TestCandidatePeriodsRules(unittest.TestCase):
    """Local maxima (chi2 minima), keep-cutoff, separation, and the cap."""

    @classmethod
    def setUpClass(cls):
        cls.t, cls.y = _dense_two_sinusoid()
        cls.freqs, cls.chi2s, cls.df = periodogram(cls.t, cls.y, SIGMA)
        cls.is_peak = _local_minima(cls.chi2s)
        cls.best = float(cls.chi2s.min())

    def test_declared_defaults(self):
        sig = inspect.signature(candidate_periods).parameters
        self.assertEqual(sig["delta_chi2_keep"].default, 12.0)
        self.assertEqual(sig["max_candidates"].default, 6)
        self.assertEqual(sig["min_sep_steps"].default, 5)

    def test_every_candidate_is_a_periodogram_local_maximum(self):
        periods, df = candidate_periods(self.t, self.y, SIGMA,
                                        delta_chi2_keep=1e9)
        self.assertAlmostEqual(df, self.df, delta=1e-15)
        for k in _grid_indices(periods, self.freqs):
            self.assertTrue(self.is_peak[k],
                            f"grid index {k} is not a local chi2 minimum")
            self.assertLess(self.chi2s[k], self.chi2s[k - 1])
            self.assertLess(self.chi2s[k], self.chi2s[k + 1])

    def test_delta_chi2_keep_cutoff_excludes_worse_peaks(self):
        periods, _ = candidate_periods(self.t, self.y, SIGMA)
        kept = _grid_indices(periods, self.freqs)
        for k in kept:
            self.assertLessEqual(self.chi2s[k], self.best + 12.0)

        peak_idx = np.flatnonzero(self.is_peak)
        excluded = [int(k) for k in peak_idx
                    if self.chi2s[k] > self.best + 12.0]
        self.assertTrue(excluded, "fixture has no peak beyond the cutoff")
        for k in excluded:
            self.assertNotIn(k, kept,
                             f"peak {k} exceeds best+12 but was kept")

        # Relaxing the cutoff must admit at least one of those peaks: proves
        # the exclusion above came from the cutoff, not from separation.
        relaxed = _grid_indices(
            candidate_periods(self.t, self.y, SIGMA, delta_chi2_keep=1e9)[0],
            self.freqs)
        self.assertGreater(len(relaxed), len(kept))

    def test_cutoff_boundary_is_inclusive_at_exactly_best_plus_keep(self):
        """A peak at exactly best + delta_chi2_keep is kept (> not >=)."""
        periods, _ = candidate_periods(self.t, self.y, SIGMA,
                                       delta_chi2_keep=1e9)
        kept = _grid_indices(periods, self.freqs)
        second = kept[1]
        margin = float(self.chi2s[second]) - self.best
        inside = candidate_periods(self.t, self.y, SIGMA,
                                   delta_chi2_keep=margin)[0]
        self.assertIn(second, _grid_indices(inside, self.freqs))
        outside = candidate_periods(self.t, self.y, SIGMA,
                                    delta_chi2_keep=margin * (1 - 1e-9))[0]
        self.assertNotIn(second, _grid_indices(outside, self.freqs))

    def test_separation_at_least_five_grid_steps(self):
        periods, df = candidate_periods(self.t, self.y, SIGMA,
                                        delta_chi2_keep=1e9)
        freqs = sorted(1.0 / P for P in periods)
        self.assertGreater(len(freqs), 1)
        for a, b in zip(freqs, freqs[1:]):
            self.assertGreaterEqual((b - a) / df, 5.0 - 1e-9,
                                    "candidates closer than 5 grid steps")

    def test_at_most_six_candidates(self):
        periods, _ = candidate_periods(self.t, self.y, SIGMA,
                                       delta_chi2_keep=1e9)
        self.assertEqual(len(periods), 6)
        for cap in (1, 2, 3, 4, 5):
            got = candidate_periods(self.t, self.y, SIGMA,
                                    delta_chi2_keep=1e9,
                                    max_candidates=cap)[0]
            self.assertEqual(len(got), cap)
        more = candidate_periods(self.t, self.y, SIGMA, delta_chi2_keep=1e9,
                                 max_candidates=9)[0]
        self.assertGreater(len(more), 6,
                           "the 6-cap must come from max_candidates, not the "
                           "supply of eligible peaks")

    def test_candidates_ordered_by_fit_quality(self):
        periods, _ = candidate_periods(self.t, self.y, SIGMA,
                                       delta_chi2_keep=1e9)
        chi2s = [self.chi2s[k] for k in _grid_indices(periods, self.freqs)]
        self.assertEqual(chi2s, sorted(chi2s))


class TestCandidatesFromInitialDataOnly(unittest.TestCase):
    """candidate_periods sees only (t, y, sigma); make_case must use exactly
    the initial observations. Finding 11's 'unchanged when all follow-up
    potential outcomes change' property holds by construction, and is asserted
    here against the stored fixtures."""

    @classmethod
    def setUpClass(cls):
        cls.cases = dev_cases(10)

    def test_deterministic_across_repeated_calls(self):
        for case in self.cases:
            a = candidate_periods(case.init_t, case.init_y, case.sigma)
            b = candidate_periods(case.init_t, case.init_y, case.sigma)
            self.assertEqual(list(a[0]), list(b[0]))
            self.assertEqual(a[1], b[1])

    def test_stored_candidates_equal_initial_data_recomputation(self):
        for case in self.cases:
            periods, df = candidate_periods(case.init_t, case.init_y,
                                            case.sigma)
            self.assertEqual(len(periods), len(case.candidates),
                             f"{case.case_id}: candidate count differs")
            for stored, recomputed in zip(case.candidates, periods):
                self.assertAlmostEqual(float(stored), float(recomputed),
                                       delta=1e-12)
            self.assertAlmostEqual(case.freq_df, df, delta=1e-15)

    def test_appending_follow_up_data_is_not_retroactive(self):
        """Sanity: the follow-up outcomes DO change a recomputation, so the
        equality above is a real constraint (candidates are frozen at t=0)."""
        changed = 0
        for case in self.cases:
            t = np.concatenate([case.init_t, case.slot_t[:6]])
            y = np.concatenate([case.init_y, case.slot_y[:6]])
            periods, _ = candidate_periods(t, y, case.sigma)
            if [round(p, 9) for p in periods] != \
                    [round(float(p), 9) for p in case.candidates]:
                changed += 1
        self.assertGreater(changed, 0,
                           "follow-up data never changes the candidate set; "
                           "the frozen-candidate test would be vacuous")

    def test_generated_case_candidates_within_keep_and_ordered(self):
        for case in self.cases:
            freqs, chi2s, df = periodogram(case.init_t, case.init_y,
                                           case.sigma)
            is_peak = _local_minima(chi2s)
            best = float(chi2s.min())
            idx = _grid_indices(case.candidates, freqs)
            for k in idx:
                self.assertTrue(is_peak[k], f"{case.case_id}: not a local min")
                self.assertLessEqual(chi2s[k], best + 12.0)
            self.assertEqual([chi2s[k] for k in idx],
                             sorted(chi2s[k] for k in idx))
            self.assertLessEqual(len(idx), 6)


class TestBasinDisjointness(unittest.TestCase):
    """Finding 10: refit basins span +-2*df, so centers must be more than
    4*df apart for the basins to be disjoint."""

    @classmethod
    def setUpClass(cls):
        cls.cases = dev_cases(10)

    def test_dev_case_candidates_are_more_than_four_df_apart(self):
        for case in self.cases:
            freqs = sorted(1.0 / P for P in case.candidates)
            self.assertGreaterEqual(len(freqs), 2)
            for a, b in zip(freqs, freqs[1:]):
                steps = (b - a) / case.freq_df
                self.assertGreater(steps, 4.0,
                                   f"{case.case_id}: basins overlap at "
                                   f"{steps:.4f} grid steps")

    def test_no_shared_frequency_between_adjacent_basins(self):
        """The 25-point basin grids of adjacent candidates never intersect."""
        for case in self.cases:
            df = case.freq_df
            grids = [np.linspace(1.0 / P - 2.0 * df, 1.0 / P + 2.0 * df, 25)
                     for P in case.candidates]
            for i in range(len(grids)):
                for j in range(i + 1, len(grids)):
                    d = np.abs(grids[i][:, None] - grids[j][None, :]).min()
                    self.assertGreater(
                        d, 0.0,
                        f"{case.case_id}: basins {i},{j} share a frequency")

    def test_synthetic_five_step_separation_is_the_binding_rule(self):
        """Exactly 4 steps apart would share a boundary frequency; the
        min_sep_steps=5 default makes that unreachable."""
        t, y = _dense_two_sinusoid()
        periods, df = candidate_periods(t, y, SIGMA, delta_chi2_keep=1e9)
        freqs = sorted(1.0 / P for P in periods)
        for a, b in zip(freqs, freqs[1:]):
            self.assertGreater((b - a) / df, 4.0)
        # With the pre-fix separation of 4 steps, an exactly-4-step pair is
        # admissible and its basin boundaries coincide.
        loose, df2 = candidate_periods(t, y, SIGMA, delta_chi2_keep=1e9,
                                       min_sep_steps=4)
        lf = sorted(1.0 / P for P in loose)
        self.assertGreaterEqual(len(lf), len(freqs))
        self.assertTrue(
            all((b - a) / df2 >= 4.0 - 1e-9 for a, b in zip(lf, lf[1:])))


if __name__ == "__main__":
    unittest.main()
