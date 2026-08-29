"""Audit replay (charter §8): re-executes a recorded campaign against the
hashed fixture and recomputes everything.

Checks, all fail-closed:
- fixture SHA-256 matches the hash pinned in meta.json at start
- the action log's successful observes replay legally (chronology, budget)
- every logged measurement equals the fixture-derived value
- state.json's observed_slots equal the replayed sequence
- verdict.json matches a fresh evaluator verdict at the pinned theta

Replay verifies integrity and recomputability of the recorded campaign;
provenance of the agent's decisions rests on the recorded provider transcript
(disclosed in the charter).

Usage: python -m aliasbreaker.replay --run <run_dir>   (from repo root)
Importable: replay(run_dir) -> dict
"""

import argparse
import hashlib
import json
from pathlib import Path

from .world import Campaign, IllegalAction, case_from_dict
from .evaluator import verdict

RV_TOL = 5e-4  # action logs before the 6-dp change stored 3 dp


def replay(run_dir):
    run = Path(run_dir)
    out = {"run": str(run), "ok": False, "checks": {}, "mismatches": []}

    def check(name, ok, detail=None):
        out["checks"][name] = bool(ok)
        if not ok:
            out["mismatches"].append({"check": name, "detail": detail})

    try:
        meta = json.loads((run / "meta.json").read_text())
        state = json.loads((run / "state.json").read_text())
        actions = [json.loads(line) for line in
                   (run / "actions.jsonl").read_text().splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as e:
        check("artifacts_readable", False, str(e))
        return out
    check("artifacts_readable", True)

    runtime_dir = run.resolve().parents[1]  # runs/<id> -> runtime/
    case_path = (runtime_dir / meta["case_path"]).resolve()
    sha = hashlib.sha256(case_path.read_bytes()).hexdigest()
    check("fixture_hash", sha == meta.get("case_sha256"),
          {"expected": meta.get("case_sha256"), "actual": sha})
    if sha != meta.get("case_sha256"):
        return out

    case = case_from_dict(json.loads(case_path.read_text()))
    campaign = Campaign(case)
    for a in actions:
        if a.get("cmd") == "observe" and a.get("ok"):
            try:
                y = campaign.observe(int(a["slot"]))
            except IllegalAction as e:
                check("replay_legality", False,
                      {"slot": a["slot"], "error": str(e)})
                return out
            if abs(y - float(a["rv"])) > RV_TOL:
                check("measurement_match", False,
                      {"slot": a["slot"], "logged": a["rv"], "replayed": y})
                return out
    check("replay_legality", True)
    check("measurement_match", True)
    check("state_matches_log", state["observed_slots"] == campaign.obs_idx,
          {"state": state["observed_slots"], "log": campaign.obs_idx})

    vfile = run / "verdict.json"
    if not vfile.exists():
        check("verdict_present", False)
        return out
    check("verdict_present", True)
    recorded = json.loads(vfile.read_text())
    fresh = verdict(case, campaign.obs_t, campaign.obs_y, meta["theta"])
    same = (recorded["resolved"] == fresh["resolved"]
            and recorded["pred"] == fresh["pred"]
            and recorded["n_obs"] == fresh["n_obs"]
            and recorded.get("observed_slots") == campaign.obs_idx
            and abs(recorded["max_support"] - fresh["max_support"]) < 1e-9)
    check("verdict_recomputes", same,
          {"recorded": {k: recorded.get(k) for k in
                        ("resolved", "pred", "n_obs", "max_support")},
           "fresh": {k: fresh[k] for k in
                     ("resolved", "pred", "n_obs", "max_support")}})
    out["ok"] = all(out["checks"].values())
    # Truth-side facts live ONLY here (evaluator-side), recomputed fresh —
    # never stored in the agent's workspace.
    out["fresh_verdict"] = fresh
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    result = replay(p.parse_args().run)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
