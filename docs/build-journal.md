# Build Journal — append-only

Format: date · event · evidence · decision. Raw material for the required
Improvement Changelog.

- 2026-08-29 · Direction chosen via 3-way pondering (human + Claude + Codex,
  two blind ideation rounds; see brainstorm/). Blind convergence on "budgeted
  active-science agent in a synthetic world"; human picked AliasBreaker
  (adaptive RV follow-up scheduling). LLM-at-runtime three-arm design approved.
- 2026-08-29 · Spec v1 written (docs/aliasbreaker-spec.md); Codex plan-gate
  review launched.
- 2026-08-29 · Kill test iteration 1 (12 random cases, sigma 2-5, weather
  .25/.4, 8 init obs): world + candidate construction works (12/12 seeds),
  two-arm eval 1.2s. Batch 9/12, scripted-adaptive 10/12, adaptive-only wins 2
  (bar: 3). Anomaly: case-006 adaptive w_truth=0.09 — suspected coarse-T0-grid
  chi2 plateau penalizing candidates unevenly as data accumulate.
- 2026-08-29 · Fitter refinement added (two-stage grid: coarse then local
  T0/e refine). Kill test iteration 2 with harder knobs (6 init obs, sigma
  3-6, weather .35/.5, delta-chi2 keep 12): batch 9/12, adaptive 10/12,
  adaptive-only 1, batch-only 0. KEY OBSERVATION: accuracy headroom over a
  strong batch baseline is small on randomly generated cases, but EFFICIENCY
  headroom is large — adaptive reaches equal-or-better accuracy using a median
  of ~2 observations vs batch's fixed 6 (batch cannot stop early: no feedback).
  Hard cases (002, 006) unresolved by both; case-006 adaptive is actively
  misled (w_truth=0.27) — a genuine failure mode worth studying for the LLM
  arm and the hot take.
- 2026-08-29 · Pending decision: revise primary metric toward resolution
  efficiency (observations spent to reach a confident correct resolution),
  keeping accuracy-at-budget as co-headline; construct hard-case families by
  predeclared rules (not post-hoc selection) for accuracy headroom. Awaiting
  Codex plan-gate verdict before freezing.
