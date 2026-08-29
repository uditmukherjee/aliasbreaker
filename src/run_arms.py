"""Run the non-LLM arms (batch, even-spacing, scripted-adaptive) on a fixture
set and save per-case results — the deterministic side of every comparison.

Usage (repo root, PYTHONPATH=src):
  python src/run_arms.py --cases data/cases/dev --label dev-fixtures-v2
"""

import argparse
import json
import time
from pathlib import Path

from aliasbreaker.world import case_from_dict
from aliasbreaker.evaluator import THETA_DEFAULT
from aliasbreaker.planners import (run_batch, run_even_spacing,
                                   run_scripted_adaptive)

ARMS = {"batch": run_batch, "even": run_even_spacing,
        "adaptive": run_scripted_adaptive}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--label", required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[1]

    rows = []
    t0 = time.time()
    for path in sorted(Path(args.cases).resolve().glob("*.json")):
        d = json.loads(path.read_text())
        case = case_from_dict(d)
        oracle = d["hidden"].get("oracle", {})
        row = {"case": case.case_id, "sigma": case.sigma,
               "n_candidates": len(case.candidates),
               "resolvable": oracle.get("resolvable"),
               "fixture": path.name}
        for arm, fn in ARMS.items():
            v = fn(case, THETA_DEFAULT)
            row[arm] = {k: v[k] for k in
                        ("correct", "abstained", "false_resolution",
                         "truth_support", "n_obs")}
            row[arm]["slots"] = v["slots"]
        rows.append(row)
        print(f"{case.case_id} resolvable={row['resolvable']} | " + " | ".join(
            f"{a}: {'OK' if row[a]['correct'] else ('abst' if row[a]['abstained'] else 'FALSE-RES')}"
            f" ({row[a]['n_obs']})" for a in ARMS))

    res = [r for r in rows if r["resolvable"]]
    summary = {"label": args.label, "theta": THETA_DEFAULT,
               "n_cases": len(rows), "n_resolvable": len(res),
               "elapsed_s": round(time.time() - t0, 2)}
    for arm in ARMS:
        summary[f"{arm}_correct_on_resolvable"] = sum(
            r[arm]["correct"] for r in res)
        summary[f"{arm}_false_resolutions"] = sum(
            r[arm]["false_resolution"] for r in rows)
        summary[f"{arm}_mean_obs"] = round(
            sum(r[arm]["n_obs"] for r in rows) / len(rows), 2)
    print(json.dumps(summary, indent=2))
    out = root / "evaluation" / f"arms-{args.label}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2))
    print(f"written to {out}")


if __name__ == "__main__":
    main()
