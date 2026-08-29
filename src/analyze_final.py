"""Frozen analysis for the final evaluation (predeclared before the
selection-lock commit; charter §7 + diff-gate 2 findings 7/9).

Primary: paired difference in correct-resolution rate on RESOLVABLE final
cases, LLM (mean over the 3 fixed replicates, eligibility-gated) minus batch
baseline, with a case-clustered bootstrap 95% interval (fixed seed).
Secondary: unsafe-resolution behavior on the unresolvable stratum, per-stratum
table, observations used, eligibility accounting. All failures retained.

Run AFTER the final arms complete:
  python src/analyze_final.py
Inputs: evaluation/final-manifest.json, evaluation/arms-final.json,
        evaluation/llm-arm-final.json (replicates r1..r3 per case)
Output: evaluation/final-analysis.json + printed tables.
"""

import json
from pathlib import Path

import numpy as np

BOOTSTRAP_SEED = 20260830
BOOTSTRAP_ITERS = 10000

ROOT = Path(__file__).resolve().parents[1]


EXPECTED_REPLICATES = 3


def main(eval_dir=None):
    ev = Path(eval_dir) if eval_dir else ROOT / "evaluation"
    manifest = json.loads((ev / "final-manifest.json").read_text())
    arms = json.loads((ev / "arms-final.json").read_text())
    llm = json.loads((ev / "llm-arm-final.json").read_text())

    strata = {c["case_id"]: c["stratum"] for c in manifest["cases"]}
    # Integrity: the arms results must cover exactly the manifest's cases,
    # and fixture hashes must match the manifest (mock-judge finding).
    manifest_ids = set(strata)
    arms_ids = {r["case"] for r in arms["rows"]}
    if arms_ids != manifest_ids:
        raise SystemExit(f"arms/manifest case mismatch: "
                         f"{sorted(arms_ids ^ manifest_ids)}")
    import hashlib
    for c in manifest["cases"]:
        fixture = ROOT / "data" / "cases" / "final" / f"{c['case_id']}.json"
        if fixture.exists():
            actual = hashlib.sha256(fixture.read_bytes()).hexdigest()
            if actual != c["sha256"]:
                raise SystemExit(f"fixture hash mismatch: {c['case_id']}")
    resolvable_ids = sorted(c["case_id"] for c in manifest["cases"]
                            if c["stratum"] != "unresolvable")
    unresolvable_ids = sorted(c["case_id"] for c in manifest["cases"]
                              if c["stratum"] == "unresolvable")

    arm_rows = {r["case"]: r for r in arms["rows"]}
    llm_by_case = {}
    for r in llm["results"]:
        llm_by_case.setdefault(r["case"], []).append(r)

    per_case = []
    for cid in sorted(strata):
        reps = llm_by_case.get(cid, [])
        # Missing replicates (crashed launcher, absent runs) score 0
        # (noncompletion = unresolved) over the EXPECTED replicate count —
        # never crash, never silently shrink the denominator.
        llm_correct = [1.0 if x["outcome"]["correct"] else 0.0 for x in reps]
        llm_false = [1.0 if x["outcome"]["false_resolution"] else 0.0
                     for x in reps]
        llm_correct += [0.0] * (EXPECTED_REPLICATES - len(llm_correct))
        llm_false += [0.0] * (EXPECTED_REPLICATES - len(llm_false))
        llm_obs = [x["verdict_raw"]["n_obs"] for x in reps
                   if x["outcome"]["eligible"] and x["verdict_raw"]]
        row = {
            "case": cid, "stratum": strata[cid],
            "llm_replicates_present": len(reps),
            "llm_eligible": sum(x["outcome"]["eligible"] for x in reps),
            "llm_correct_replicates": llm_correct,
            "llm_correct_mean": float(np.mean(llm_correct)),
            "llm_false_res_mean": float(np.mean(llm_false)),
            "llm_obs_eligible": llm_obs,
        }
        for arm in ("batch", "even", "adaptive"):
            a = arm_rows[cid][arm]
            row[f"{arm}_correct"] = bool(a["correct"])
            row[f"{arm}_false_resolution"] = bool(a["false_resolution"])
            row[f"{arm}_n_obs"] = a["n_obs"]
        per_case.append(row)

    res_rows = [r for r in per_case if r["case"] in resolvable_ids]
    if not res_rows:
        raise SystemExit("no resolvable cases in inputs — nothing to analyze")
    # Two-stage bootstrap: resample cases WITH their replicate vectors, then
    # within each drawn case resample replicate outcomes — so replicate
    # variance is propagated, not discarded (mock-judge finding).
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    reps_matrix = [np.array(r["llm_correct_replicates"]) for r in res_rows]
    batch_vec = np.array([1.0 if r["batch_correct"] else 0.0
                          for r in res_rows])
    n = len(res_rows)
    boot = np.empty(BOOTSTRAP_ITERS)
    for it in range(BOOTSTRAP_ITERS):
        idx = rng.integers(0, n, n)
        diffs_it = np.empty(n)
        for j, ci_ in enumerate(idx):
            reps = reps_matrix[ci_]
            resampled = reps[rng.integers(0, len(reps), len(reps))]
            diffs_it[j] = resampled.mean() - batch_vec[ci_]
        boot[it] = diffs_it.mean()
    diffs = np.array([reps_matrix[j].mean() - batch_vec[j]
                      for j in range(n)])
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]

    def arm_rate(arm):
        return sum(1 for r in res_rows if r[f"{arm}_correct"]) / len(res_rows)

    unres = [r for r in per_case if r["case"] in unresolvable_ids]
    analysis = {
        "bootstrap_seed": BOOTSTRAP_SEED, "bootstrap_iters": BOOTSTRAP_ITERS,
        "n_resolvable": len(res_rows), "n_unresolvable": len(unres),
        "primary": {
            "llm_correct_rate_resolvable": float(np.mean(
                [r["llm_correct_mean"] for r in res_rows])),
            "batch_correct_rate_resolvable": arm_rate("batch"),
            "paired_mean_diff_llm_minus_batch": float(diffs.mean()),
            "bootstrap_95ci": ci,
            "note": ("case-clustered bootstrap over resolvable cases; small "
                     "n — interval is descriptive, no significance claim"),
        },
        "secondary": {
            "even_correct_rate_resolvable": arm_rate("even"),
            "adaptive_correct_rate_resolvable": arm_rate("adaptive"),
            "unresolvable_stratum": {
                "llm_false_res_mean": float(np.mean(
                    [r["llm_false_res_mean"] for r in unres])) if unres else None,
                **{f"{arm}_false_resolutions": sum(
                    1 for r in unres if r[f"{arm}_false_resolution"])
                    for arm in ("batch", "even", "adaptive")},
            },
            "llm_mean_obs_eligible": (
                float(np.mean(all_obs)) if (all_obs := [
                    o for r in per_case for o in r["llm_obs_eligible"]])
                else None),
            "llm_ineligible_runs": llm.get("ineligible", []),
        },
        "per_case": per_case,
    }
    out = ev / "final-analysis.json"
    out.write_text(json.dumps(analysis, indent=2))
    print(json.dumps({k: analysis[k] for k in
                      ("primary", "secondary")}, indent=2))
    print(f"\nfull analysis -> {out}")


if __name__ == "__main__":
    main()
