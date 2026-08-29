"""Hidden-outcome (slot_y) leakage guards — codex diff-gate 1, finding 8.

tests/test_leakage.py poisons only `true_params` / `true_basin_index`; it leaves
`slot_y` identical between the clean and poisoned cases. Unvisited `slot_y`
values are the most important hidden information in the world: a planner that
read every future realized outcome would still pass that suite.

These tests close the gap:
  * batch / even-spacing plan from the INITIAL data only -> replacing every
    slot_y value must not move a single scheduled slot.
  * scripted-adaptive may read a slot_y value ONLY for a slot it has legally
    observed. Proven two ways: a recording ndarray that logs every index read,
    and a two-pass replay in which every unobserved outcome is poisoned.
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

POISON = 1.0e6


def _replace_slot_y(case, transform):
    """Deep copy with every realized outcome replaced by transform(slot_y)."""
    poisoned = copy.deepcopy(case)
    poisoned.slot_y = transform(np.asarray(case.slot_y, dtype=float))
    return poisoned


class RecordingArray(np.ndarray):
    """ndarray that records every index used to read it.

    Scalar integer reads land in `.reads`; anything else (slice, fancy index,
    mask) lands in `.other_reads` so the test can prove no bulk read happened.
    """

    def __new__(cls, values, reads, other_reads):
        obj = np.asarray(values, dtype=float).view(cls)
        obj.reads = reads
        obj.other_reads = other_reads
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.reads = getattr(obj, "reads", None)
        self.other_reads = getattr(obj, "other_reads", None)

    def __getitem__(self, key):
        if isinstance(key, (int, np.integer)):
            if self.reads is not None:
                self.reads.add(int(key))
        else:
            if self.other_reads is not None:
                self.other_reads.append(repr(key))
        return super().__getitem__(key)


class TestBatchArmsIgnoreSlotY(unittest.TestCase):
    """Non-adaptive arms plan from the initial data only (charter section 6)."""

    @classmethod
    def setUpClass(cls):
        cls.cases = dev_cases(10)
        # Aggressive, sign-flipping, offset transform: nothing about the true
        # outcomes survives, so any dependence shows up immediately.
        cls.poisoned = [_replace_slot_y(c, lambda a: -3.0 * a + 17.5)
                        for c in cls.cases]

    def test_slot_y_actually_changed(self):
        """Guard the guard: the poisoned fixtures must really differ."""
        for clean, dirty in zip(self.cases, self.poisoned):
            self.assertEqual(clean.slot_y.shape, dirty.slot_y.shape)
            self.assertFalse(np.allclose(clean.slot_y, dirty.slot_y),
                             f"{clean.case_id}: slot_y unchanged by poisoning")
            # Everything else must be untouched, or the test proves nothing.
            np.testing.assert_array_equal(clean.slot_t, dirty.slot_t)
            np.testing.assert_array_equal(clean.init_t, dirty.init_t)
            np.testing.assert_array_equal(clean.init_y, dirty.init_y)
            self.assertEqual(list(clean.candidates), list(dirty.candidates))

    def test_batch_design_identical_under_slot_y_poisoning(self):
        for clean, dirty in zip(self.cases, self.poisoned):
            self.assertEqual(batch_design(clean), batch_design(dirty),
                             f"{clean.case_id}: batch design moved")

    def test_run_batch_slots_identical_under_slot_y_poisoning(self):
        for clean, dirty in zip(self.cases, self.poisoned):
            self.assertEqual(run_batch(clean)["slots"],
                             run_batch(dirty)["slots"],
                             f"{clean.case_id}: batch slots moved")

    def test_even_spacing_slots_identical_under_slot_y_poisoning(self):
        for clean, dirty in zip(self.cases, self.poisoned):
            self.assertEqual(run_even_spacing(clean)["slots"],
                             run_even_spacing(dirty)["slots"],
                             f"{clean.case_id}: even-spacing slots moved")

    def test_batch_design_never_reads_slot_y_at_all(self):
        """batch_design is a pure function of the initial data + slot times."""
        for case in self.cases:
            probe = copy.deepcopy(case)
            reads, other = set(), []
            probe.slot_y = RecordingArray(case.slot_y, reads, other)
            batch_design(probe)
            self.assertEqual(reads, set(),
                             f"{case.case_id}: batch_design read slot_y")
            self.assertEqual(other, [],
                             f"{case.case_id}: batch_design bulk-read slot_y")


class TestAdaptiveReadsOnlyObservedOutcomes(unittest.TestCase):
    """The adaptive arm's decisions may depend only on legally revealed data."""

    @classmethod
    def setUpClass(cls):
        cls.cases = dev_cases(10)

    def test_only_observed_slot_indices_are_read(self):
        for case in self.cases:
            probe = copy.deepcopy(case)
            reads, other = set(), []
            probe.slot_y = RecordingArray(case.slot_y, reads, other)
            out = run_scripted_adaptive(probe)
            self.assertEqual(other, [],
                             f"{case.case_id}: bulk read of slot_y {other}")
            self.assertEqual(
                reads, set(out["slots"]),
                f"{case.case_id}: read slot_y at {sorted(reads)} but observed "
                f"{sorted(out['slots'])}")

    def test_adaptive_invariant_to_poisoned_unobserved_outcomes(self):
        """Two-pass proof: keep only the outcomes pass 1 legally revealed,
        poison every other slot, and require an identical campaign."""
        for case in self.cases:
            first = run_scripted_adaptive(case)
            observed = set(first["slots"])

            def keep_only_observed(a, observed=observed):
                out = np.full(a.shape, POISON, dtype=float)
                for i in observed:
                    out[i] = a[i]
                return out

            poisoned = _replace_slot_y(case, keep_only_observed)
            second = run_scripted_adaptive(poisoned)

            self.assertEqual(first["slots"], second["slots"],
                             f"{case.case_id}: adaptive schedule changed when "
                             "unobserved outcomes were poisoned")
            for key in ("resolved", "pred", "n_obs"):
                self.assertEqual(first[key], second[key],
                                 f"{case.case_id}: {key} changed")
            self.assertAlmostEqual(first["max_support"], second["max_support"],
                                   places=12)

    def test_adaptive_stays_chronological_and_within_budget(self):
        """Sanity rail for the leakage proofs above."""
        for case in self.cases:
            out = run_scripted_adaptive(case)
            slots = out["slots"]
            self.assertEqual(slots, sorted(slots))
            self.assertEqual(len(slots), len(set(slots)))
            self.assertLessEqual(len(slots), case.budget)


if __name__ == "__main__":
    unittest.main()
