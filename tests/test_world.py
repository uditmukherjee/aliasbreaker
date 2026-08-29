"""World determinism (no runtime RNG) and the chronological state machine
(charter sections 1-2)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from aliasbreaker.world import (Campaign, IllegalAction, keyed_noise,
                                make_case, truth_rv)

from helpers import get_case


class TestKeyedNoise(unittest.TestCase):

    def test_reproducible(self):
        for key in ((1, 0, 0), (7, 1, 3), (123, 0, 41)):
            with self.subTest(key=key):
                self.assertEqual(keyed_noise(*key), keyed_noise(*key))

    def test_distinct_across_keys(self):
        keys = [(s, st, i) for s in (1, 2, 3) for st in (0, 1)
                for i in range(8)]
        values = [keyed_noise(*k) for k in keys]
        self.assertEqual(len(set(values)), len(values),
                         "keyed_noise collided across (seed, stream, idx)")

    def test_stream_separation(self):
        # The init stream and the slot stream must not share draws at the same
        # index, or follow-up outcomes would be correlated with the initial data.
        for i in range(10):
            self.assertNotEqual(keyed_noise(5, 0, i), keyed_noise(5, 1, i))

    def test_returns_python_float(self):
        v = keyed_noise(1, 0, 0)
        self.assertIsInstance(v, float)
        self.assertTrue(np.isfinite(v))

    def test_accepts_numpy_integer_keys(self):
        self.assertEqual(keyed_noise(np.int64(4), np.int64(1), np.int64(2)),
                         keyed_noise(4, 1, 2))


class TestMakeCaseDeterminism(unittest.TestCase):

    SEED = 11

    def setUp(self):
        self.a = make_case(self.SEED)
        self.b = make_case(self.SEED)
        if self.a is None:
            self.skipTest(f"seed {self.SEED} produced no admissible case")

    def test_identical_arrays(self):
        for name in ("init_t", "init_y", "slot_t", "slot_y"):
            with self.subTest(field=name):
                np.testing.assert_array_equal(getattr(self.a, name),
                                              getattr(self.b, name))

    def test_identical_candidates_and_metadata(self):
        self.assertEqual(self.a.candidates, self.b.candidates)
        self.assertEqual(self.a.freq_df, self.b.freq_df)
        self.assertEqual(self.a.true_params, self.b.true_params)
        self.assertEqual(self.a.true_basin_index, self.b.true_basin_index)
        self.assertEqual(self.a.case_id, self.b.case_id)
        self.assertEqual(self.a.sigma, self.b.sigma)
        self.assertEqual(self.a.budget, self.b.budget)

    def test_different_seeds_give_different_worlds(self):
        other = None
        s = self.SEED + 1
        while other is None and s < self.SEED + 60:
            other = make_case(s)
            s += 1
        self.assertIsNotNone(other)
        self.assertNotEqual(list(self.a.init_y), list(other.init_y))

    def test_sigma_knob_changes_the_realized_noise_scale(self):
        low = make_case(self.SEED, sigma=1.0)
        high = make_case(self.SEED, sigma=5.0)
        if low is None or high is None:
            self.skipTest("sigma variants not admissible for this seed")
        # Same keyed draws, different amplitude -> different realized outcomes.
        self.assertNotEqual(list(low.init_y), list(high.init_y))

    def test_realized_outcomes_are_truth_plus_scaled_noise(self):
        case = self.a
        expected = truth_rv(case.true_params, case.slot_t) + case.sigma * np.array(
            [keyed_noise(case.seed, 1, i) for i in range(len(case.slot_t))])
        np.testing.assert_allclose(case.slot_y, expected, atol=1e-12)

    def test_slot_times_are_sorted_and_inside_the_horizon(self):
        st = self.a.slot_t
        np.testing.assert_array_equal(st, np.sort(st))
        self.assertGreaterEqual(float(st.min()), 31.0)
        self.assertLess(float(st.max()), 91.0)
        self.assertEqual(len(st), len(self.a.slot_y))

    def test_candidate_count_meets_the_minimum(self):
        self.assertGreaterEqual(len(self.a.candidates), 3)

    def test_require_truth_basin_is_honoured(self):
        self.assertGreaterEqual(self.a.true_basin_index, 0)
        self.assertLess(self.a.true_basin_index, len(self.a.candidates))


class TestCampaign(unittest.TestCase):

    def setUp(self):
        self.case = get_case(1)
        self.campaign = Campaign(self.case)

    def test_initial_state(self):
        self.assertEqual(self.campaign.cursor, 0)
        self.assertEqual(self.campaign.budget_left(), self.case.budget)
        self.assertEqual(len(self.campaign.remaining_slots()),
                         len(self.case.slot_t))

    def test_observe_returns_the_realized_outcome(self):
        y = self.campaign.observe(3)
        self.assertAlmostEqual(y, float(self.case.slot_y[3]), places=12)

    def test_observe_advances_the_cursor_past_the_slot(self):
        self.campaign.observe(3)
        self.assertEqual(self.campaign.cursor, 4)
        self.campaign.observe(9)
        self.assertEqual(self.campaign.cursor, 10)

    def test_no_time_travel(self):
        self.campaign.observe(5)
        for bad in (0, 4, 5):
            with self.subTest(idx=bad):
                with self.assertRaises(IllegalAction):
                    self.campaign.observe(bad)

    def test_no_revisit_of_the_observed_slot(self):
        self.campaign.observe(2)
        with self.assertRaises(IllegalAction):
            self.campaign.observe(2)

    def test_out_of_range_indices_rejected(self):
        n = len(self.case.slot_t)
        for bad in (-1, n, n + 5):
            with self.subTest(idx=bad):
                with self.assertRaises(IllegalAction):
                    self.campaign.observe(bad)

    def test_budget_enforced(self):
        for _ in range(self.case.budget):
            self.campaign.observe(self.campaign.cursor)
        self.assertEqual(self.campaign.budget_left(), 0)
        with self.assertRaises(IllegalAction):
            self.campaign.observe(self.campaign.cursor)

    def test_budget_left_decrements(self):
        for k in range(1, self.case.budget + 1):
            self.campaign.observe(self.campaign.cursor)
            self.assertEqual(self.campaign.budget_left(),
                             self.case.budget - k)

    def test_remaining_slots_shrinks_and_matches_times(self):
        self.campaign.observe(4)
        rem = self.campaign.remaining_slots()
        self.assertEqual([i for i, _ in rem],
                         list(range(5, len(self.case.slot_t))))
        for i, t in rem:
            self.assertAlmostEqual(t, float(self.case.slot_t[i]), places=12)

    def test_failed_observe_leaves_state_untouched(self):
        self.campaign.observe(4)
        snapshot = (self.campaign.cursor, list(self.campaign.obs_idx),
                    list(self.campaign.obs_t), list(self.campaign.obs_y))
        with self.assertRaises(IllegalAction):
            self.campaign.observe(1)
        self.assertEqual(
            snapshot,
            (self.campaign.cursor, list(self.campaign.obs_idx),
             list(self.campaign.obs_t), list(self.campaign.obs_y)))

    def test_data_returns_initial_plus_observed_in_order(self):
        picks = [1, 4, 9]
        for idx in picks:
            self.campaign.observe(idx)
        t, y = self.campaign.data()
        n_init = len(self.case.init_t)
        self.assertEqual(len(t), n_init + len(picks))
        np.testing.assert_array_equal(t[:n_init], self.case.init_t)
        np.testing.assert_array_equal(y[:n_init], self.case.init_y)
        np.testing.assert_allclose(t[n_init:], self.case.slot_t[picks],
                                   atol=1e-12)
        np.testing.assert_allclose(y[n_init:], self.case.slot_y[picks],
                                   atol=1e-12)

    def test_data_before_any_observation_is_the_initial_data(self):
        t, y = self.campaign.data()
        np.testing.assert_array_equal(t, self.case.init_t)
        np.testing.assert_array_equal(y, self.case.init_y)

    def test_two_campaigns_on_one_case_are_independent_and_identical(self):
        a, b = Campaign(self.case), Campaign(self.case)
        for idx in (1, 4, 7):
            a.observe(idx)
            b.observe(idx)
        self.assertEqual(a.obs_idx, b.obs_idx)
        self.assertEqual(a.obs_y, b.obs_y)
        self.assertEqual(self.campaign.cursor, 0)


if __name__ == "__main__":
    unittest.main()
