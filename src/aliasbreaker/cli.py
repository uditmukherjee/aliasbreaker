"""World CLI — the ONLY interface the AliasBreaker runtime agent may use.

Terminal tools with JSON I/O; campaign state persists in a run directory so
each invocation is a fresh process. Legality (chronology, budget, no revisits)
is enforced by the world regardless of what the caller asks. Hidden truth is
never printed; diagnostics are auditable numbers, never recommendations.

Integrity properties (diff-gate 1 rework):
- theta is frozen: taken from the committed calibration (THETA_DEFAULT) at
  `start`, pinned into meta.json, no runtime override exists.
- Path containment: --run must resolve under ./runs, --case under the repo's
  data/cases tree. The fixture's SHA-256 is pinned in meta.json at start and
  re-verified on every later command.
- Ordering: actions are logged before state is saved; verdict.json is written
  before the finalized flag flips (a crash leaves a recoverable, not a
  bricked, run).
- --why is mandatory and non-empty on observe/finalize.
- All protocol errors print JSON and exit 2 (argparse errors included).

Exit codes: 0 = ok, 2 = illegal action / protocol error (JSON error printed).
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

from .world import Campaign, IllegalAction, case_from_dict
from .fitting import fit_basin, predict_circular, support_from_chi2
from .evaluator import verdict, THETA_DEFAULT

SEP_CAP = 4.0  # separation cap in sigma units (matches planner B_CAP)


def _fail(msg):
    print(json.dumps({"error": msg}))
    sys.exit(2)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _contained(child, parent):
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _run_dir(arg):
    run = Path(arg)
    if not _contained(run, Path.cwd() / "runs"):
        _fail("run directory must be under ./runs")
    return run


def _load_run(run_arg):
    run = _run_dir(run_arg)
    if not (run / "meta.json").exists():
        _fail(f"run {run} not initialized (no meta.json)")
    meta = json.loads((run / "meta.json").read_text())
    state = json.loads((run / "state.json").read_text())
    case_path = Path.cwd() / meta["case_path"]
    if _sha256(case_path) != meta["case_sha256"]:
        _fail("fixture hash mismatch: case file changed since start")
    case = case_from_dict(json.loads(case_path.read_text()))
    campaign = Campaign(case)
    for idx in state["observed_slots"]:
        campaign.observe(idx)
    return run, meta, state, case, campaign


def _save_state(run, state):
    (run / "state.json").write_text(json.dumps(state, indent=2))


def _log(run, entry):
    entry = {"ts": round(time.time(), 3), **entry}
    with open(run / "actions.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _require_why(args):
    if not (args.why or "").strip():
        _fail("--why is required: give a one-sentence rationale")


def _fits_support(case, campaign):
    t, y = campaign.data()
    fits = [fit_basin(t, y, case.sigma, P, case.freq_df)
            for P in case.candidates]
    support = support_from_chi2([f["chi2"] for f in fits])
    return fits, support


def _public_state(case, campaign, state, meta):
    fits, support = _fits_support(case, campaign)
    return {
        "case_id": case.case_id,
        "sigma_m_per_s": case.sigma,
        "theta": meta["theta"],
        "budget_left": campaign.budget_left(),
        "finalized": state["finalized"],
        "initial_observations": [
            {"t": round(float(t), 4), "rv": round(float(y), 3)}
            for t, y in zip(case.init_t, case.init_y)],
        "campaign_observations": [
            {"slot": i, "t": round(t, 4), "rv": round(y, 3)}
            for i, t, y in zip(campaign.obs_idx, campaign.obs_t,
                               campaign.obs_y)],
        "candidates": [
            {"index": i, "period_days": round(f["P"], 5),
             "K_m_per_s": round(f["K"], 3), "chi2": round(f["chi2"], 3),
             "support": round(float(s), 6)}
            for i, (f, s) in enumerate(zip(fits, support))],
        "remaining_slots": [
            {"slot": i, "t": round(t, 4)}
            for i, t in campaign.remaining_slots()],
        "notes": ("support is candidate-set-relative (NOT a calibrated "
                  "probability); observing slot j makes all earlier slots "
                  "unreachable"),
    }


def cmd_start(args):
    run = _run_dir(args.run)
    if (run / "meta.json").exists():
        _fail(f"run directory {run} already initialized")
    case_path = Path(args.case)
    repo_cases = Path.cwd().parent / "data" / "cases"
    if not _contained(case_path, repo_cases):
        _fail("case fixture must live under the repository data/cases tree")
    if not case_path.exists():
        _fail(f"case fixture not found: {case_path}")
    run.mkdir(parents=True, exist_ok=True)
    case = case_from_dict(json.loads(case_path.read_text()))
    meta = {
        "case_path": os.path.relpath(case_path.resolve(),
                                     Path.cwd()).replace("\\", "/"),
        "case_id": case.case_id,
        "case_sha256": _sha256(case_path),
        "theta": THETA_DEFAULT,
        "created": round(time.time(), 3),
    }
    (run / "meta.json").write_text(json.dumps(meta, indent=2))
    state = {"observed_slots": [], "finalized": False}
    _log(run, {"cmd": "start", "case_id": case.case_id,
               "case_sha256": meta["case_sha256"], "theta": THETA_DEFAULT})
    _save_state(run, state)
    campaign = Campaign(case)
    print(json.dumps(_public_state(case, campaign, state, meta), indent=1))


def cmd_state(args):
    run, meta, state, case, campaign = _load_run(args.run)
    _log(run, {"cmd": "state"})
    print(json.dumps(_public_state(case, campaign, state, meta), indent=1))


def cmd_diagnostics(args):
    run, meta, state, case, campaign = _load_run(args.run)
    if state["finalized"]:
        _fail("run is finalized")
    fits, support = _fits_support(case, campaign)
    future = campaign.remaining_slots()
    out = {"pairs": [], "notes": ("separations in sigma units, capped at "
                                  f"{SEP_CAP}; diagnostics only — no "
                                  "recommendation implied")}
    if future:
        f_idx = [i for i, _ in future]
        f_t = np.array([t for _, t in future])
        curves = [predict_circular(f, f_t) for f in fits]
        n = len(fits)
        for i in range(n):
            for j in range(i + 1, n):
                sp = float(support[i] * support[j])
                if sp < 1e-4:
                    continue
                sep = np.clip(np.abs(curves[i] - curves[j]) / case.sigma,
                              0.0, SEP_CAP)
                order = np.argsort(-sep)[:3]
                out["pairs"].append({
                    "pair": [i, j],
                    "support_product": round(sp, 6),
                    "best_future_slots": [
                        {"slot": f_idx[k], "t": round(float(f_t[k]), 4),
                         "separation_sigma": round(float(sep[k]), 2)}
                        for k in order],
                    "n_future_slots_sep_gt2": int(np.sum(sep > 2.0)),
                })
    _log(run, {"cmd": "diagnostics"})
    print(json.dumps(out, indent=1))


def cmd_observe(args):
    _require_why(args)
    run, meta, state, case, campaign = _load_run(args.run)
    if state["finalized"]:
        _fail("run is finalized")
    try:
        y = campaign.observe(int(args.slot))
    except IllegalAction as e:
        _log(run, {"cmd": "observe", "slot": int(args.slot), "ok": False,
                   "error": str(e), "why": args.why})
        _fail(f"illegal action: {e}")
    _log(run, {"cmd": "observe", "slot": int(args.slot), "ok": True,
               "rv": round(y, 6), "why": args.why})
    state["observed_slots"].append(int(args.slot))
    _save_state(run, state)
    fits, support = _fits_support(case, campaign)
    print(json.dumps({
        "slot": int(args.slot),
        "t": round(float(case.slot_t[int(args.slot)]), 4),
        "rv": round(y, 3),
        "budget_left": campaign.budget_left(),
        "support": [round(float(s), 6) for s in support],
    }, indent=1))


def cmd_finalize(args):
    _require_why(args)
    run, meta, state, case, campaign = _load_run(args.run)
    if state["finalized"]:
        _fail("run is already finalized")
    theta = meta["theta"]  # pinned at start; never floats with code changes
    v = verdict(case, campaign.obs_t, campaign.obs_y, theta)
    # PUBLIC fields only — truth-side facts (correct, truth_support, ...)
    # are never written into the agent's workspace; the evaluator recomputes
    # them from the case + observations (mock-judge critical finding 2).
    public_v = {
        "resolved": v["resolved"], "abstained": v["abstained"],
        "pred": v["pred"], "max_support": v["max_support"],
        "chi2s": v["chi2s"], "n_obs": v["n_obs"], "theta": theta,
        "observed_slots": campaign.obs_idx, "stop_reason": args.why,
    }
    (run / "verdict.json").write_text(json.dumps(public_v, indent=2))
    _log(run, {"cmd": "finalize", "why": args.why,
               "resolved": v["resolved"]})
    state["finalized"] = True
    _save_state(run, state)
    print(json.dumps({
        "resolved": v["resolved"],
        "abstained": v["abstained"],
        "selected_candidate_index": v["pred"] if v["resolved"] else None,
        "max_support": round(v["max_support"], 6),
        "observations_used": v["n_obs"],
        "theta": theta,
    }, indent=1))


class _JsonArgParser(argparse.ArgumentParser):
    def error(self, message):
        _fail(f"protocol error: {message}")


def main(argv=None):
    p = _JsonArgParser(prog="aliasbreaker.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--case", required=True)
    s.add_argument("--run", required=True)
    for name in ("state", "diagnostics"):
        sp = sub.add_parser(name)
        sp.add_argument("--run", required=True)
    o = sub.add_parser("observe")
    o.add_argument("--run", required=True)
    o.add_argument("--slot", required=True, type=int)
    o.add_argument("--why", default="")
    f = sub.add_parser("finalize")
    f.add_argument("--run", required=True)
    f.add_argument("--why", default="")
    args = p.parse_args(argv)
    {"start": cmd_start, "state": cmd_state, "diagnostics": cmd_diagnostics,
     "observe": cmd_observe, "finalize": cmd_finalize}[args.cmd](args)


if __name__ == "__main__":
    main()
