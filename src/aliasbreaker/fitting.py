"""Fixed-period orbit fitting.

For fixed (P, e, T0) the RV model is linear:
  v = gamma + K*cos(nu+omega) + K*e*cos(omega)
    = C + A*cos(nu) + B*sin(nu),  A = K*cos(omega), B = -K*sin(omega),
      C = gamma + e*A
so we grid-search (e, T0) and solve the linear part exactly. Deterministic.
"""

import numpy as np

from .kepler import true_anomaly

E_GRID = (0.0, 0.15, 0.3, 0.45, 0.6)
N_T0 = 32


def _fit_grid(t, y, sigma, P, e_values, t0_values):
    best = None
    for e in e_values:
        for T0 in t0_values:
            nu = true_anomaly(t, P, T0, e)
            X = np.column_stack([np.cos(nu), np.sin(nu), np.ones_like(nu)])
            coef, *_ = np.linalg.lstsq(X, y, rcond=None)
            resid = (y - X @ coef) / sigma
            chi2 = float(resid @ resid)
            if best is None or chi2 < best["chi2"]:
                A, B, C = (float(c) for c in coef)
                best = {
                    "P": float(P), "e": float(e), "T0": float(T0),
                    "K": float(np.hypot(A, B)),
                    "omega": float(np.arctan2(-B, A)),
                    "gamma": float(C - e * A),
                    "chi2": chi2,
                }
    return best


def fit_fixed_period(t, y, sigma, P, e_grid=E_GRID, n_t0=N_T0):
    """Best-fit orbit at fixed period P: coarse grid, then local refinement.

    The refinement stage keeps the chi2 surface from plateauing on the coarse
    T0 grid, which otherwise penalizes candidates unevenly as data accumulate.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)
    coarse = _fit_grid(t, y, sigma, P, e_grid,
                       np.linspace(0.0, P, n_t0, endpoint=False))
    step = P / n_t0
    t0_fine = coarse["T0"] + np.linspace(-step, step, 17)
    e_fine = np.clip(coarse["e"] + np.array([-0.075, -0.0375, 0.0, 0.0375, 0.075]),
                     0.0, 0.7)
    fine = _fit_grid(t, y, sigma, P, np.unique(e_fine), t0_fine)
    return fine if fine["chi2"] < coarse["chi2"] else coarse


def refit_candidates(candidates, t, y, sigma):
    """Refit every candidate (fixed period) on the full data set."""
    return [fit_fixed_period(t, y, sigma, c["P"]) for c in candidates]


def weights_from_chi2(chi2s):
    """Relative likelihood weights from chi-squared values."""
    a = np.asarray(chi2s, dtype=float)
    w = np.exp(-0.5 * (a - a.min()))
    return w / w.sum()
