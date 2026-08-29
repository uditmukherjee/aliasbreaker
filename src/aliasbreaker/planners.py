"""Non-LLM arms v3 (charter §6; mock-judge critical finding 1): batch
baseline, even-spacing context baseline, scripted-adaptive ablation. All run
through the Campaign state machine and the shared evaluator verdict; none
touch hidden truth or unvisited outcomes.

v3 fixes the degenerate baseline scoring found by the pre-freeze mock
judging: the old linear/capped score (cap 4 vs need 6) saturated after ~2
picks and then selected slots by array index. Scoring is now chi2-shaped —
discrimination between hypotheses accumulates as (delta/sigma)^2, exactly
what the evaluator's chi2 measures — uncapped per slot, saturating per PAIR
only at the decided threshold, with an unsaturated fallback so the score can
never degenerate to index picks. All plan-executing arms also apply the
SHARED deterministic stop rule while executing (charter §1/§6): stopping when
the shared verdict rule already resolves requires no scheduling feedback.
"""

import numpy as np

from .fitting import fit_basin, predict_circular, support_from_chi2
from .world import Campaign
from .evaluator import verdict, THETA_DEFAULT

# Delta-chi2 at which a candidate pair counts as decided: just above the
# ~11.6 needed for support 0.997 over a single rival; beyond it, further
# evidence on the same pair has diminishing planning value.
PAIR_NEED_CHI2 = 16.0


def _fits_and_support(case, t, y):
    fits = [fit_basin(t, y, case.sigma, P, case.freq_df)
            for P in case.candidates]
    support = support_from_chi2([f["chi2"] for f in fits])
    return fits, support


def _pair_b2(fits, slot_t, sigma):
    """b2[pair, slot] = squared predicted separation in sigma units, UNCAPPED."""
    curves = np.array([predict_circular(f, slot_t) for f in fits])
    n = len(fits)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    b2 = np.array([((curves[i] - curves[j]) / sigma) ** 2 for i, j in pairs])
    return pairs, b2


def _slot_value(pairs, b2, support, remaining, forbidden):
    """Marginal chi2 gain with per-pair saturation and an unsaturated
    fallback (never index-degenerate). support=None -> unweighted (the
    strongest batch variant in the pre-freeze sweep; support-weighting
    over-concentrates on the current top pair)."""
    value = np.zeros(b2.shape[1])
    raw = np.zeros(b2.shape[1])
    for k, (i, j) in enumerate(pairs):
        w = 1.0 if support is None else support[i] * support[j]
        value += w * np.minimum(b2[k], remaining[k])
        raw += w * b2[k]
    if forbidden:
        value[list(forbidden)] = -np.inf
        raw[list(forbidden)] = -np.inf
    return value if float(np.max(value)) > 0.0 else raw


def batch_design(case):
    """Joint greedy set design from the initial fits only: each pick
    maximizes the marginal unweighted chi2-shaped gain of the whole plan
    (strongest of 8 variants swept pre-freeze; see journal). Deterministic
    tie-break: earliest slot (argmax returns the first maximum)."""
    fits, _support = _fits_and_support(case, case.init_t, case.init_y)
    pairs, b2 = _pair_b2(fits, case.slot_t, case.sigma)
    remaining = np.full(len(pairs), PAIR_NEED_CHI2)
    picks = []
    for _ in range(min(case.budget, len(case.slot_t))):
        value = _slot_value(pairs, b2, None, remaining, picks)
        pick = int(np.argmax(value))
        picks.append(pick)
        remaining = np.maximum(remaining - b2[:, pick], 0.0)
    return sorted(picks)


def _execute_plan(case, picks, theta):
    """Execute a predeclared plan in chronological order under the SHARED
    stop rule: after each observation, if the shared verdict rule already
    resolves, stop. Requires no scheduling feedback; charter §1 gives every
    acting policy the stop action."""
    campaign = Campaign(case)
    for idx in picks:
        campaign.observe(idx)
        t, y = campaign.data()
        _fits, support = _fits_and_support(case, t, y)
        if float(np.max(support)) >= theta:
            break
    out = verdict(case, campaign.obs_t, campaign.obs_y, theta)
    out["slots"] = campaign.obs_idx
    return out


def run_batch(case, theta=THETA_DEFAULT):
    """Baseline: joint greedy design committed upfront (planned from initial
    data only), executed with the shared stop rule."""
    return _execute_plan(case, batch_design(case), theta)


def run_even_spacing(case, theta=THETA_DEFAULT):
    """Context baseline: approximately evenly spaced slots, shared stop rule."""
    n = len(case.slot_t)
    k = min(case.budget, n)
    picks = sorted({int(round(i)) for i in np.linspace(0, n - 1, k)})
    return _execute_plan(case, picks, theta)


def run_scripted_adaptive(case, theta=THETA_DEFAULT):
    """Ablation arm: same chi2-shaped score as the batch design, recomputed
    after every observation with refitted candidates and updated support;
    same shared stop rule. Fully predeclared; chronological."""
    campaign = Campaign(case)
    pairs0 = [(i, j) for i in range(len(case.candidates))
              for j in range(i + 1, len(case.candidates))]
    remaining = np.full(len(pairs0), PAIR_NEED_CHI2)
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
        pairs, b2 = _pair_b2(fits, future_t, case.sigma)
        value = _slot_value(pairs, b2, support, remaining, forbidden=[])
        local = int(np.argmax(value))
        campaign.observe(future_idx[local])
        remaining = np.maximum(remaining - b2[:, local], 0.0)
    out = verdict(case, campaign.obs_t, campaign.obs_y, theta)
    out["slots"] = campaign.obs_idx
    return out
