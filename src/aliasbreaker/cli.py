"""World CLI — the ONLY interface the AliasBreaker runtime agent may use.

Terminal tools with JSON I/O; campaign state persists in a run directory so
each invocation is a fresh process. Legality (chronology, budget, no revisits)
is enforced by the world regardless of what the caller asks. Hidden truth is
never printed; diagnostics are auditable numbers, never recommendations.

Commands (run from repo root, src on PYTHONPATH or via `python -m`):
  python -m aliasbreaker.cli start  --case <fixture.json> --run <run_dir>
  python -m aliasbreaker.cli state  --run <run_dir>
  python -m aliasbreaker.cli diagnostics --run <run_dir>
  python -m aliasbreaker.cli observe --run <run_dir> --slot <idx> [--why <text>]
  python -m aliasbreaker.cli finalize --run <run_dir> [--why <text>]

Exit codes: 0 = ok, 2 = illegal action / protocol error (JSON error printed).
"""

import argparse
import json
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


def _load_run(run_dir):
    run = Path(run_dir)
    meta = json.loads((run / "meta.json").read_text())
    state = json.loads((run / "state.json").read_text())
    case = case_from_dict(json.loads(Path(meta["case_path"]).read_text()))
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


def _fits_support(case, campaign):
    t, y = campaign.data()
    fits = [fit_basin(t, y, case.sigma, P, case.freq_df)
            for P in case.candidates]
    support = support_from_chi2([f["chi2"] for f in fits])
    return fits, support


def _public_state(case, campaign, state):
    fits, support = _fits_support(case, campaign)
    return {
        "case_id": case.case_id,
        "sigma_m_per_s": case.sigma,
        "budget_left": campaign.budget_left(),
        "finalized": state["finalized"],
        "initial_observations": [
            {"t": round(float(t), 3), "rv": round(float(y), 2)}
            for t, y in zip(case.init_t, case.init_y)],
        "campaign_observations": [
            {"slot": i, "t": round(t, 3), "rv": round(y, 2)}
            for i, t, y in zip(campaign.obs_idx, campaign.obs_t,
                               campaign.obs_y)],
        "candidates": [
            {"index": i, "period_days": round(f["P"], 4),
             "K_m_per_s": round(f["K"], 2), "chi2": round(f["chi2"], 2),
             "support": round(float(s), 4)}
            for i, (f, s) in enumerate(zip(fits, support))],
        "remaining_slots": [
            {"slot": i, "t": round(t, 3)}
            for i, t in campaign.remaining_slots()],
        "notes": ("support is candidate-set-relative (NOT a calibrated "
                  "probability); observing slot j makes all earlier slots "
                  "unreachable"),
    }


def cmd_start(args):
    run = Path(args.run)
    if (run / "meta.json").exists():
        _fail(f"run directory {run} already initialized")
    run.mkdir(parents=True, exist_ok=True)
    case_path = Path(args.case)
    case = case_from_dict(json.loads(case_path.read_text()))
    meta = {"case_path": str(case_path.resolve()), "case_id": case.case_id,
            "theta": args.theta, "created": round(time.time(), 3)}
    (run / "meta.json").write_text(json.dumps(meta, indent=2))
    state = {"observed_slots": [], "finalized": False}
    _save_state(run, state)
    campaign = Campaign(case)
    _log(run, {"cmd": "start", "case_id": case.case_id})
    print(json.dumps(_public_state(case, campaign, state), indent=1))


def cmd_state(args):
    run, meta, state, case, campaign = _load_run(args.run)
    _log(run, {"cmd": "state"})
    print(json.dumps(_public_state(case, campaign, state), indent=1))


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
                    "support_product": round(sp, 4),
                    "best_future_slots": [
                        {"slot": f_idx[k], "t": round(float(f_t[k]), 3),
                         "separation_sigma": round(float(sep[k]), 2)}
                        for k in order],
                    "n_future_slots_sep_gt2": int(np.sum(sep > 2.0)),
                })
    _log(run, {"cmd": "diagnostics"})
    print(json.dumps(out, indent=1))


def cmd_observe(args):
    run, meta, state, case, campaign = _load_run(args.run)
    if state["finalized"]:
        _fail("run is finalized")
    try:
        y = campaign.observe(int(args.slot))
    except IllegalAction as e:
        _log(run, {"cmd": "observe", "slot": int(args.slot), "ok": False,
                   "error": str(e), "why": args.why})
        _fail(f"illegal action: {e}")
    state["observed_slots"].append(int(args.slot))
    _save_state(run, state)
    fits, support = _fits_support(case, campaign)
    _log(run, {"cmd": "observe", "slot": int(args.slot), "ok": True,
               "rv": round(y, 3), "why": args.why})
    print(json.dumps({
        "slot": int(args.slot),
        "t": round(float(case.slot_t[int(args.slot)]), 3),
        "rv": round(y, 2),
        "budget_left": campaign.budget_left(),
        "support": [round(float(s), 4) for s in support],
    }, indent=1))


def cmd_finalize(args):
    run, meta, state, case, campaign = _load_run(args.run)
    if state["finalized"]:
        _fail("run is already finalized")
    theta = meta.get("theta") or THETA_DEFAULT
    v = verdict(case, campaign.obs_t, campaign.obs_y, theta)
    state["finalized"] = True
    _save_state(run, state)
    (run / "verdict.json").write_text(json.dumps(
        {**v, "theta": theta, "observed_slots": campaign.obs_idx,
         "stop_reason": args.why}, indent=2))
    _log(run, {"cmd": "finalize", "why": args.why,
               "resolved": v["resolved"]})
    public = {
        "resolved": v["resolved"],
        "abstained": v["abstained"],
        "selected_candidate_index": v["pred"] if v["resolved"] else None,
        "max_support": v["max_support"],
        "observations_used": v["n_obs"],
        "theta": theta,
    }
    print(json.dumps(public, indent=1))


def main(argv=None):
    p = argparse.ArgumentParser(prog="aliasbreaker.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--case", required=True)
    s.add_argument("--run", required=True)
    s.add_argument("--theta", type=float, default=None)
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
