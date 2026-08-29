"""Theta calibration (charter §3).

Runs the complete selection-and-stopping procedure (batch, even-spacing, and
scripted-adaptive arms — every non-LLM campaign class) over a large
independent synthetic calibration set, and selects the smallest theta from the
predeclared grid whose WORST-ARM false-resolution rate is <= 5%.

The calibration set is generated with require_truth_basin=False so cases where
the periodogram misses the true basin (natural unresolvables) are included at
their natural rate.

Run: python src/calibrate_theta.py
"""

import json
import time
from pathlib import Path

from aliasbreaker.world import make_case
from aliasbreaker.planners import (run_batch, run_even_spacing,
                                   run_scripted_adaptive)

THETA_GRID = [0.85, 0.90, 0.95, 0.99, 0.997]
N_CASES = 120
FRR_BOUND = 0.05
KNOBS = [{"sigma": 2.0}, {"sigma": 3.0}, {"sigma": 4.0}, {"sigma": 5.0}]
ARMS = {"batch": run_batch, "even": run_even_spacing,
        "adaptive": run_scripted_adaptive}


def main():
    cases, seed = [], 1000
    while len(cases) < N_CASES and seed < 3000:
        seed += 1
        case = make_case(seed, require_truth_basin=False,
                         **KNOBS[len(cases) % len(KNOBS)])
        if case is not None:
            cases.append(case)
    n_basin_absent = sum(1 for c in cases if c.true_basin_index < 0)
    print(f"calibration set: {len(cases)} cases "
          f"({n_basin_absent} with truth basin absent)")

    t0 = time.time()
    table = {}
    for theta in THETA_GRID:
        row = {}
        for arm, fn in ARMS.items():
            results = [fn(c, theta) for c in cases]
            row[arm] = {
                "false_resolution_rate": round(
                    sum(r["false_resolution"] for r in results) / len(cases), 4),
                "correct_rate": round(
                    sum(r["correct"] for r in results) / len(cases), 4),
                "abstain_rate": round(
                    sum(r["abstained"] for r in results) / len(cases), 4),
            }
        row["worst_arm_frr"] = max(v["false_resolution_rate"]
                                   for v in row.values() if isinstance(v, dict))
        table[str(theta)] = row
        print(f"theta={theta}: worst-arm FRR={row['worst_arm_frr']:.3f}  "
              + "  ".join(f"{a}: corr={row[a]['correct_rate']:.2f} "
                          f"frr={row[a]['false_resolution_rate']:.3f}"
                          for a in ARMS))

    chosen = next((th for th in THETA_GRID
                   if table[str(th)]["worst_arm_frr"] <= FRR_BOUND), None)
    elapsed = time.time() - t0
    out = {
        "theta_grid": THETA_GRID, "n_cases": len(cases),
        "n_basin_absent": n_basin_absent, "frr_bound": FRR_BOUND,
        "selection_rule": "smallest theta with worst-arm FRR <= bound",
        "chosen_theta": chosen, "elapsed_s": round(elapsed, 1),
        "table": table,
        "seeds": [c.seed for c in cases],
    }
    path = Path(__file__).resolve().parents[1] / "evaluation" / "theta-calibration.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"\nchosen theta: {chosen}  ({elapsed:.0f}s)  -> {path}")


if __name__ == "__main__":
    main()
