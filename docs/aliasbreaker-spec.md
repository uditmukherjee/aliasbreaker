# AliasBreaker — Design Spec v1 (pre-kill-test)

An agentic workflow that allocates scarce follow-up observations to break
orbital-period aliases in radial-velocity (RV) exoplanet data.

Status: DRAFT for plan-gate review. The kill test (§9) decides commitment.

## 1. One-sentence story

Sparse telescope sampling leaves several orbits that all fit the data; the agent
decides *when to look next* so the aliases stop fooling us — within a budget of
six observations.

## 2. Problem and user value (rubric: 15 pts)

- **User:** An astronomer (or astronomy student / small-observatory scheduler)
  who has sparse RV measurements of a star showing a periodic signal with
  several plausible period aliases, and must plan scarce follow-up telescope
  time to determine the true orbit.
- **Bottleneck:** Telescope time is allocated in small budgets; naive nightly
  or evenly spaced follow-up can repeatedly sample the same orbital phase,
  leaving daily/harmonic aliases unresolved — a well-documented problem in RV
  astronomy (period aliasing from diurnal sampling; e.g., the literature on
  alias disambiguation in RV surveys).
- **Value:** A follow-up plan that resolves the orbit in fewer visits, plus an
  evidence-backed resolution report. Honest framing: a *planning copilot*
  validated on synthetic systems with known truth — exactly how such tools are
  validated in practice before use on sky.
- **Scope honesty:** We do not claim to replace professional scheduling
  pipelines; we demonstrate measurable value of adaptive planning on a
  controlled, reproducible benchmark.

## 3. The world (synthetic, ground truth by construction)

- Keplerian single-planet RV model: v(t) = γ + K[cos(ν(t)+ω) + e·cos ω], with
  Kepler's equation solved by Newton iteration (our own implementation — part
  of the learning goal).
- Each **case** = hidden true orbit + ~8 sparse initial observations (near
  nightly cadence over ~30 nights) + a set of 3–6 **candidate orbits** that all
  fit the initial data comparably (constructed from the daily-alias family
  1/P ± k/day and harmonics, each refit to the initial data — the true orbit is
  one of them, refit the same way so its exact parameters never leak).
- **Follow-up slots:** nights 31–90 with per-night visibility offsets, a
  weather/availability mask, and a few off-cadence (fractional-night) slots.
  The agent may observe only at legal slots; budget = 6 observations.
- **Deterministic noise keyed by (case, slot):** any policy requesting the same
  slot receives the identical measurement — fair comparison by construction,
  reproducible everywhere.
- Fixture size: tens of KB (JSON). Pure Python + NumPy. Offline. Windows-safe.

## 4. Three-arm design (rubric: Measured Improvement 15 + Hot Take 5)

| Arm | What it is | Role |
| --- | --- | --- |
| **Baseline** | Batch planner: selects all 6 follow-up times upfront by greedy prior-weighted discrimination, then fits and picks the best candidate | The credible "simple script" baseline the brief asks for — genuinely strong, not a strawman |
| **Ablation arm** | Scripted adaptive policy: same greedy scoring, but re-scored after each observation with updated candidate weights | Isolates the value of *adaptivity itself*; doubles as the required ablation |
| **Advanced** | LLM agent: makes the observation-selection, early-stop, and abstain decisions through a strict tool schema | The agentic workflow being judged |

