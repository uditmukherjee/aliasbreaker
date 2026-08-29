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
- 2026-08-29 · ARCHITECTURE DECISION (human + Claude): the runtime agent is a
  Claude Code project itself — a /aliasbreaker skill drives a locked-down
  session (allowlist = World CLI only) headlessly via `claude -p`, model
  pinned to Sonnet 5; trace auditor verifies no out-of-protocol tool call.
  Rationale: subscription-based (no API key), richest trajectory format,
  meta-story (runtime built in the harness that built it). Disclosed
  tradeoffs: judges need Claude Code (runs on any ANTHROPIC_API_KEY) or the
  keyless audit-replay path; sampling params not controllable in-harness.
  Evidence-ledger rule added: every phase closes with artifact + journal row
  + commit.
- 2026-08-29 · A1 World CLI shipped (src/aliasbreaker/cli.py): start/state/
  diagnostics/observe/finalize with per-run state dir + append-only action
  log; legality enforced world-side (smoke test: chronology violation
  correctly rejected with exit 2). Case fixtures serialized to
  data/cases/dev/ (12 cases, same seeds as feasibility).
- 2026-08-29 · A2 theta calibration (charter §3): 120 fresh cases incl. 12
  natural basin-absent; grid {0.85,...,0.997}; smallest theta with worst-arm
  FRR <= 5% is 0.997 (exactly 5.0%). FRR falls slowly with theta because
  false resolutions are dominated by decisive wrong fits (incl. basin-absent
  cases), not marginal crossings. Power cost disclosed: batch correct-rate
  0.69 -> 0.47 across the grid. THETA_DEFAULT=0.997 committed; table in
  evaluation/theta-calibration.json.
- 2026-08-29 · A3/A4 shipped: runtime/ Claude Code project (CLAUDE.md protocol
  v1, locked settings allowing only the World CLI, /aliasbreaker skill),
  headless launcher (scripts/run_llm_arm.py, model pinned claude-sonnet-5,
  fixed replicate IDs, timeouts/noncompletions recorded), trace auditor
  (scripts/audit_trace.py — any non-CLI tool call disqualifies the run).
- 2026-08-29 · B1 test suite (Opus subagent): 94 stdlib-unittest tests green
  in 3.8s — physics, periodogram/basins, world determinism, leakage guards
  (poisoned-truth cases choose identical slots), chronology/budget, verdict
  consistency, planners, oracle. No real bugs found in src/.
- 2026-08-29 · END-TO-END PROOF: first headless runtime-agent run (Sonnet 5,
  locked profile) on case-101 — CORRECT resolution in 4/6 observations, 93s.
  Trajectory shows the v1 guidance working: confirmation observation after a
  single-obs support crossing, candidate pruning, evidence-citing finalize
  rationale, 2 observations saved. Auditor v1 had two false-positive classes
  (our own /aliasbreaker Skill invocation; `cd runtime &&` prefix) and one
  real gap (quoted --why text scanned for shell metacharacters); fixed —
  quoted content exempted, cd-prefix + Skill(aliasbreaker) allowed, single
  '&' and pipes/redirection still rejected. Smoke transcript re-audits clean
  (13 tool calls, 0 violations); preserved at
  evaluation/transcripts/smoke-case-101-r1.transcript.jsonl.
- 2026-08-29 · B2 report generator (Opus subagent): src/aliasbreaker/report.py
  renders the observer-facing campaign report (banner, campaign log with
  agent rationales, support table, verdict box, 3 figures, limitations,
  human-approval field, reveal-only evaluator appendix); demo at
  evaluation/reports/demo-case-101.html. Subagent findings triaged:
  (1) CHARTER/CODE MISMATCH — calibration used a grid extended past the
  charter's declared {0.85..0.99}; resolved by pre-freeze charter amendment
  (0.997 added; no original grid member met the 5% bound) with rationale
  journaled. (2) CLI now pins effective theta at `start` (was: floated with
  THETA_DEFAULT at finalize). (3) High theta assessed as a FEATURE: a
  4-sigma-separating slot yields dchi2~16 (support -> ~1.0) in one
  observation, so decisive scheduling resolves while weak scheduling
  abstains — the demo's weaker greedy campaign topping out at 0.991 and
  abstaining (correct candidate leading, no false resolution) demonstrates
  exactly that incentive.
