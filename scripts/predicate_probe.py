"""Measure the joint distribution of stratum-predicate quantities across
~200 valid cases so relaxed thresholds can be chosen by EXISTENCE (arm-
independent), not guesswork."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(r"D:\Apps\micro1-frontier-hackathon")
sys.path.insert(0, str(ROOT / "src"))

from aliasbreaker.world import make_case
from aliasbreaker.fitting import fit_circular, predict_circular, support_from_chi2

KNOBS = [{"sigma": 2.0}, {"sigma": 3.0}, {"sigma": 4.0}, {"sigma": 5.0}]

rows = []
seed = 20000
while len(rows) < 200 and seed < 22000:
    seed += 1
    case = make_case(seed, require_truth_basin=True,
                     **KNOBS[len(rows) % len(KNOBS)])
    if case is None or len(case.candidates) < 3:
        continue
    fits = [fit_circular(case.init_t, case.init_y, case.sigma, P)
            for P in case.candidates]
    support = support_from_chi2([f["chi2"] for f in fits])
    curves = np.array([predict_circular(f, case.slot_t) for f in fits])
    b = case.true_basin_index
    n = len(fits)
    n_slots = len(case.slot_t)
    early = slice(0, max(1, n_slots // 3))
    t_end = float(case.slot_t[-1])

    sep = {}
    for i in range(n):
        for j in range(i + 1, n):
            sep[(i, j)] = np.abs(curves[i] - curves[j]) / case.sigma

    # tempting-early quantities under different liveness demands
    true_pairs = [p for p in sep if b in p]
    best_true_early = max(float(sep[p][early].max()) for p in true_pairs)
    def wrong_best(min_a, min_b):
        vals = [float(sep[(i, j)][early].max()) for (i, j) in sep
                if b not in (i, j)
                and max(support[i], support[j]) >= min_a
                and min(support[i], support[j]) >= min_b]
        return max(vals) if vals else 0.0
    # scarce-window quantities for best live rival
    live_rivals = [i for i in range(n) if i != b and support[i] >= 0.10]
    scarce = None
    if live_rivals:
        r = min(live_rivals, key=lambda i: fits[i]["chi2"])
        rp = (min(b, r), max(b, r))
        disc = np.flatnonzero(sep[rp] > 2.0)
        if len(disc):
            times = case.slot_t[disc]
            scarce = {"n": int(len(disc)),
                      "from_end": float(t_end - times.min()),
                      "span": float(times.max() - times.min())}
    rows.append({
        "best_true_early": best_true_early,
        "wrong_strict": wrong_best(0.10, 0.10),
        "wrong_one_live": wrong_best(0.10, 0.02),
        "scarce": scarce,
    })

n = len(rows)
print(f"{n} valid cases (seeds scanned to {seed})")
for wl, tl in [(2.5, 1.5), (2.0, 1.5), (2.0, 2.0), (2.5, 2.0)]:
    strict = sum(1 for r in rows
                 if r["wrong_strict"] > wl and r["best_true_early"] < tl)
    onelive = sum(1 for r in rows
                  if r["wrong_one_live"] > wl and r["best_true_early"] < tl)
    print(f"tempting wrong>{wl} true<{tl}: strict-live {strict}/{n}, "
          f"one-live {onelive}/{n}")
scarce_rows = [r["scarce"] for r in rows if r["scarce"]]
print(f"\nscarce candidates (best-rival disc slots): {len(scarce_rows)}/{n}")
for max_n, last, span in [(3, 20, 5), (5, 25, 10), (8, 30, 15),
                          (6, 30, 30), (10, 40, 40)]:
    k = sum(1 for s in scarce_rows
            if s["n"] <= max_n and s["from_end"] <= last and s["span"] <= span)
    print(f"scarce n<={max_n} last{last}d span<={span}d: {k}/{n}")
counts = [s["n"] for s in scarce_rows]
print("disc-slot count percentiles:",
      np.percentile(counts, [5, 25, 50, 75]).round(1).tolist())
print("from_end percentiles:",
      np.percentile([s["from_end"] for s in scarce_rows],
                    [5, 25, 50]).round(1).tolist())
