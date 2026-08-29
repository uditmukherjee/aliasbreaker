"""AliasBreaker feasibility harness v2 (replaces the retired kill test).

Per plan-gate finding F27, this checks FEASIBILITY ONLY — world validity,
truth-blind candidate construction, chronology enforcement, determinism,
oracle behavior, and runtime. It does not tune difficulty against arm
outcomes; final evaluation cases are governed by docs/evaluation-charter.md.

Run: python src/feasibility.py
"""

import json
import time
from pathlib import Path

import numpy as np

from aliasbreaker.world import make_case, truth_rv, Campaign, IllegalAction
from aliasbreaker.fitting import fit_circular, candidate_periods
from aliasbreaker.evaluator import verdict, resolvable, THETA_DEFAULT
from aliasbreaker.planners import run_batch, run_even_spacing, run_scripted_adaptive


def checks():
    # Physics: circular fit recovers a known signal on dense data.
    t = np.linspace(0.0, 40.0, 400)
    params = {"P": 7.3, "K": 15.0, "phi": 1.1, "gamma": 2.0}
    y = truth_rv(params, t)
    fit = fit_circular(t, y, 1.0, params["P"])
    assert abs(fit["K"] - params["K"]) < 1e-6 and abs(fit["gamma"] - 2.0) < 1e-6
    # Truth-blindness: candidate construction sees only (t, y, sigma).
    periods, _df = candidate_periods(t, y + 0.1, 1.0)
    assert any(abs(P - params["P"]) / params["P"] < 0.02 for P in periods)
    # Chronology and budget enforcement.
    case = None
    seed = 0
    while case is None:
        seed += 1
        case = make_case(seed)
    c = Campaign(case)
    c.observe(3)
    for bad in (2, 3):
        try:
            c.observe(bad)
            raise AssertionError("time travel permitted")
        except IllegalAction:
            pass
    c2 = Campaign(case)
    for _ in range(case.budget):
        c2.observe(c2.cursor)
    try:
        c2.observe(c2.cursor)
        raise AssertionError("budget not enforced")
    except IllegalAction:
        pass
    # Determinism: same actions -> identical outcomes and verdict.
    a, b = Campaign(case), Campaign(case)
    for idx in (1, 4, 7):
        a.observe(idx), b.observe(idx)
    va = verdict(case, a.obs_t, a.obs_y)
    vb = verdict(case, b.obs_t, b.obs_y)
    assert a.obs_y == b.obs_y and va == vb
    print("checks passed: physics, truth-blind candidates, chronology, "
          "budget, determinism")


def main():
    checks()
    cases, seed = [], 100
    knobs = [{"sigma": 2.0}, {"sigma": 3.0}, {"sigma": 4.0}, {"sigma": 5.0}]
    while len(cases) < 12 and seed < 400:
        seed += 1
        case = make_case(seed, **knobs[len(cases) % len(knobs)])
        if case is not None:
            cases.append(case)
    print(f"generated {len(cases)} dev cases from {seed - 100} seeds")

    t0 = time.time()
    oracle = {c.case_id: resolvable(c) for c in cases}
    t_oracle = time.time() - t0
    print(f"oracle: {sum(oracle.values())}/{len(cases)} resolvable "
          f"({t_oracle:.1f}s)")

    rows = []
    t0 = time.time()
    for case in cases:
        row = {"case": case.case_id, "sigma": case.sigma,
               "n_candidates": len(case.candidates),
               "resolvable": oracle[case.case_id]}
        for name, fn in (("batch", run_batch), ("even", run_even_spacing),
                         ("adaptive", run_scripted_adaptive)):
            v = fn(case)
            row[name] = {k: v[k] for k in
                         ("correct", "abstained", "false_resolution",
                          "truth_support", "n_obs")}
        rows.append(row)
        fmt = lambda r: ("OK" if r["correct"] else
                         ("abst" if r["abstained"] else "FALSE-RES"))
        print(f"{case.case_id} cands={row['n_candidates']} sigma={case.sigma:.0f} "
              f"resolvable={row['resolvable']} | "
              f"batch {fmt(row['batch'])} ({row['batch']['n_obs']}) | "
              f"even {fmt(row['even'])} ({row['even']['n_obs']}) | "
              f"adaptive {fmt(row['adaptive'])} ({row['adaptive']['n_obs']})")
    elapsed = time.time() - t0

    res = [r for r in rows if r["resolvable"]]
    summary = {
        "n_cases": len(rows), "n_resolvable": len(res),
        "theta": THETA_DEFAULT, "oracle_s": t_oracle, "arms_s": elapsed,
    }
    for arm in ("batch", "even", "adaptive"):
        summary[f"{arm}_correct_on_resolvable"] = sum(
            r[arm]["correct"] for r in res)
        summary[f"{arm}_false_resolutions"] = sum(
            r[arm]["false_resolution"] for r in rows)
    print(json.dumps(summary, indent=2))

    out = Path(__file__).resolve().parents[1] / "evaluation" / "feasibility-results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    print(f"written to {out}")


if __name__ == "__main__":
    main()
