# AliasBreaker — Design Spec v2 (post plan-gate)

v1 was reviewed by the Codex plan-gate (NEEDS-REWORK, 32 findings; see
`docs/process/spec-review-codex.md` and `docs/process/spec-review-triage.md`).
v2 incorporates the accepted findings. Evaluation protocol lives in
`docs/evaluation-charter.md` (the charter is the authority on metrics, arms,
fixtures, and freeze discipline; this spec defers to it).

## 1. One-sentence story

Sparse telescope sampling leaves several orbital periods that all fit the
data; an agent that decides night by night whether to observe, skip, or stop
resolves the true orbit within a six-visit budget.

## 2. User and problem (single persona, honest scope)

**Persona:** a radial-velocity follow-up observer responsible for allocating a
small number of follow-up visits on a small ground-based spectrograph after an
initial sparse campaign shows a periodic signal with alias ambiguity.

**Bottleneck:** follow-up visits are scarce and scheduled in advance; naive
cadences resample the same phase and leave daily/harmonic aliases standing.
Period aliasing from diurnal sampling is a documented failure mode in RV
astronomy (alias-disambiguation literature, e.g. Dawson & Fabrycky 2010 — cite
checked before submission).

**Scope honesty (stated everywhere user-facing):** synthetic benchmark /
decision support only. Scheduled-availability world, fixed measurement
precision, circular orbits, white Gaussian noise — each simplification
disclosed. No real observatory integration; any real-world use requires
astronomer review (human-approval field in every report).

## 3. World (charter §1–2)

Circular-orbit RV world; chronological state machine (observe/skip/stop, no
time travel, no revisits); fixtures store realized potential outcomes for
every slot (no runtime RNG); candidates derived from the initial data by a
declared periodogram procedure — hidden truth touches only generation and
scoring. Eccentric-orbit machinery from the kill test is retained in-repo as
the documented removed experiment (evidence: chi2-plateau anomaly, overfitting
risk at 6 initial points).

## 4. Arms (charter §6)

Batch baseline (joint greedy set design, committed upfront), even-spacing
context baseline, scripted-adaptive ablation, and the LLM agent. One
information contract; shared deterministic evaluator-owned verdict rule; the
LLM controls only scheduling and stopping — it never supplies scored
confidence. If the scripted ablation beats the LLM arm, that result is
reported unchanged and becomes hot-take material; the benchmark is not
retrofitted.

## 5. LLM agent runtime (rubric: Agent Solution & Engineering)

- **Loop protocol (finite-state):** max 40 tool turns per case; states
  OBSERVING → STOPPED; actions `observe(slot)`, `skip_to(night)`, `stop()`;
  illegal actions are rejected with an error result (logged, never silently
  fixed), 3 consecutive protocol violations = noncompletion.
- **Tools (diagnostics only, never recommendations):** `get_state` (candidates,
  fits, measurements, remaining slots, budget), `support_table`,
  `pairwise_separation(slot_range)`, `window_scarcity`, plus the actions.
- **Strategic room for the LLM (the tested hypothesis):** multi-pair coverage,
  reserving scarce future windows, confirmation before commitment, calibrated
  stopping/abstention, recovery from misleading observations. Treated as a
  hypothesis, not a foregone conclusion.
- **Model:** pinned Anthropic model ID + reported provider version; fixed
  sampling parameters; replicate and retry protocol per charter §7.
- **Trajectory schema:** prompt + version, case/fixture hashes, all assistant
  messages, tool calls/results, invalid actions, retries, recovery, stopping
  decision, token/cost, harness version. Redaction pass before packaging.

## 6. Deliverable artifact (rubric: End-to-End Quality)

Per-case campaign report (HTML via pinned matplotlib for plots): campaign log
(night-by-night decisions with the agent's stated rationale, labeled
qualitative), support table, folded RV plot at the resolved period, residuals,
next-action-or-stop statement, limitations, human-approval field, and the
"synthetic benchmark" banner. A judge should see a document an observer could
bring to a scheduling discussion — with its assumptions on its sleeve.

## 7. Reproducibility (charter §8)

Pinned Python 3.12.x patch + pinned NumPy/matplotlib/SDK; fixtures hashed and
committed; two paths: live rerun (`ANTHROPIC_API_KEY`) and audit replay (no
key). Exact commands for baseline, ablation, advanced, evaluation, replay.
Expected outputs, runtime, and cost documented. Official runs from a pushed
commit.

## 8. Execution plan and ops (deadline Aug 31, 23:30 IST)

1. Rework core to charter (circular world, chronological state machine,
   periodogram candidates, fixture-stored outcomes) + tests (physics limits,
   leakage, chronology, budget, determinism, scoring, replay tampering).
2. Non-LLM arms + θ calibration on dev cases.
3. LLM arm + trajectory capture; dev-case shakedown.
4. FREEZE (charter §9). Final runs: all arms, 3 LLM replicates.
5. Reports, README (user, bottleneck, evidence chain, changelog with removed
   experiment, hot take from observed failures, pre-existing-vs-hackathon
   disclosure, licenses, safety), reproduction guide.
6. **Reserved final ~10–12h:** clean-environment reproduction, video (script
   covers: user/problem, baseline, one full real execution, comparison table,
   changelog walk, highest-impact change, removed experiment), ZIP < 50 MB
   extracted-and-tested, HackerEarth draft saved early, final submission.

Disclosure note: everything in this repo was created during the hackathon
window; pre-existing assets are limited to public libraries (NumPy,
matplotlib, Anthropic SDK) and the orchestration pattern documented in
`docs/orchestration-reference.md` (process knowledge, not code).
