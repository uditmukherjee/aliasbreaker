"""Generate case fixtures to disk.

Usage:
  python src/make_cases.py dev    -> data/cases/dev/*.json (12 shakedown cases)
  python src/make_cases.py final  -> data/cases/final/*.json + manifest
                                     (charter §5 strata, fresh seeds >= 5000)

Final-set stratum membership is decided by PREDECLARED STRUCTURAL PREDICATES
computed from the world (candidate fits, truth, realized outcomes) — never
from any policy's performance. Charter §5.
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from aliasbreaker.world import make_case, case_to_dict
from aliasbreaker.fitting import fit_circular, predict_circular
from aliasbreaker.evaluator import resolvable, THETA_DEFAULT

DEV_KNOBS = [{"sigma": 2.0}, {"sigma": 3.0}, {"sigma": 4.0}, {"sigma": 5.0}]
ORACLE_CFG = {"n_random": 2000, "oracle_seed": 1234, "theta": THETA_DEFAULT}


def write_case(case, out_dir):
    """Serialize a case with its hidden oracle label + exact oracle config
    (charter §4: computed at generation, stored hidden)."""
    d = case_to_dict(case)
    d["hidden"]["oracle"] = {
        "resolvable": resolvable(case, theta=ORACLE_CFG["theta"],
                                 n_random=ORACLE_CFG["n_random"],
                                 oracle_seed=ORACLE_CFG["oracle_seed"]),
        **ORACLE_CFG,
    }
    path = out_dir / f"{case.case_id}.json"
    path.write_text(json.dumps(d, indent=1))
    print(f"wrote {path}  (candidates={len(case.candidates)}, "
          f"slots={len(case.slot_t)}, "
          f"resolvable={d['hidden']['oracle']['resolvable']})")


def gen_dev(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    cases, seed = [], 100
    while len(cases) < 12 and seed < 400:
        seed += 1
        case = make_case(seed, **DEV_KNOBS[len(cases) % len(DEV_KNOBS)])
        if case is not None:
            cases.append(case)
    for case in cases:
        write_case(case, out_dir)


# ---------------- Final-set strata (charter §5, predeclared) ----------------

FINAL_SEED_START = 5000
FINAL_KNOBS = [{"sigma": 2.0}, {"sigma": 3.0}, {"sigma": 4.0}, {"sigma": 5.0}]
QUOTAS = {"ordinary": 4, "tempting_early": 2, "scarce_window": 2,
          "misleading_obs": 2, "unresolvable": 2}


LIVE_SUPPORT = 0.10          # a candidate is "live" iff init support >= this
SCARCE_LAST_DAYS = 20.0      # scarce window: qualifying slots in last N days
SCARCE_SPAN_DAYS = 5.0       # ... and spanning at most this many days
SCARCE_MAX_SLOTS = 3


def _structure(case):
    """Structural features used ONLY for stratum predicates. May consult
    hidden truth and realized outcomes; never any policy's behavior."""
    from aliasbreaker.fitting import support_from_chi2, fit_basin
    fits = [fit_circular(case.init_t, case.init_y, case.sigma, P)
            for P in case.candidates]
    support0 = support_from_chi2([f["chi2"] for f in fits])
    curves = np.array([predict_circular(f, case.slot_t) for f in fits])
    n = len(fits)
    b = case.true_basin_index
    sep = {}
    for i in range(n):
        for j in range(i + 1, n):
            sep[(i, j)] = np.abs(curves[i] - curves[j]) / case.sigma
    return fits, support0, curves, sep, b


def _support_after_one_obs(case, k):
    """Arm-neutral: candidate supports after adding realized outcome k to the
    initial data (same basin-refit + support rule as the evaluator)."""
    from aliasbreaker.fitting import fit_basin, support_from_chi2
    t = np.concatenate([case.init_t, [case.slot_t[k]]])
    y = np.concatenate([case.init_y, [case.slot_y[k]]])
    fits = [fit_basin(t, y, case.sigma, P, case.freq_df)
            for P in case.candidates]
    return support_from_chi2([f["chi2"] for f in fits])


