"""Circular-orbit fitting and least-squares periodogram (v2, post plan-gate).

Model: v(t) = gamma + A*cos(2*pi*f*t) + B*sin(2*pi*f*t), f = 1/P.
Exactly linear at fixed period -> deterministic, no optimizer, healthy dof.
Candidate periods are derived from the initial data ONLY (truth-blind).
"""

import numpy as np


def fit_circular(t, y, sigma, P):
    """Exact linear least-squares fit at fixed period P."""
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    w = 2.0 * np.pi * t / P
    X = np.column_stack([np.cos(w), np.sin(w), np.ones_like(w)])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = (y - X @ coef) / sigma
    A, B, C = (float(c) for c in coef)
    return {
        "P": float(P), "A": A, "B": B, "gamma": C,
        "K": float(np.hypot(A, B)),
        "chi2": float(resid @ resid),
    }


def predict_circular(fit, t):
    t = np.asarray(t, dtype=float)
    w = 2.0 * np.pi * t / fit["P"]
    return fit["gamma"] + fit["A"] * np.cos(w) + fit["B"] * np.sin(w)


def chi2_constant(y, sigma):
    y = np.asarray(y, dtype=float)
    resid = (y - y.mean()) / sigma
    return float(resid @ resid)


def periodogram(t, y, sigma, fmin=0.01, fmax=1.2, oversample=4):
    """Least-squares periodogram: chi2 of the circular fit at each frequency."""
    t = np.asarray(t, dtype=float)
    span = float(t.max() - t.min())
    df = 1.0 / (oversample * span)
    freqs = np.arange(fmin, fmax, df)
    chi2s = np.array([fit_circular(t, y, sigma, 1.0 / f)["chi2"] for f in freqs])
    return freqs, chi2s, df


def fit_basin(t, y, sigma, P_center, df, half_width_steps=2.0, n_fine=25):
    """Best circular fit with the period refined WITHIN the candidate's own
    frequency basin (±half_width_steps grid steps around its center).

    Candidates keep their identity by basin; without this, a candidate frozen
    at its initial grid peak accumulates phase error over the follow-up
    horizon and even the true candidate stops fitting its own data.
    """
    f0 = 1.0 / P_center
    fs = np.linspace(f0 - half_width_steps * df, f0 + half_width_steps * df,
                     n_fine)
    fs = fs[fs > 1e-6]
    best = None
    for f in fs:
        fit = fit_circular(t, y, sigma, 1.0 / f)
        if best is None or fit["chi2"] < best["chi2"]:
            best = fit
    return best


def candidate_periods(t, y, sigma, delta_chi2_keep=12.0, max_candidates=6,
                      min_sep_steps=5):
    """Candidate periods = top non-overlapping periodogram basins.

    Derived from the supplied observations only; the hidden truth is never an
    input. Returns (periods, df) with periods ordered by fit quality.
    """
    freqs, chi2s, df = periodogram(t, y, sigma)
    is_peak = np.zeros(len(freqs), dtype=bool)
    is_peak[1:-1] = (chi2s[1:-1] < chi2s[:-2]) & (chi2s[1:-1] < chi2s[2:])
    order = np.argsort(chi2s)
    best_chi2 = float(chi2s.min())
    kept = []
    for i in order:
        if not is_peak[i]:
            continue
        if chi2s[i] > best_chi2 + delta_chi2_keep:
            break
        if any(abs(freqs[i] - freqs[j]) < min_sep_steps * df for j in kept):
            continue
        kept.append(i)
        if len(kept) >= max_candidates:
            break
    return [1.0 / freqs[i] for i in kept], df


def support_from_chi2(chi2s):
    """Normalized candidate support (candidate-set-relative; NOT a calibrated
    probability): S_i = exp(-0.5*(chi2_i - chi2_min)) / sum_j(...)."""
    a = np.asarray(chi2s, dtype=float)
    s = np.exp(-0.5 * (a - a.min()))
    return s / s.sum()
