"""AliasBreaker kill test.

Decides whether the idea has measurable adaptivity headroom before we commit:
  1. Do alias candidate sets genuinely fit the initial data?
  2. Does scripted-adaptive beat the batch baseline on enough draft cases?
  3. Does the whole two-arm evaluation run in minutes?

Run: python src/killtest.py
"""

import json
import time
from pathlib import Path

import numpy as np

from aliasbreaker.kepler import rv, solve_kepler
from aliasbreaker.world import make_case
from aliasbreaker.planners import run_batch, run_scripted_adaptive


def sanity_checks():
    # e=0: RV must reduce to a pure sinusoid.
    t = np.linspace(0.0, 30.0, 500)
    got = rv(t, P=7.0, T0=2.0, e=0.0, K=12.0, omega=0.5, gamma=3.0)
    expected = 3.0 + 12.0 * np.cos(2 * np.pi * (t - 2.0) / 7.0 + 0.5)
    assert np.max(np.abs(got - expected)) < 1e-8, "circular-orbit sanity failed"
    # Kepler solver: E - e sinE == M.
    M = np.linspace(0.0, 2 * np.pi, 100)
    for e in (0.1, 0.4, 0.7):
        E = solve_kepler(M, e)
        assert np.max(np.abs(E - e * np.sin(E) - M)) < 1e-8
    print("sanity checks passed (circular-orbit limit, Kepler residuals)")


def main():
    sanity_checks()
    configs = []
    seed = 0
    # Spread of difficulty knobs; keep generating until 12 valid cases.
    # Calibration iteration 1 (recorded in journal): fewer initial points,
    # higher noise, sparser windows, looser alias admission -> harder cases.
    knobs = [
        {"sigma": 3.0, "weather": 0.35}, {"sigma": 4.0, "weather": 0.35},
        {"sigma": 5.0, "weather": 0.5}, {"sigma": 6.0, "weather": 0.5},
    ]
    cases = []
    while len(cases) < 12 and seed < 200:
        seed += 1
        knob = knobs[len(cases) % len(knobs)]
        case = make_case(seed, sigma=knob["sigma"], weather=knob["weather"],
                         n_init=6, delta_chi2_keep=12.0)
        if case is not None:
            cases.append(case)
    print(f"generated {len(cases)} cases from {seed} seeds\n")

    rows = []
    t_start = time.time()
    for case in cases:
        b = run_batch(case)
        a = run_scripted_adaptive(case)
        rows.append({
            "case": case.case_id, "n_candidates": len(case.candidates),
            "sigma": case.sigma, "true_P": round(case.true_params["P"], 3),
            "periods": [round(c["P"], 3) for c in case.candidates],
            "batch": {k: b[k] for k in ("passed", "abstain", "truth_weight", "obs_used")},
            "adaptive": {k: a[k] for k in ("passed", "abstain", "truth_weight", "obs_used")},
        })
        print(f"{case.case_id}  cands={len(case.candidates)}  sigma={case.sigma:.0f}  "
              f"batch: {'PASS' if b['passed'] else ('abstain' if b['abstain'] else 'WRONG')} "
              f"(w_truth={b['truth_weight']:.2f})  "
              f"adaptive: {'PASS' if a['passed'] else ('abstain' if a['abstain'] else 'WRONG')} "
              f"(w_truth={a['truth_weight']:.2f}, obs={a['obs_used']})")
    elapsed = time.time() - t_start

    batch_pass = sum(r["batch"]["passed"] for r in rows)
    adaptive_pass = sum(r["adaptive"]["passed"] for r in rows)
    adaptive_only = [r["case"] for r in rows
                     if r["adaptive"]["passed"] and not r["batch"]["passed"]]
    batch_only = [r["case"] for r in rows
                  if r["batch"]["passed"] and not r["adaptive"]["passed"]]
    print(f"\nbatch passes:    {batch_pass}/{len(rows)}")
    print(f"adaptive passes: {adaptive_pass}/{len(rows)}")
    print(f"adaptive-only wins: {adaptive_only}")
    print(f"batch-only wins:    {batch_only}")
    print(f"two-arm evaluation wall time: {elapsed:.1f}s")

    out = Path(__file__).resolve().parents[1] / "evaluation" / "killtest-results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "batch_pass": batch_pass, "adaptive_pass": adaptive_pass,
        "adaptive_only_wins": adaptive_only, "batch_only_wins": batch_only,
        "elapsed_s": elapsed, "rows": rows,
    }, indent=2))
    print(f"results written to {out}")


if __name__ == "__main__":
    main()
