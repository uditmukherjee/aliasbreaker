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
- 2026-08-29 · Codex plan-gate on spec v1: NEEDS-REWORK, 32 findings (8
  Critical). All accepted or modified-accepted; triage in
  brainstorm/spec-review-triage.md. Headline fixes: dev/final eval separation
  with freeze protocol; evaluator-owned support metric + theta calibration
  (LLM never supplies confidence); resolvability oracle; chronological state
  machine; circular-orbit v1; truth-blind periodogram candidates;
  fixture-stored outcomes; audit-replay framing; final 10-12h reserved for ops.
- 2026-08-29 · REMOVED EXPERIMENT (documented): eccentric-orbit fitting
  (grid+linear LS over e, T0). Built and used in kill-test iterations 1-2;
  removed per gate findings F3/F4 — ~5 effective params from 6-8 initial obs
  overfits, and the coarse-T0-grid chi2 plateau caused the case-006 anomaly
  (adaptive truth-weight 0.09). Evidence: evaluation/killtest-results.json at
  commit ffd8e19; implementation preserved in git history at that commit.
- 2026-08-29 · v2 core rebuilt to charter: circular world, Campaign state
  machine (chronology/budget/no-revisit enforced by tests), truth-blind
  periodogram candidates, stored potential outcomes, shared evaluator,
  resolvability oracle, three non-LLM arms.
- 2026-08-29 · Feasibility run 1 exposed a REAL BUG predicted by gate finding
  F5: candidates frozen at initial periodogram grid peaks accumulate phase
  error over the 60-night horizon; even the true candidate stops fitting its
  own data -> false resolutions everywhere (adaptive 10/12 false-res).
  Fix: basin-refit (candidate identity = disjoint frequency basin, period
  refined within basin at every refit). Feasibility run 2: batch 8/12 correct
  0 false-res; even-spacing 6/12 (1 false-res); scripted-adaptive 7/12
  (1 false-res) using 2-6 obs vs batch's fixed 6. All integrity checks pass;
  oracle 12/12 resolvable; runtime sub-second. theta=0.9 placeholder shows
  ~1 false-res per adaptive arm -> calibration will likely select a stricter
  theta. Scripted-adaptive's stop-on-first-resolve shows a confirmation
  weakness (case-110 false-res at 2 obs) — a concrete headroom hypothesis for
  the LLM arm.
