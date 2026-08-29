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

FINAL_SEED_START = 30000
FINAL_KNOBS = [{"sigma": 2.0}, {"sigma": 3.0}, {"sigma": 4.0}, {"sigma": 5.0}]
# Amended pre-freeze (probe of 200 cases, committed evidence): the originally
# hypothesized tempting_early stratum is structurally absent in this world
# (0/200 at every threshold) and scarce_window never occurs naturally (median
# rival pair has ~25 discriminating slots spread across the horizon). ->
# tempting_early replaced by "crowded" (hardest natural axis); scarce_window
# CONSTRUCTED by masking early discriminating slots (availability is
# exogenous; masking uses truth, which stratum construction may).
QUOTAS = {"ordinary": 4, "crowded": 2, "misleading_obs": 2,
          "unresolvable": 2}
N_SCARCE_CONSTRUCTED = 2
SCARCE_KEEP_LAST_DAYS = 25.0
SCARCE_MAX_DISC = 6


LIVE_SUPPORT = 0.10          # a candidate is "live" iff init support >= this


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

    # crowded: maximum candidate load at high noise — the hardest NATURAL
    # difficulty axis (replaces the structurally-absent tempting_early).
    flags["crowded"] = (len(case.candidates) >= 6 and case.sigma >= 4.0)
    if flags["crowded"]:
        return "crowded", flags

    return "ordinary", flags


def construct_scarce_case(seed, sigma):
    """Constructed scarce-window case (reservation test): take a natural
    resolvable case and REMOVE every slot where the best live rival pair
    separates > 2 sigma, except those in the final SCARCE_KEEP_LAST_DAYS
    days. Observatory availability is exogenous, so a schedule missing those
    nights is physically legitimate; stratum construction may use hidden
    truth (charter §5), never policy behavior. The masked case must still
    pass the resolvability oracle."""
    from dataclasses import replace as dc_replace
    case = make_case(seed, sigma=sigma)
    if case is None or len(case.candidates) < 3:
        return None, None
    fits, support0, curves, sep, b = _structure(case)
    live_rivals = [i for i in range(len(fits))
                   if i != b and support0[i] >= LIVE_SUPPORT]
    if not live_rivals:
        return None, None
    r = min(live_rivals, key=lambda i: fits[i]["chi2"])
    rp = (min(b, r), max(b, r))
    disc = sep[rp] > 2.0
    t_end = float(case.slot_t[-1])
    keep = ~disc | (case.slot_t >= t_end - SCARCE_KEEP_LAST_DAYS)
    kept_disc = int(np.sum(disc & keep))
    if not (1 <= kept_disc <= SCARCE_MAX_DISC) or int(np.sum(keep)) < 12:
        return None, None
    masked = dc_replace(
        case, case_id=f"case-{seed}m",
        slot_t=case.slot_t[keep], slot_y=case.slot_y[keep])
    is_res = resolvable(masked, theta=ORACLE_CFG["theta"],
                        n_random=ORACLE_CFG["n_random"],
                        oracle_seed=ORACLE_CFG["oracle_seed"])
    if not is_res:
        return None, None
    flags = {"resolvable": True, "constructed_scarce": True,
             "masked_slots": int(np.sum(~keep)), "kept_disc": kept_disc,
             "rival_pair": list(rp)}
    return masked, flags


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

    # Constructed scarce-window cases (reservation test), fresh seed range.
    filled["scarce_window"] = []
    s_seed = FINAL_SEED_START + 50000
    s_sigmas = [3.0, 4.0]
    while len(filled["scarce_window"]) < N_SCARCE_CONSTRUCTED and \
            s_seed < FINAL_SEED_START + 52000:
        s_seed += 1
        sigma = s_sigmas[len(filled["scarce_window"]) % len(s_sigmas)]
        masked, flags = construct_scarce_case(s_seed, sigma)
        if masked is None:
            continue
        d = case_to_dict(masked)
        d["hidden"]["oracle"] = {"resolvable": True, **ORACLE_CFG}
        path = out_dir / f"{masked.case_id}.json"
        path.write_text(json.dumps(d, indent=1))
        filled["scarce_window"].append({
            "case_id": masked.case_id, "seed": masked.seed,
            "sigma": masked.sigma, "stratum": "scarce_window",
            "constructed": True, "predicate_flags": flags,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
        print(f"{masked.case_id}: stratum=scarce_window (constructed) "
              f"sigma={sigma} masked={flags['masked_slots']} "
              f"kept_disc={flags['kept_disc']}")
    if len(filled["scarce_window"]) < N_SCARCE_CONSTRUCTED:
        raise SystemExit("could not construct scarce-window cases")
    import platform
    import subprocess as sp
    commit = sp.run(["git", "rev-parse", "HEAD"], capture_output=True,
                    text=True).stdout.strip()
    manifest = {
        "seed_range_scanned": [FINAL_SEED_START, seed],
        "n_seeds_scanned": n_scanned, "n_valid_cases_seen": n_valid,
        "quotas": {**QUOTAS, "scarce_window_constructed": N_SCARCE_CONSTRUCTED},
        "ordinary_sigma_subquota": "one case per sigma in {2,3,4,5}",
        "theta": THETA_DEFAULT,
        "oracle": ORACLE_CFG,
        "predicate_thresholds": {
            "live_support": LIVE_SUPPORT,
            "misleading_overtake_support_ge": 0.5,
            "crowded_min_candidates": 6, "crowded_min_sigma": 4.0,
            "scarce_keep_last_days": SCARCE_KEEP_LAST_DAYS,
            "scarce_max_disc_slots": SCARCE_MAX_DISC,
        },
        "stratum_precedence":
            "unresolvable > misleading_obs > crowded > ordinary (natural "
            "scan; overflow discarded, never demoted); scarce_window is "
            "CONSTRUCTED from a separate fresh seed range by availability "
            "masking (probe evidence: the stratum is structurally absent in "
            "natural draws)",
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
