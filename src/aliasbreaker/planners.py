"""Non-LLM arms: batch baseline and scripted-adaptive policy.

Both share the same fitter, verifier, noise, and slots. The batch planner
commits to all observation times upfront; the scripted-adaptive policy re-plans
after every observation with updated candidate weights and refitted curves.
"""

import numpy as np

from .kepler import rv_params
from .fitting import refit_candidates, weights_from_chi2
from .world import observe

B_CAP = 4.0          # per-observation discrimination cap (units of sigma)
PAIR_NEED = 6.0      # total discrimination evidence sought per candidate pair
CONF_THRESHOLD = 0.9
EARLY_STOP = 0.97


def _pair_b(curves, sigma):
    """b[i,j,t] = capped |v_i - v_j| / sigma for all candidate pairs."""
    n = curves.shape[0]
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    b = np.array([np.clip(np.abs(curves[i] - curves[j]) / sigma, 0.0, B_CAP)
                  for i, j in pairs])
    return pairs, b


def _slot_value(pairs, b, weights, remaining, used):
    n_slots = b.shape[1]
    value = np.zeros(n_slots)
    for k, (i, j) in enumerate(pairs):
        value += weights[i] * weights[j] * np.minimum(b[k], remaining[k])
    value[list(used)] = -np.inf
    return value


def final_verdict(case, obs_t, obs_y):
    """Shared evaluator-facing verdict: refit all candidates on all data."""
    all_t = np.concatenate([case.init_t, np.asarray(obs_t)])
    all_y = np.concatenate([case.init_y, np.asarray(obs_y)])
    fits = refit_candidates(case.candidates, all_t, all_y, case.sigma)
    chi2s = [f["chi2"] for f in fits]
    w = weights_from_chi2(chi2s)
    pred = int(np.argmax(w))
    confident = float(w[pred]) >= CONF_THRESHOLD
    return {
        "pred": pred,
        "abstain": not confident,
        "passed": confident and pred == case.true_index,
        "truth_weight": float(w[case.true_index]),
        "max_weight": float(w[pred]),
        "chi2s": chi2s,
    }


def run_batch(case):
    """Baseline: plan all observations upfront from the initial fits."""
    curves = np.array([rv_params(c, case.slot_t) for c in case.candidates])
    weights = weights_from_chi2([c["chi2"] for c in case.candidates])
    pairs, b = _pair_b(curves, case.sigma)
    remaining = np.full(len(pairs), PAIR_NEED)
    used = []
    for _ in range(case.budget):
        value = _slot_value(pairs, b, weights, remaining, used)
        pick = int(np.argmax(value))
        used.append(pick)
        remaining = np.maximum(remaining - b[:, pick], 0.0)
    obs_t = [float(case.slot_t[i]) for i in used]
    obs_y = [observe(case, i) for i in used]
    out = final_verdict(case, obs_t, obs_y)
    out.update({"obs_used": len(used), "slots": used})
    return out


def run_scripted_adaptive(case):
    """Ablation arm: same scoring, re-planned after every observation."""
    fits = list(case.candidates)
    obs_slots, obs_t, obs_y = [], [], []
    pairs = [(i, j) for i in range(len(fits)) for j in range(i + 1, len(fits))]
    remaining = np.full(len(pairs), PAIR_NEED)
    for _ in range(case.budget):
        weights = weights_from_chi2([f["chi2"] for f in fits])
        if float(np.max(weights)) >= EARLY_STOP:
            break
        curves = np.array([rv_params(f, case.slot_t) for f in fits])
        pairs, b = _pair_b(curves, case.sigma)
        value = _slot_value(pairs, b, weights, remaining, obs_slots)
        pick = int(np.argmax(value))
        obs_slots.append(pick)
        obs_t.append(float(case.slot_t[pick]))
        obs_y.append(observe(case, pick))
        remaining = np.maximum(remaining - b[:, pick], 0.0)
        all_t = np.concatenate([case.init_t, obs_t])
        all_y = np.concatenate([case.init_y, obs_y])
        fits = refit_candidates(case.candidates, all_t, all_y, case.sigma)
    out = final_verdict(case, obs_t, obs_y)
    out.update({"obs_used": len(obs_slots), "slots": obs_slots})
    return out