def classify_stratum(case, is_resolvable):
    """Stratum by predeclared structural rules (charter §5).

    Precedence when several predicates hold: unresolvable > misleading_obs >
    scarce_window > tempting_early > ordinary. Returns (stratum, flags) where
    flags records every predicate evaluation for evaluator-side audit.
    """
    flags = {"resolvable": bool(is_resolvable)}
    if not is_resolvable:
        return "unresolvable", flags
    if len(case.candidates) < 3 or case.true_basin_index < 0:
        return None, flags
    fits, support0, curves, sep, b = _structure(case)
    n = len(fits)
    n_slots = len(case.slot_t)
    live = [i for i in range(n) if support0[i] >= LIVE_SUPPORT]
    first_half = range(0, max(1, n_slots // 2))
    early = range(0, max(1, n_slots // 3))
    t_end = float(case.slot_t[-1])

    # misleading_obs: a LIVE wrong candidate OVERTAKES the truth in the
    # shared support rule after one early realized outcome is added.
    flags["misleading_obs"] = False
    for k in first_half:
        s1 = _support_after_one_obs(case, k)
        for i in live:
            if i != b and s1[i] > s1[b] and s1[i] >= 0.5:
                flags["misleading_obs"] = True
                flags["misleading_slot"] = int(k)
                break
        if flags["misleading_obs"]:
            break
    if flags["misleading_obs"]:
        return "misleading_obs", flags

    # scarce_window: for the best-fitting LIVE rival pair vs truth, all
    # discriminating slots (sep > 2 sigma) sit in the last SCARCE_LAST_DAYS
    # days, number <= SCARCE_MAX_SLOTS, and span <= SCARCE_SPAN_DAYS days.
    flags["scarce_window"] = False
    live_rivals = [i for i in live if i != b]
    if live_rivals:
        r = min(live_rivals, key=lambda i: fits[i]["chi2"])
        rp = (min(b, r), max(b, r))
        disc = np.flatnonzero(sep[rp] > 2.0)
        if 0 < len(disc) <= SCARCE_MAX_SLOTS:
            times = case.slot_t[disc]
            if (times.min() >= t_end - SCARCE_LAST_DAYS
                    and times.max() - times.min() <= SCARCE_SPAN_DAYS):
                flags["scarce_window"] = True
    if flags["scarce_window"]:
        return "scarce_window", flags

    # tempting_early: strongest early separation belongs to a pair of LIVE
    # wrong candidates while every truth-involving pair stays weak early.
    flags["tempting_early"] = False
    wrong_live_pairs = [p for p in sep
                        if b not in p and p[0] in live and p[1] in live]
    true_pairs = [p for p in sep if b in p]
    if wrong_live_pairs and true_pairs:
        e = list(early)
        best_wrong = max(float(sep[p][e].max()) for p in wrong_live_pairs)
        best_true = max(float(sep[p][e].max()) for p in true_pairs)
        if best_wrong > 2.5 and best_true < 1.5:
            flags["tempting_early"] = True
    if flags["tempting_early"]:
        return "tempting_early", flags

    return "ordinary", flags


def gen_final(out_dir, manifest_path):
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SystemExit(f"refusing to generate into non-empty {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    assert ORACLE_CFG["theta"] == THETA_DEFAULT  # single theta source
    filled = {k: [] for k in QUOTAS}
    # ordinary carries a one-case subquota per sigma (charter §5).
    ordinary_sigmas_needed = {2.0, 3.0, 4.0, 5.0}
    seed = FINAL_SEED_START - 1
    knob_i = 0
    n_scanned = n_valid = 0
    while any(len(filled[s]) < QUOTAS[s] for s in QUOTAS) and \
            seed < FINAL_SEED_START + 4000:
        seed += 1
        n_scanned += 1
        knob = FINAL_KNOBS[knob_i % len(FINAL_KNOBS)]
        knob_i += 1
        case = make_case(seed, require_truth_basin=False, **knob)
        if case is None or len(case.candidates) < 3:
            continue
        n_valid += 1
        is_res = resolvable(case, theta=ORACLE_CFG["theta"],
                            n_random=ORACLE_CFG["n_random"],
                            oracle_seed=ORACLE_CFG["oracle_seed"])
        stratum, flags = classify_stratum(case, is_res)
        if stratum is None or len(filled[stratum]) >= QUOTAS[stratum]:
            continue
        if stratum == "ordinary":
            if case.sigma not in ordinary_sigmas_needed:
                continue
            ordinary_sigmas_needed.discard(case.sigma)
        d = case_to_dict(case)
        d["hidden"]["oracle"] = {"resolvable": is_res, **ORACLE_CFG}
        # stratum lives ONLY here (evaluator-owned manifest) — never in the
        # fixture (diff-gate 2 finding 4).
        path = out_dir / f"{case.case_id}.json"
        path.write_text(json.dumps(d, indent=1))
        filled[stratum].append({
            "case_id": case.case_id, "seed": case.seed,
            "sigma": case.sigma, "stratum": stratum,
            "predicate_flags": {k: v for k, v in flags.items()},
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
        print(f"{case.case_id}: stratum={stratum} sigma={case.sigma} "
              f"cands={len(case.candidates)} resolvable={is_res}")
    if any(len(filled[s]) < QUOTAS[s] for s in QUOTAS):
        raise SystemExit(f"could not fill quotas within seed budget: "
                         f"{ {s: len(v) for s, v in filled.items()} }")
    import platform
    import subprocess as sp
    commit = sp.run(["git", "rev-parse", "HEAD"], capture_output=True,
                    text=True).stdout.strip()
    manifest = {
        "seed_range_scanned": [FINAL_SEED_START, seed],
        "n_seeds_scanned": n_scanned, "n_valid_cases_seen": n_valid,
        "quotas": QUOTAS,
        "ordinary_sigma_subquota": "one case per sigma in {2,3,4,5}",
        "theta": THETA_DEFAULT,
        "oracle": ORACLE_CFG,
        "predicate_thresholds": {
            "live_support": LIVE_SUPPORT,
            "scarce_last_days": SCARCE_LAST_DAYS,
            "scarce_span_days": SCARCE_SPAN_DAYS,
            "scarce_max_slots": SCARCE_MAX_SLOTS,
            "tempting_wrong_sep_gt": 2.5, "tempting_true_sep_lt": 1.5,
            "misleading_overtake_support_ge": 0.5,
        },
        "stratum_precedence":
            "unresolvable > misleading_obs > scarce_window > tempting_early "
            "> ordinary (higher-precedence overflow cases are discarded, "
            "never demoted)",
        "generator_commit": commit,
        "environment": {"python": platform.python_version(),
                        "numpy": np.__version__},
        "cases": [c for s in QUOTAS for c in filled[s]],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"manifest -> {manifest_path}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "dev"
    root = Path(__file__).resolve().parents[1]
    if which == "dev":
        gen_dev(root / "data" / "cases" / "dev")
    elif which == "final":
        gen_final(root / "data" / "cases" / "final",
                  root / "evaluation" / "final-manifest.json")
    else:
        raise SystemExit(f"unknown set: {which}")