- 2026-08-29 · Codex DIFF-GATE 1: NEEDS-REWORK, 14 findings (brainstorm/
  diffgate1-codex.md). Accepted all Criticals: auditor's quoted-content
  exemption allowed $()/backtick substitution (fixed: $, backticks, CR/LF
  now forbidden raw, grammar parsed with shlex); CLI unbound to assigned
  case/run and --theta overridable (fixed: --theta removed, path containment
  under runs/ and data/cases/, fixture SHA-256 pinned at start and
  re-verified every command; auditor enforces assigned case/run, exactly one
  start first + one finalize last); launcher scored ineligible runs (fixed:
  eligibility = clean exit + clean audit + clean replay, else scored
  noncompletion, raw record retained); charter §8 audit replay implemented
  (src/aliasbreaker/replay.py — fixture hash, action replay, measurement
  match, verdict recomputation; tamper test: edited verdict.json detected).
  Also: transactional ordering (log-before-state, verdict-before-flag),
  mandatory --why, JSON argparse errors, exact theta + higher precision in
  public state, basin separation 4->5 grid steps (charter amended), oracle
  label + config serialized into fixtures at generation, calibration selects
  on integer counts. Deferred with rationale: SQLite event store and MCP
  rewrite (over-engineering at this scale — Bash grammar is now fail-closed
  and disclosed), report hash-binding (minimal case-id check planned),
  frozen-manifest launcher mode (built at freeze, Phase D).
- 2026-08-29 · DEV SHAKEDOWN v1 (fixtures v1, prompt v1, Sonnet 5): 12 runs,
  11 completed, 10 CORRECT, 0 false resolutions, obs 3-6. Case-111
  noncompletion caused by orchestrator editing cli.py mid-flight (fixture-
  hash field missing in its meta) — our fault, disclosed; its transcript
  shows the agent attempting recovery with out-of-protocol commands (sleep,
  2>&1), which the auditor correctly flagged. Audit failures on 105/107/108/
  112 were auditor-v1 false positives (quoted absolute cd path blanked
  before the runtime check) — fixed in auditor v2. Evidence:
  evaluation/llm-arm-dev-v1.json.
- 2026-08-29 · Fixtures v2 regenerated (basin separation 5 steps, oracle
  labels embedded; all 12 dev cases resolvable). Non-LLM arms on fixtures v2
  at theta=0.997: batch 6/12, even 4/12, adaptive 4/12, zero false
  resolutions (evaluation/arms-dev-fixtures-v2.json). New observed failure
  mode: scripted-adaptive burned the chronological cursor with greedy late
  jumps and abstained at 3 obs on case-111 — cursor management joins
  confirmation as a pre-registered LLM-headroom hypothesis. Tests 94/94
  green after rework; CLI v2 + replay validated end-to-end incl. tamper
  detection.
- 2026-08-29 · Gate-mandated regression tests (Opus subagent): suite 94 ->
  198 green in 5.1s. Proofs added: batch/even plans read hidden outcomes
  zero times; adaptive reads exactly the observed set; -0.5 support
  coefficient locked (negative test incl.); 53 adversarial auditor cases
  fail closed; replay detects 9 tamper types. Subagent flagged that the
  orchestrator's brief wrongly asked semicolons-in-why to pass; the shipped
  fail-closed contract was encoded instead (correct call).
- 2026-08-29 · ITERATION LEDGER, fixtures v2, theta 0.997, identical cases:
  | arm | correct | false-res | mean obs |
  | batch (baseline)      | 6/12 | 0 | 6.0 |
  | even-spacing          | 4/12 | 0 | 6.0 |
  | scripted-adaptive     | 4/12 | 0 | 4.5 |
  | LLM v1 (dev-v1b)      | 9/12 | 0 | ~4.1 | (11/12 eligible)
  Evidence: evaluation/arms-dev-fixtures-v2.json, evaluation/llm-arm-dev-v1b.json.
  LLM failure analysis: case-103 DISQUALIFIED by the eligibility gate — a
  semicolon inside a --why rationale (protocol rule 3); its raw verdict was
  CORRECT, so protocol compliance cost one case (the gate working as
  designed). Cases 104/107: reasoned abstentions from bad positions — the
  agent jumped deep early, stranded the cursor, then correctly concluded the
  REMAINING slots could not resolve (same pathology as scripted-adaptive's
  case-111). Confirmation behavior confirmed working (103's stop_reason
  cites confirmation points crossing theta).
- 2026-08-29 · Prompt v2 (runtime/CLAUDE.md): evidence-driven changes only —
  (1) rationale hygiene first (converts 103-type losses), (2) cursor thrift
  rule: earliest among comparable slots, deep jumps only when discrimination
  genuinely lives late, plus never abstain while a discriminating slot is
  reachable (targets 104/107), (3) confirmation guidance kept verbatim.
  Launching dev-v2 shakedown on identical fixtures for the paired
  comparison.
