"""Resolvability oracle (charter section 4): arm-independent, deterministic,
and false by construction whenever the truth's basin is absent.

The production oracle uses n_random=2000; these tests use a much smaller
random budget so the suite stays fast. Determinism is what is under test, and
it holds for any fixed n_random because the RNG is seeded from the case.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from aliasbreaker.evaluator import resolvable
from aliasbreaker.world import make_case

from helpers import dev_cases

N_RANDOM = 200


def _find_absent_basin_case(max_seed=200):
    """A case generated without the truth-basin requirement whose truth basin
    really is missing from the candidate set."""
    for seed in range(1, max_seed + 1):
        case = make_case(seed, require_truth_basin=False)
        if case is not None and case.true_basin_index == -1:
            return case
    return None


_ABSENT_CASE = _find_absent_basin_case()


class TestOracle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = dev_cases(4)

    def test_deterministic_for_the_same_case(self):
        for case in self.cases:
            with self.subTest(case=case.case_id):
                a = resolvable(case, n_random=N_RANDOM)
                b = resolvable(case, n_random=N_RANDOM)
                self.assertIs(a, b)
                self.assertIsInstance(a, bool)

    def test_deterministic_across_equivalent_regenerated_cases(self):
        case = self.cases[0]
        twin = make_case(case.seed, sigma=case.sigma)
        self.assertIsNotNone(twin)
        self.assertIs(resolvable(case, n_random=N_RANDOM),
                      resolvable(twin, n_random=N_RANDOM))

    def test_oracle_seed_is_honoured(self):
        case = self.cases[0]
        a = resolvable(case, n_random=N_RANDOM, oracle_seed=99)
        b = resolvable(case, n_random=N_RANDOM, oracle_seed=99)
        self.assertIs(a, b)

    def test_more_random_designs_never_reduce_resolvability(self):
        for case in self.cases:
            with self.subTest(case=case.case_id):
                if resolvable(case, n_random=10):
                    self.assertTrue(resolvable(case, n_random=60))

    def test_impossible_theta_makes_nothing_resolvable(self):
        for case in self.cases:
            with self.subTest(case=case.case_id):
                self.assertFalse(
                    resolvable(case, theta=1.01, n_random=N_RANDOM))

    @unittest.skipIf(
        _ABSENT_CASE is None,
        "no seed <= 200 produced a case with true_basin_index == -1; the "
        "candidate procedure captures the truth basin very reliably at the "
        "default sigma, so this branch could not be exercised")
    def test_absent_truth_basin_is_never_resolvable(self):
        self.assertEqual(_ABSENT_CASE.true_basin_index, -1)
        self.assertFalse(resolvable(_ABSENT_CASE, n_random=N_RANDOM))
        # Short-circuits before any design search, so it holds for any budget.
        self.assertFalse(resolvable(_ABSENT_CASE, n_random=0))
        self.assertFalse(resolvable(_ABSENT_CASE, theta=0.0, n_random=N_RANDOM))

    @unittest.skipIf(_ABSENT_CASE is None, "no absent-basin case available")
    def test_absent_truth_basin_case_still_has_candidates(self):
        # The case is well-formed; only the truth's basin is missing.
        self.assertGreaterEqual(len(_ABSENT_CASE.candidates), 3)
        self.assertEqual(len(_ABSENT_CASE.slot_t), len(_ABSENT_CASE.slot_y))


if __name__ == "__main__":
    unittest.main()
