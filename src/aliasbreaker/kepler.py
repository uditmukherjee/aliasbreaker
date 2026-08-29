"""Keplerian radial-velocity model. Own implementation (learning goal + no deps)."""

import numpy as np


def solve_kepler(M, e, tol=1e-10, max_iter=60):
    """Solve Kepler's equation E - e*sin(E) = M for E. Vectorized Newton."""
    M = np.asarray(M, dtype=float)
    E = M + e * np.sin(M)
    for _ in range(max_iter):
        f = E - e * np.sin(E) - M
        fp = 1.0 - e * np.cos(E)
        dE = f / fp
        E = E - dE
        if np.max(np.abs(dE)) < tol:
            break
    return E


def true_anomaly(t, P, T0, e):
    """True anomaly at times t for period P, periastron time T0, eccentricity e."""
    M = 2.0 * np.pi * ((np.asarray(t, dtype=float) - T0) / P)
    M = np.mod(M, 2.0 * np.pi)
    E = solve_kepler(M, e)
    nu = 2.0 * np.arctan2(
        np.sqrt(1.0 + e) * np.sin(E / 2.0),
        np.sqrt(1.0 - e) * np.cos(E / 2.0),
    )
    return nu


def rv(t, P, T0, e, K, omega, gamma):
    """Stellar radial velocity (m/s) for a single-planet Keplerian orbit."""
    nu = true_anomaly(t, P, T0, e)
    return gamma + K * (np.cos(nu + omega) + e * np.cos(omega))


def rv_params(params, t):
    return rv(t, params["P"], params["T0"], params["e"], params["K"],
              params["omega"], params["gamma"])