- 2026-08-29 · DEV-V2 RESULT (identical fixtures/theta): 11/12 correct,
  12/12 eligible, 0 false resolutions, mean ~4.4 obs. Paired vs v1b:
  case-103 converted (rationale hygiene — no protocol violations anywhere),
  case-104 converted (cursor thrift — resolved in 5 obs where v1 stranded
  itself), no regressions; case-107 still abstains but now at the full
  budget (fights to the end) instead of quitting at 3 obs. Ledger:
  even 4/12 · adaptive 4/12 · batch 6/12 · LLM v1 9/12 · LLM v2 11/12.
  Evidence: evaluation/llm-arm-dev-v2.json. Prompt v2 is the final prompt;
  policies now locked pending freeze.
- 2026-08-29 · WORDING AMENDMENT (diff-gate 2 finding 7): the v1->v2 ledger
  entry above should be read as: an observed +2 gated-score difference in ONE
  paired development draw (single LLM replicate per prompt version, dev cases
  adaptively inspected during prompt design — in-sample development evidence,
  not a stable-effect claim). Raw scientific outcomes separate from gated:
  v1 was 10/12 raw-correct (case-103 correct but disqualified), v2 11/12 raw
  and gated. "Zero false resolutions" = zero OBSERVED. Mean-obs denominator:
  eligible runs. No uncertainty claim is supported by one replicate; the
  final evaluation runs 3 predeclared replicates.
- 2026-08-29 · Codex DIFF-GATE 2 (pre-freeze): APPROVE-WITH-CHANGES, 9
  findings (brainstorm/diffgate2-codex.md). Implemented before lock:
  charter §4 amendment authorizing oracle use SOLELY for the predeclared
  10/2 resolvable/unresolvable composition; §5 rewritten with full quota
  vector (incl. ordinary one-per-sigma subquota), precedence, discard-not-
  demote overflow rule, and all numeric thresholds; stratum predicates
  strengthened (live-candidate requirements, misleading = support OVERTAKE
  under the shared rule, scarce window defined in days on slot_t); stratum
  field removed from fixtures (manifest-only); generator fails on non-empty
  output dir, records seed range + predicate flags + generator commit + env;
  prompt v2.1 (dev-history commentary removed, metrics named, quoting
  clarified, abstention rule scoped to live pairs — guidance semantics
  unchanged from measured v2); CLI leak-scan test added; frozen analysis
  path (src/analyze_final.py: replicate-mean per case, paired diff vs batch,
  case-clustered bootstrap seed 20260830) + final-run-config.json. Deferred,
  disclosed: full behavioral confirmation-existence check in misleading
  predicate (oracle resolvability already guarantees recoverability by some
  design); canonical-JSON serialization ceremony; clean-checkout generation
  (replaced by clean-working-tree verification at the lock commit).
- 2026-08-29 · MOCK JUDGING (adversarial Opus subagent as micro1 evaluator,
  human-requested): 55/100 as-stands, gate-FAIL on missing README/repro/
  video/trajectory packaging — and three verified criticals. (1) THE BATCH
  BASELINE WAS DEGENERATE: linear pair score capped at 4 vs need 6 saturated
  after ~2 picks, after which argmax over an all-zero vector selected slots
  BY ARRAY INDEX — 35/72 baseline observations were index picks; one case
  spent all 6 visits in the first 5 days of a 60-day horizon. An accidentally
  weakened baseline (charter §5.1 violation in spirit). (2) verdict.json in
  the agent's workspace carried correct/truth_support — an answer key in
  sibling dirs during replicates. (3) docs/orchestration-reference.md
  described a private client repo inside a submission whose ownership
  transfers to micro1.