All three arms share the same fitter, verifier, noise, and slots. The measured
deltas cleanly separate (a) adaptivity value and (b) LLM-judgment value — the
second comparison is the built-in hot-take material ("where does an LLM planner
beat a hand-rolled heuristic, and where doesn't it?").

## 5. The LLM agent (rubric: Agent Solution & Engineering, 30 pts)

Agentic, not a wrapper: the agent's choices determine *which evidence exists*.

- **Tools (strict JSON schema):** `get_case_brief` (candidates, windows,
  weights — never the truth), `predict_curves` (candidate RVs over slots),
  `evaluate_discrimination` (pairwise separation diagnostics), `observe(slot)`
  (spends budget — irreversible), `refit_candidates`, `submit_verdict
  (candidate | abstain, confidence, justification)`.
- **Agentic behaviors judges can see in trajectories:** hypothesis pruning,
  switching from broad discrimination to targeted confirmation, reserving a
  confirmation visit, reacting to a surprising measurement (retry/replan),
  early stopping to save budget, justified abstention when windows make
  candidates observationally equivalent.
- **Guardrails:** the agent cannot see hidden truth or noise seeds; verdict
  must cite numeric evidence (final Δχ² table) produced by the deterministic
  fitter — the report is verified, not vibes.
- **Model:** Anthropic API (pinned model ID), provider-replaceable interface.
  Temperature/retry budget fixed and disclosed.
- **Trajectory capture:** every run logs system prompt, tool calls, tool
  results, and decisions to JSONL — the submission's trajectory requirement is
  a byproduct, not an afterthought.

## 6. Evaluation (rubric: Measured Improvement; qualification gate)

- **Primary metric:** alias-resolution rate — fraction of cases where the
  submitted candidate is the hidden truth with relative likelihood ≥ 0.9
  within budget. Wrong pick = fail; abstention on a resolvable case = fail;
  abstention on the constructed-equivalent case = pass (correct behavior).
- **Secondary:** observations used, correct-abstention behavior, wall time,
  cost per case.
- **Eval set:** ~10–12 frozen cases across noise levels, eccentricities, alias
  structures, window sparsity. **Adversarial case:** two aliases that agree at
  every integer-night slot and separate only in one short off-cadence window.
  Second adversarial flavor: a case whose candidates are genuinely equivalent
  within the legal windows — correct answer is abstention.
- Cases frozen (seeds committed) before final runs; metric defined here,
  before implementation. Difficulty calibration during the kill test is
  disclosed in the changelog.
- **Repeatability:** the world is deterministic; the LLM arm is run N=3 times
  on the frozen set and we report all runs.

## 7. Reproducibility (rubric: 15 pts + qualification gate)

- Pure Python 3.11 + NumPy (pinned); no data downloads; fixtures in-repo.
- One command each: baseline, ablation, advanced, evaluation.
- **Two reproduction paths:** (a) live — judge sets `ANTHROPIC_API_KEY` and
  re-runs the agent; (b) recorded — committed trajectories replay through the
  same deterministic world to reproduce the headline table with no key. Both
  documented; recorded path is the qualification-gate safety net.
- `.env.example`, versions pinned, expected outputs and approximate cost/runtime
  documented.

## 8. End-to-end quality (rubric: 20 pts)

Final artifact per case: a **follow-up resolution report** — chosen observation
times on a calendar, the surviving orbit with parameters and uncertainties, the
Δχ² evidence table, folded-RV plot at the resolved period, and explicit
limitations. Something an observer could actually take to a scheduling meeting.
Demo video: candidate curves overlaid, observations landing one at a time,
wrong aliases visibly dying, final report shown.

## 9. Kill test (before full commitment)

Build world + fitter + batch baseline + scripted adaptive arm (~few hours, no
LLM). Commit to AliasBreaker only if:

1. Case generation yields ≥3-candidate alias sets that genuinely fit the
   initial data.
2. Scripted-adaptive beats batch on ≥3 of ~12 draft cases (adaptivity
   headroom exists → LLM arm has room to shine and something to be measured
   against).
3. Full two-arm evaluation runs in minutes on this machine.

Fallback if it fails: Circuit Sleuth reuses the entire skeleton (budgeted
world, three arms, evaluator, traces) with a different forward model.

## 10. Risks and open questions (for plan-gate review)

- **R1 Baseline saturation:** batch may already resolve most cases → mitigated
  by kill test + difficulty knobs (windows, noise, candidate count).
- **R2 LLM ≈ scripted-adaptive:** possible outcome; then the honest headline is
  baseline→adaptive improvement, and LLM-vs-scripted becomes the insight/hot
  take. Disclosed, not hidden.
- **R3 Physics correctness:** our Kepler/RV implementation must be validated
  (unit tests against known limits: circular orbit sinusoid, e→0 consistency,
  period recovery on dense data).
- **R4 Leakage:** candidate construction must never hand the agent the true
  parameters (all candidates refit from initial data identically).
- **R5 Time:** ~2 days remain; the LLM arm + eval + video must fit after the
  kill test. Orchestration per docs/orchestration-reference.md (plan-gate,
  diff-gate, journal).
