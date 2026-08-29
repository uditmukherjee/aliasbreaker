"""Non-LLM arms v2 (charter §6): batch baseline, even-spacing context baseline,
scripted-adaptive ablation. All run through the Campaign state machine and the
shared evaluator verdict; none touch hidden truth or unvisited outcomes.
"""

import numpy as np

from .fitting import fit_basin, predict_circular, support_from_chi2
from .world import Campaign
from .evaluator import verdict, THETA_DEFAULT

B_CAP = 4.0      # per-observation discrimination cap (units of sigma)
PAIR_NEED = 6.0  # discrimination evidence sought per candidate pair


def _fits_and_support(case, t, y):
    fits = [fit_basin(t, y, case.sigma, P, case.freq_df)
            for P in case.candidates]
    support = support_from_chi2([f["chi2"] for f in fits])
    return fits, support


def _pair_b(fits, slot_t, sigma):
    curves = np.array([predict_circular(f, slot_t) for f in fits])
    n = len(fits)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    b = np.array([np.clip(np.abs(curves[i] - curves[j]) / sigma, 0.0, B_CAP)
                  for i, j in pairs])
    return pairs, b


def _slot_value(pairs, b, support, remaining, forbidden):
    value = np.zeros(b.shape[1])
    for k, (i, j) in enumerate(pairs):
        value += support[i] * support[j] * np.minimum(b[k], remaining[k])
    if forbidden:
        value[list(forbidden)] = -np.inf
    return value


def batch_design(case):
    """Joint greedy set design from the initial fits: each pick maximizes the
    marginal pair-coverage gain of the whole plan. Deterministic tie-break:
    earliest slot (argmax returns the first maximum)."""
    fits, support = _fits_and_support(case, case.init_t, case.init_y)
    pairs, b = _pair_b(fits, case.slot_t, case.sigma)
    remaining = np.full(len(pairs), PAIR_NEED)
    picks = []
    for _ in range(min(case.budget, len(case.slot_t))):
        value = _slot_value(pairs, b, support, remaining, picks)
        pick = int(np.argmax(value))
        picks.append(pick)
        remaining = np.maximum(remaining - b[:, pick], 0.0)
    return sorted(picks)


def run_batch(case, theta=THETA_DEFAULT):
    """Baseline: commit to the joint greedy design upfront; no feedback, no
    early stopping (structural: a batch plan receives no interim results)."""
    campaign = Campaign(case)
    for idx in batch_design(case):
        campaign.observe(idx)
    out = verdict(case, campaign.obs_t, campaign.obs_y, theta)
    out["slots"] = campaign.obs_idx
    return out


def run_even_spacing(case, theta=THETA_DEFAULT):
    """Context baseline: k approximately evenly spaced slots."""
    n = len(case.slot_t)
    k = min(case.budget, n)
    picks = sorted({int(round(i)) for i in np.linspace(0, n - 1, k)})
    campaign = Campaign(case)
    for idx in picks:
        campaign.observe(idx)
    out = verdict(case, campaign.obs_t, campaign.obs_y, theta)
    out["slots"] = campaign.obs_idx
    return out


def run_scripted_adaptive(case, theta=THETA_DEFAULT):
    """Ablation arm: same pair-coverage score as the batch design, recomputed
    after every observation; stops when the shared verdict rule would resolve.
    Fully predeclared; chronological (can only pick slots at/after the
    cursor)."""
    campaign = Campaign(case)
    pairs0 = [(i, j) for i in range(len(case.candidates))
              for j in range(i + 1, len(case.candidates))]
    remaining = np.full(len(pairs0), PAIR_NEED)
    while campaign.budget_left() > 0:
        t, y = campaign.data()
        fits, support = _fits_and_support(case, t, y)
        if float(np.max(support)) >= theta:
            break
        future = campaign.remaining_slots()
        if not future:
            break
        future_idx = [i for i, _ in future]
        future_t = np.array([ft for _, ft in future])
        pairs, b = _pair_b(fits, future_t, case.sigma)
        value = _slot_value(pairs, b, support, remaining, forbidden=[])
        local = int(np.argmax(value))
        campaign.observe(future_idx[local])
        remaining = np.maximum(remaining - b[:, local], 0.0)
    out = verdict(case, campaign.obs_t, campaign.obs_y, theta)
    out["slots"] = campaign.obs_idx
    return out
