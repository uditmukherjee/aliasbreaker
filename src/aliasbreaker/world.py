"""Synthetic RV world: case generation, observation API, deterministic noise.

Ground truth by construction. Noise is keyed by (case seed, stream, index) so
any policy requesting the same observation receives the identical measurement.
"""

from dataclasses import dataclass, field

import numpy as np

from .kepler import rv
from .fitting import fit_fixed_period

STREAM_INIT = 0
STREAM_SLOT = 1


def keyed_noise(seed, stream, idx):
    rng = np.random.default_rng(np.random.SeedSequence([int(seed), int(stream), int(idx)]))
    return float(rng.standard_normal())


@dataclass
class Case:
    case_id: str
    seed: int
    sigma: float
    budget: int
    init_t: np.ndarray
    init_y: np.ndarray
    slot_t: np.ndarray            # legal follow-up observation times
    candidates: list              # fitted param dicts (fixed periods), agent-visible
    true_params: dict = field(repr=False)   # evaluator-only
    true_index: int = field(repr=False)     # evaluator-only


def observe(case, slot_idx):
    """Spend one observation at slot slot_idx; returns the noisy measurement."""
    t = float(case.slot_t[slot_idx])
    clean = float(rv(t, **{k: case.true_params[k] for k in
                           ("P", "T0", "e", "K", "omega", "gamma")}))
    return clean + case.sigma * keyed_noise(case.seed, STREAM_SLOT, slot_idx)


def _alias_period_pool(P):
    f = 1.0 / P
    pool = []
    for fa in (f + 1.0, abs(f - 1.0), f + 2.0, abs(f - 2.0)):
        if fa > 1e-6:
            pool.append(1.0 / fa)
    pool.extend([P / 2.0, 2.0 * P])
    return [p for p in pool if 1.2 <= p <= 200.0]


def make_case(seed, sigma=3.0, weather=0.3, n_init=8, n_offcadence=4,
              budget=6, delta_chi2_keep=9.0, max_candidates=6):
    """Generate a case whose alias candidates genuinely fit the initial data.

    Returns None if no admissible alias structure is found (caller retries
    with another seed).
    """
    rng = np.random.default_rng(np.random.SeedSequence([int(seed), 7]))
    for _attempt in range(40):
        P = float(rng.uniform(3.0, 20.0))
        K = float(rng.uniform(8.0, 30.0))
        e = float(rng.choice([0.0, 0.15, 0.3, 0.45]))
        omega = float(rng.uniform(0.0, 2.0 * np.pi))
        T0 = float(rng.uniform(0.0, P))
        gamma = float(rng.uniform(-5.0, 5.0))
        true_params = {"P": P, "T0": T0, "e": e, "K": K, "omega": omega,
                       "gamma": gamma}

        nights = np.sort(rng.choice(np.arange(30), size=n_init, replace=False))
        init_t = nights + 0.15 + 0.05 * rng.random(n_init)
        clean = rv(init_t, **true_params)
        init_y = clean + sigma * np.array(
            [keyed_noise(seed, STREAM_INIT, i) for i in range(n_init)])

        # Truth is refit from the data exactly like every alias: no leakage of
        # the generating parameters into the candidate set.
        fits = [fit_fixed_period(init_t, init_y, sigma, P)]
        for pa in _alias_period_pool(P):
            fits.append(fit_fixed_period(init_t, init_y, sigma, pa))

        # Dedupe near-identical periods (keep the better fit).
        deduped = []
        for c in sorted(fits, key=lambda c: c["chi2"]):
            if all(abs(c["P"] - d["P"]) / d["P"] > 0.01 for d in deduped):
                deduped.append(c)

        chi2_min = min(c["chi2"] for c in deduped)
        keep = [c for c in deduped
                if c["chi2"] <= chi2_min + delta_chi2_keep and c["K"] > 1.0]
        keep = sorted(keep, key=lambda c: c["chi2"])[:max_candidates]

        true_kept = [c for c in keep if abs(c["P"] - P) / P <= 0.01]
        if len(keep) < 3 or not true_kept:
            continue

        order = rng.permutation(len(keep))
        candidates = [keep[i] for i in order]
        true_index = int(np.argmax([abs(c["P"] - P) / P <= 0.01
                                    for c in candidates]))

        slot_times = []
        for night in range(31, 91):
            if rng.random() < weather:
                continue
            slot_times.append(night + 0.1 + 0.25 * rng.random())
        oc_nights = rng.choice(np.arange(31, 91), size=n_offcadence,
                               replace=False)
        for night in oc_nights:
            slot_times.append(float(night) + 0.45 + 0.15 * rng.random())
        slot_t = np.sort(np.array(slot_times))

        return Case(
            case_id=f"case-{seed:03d}", seed=int(seed), sigma=float(sigma),
            budget=int(budget), init_t=init_t, init_y=init_y, slot_t=slot_t,
            candidates=candidates, true_params=true_params,
            true_index=true_index,
        )
    return None
