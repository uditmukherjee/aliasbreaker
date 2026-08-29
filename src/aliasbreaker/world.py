"""Synthetic RV world v2 (post plan-gate).

- Circular-orbit truth; white Gaussian noise (declared idealized benchmark).
- Fixtures store REALIZED potential outcomes for every slot: no runtime RNG.
- Candidates come from a truth-blind periodogram of the initial data.
- The Campaign state machine enforces chronology, budget, and no revisits.
"""

from dataclasses import dataclass, field

import numpy as np

from .fitting import candidate_periods

STREAM_INIT = 0
STREAM_SLOT = 1


def keyed_noise(seed, stream, idx):
    rng = np.random.default_rng(
        np.random.SeedSequence([int(seed), int(stream), int(idx)]))
    return float(rng.standard_normal())


def truth_rv(params, t):
    """Circular-orbit radial velocity of the hidden truth."""
    t = np.asarray(t, dtype=float)
    return params["gamma"] + params["K"] * np.cos(
        2.0 * np.pi * t / params["P"] + params["phi"])


@dataclass
class Case:
    case_id: str
    seed: int
    sigma: float
    budget: int
    init_t: np.ndarray
    init_y: np.ndarray
    slot_t: np.ndarray                       # legal follow-up slot times
    candidates: list                         # candidate periods (agent-visible)
    freq_df: float                           # periodogram grid step
    slot_y: np.ndarray = field(repr=False)   # realized outcomes (world/evaluator only)
    true_params: dict = field(repr=False)    # evaluator-only
    true_basin_index: int = field(repr=False)  # candidate basin holding truth, -1 if absent


class IllegalAction(Exception):
    pass


class Campaign:
    """Chronological follow-up campaign over a case's slots.

    Time only moves forward: observing slot j moves the cursor past j, so
    earlier slots become unreachable (a skipped night cannot be revisited).
    Realized outcomes stay hidden behind observe().
    """

    def __init__(self, case):
        self.case = case
        self.cursor = 0
        self.obs_idx, self.obs_t, self.obs_y = [], [], []

    def budget_left(self):
        return self.case.budget - len(self.obs_idx)

    def remaining_slots(self):
        return [(i, float(self.case.slot_t[i]))
                for i in range(self.cursor, len(self.case.slot_t))]

    def observe(self, idx):
        idx = int(idx)
        if not (self.cursor <= idx < len(self.case.slot_t)):
            raise IllegalAction(
                f"slot {idx} not observable (cursor={self.cursor}, "
                f"n_slots={len(self.case.slot_t)})")
        if self.budget_left() <= 0:
            raise IllegalAction("observation budget exhausted")
        self.cursor = idx + 1
        self.obs_idx.append(idx)
        self.obs_t.append(float(self.case.slot_t[idx]))
        y = float(self.case.slot_y[idx])
        self.obs_y.append(y)
        return y

    def data(self):
        """All measurements acquired so far (initial + campaign)."""
        t = np.concatenate([self.case.init_t, np.asarray(self.obs_t)])
        y = np.concatenate([self.case.init_y, np.asarray(self.obs_y)])
        return t, y


def make_case(seed, sigma=3.0, avail_frac=0.65, n_init=6, n_offcadence=4,
              budget=6, require_truth_basin=True, min_candidates=3):
    """Generate a case. Candidates are periodogram-derived (truth-blind).

    Returns None if no admissible case emerges from this seed.
    """
    rng = np.random.default_rng(np.random.SeedSequence([int(seed), 7]))
    for _attempt in range(40):
        true_params = {
            "P": float(rng.uniform(3.0, 20.0)),
            "K": float(rng.uniform(8.0, 30.0)),
            "phi": float(rng.uniform(0.0, 2.0 * np.pi)),
            "gamma": float(rng.uniform(-5.0, 5.0)),
        }
        nights = np.sort(rng.choice(np.arange(30), size=n_init, replace=False))
        init_t = nights + 0.15 + 0.05 * rng.random(n_init)
        init_y = truth_rv(true_params, init_t) + sigma * np.array(
            [keyed_noise(seed, STREAM_INIT, i) for i in range(n_init)])

        periods, df = candidate_periods(init_t, init_y, sigma)
        if len(periods) < min_candidates:
            continue

        f_true = 1.0 / true_params["P"]
        basin = -1
        for i, P in enumerate(periods):
            if abs(1.0 / P - f_true) <= 2.0 * df:
                basin = i
                break
        if require_truth_basin and basin < 0:
            continue

        slot_times = []
        for night in range(31, 91):
            if rng.random() > avail_frac:
                continue
            slot_times.append(night + 0.1 + 0.25 * rng.random())
        oc_nights = rng.choice(np.arange(31, 91), size=n_offcadence,
                               replace=False)
        for night in oc_nights:
            slot_times.append(float(night) + 0.45 + 0.15 * rng.random())
        slot_t = np.sort(np.array(slot_times))
        slot_y = truth_rv(true_params, slot_t) + sigma * np.array(
            [keyed_noise(seed, STREAM_SLOT, i) for i in range(len(slot_t))])

        return Case(
            case_id=f"case-{seed:03d}", seed=int(seed), sigma=float(sigma),
            budget=int(budget), init_t=init_t, init_y=init_y,
            slot_t=slot_t, slot_y=slot_y, candidates=list(periods),
            freq_df=float(df), true_params=true_params,
            true_basin_index=int(basin),
        )
    return None
