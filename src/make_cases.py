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


def _structure(case):
    """Structural features used ONLY for stratum predicates."""
    fits = [fit_circular(case.init_t, case.init_y, case.sigma, P)
            for P in case.candidates]
    curves = np.array([predict_circular(f, case.slot_t) for f in fits])
    n = len(fits)
    b = case.true_basin_index
    sep = {}
    for i in range(n):
        for j in range(i + 1, n):
            sep[(i, j)] = np.abs(curves[i] - curves[j]) / case.sigma
    n_slots = len(case.slot_t)
    early = slice(0, max(1, n_slots // 3))
    first_half = slice(0, max(1, n_slots // 2))
    late_start = (2 * n_slots) // 3
    return fits, curves, sep, b, early, first_half, late_start, n_slots


def classify_stratum(case, is_resolvable):
    """Return the stratum name for a case, by predeclared structural rules.

    Precedence when several predicates hold: unresolvable > misleading_obs >
    scarce_window > tempting_early > ordinary (deterministic, declared here).
    """
    if not is_resolvable:
        return "unresolvable"
    if len(case.candidates) < 3 or case.true_basin_index < 0:
        return None
    fits, curves, sep, b, early, first_half, late_start, n_slots = \
        _structure(case)
    n = len(fits)
    true_pairs = [p for p in sep if b in p]
    wrong_pairs = [p for p in sep if b not in p]

    # misleading_obs: an early realized outcome fits some wrong candidate
    # well (<1 sigma) while missing the truth badly (>2 sigma).
    truth_curve = curves[b]
    for k in range(*first_half.indices(n_slots)):
        y = case.slot_y[k]
        if abs(y - truth_curve[k]) > 2.0 * case.sigma:
            for i in range(n):
                if i != b and abs(y - curves[i][k]) < 1.0 * case.sigma:
                    return "misleading_obs"

    # scarce_window: for the best-fitting rival, discriminating slots
    # (sep > 2 sigma) number <= 3 and all sit in the final third.
    rivals = sorted((i for i in range(n) if i != b),
                    key=lambda i: fits[i]["chi2"])
    rp = (min(b, rivals[0]), max(b, rivals[0]))
    disc = np.flatnonzero(sep[rp] > 2.0)
    if 0 < len(disc) <= 3 and disc.min() >= late_start:
        return "scarce_window"

    # tempting_early: the strongest early separation belongs to a wrong pair
    # while every true-pair separation stays weak early.
    if wrong_pairs and true_pairs:
        best_wrong_early = max(float(sep[p][early].max()) for p in wrong_pairs)
        best_true_early = max(float(sep[p][early].max()) for p in true_pairs)
        if best_wrong_early > 2.5 and best_true_early < 1.5:
            return "tempting_early"

    return "ordinary"


def gen_final(out_dir, manifest_path):
    out_dir.mkdir(parents=True, exist_ok=True)
    filled = {k: [] for k in QUOTAS}
    seed = FINAL_SEED_START
    knob_i = 0
    while any(len(filled[s]) < QUOTAS[s] for s in QUOTAS) and \
            seed < FINAL_SEED_START + 4000:
        seed += 1
        knob = FINAL_KNOBS[knob_i % len(FINAL_KNOBS)]
        knob_i += 1
        case = make_case(seed, require_truth_basin=False, **knob)
        if case is None or len(case.candidates) < 3:
            continue
        is_res = resolvable(case, theta=ORACLE_CFG["theta"],
                            n_random=ORACLE_CFG["n_random"],
                            oracle_seed=ORACLE_CFG["oracle_seed"])
        stratum = classify_stratum(case, is_res)
        if stratum is None or len(filled[stratum]) >= QUOTAS[stratum]:
            continue
        d = case_to_dict(case)
        d["hidden"]["oracle"] = {"resolvable": is_res, **ORACLE_CFG}
        d["stratum"] = stratum
        path = out_dir / f"{case.case_id}.json"
        path.write_text(json.dumps(d, indent=1))
        filled[stratum].append({
            "case_id": case.case_id, "seed": case.seed,
            "sigma": case.sigma, "stratum": stratum,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
        print(f"{case.case_id}: stratum={stratum} sigma={case.sigma} "
              f"cands={len(case.candidates)} resolvable={is_res}")
    if any(len(filled[s]) < QUOTAS[s] for s in QUOTAS):
        raise SystemExit(f"could not fill quotas within seed budget: "
                         f"{ {s: len(v) for s, v in filled.items()} }")
    manifest = {
        "generated_from_seed": FINAL_SEED_START,
        "quotas": QUOTAS, "theta": THETA_DEFAULT,
        "oracle": ORACLE_CFG,
        "stratum_precedence":
            "unresolvable > misleading_obs > scarce_window > tempting_early "
            "> ordinary",
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
