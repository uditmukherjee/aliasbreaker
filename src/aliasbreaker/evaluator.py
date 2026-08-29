"""Evaluator-owned verdict rule and resolvability oracle (charter §3–4).

The verdict is deterministic and identical for every arm: no agent supplies
its own confidence. THETA below is a pre-calibration placeholder; the final
value comes from the charter's calibration run and is committed with it.
"""

import itertools

import numpy as np

from .fitting import fit_basin, support_from_chi2

# Calibrated per charter §3 on 120 dev cases (smallest grid value with
# worst-arm false-resolution rate <= 5%). See evaluation/theta-calibration.json.
THETA_DEFAULT = 0.997


def verdict(case, obs_t, obs_y, theta=THETA_DEFAULT):
    """Refit every candidate (within its basin) on all data; apply the rule."""
    all_t = np.concatenate([case.init_t, np.asarray(obs_t, dtype=float)])
    all_y = np.concatenate([case.init_y, np.asarray(obs_y, dtype=float)])
    fits = [fit_basin(all_t, all_y, case.sigma, P, case.freq_df)
            for P in case.candidates]
    chi2s = [f["chi2"] for f in fits]
    support = support_from_chi2(chi2s)
    pred = int(np.argmax(support))
    resolved = float(support[pred]) >= theta
    correct = (resolved and case.true_basin_index >= 0
               and pred == case.true_basin_index)
    truth_support = (float(support[case.true_basin_index])
                     if case.true_basin_index >= 0 else 0.0)
    return {
        "resolved": resolved,
        "abstained": not resolved,
        "pred": pred,
        "correct": bool(correct),
        "false_resolution": bool(resolved and not correct),
        "max_support": float(support[pred]),
        "truth_support": truth_support,
        "chi2s": chi2s,
        "n_obs": int(len(obs_t)),
    }


def _design_outcome(case, idx_set, theta):
    obs_t = [float(case.slot_t[i]) for i in idx_set]
    obs_y = [float(case.slot_y[i]) for i in idx_set]
    return verdict(case, obs_t, obs_y, theta)


def resolvable(case, theta=THETA_DEFAULT, n_random=2000, oracle_seed=1234):
    """Arm-independent resolvability oracle (charter §4).

    RESOLVABLE iff truth's basin is among the candidates AND at least one
    legal budget-sized design (greedy joint design or one of n_random seeded
    random designs) yields a correct resolved verdict on the realized
    outcomes.
    """
    if case.true_basin_index < 0:
        return False
    n = len(case.slot_t)
    k = min(case.budget, n)

    from .planners import batch_design  # local import to avoid cycle
    greedy = batch_design(case)
    if _design_outcome(case, sorted(greedy), theta)["correct"]:
        return True

    rng = np.random.default_rng(
        np.random.SeedSequence([int(case.seed), int(oracle_seed)]))
    for _ in range(n_random):
        idx_set = sorted(rng.choice(n, size=k, replace=False).tolist())
        if _design_outcome(case, idx_set, theta)["correct"]:
            return True
    return False