- 2026-08-29 · Fixes, all verified: client-repo doc deleted (compliance).
  Verdict split — run dirs now store PUBLIC fields only; truth-side facts
  recomputed fresh by the evaluator during replay (leak test extended).
  BASELINE REBUILT: chi2-shaped scoring (discrimination accumulates as
  (delta/sigma)^2, matching the evaluator), uncapped per slot, per-pair
  saturation at delta-chi2=16 with an unsaturated fallback (can never
  degenerate to index picks); 8 scoring variants swept openly
  (weighted/unweighted x saturated/unsaturated x need in {8..32}) and the
  STRONGEST adopted as the baseline (unweighted saturated, 7/12): a baseline
  chosen to be as good as we could make it. Shared stop rule extended to all
  plan-executing arms (charter §6 amended; denying batch the stop had
  structurally gifted the adaptive arms their efficiency margin). Launcher:
  model-identity enforcement in eligibility, loud Claude-Code precondition,
  prompt-sha256 + code-commit provenance in summaries. Auditor: cd target
  must equal the launcher-supplied runtime dir exactly (path-suffix bypass
  closed). analyze_final: executed for the first time via synthetic dry-run
  after fixing crash paths (missing replicates score 0 over 3 expected; NaN
  guards; manifest/arms case-set + fixture-hash validation) and the
  bootstrap upgraded to two-stage (replicate variance propagated).
  runtime/runs un-gitignored (trajectory evidence in-repo).
- 2026-08-29 · HONEST DEV LEDGER (fair baseline, identical fixtures/theta):
  even 4/12 (5.5 obs) · scripted-adaptive 4/12 (4.25) · batch 7/12 (5.17) ·
  LLM v2 11/12 (~4.4, single replicate, dev cases inspected during prompt
  design — in-sample). Margin vs fair batch: +4 cases observed, obs roughly
  equal. Mock judge's own fair-batch probe reported 9/12; our sweep's best
  reproducible variant reaches 7/12 — discrepancy noted, our 8-variant sweep
  is committed as the anti-strawman evidence. Final evaluation (fresh
  stratified cases, 3 replicates) remains the arbiter.
- 2026-08-29 · Deferred from mock judging, disclosed: additional
  "top2+thrift" scripted ablation; deny-by-default settings hardening;
  history rewrite for the deleted client doc (present in git history; the
  submission ZIP is built from the working tree, and the repo stays private
  until then).
- 2026-08-30 · FREEZE CEREMONY, first attempt: generator FAILED CLOSED after
  4000 seeds — ordinary/misleading/unresolvable quotas filled, but ZERO
  tempting_early and ZERO scarce_window cases. A 200-case probe (committed
  script) showed both strata are STRUCTURALLY ABSENT in this world:
  tempting_early 0/200 at every threshold (truth always separates early from
  some rival); the best rival pair has a median ~25 discriminating slots
  spread across the horizon (5th pct of earliest-disc-from-end = 46 days),
  so a natural late-narrow window cannot occur. Round-2 intuition, falsified
  by measurement.
- 2026-08-30 · Charter §5 amended pre-freeze (before any arm touched any
  final seed; aborted partial generation discarded unrun): tempting_early ->
  "crowded" (6 candidates AND sigma>=4, hardest natural axis);
  scarce_window -> CONSTRUCTED by availability masking (remove early
  discriminating slots of the best live rival except the final 25 days, 1-6
  kept, oracle re-verified post-mask) — availability is exogenous, and the
  stratum directly tests the pre-registered cursor-reservation hypothesis.
  Natural scan restarts from seed 30000; constructed cases from 80000+.
- 2026-08-30 · FREEZE executed: selection-lock v2 (2afd065) -> generation ->
  one correctness fix (manifest assembly omitted constructed entries;
  fixtures proven byte-identical across regeneration) -> FREEZE commit
  bae385d, tag freeze-v1. 12 cases / 5 strata / one-per-sigma ordinary,
  34 KB fixtures, all hashes verified, no stratum/oracle leakage.
- 2026-08-30 · FINAL RESULTS (frozen; evaluation/final-analysis.json).
  36/36 LLM runs eligible — zero protocol violations across the entire
  official matrix; prompt sha + commit recorded per run. Resolvable (n=10):
  LLM 76.7% vs batch 20%, even 40%, adaptive 40%; paired LLM-batch +0.57,
  bootstrap 95% [0.30, 0.83]; LLM mean obs 4.9. Strata: misleading 6/6 LLM
  replicate wins (confirmation behavior defeats the planted trap; batch
  0/2); scarce/reservation 5/6 (cursor management works); crowded 2/6
  (hard for everyone); ordinary 10/12. NEGATIVE RESULT, reported unretouched:
  unresolvable stratum 6/6 FALSE RESOLUTIONS by the LLM (scripted arm: 0) —
  on basin-absent cases the agent's superior discrimination drives a wrong
  candidate decisively past theta. Named: menu-incompleteness amplification.
  Insight for future systems: relative support needs an absolute
  model-adequacy companion check with "none of the above" scoreable.
  README updated with final tables, failure mode, and hot take.
