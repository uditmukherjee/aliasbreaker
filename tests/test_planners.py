"""Non-LLM arms (charter section 6): determinism, legality, budget, and
chronology of the scheduling produced by each scripted arm."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from aliasbreaker.evaluator import THETA_DEFAULT
from aliasbreaker.planners import (batch_design, run_batch, run_even_spacing,
                                   run_scripted_adaptive)

from helpers import dev_cases

VERDICT_KEYS = {"resolved", "abstained", "pred", "correct", "false_resolution",
                "max_support", "truth_support", "chi2s", "n_obs", "slots"}


class TestBatchDesign(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = dev_cases(10)

    def test_deterministic(self):
        for case in self.cases:
            with self.subTest(case=case.case_id):
                self.assertEqual(batch_design(case), batch_design(case))

    def test_sorted_unique_in_range_and_within_budget(self):
        for case in self.cases:
            with self.subTest(case=case.case_id):
                design = batch_design(case)
                self.assertEqual(design, sorted(design))
                self.assertEqual(len(design), len(set(design)),
                                 f"duplicate slot in design {design}")
                self.assertLessEqual(len(design), case.budget)
                for idx in design:
                    self.assertGreaterEqual(idx, 0)
                    self.assertLess(idx, len(case.slot_t))
                    self.assertIsInstance(idx, int)

    def test_uses_the_full_budget_when_slots_allow(self):
        for case in self.cases:
            with self.subTest(case=case.case_id):
                expected = min(case.budget, len(case.slot_t))
                self.assertEqual(len(batch_design(case)), expected)


class TestArms(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.cases = dev_cases(10)
        cls.results = {
            "batch": [run_batch(c) for c in cls.cases],
            "even": [run_even_spacing(c) for c in cls.cases],
            "adaptive": [run_scripted_adaptive(c) for c in cls.cases],
        }

    def test_all_arms_complete_on_every_dev_case(self):
        for arm, outs in self.results.items():
            with self.subTest(arm=arm):
                self.assertEqual(len(outs), len(self.cases))
                for out in outs:
                    self.assertTrue(VERDICT_KEYS.issubset(out.keys()))

    def test_run_batch_slots_equal_the_design(self):
        for case, out in zip(self.cases, self.results["batch"]):
            with self.subTest(case=case.case_id):
                self.assertEqual(out["slots"], batch_design(case))

    def test_every_arm_respects_budget_range_and_chronology(self):
        for arm, outs in self.results.items():
            for case, out in zip(self.cases, outs):
                with self.subTest(arm=arm, case=case.case_id):
                    slots = out["slots"]
                    self.assertLessEqual(len(slots), case.budget)
                    self.assertEqual(out["n_obs"], len(slots))
                    self.assertEqual(len(slots), len(set(slots)))
                    for a, b in zip(slots, slots[1:]):
                        self.assertLess(a, b, "slots must strictly increase")
                    for idx in slots:
                        self.assertIn(idx, range(len(case.slot_t)))

    def test_arms_are_deterministic(self):
        case = self.cases[0]
        for fn in (run_batch, run_even_spacing, run_scripted_adaptive):
            with self.subTest(fn=fn.__name__):
                a, b = fn(case), fn(case)
                self.assertEqual(a["slots"], b["slots"])
                self.assertEqual(a["pred"], b["pred"])
                self.assertEqual(a["resolved"], b["resolved"])

    def test_even_spacing_is_actually_spread_out(self):
        for case, out in zip(self.cases, self.results["even"]):
            with self.subTest(case=case.case_id):
                slots = out["slots"]
                self.assertEqual(slots[0], 0)
                self.assertEqual(slots[-1], len(case.slot_t) - 1)

    def test_scripted_adaptive_stops_early_only_when_resolved(self):
        # The ablation's declared stopping rule: it keeps observing until the
        # shared verdict rule would resolve, or the budget/horizon runs out.
        for case, out in zip(self.cases, self.results["adaptive"]):
            with self.subTest(case=case.case_id):
                if len(out["slots"]) < case.budget:
                    self.assertTrue(
                        out["resolved"]
                        or out["max_support"] >= THETA_DEFAULT
                        or not out["slots"]
                        or out["slots"][-1] == len(case.slot_t) - 1,
                        "stopped early without resolving or exhausting slots")

    def test_theta_is_threaded_through_the_arms(self):
        case = self.cases[0]
        loose = run_batch(case, theta=0.0)
        self.assertTrue(loose["resolved"])
        strict = run_batch(case, theta=1.01)
        self.assertFalse(strict["resolved"])
        self.assertEqual(loose["slots"], strict["slots"])

    def test_adaptive_never_exceeds_budget_under_a_loose_theta(self):
        for case in self.cases:
            with self.subTest(case=case.case_id):
                out = run_scripted_adaptive(case, theta=1.01)
                self.assertLessEqual(len(out["slots"]), case.budget)


if __name__ == "__main__":
    unittest.main()
