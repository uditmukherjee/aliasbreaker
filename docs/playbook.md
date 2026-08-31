# Evaluation-First Agent Development — a playbook

Fourteen principles, each learned the hard way while building AliasBreaker,
each domain-independent. The physics was just a world whose ground truth was
cheap; every principle below transfers to document extraction, support
triage, code repair, routing, retrieval — any system where a model makes
decisions and someone has to believe the results.

Each principle has: what it says, the moment that taught it (with the
artifact in this repo), a checklist, and a non-physics translation.
The companion narrative is [`narrative.md`](narrative.md).

---

## 1. Build the evaluation harness before the product

The first thing that ran was not an agent — it was a feasibility harness with
two deterministic arms and an evaluator. It caught a physics bug on day one
(candidates frozen at periodogram grid peaks drifted out of phase over the
horizon; even the *true* candidate stopped fitting its own data). No agent
existed yet; nothing was lost.
*Evidence:* `evaluation/feasibility-results.json`, journal 2026-08-29.

- [ ] Before writing the agent, write: the world/fixtures, a baseline, the
      evaluator, and one end-to-end run that prints a table.
- [ ] Treat the first table as a smoke test of the *evaluation*, not the
      product. Absurd numbers mean the harness is wrong.
- [ ] Every later change is judged by the same table.

*Elsewhere:* for a contract-extraction agent, build the fixture set, the
regex/heuristic baseline, and the field-level scorer before any prompt.

## 2. Ground truth by construction

Real telescope data would have cost 50 MB of fixtures, fuzzy negatives ("no
confirmed planet" is not "no planet"), flaky downloads for reviewers, and no
exact answers. Generating the world from real physics gave exact truth,
34 KB of fixtures, and full offline reproducibility.
*Evidence:* `docs/process/round2-merged.md` (the pivot), `data/cases/`.

- [ ] Ask: can I *generate* inputs whose correct answer I know by
      construction? Usually yes, and it is honest if disclosed.
- [ ] Store realized inputs, not RNG seeds (no cross-version drift).
- [ ] Disclose every simplification of the synthetic world.

*Elsewhere:* generate synthetic invoices with known fields; synthetic tickets
with known routing; code with injected known bugs.

## 3. The baseline is the arm that matters most — and the easiest to strawman by accident

Our first baseline scored candidate nights with a capped linear score whose
"need" quota was exhausted after two picks; the score vector went to all
zeros and `argmax` silently chose nights **by array index**. 35 of 72
baseline observations were index picks. Nobody intended it. An adversarial
reviewer instrumented it. Fixing it (χ²-shaped score, eight variants swept,
strongest adopted) *shrank* our margin — to a number that survives hostile
reading.
*Evidence:* journal 2026-08-29 "MOCK JUDGING"; `src/aliasbreaker/planners.py`.

- [ ] Instrument the baseline: log *why* it chose each action.
- [ ] Sweep baseline variants openly and adopt the strongest; commit the
      sweep.
- [ ] Give the baseline every structural advantage the advanced arm has that
      does not require intelligence (we had denied it the shared stop rule).
- [ ] Be suspicious of a large margin. It is more often a weak baseline than
      a strong agent.

## 4. Three arms, or you cannot answer "is the LLM decoration?"

Baseline / **scripted-adaptive ablation** / LLM agent. The ablation uses the
same tools, the same re-planning loop, the same stop rule — everything except
the model's judgment. On the frozen set: batch 20%, scripted-adaptive 40%,
LLM 77%. The middle number is what makes the third number believable.
*Evidence:* `evaluation/final-analysis.json`.

- [ ] Write a hand-scripted version of your agent's policy. If it matches
      the LLM, you have learned something cheaper than an agent.
- [ ] Share tools, evidence, verdict rule, and budget across all arms; list
      every intentional difference.

## 5. The agent never grades itself

Verdicts are computed by an independent evaluator from the data the agent
gathered; the agent controls only what to observe and when to stop. An early
design let the agent "submit confidence" — a review called it a gaming vector
and it was removed before a line of agent code existed.
*Evidence:* `docs/evaluation-charter.md` §3; `src/aliasbreaker/evaluator.py`.

- [ ] Confidence, scores, pass/fail: computed outside the model, from
      artifacts the model produced.
- [ ] Publish the exact formula. "Normalized support" is not "probability";
      say which one you have.

## 6. A result counts only if the process was clean (fail-closed gates)

Every LLM run passes three gates or scores as noncompletion: the trace
auditor (only the declared tool grammar; any other tool call disqualifies),
audit replay (recorded actions re-executed against hashed fixtures), and
model identity. A correct run was disqualified over a **semicolon** inside a
rationale — and that was the right call. All 36 official runs later passed
clean.
*Evidence:* `scripts/audit_trace.py`, `src/aliasbreaker/replay.py`,
`evaluation/llm-arm-final.json` (`n_eligible`).

- [ ] Define the protocol an agent must follow; write the auditor; make it
      fail closed (empty/truncated/malformed = fail).
- [ ] Never silently retry an ineligible run. Report it.
- [ ] Design the protocol so a good agent *can* comply (rule 13).

## 7. Record and replay

Noise keyed per slot, realized outcomes stored in fixtures, an action log,
and a replay that recomputes every measurement and verdict — so a reviewer
verifies the headline table offline in seconds, and any edited byte is
detected. Replay is also what let a packaging subagent verify 36 runs from a
clean extraction without an API key.
*Evidence:* `docs/reproduction.md` §3; `tests/test_replay.py`.

- [ ] Make the world deterministic given the agent's actions.
- [ ] Store what is needed to recompute, hash it, and test that tampering
      is caught.
- [ ] Separate "replay verifies integrity" from "provenance of the model's
      decisions rests on the recorded transcript" — say both.

## 8. Freeze discipline: lock the rules before you look

Development cases were inspected freely while tuning prompts. The final set
was generated from fresh seeds only after a **pushed selection-lock commit**
containing the charter, generator, prompts, policies, analysis code, and
replicate IDs; the freeze commit added only fixtures and hashes; results
were whatever came out. When the first generation failed closed, the rules
were amended *before* any arm touched any final seed — and journaled.
*Evidence:* tag `freeze-v1`; `evaluation/final-manifest.json`;
`evaluation/final-run-config.json`.

- [ ] Separate dev fixtures from final fixtures. Tune on dev only.
- [ ] Predeclare the metric, aggregation, replicate policy, failure scoring,
      and bootstrap seed.
- [ ] Lock commit → generate → freeze commit → run → no changes.

## 9. Verify your test categories exist before you promise them

The charter declared five adversarial strata. A 200-case probe showed two of
them were **structurally impossible** in this world (0/200 at every
threshold). We replaced one and constructed the other by masking schedules,
before the freeze, with the probe committed.
*Evidence:* `scripts/predicate_probe.py`; journal 2026-08-30.

- [ ] Before promising a hard-case stratum, measure its base rate in the
      generator's distribution.
- [ ] If it does not occur naturally, construct it explicitly and say so, or
      drop it.

## 10. Point adversarial review at your own evaluation

Friendly review approved the spec. An independent reviewer (a different model
family, invoked blind) returned NEEDS-REWORK with 32 findings; two later gates
found more; a subagent role-playing the *evaluator* found the degenerate
baseline, an answer key in the agent's workspace, and a compliance problem.
Every one of those was invisible from inside.
*Evidence:* `docs/process/spec-review-codex.md`, `diffgate1-codex.md`,
`diffgate2-codex.md`, journal "MOCK JUDGING".

- [ ] Gate plans and diffs with a reviewer that shares none of your context
      or model biases; embed the material inline so it cannot skim.
- [ ] Run one review whose brief is "you are the person who will score
      this; try to disqualify it."
- [ ] Triage in writing: accept, modify, or defer *with reason*. Keep the
      verbatim reviews in the repo.

## 11. Iterate prompts with a ledger, not vibes

Prompt v1 → v2 changed exactly two things, each traceable to an observed
failure (a semicolon disqualification; cursor-stranding on two cases), scored
on the same fixed dev set, paired per case. The journal entry was then
amended to say what a single replicate can and cannot support.
*Evidence:* `runtime/CLAUDE.md` history; `evaluation/llm-arm-dev-v1b.json`,
`llm-arm-dev-v2.json`.

- [ ] One prompt version per row; same cases; paired comparison; state the
      replicate count next to every claim.
- [ ] Keep the failed version's transcripts.

## 12. Relative confidence is a trap

On cases whose true answer was **not among the candidates**, the agent
resolved a wrong candidate decisively in 6 of 6 runs — while the dumber
scripted arm abstained. Better evidence-gathering amplified confidence in a
broken option set. No relative threshold can catch this; only an absolute
adequacy check ("does the winner actually fit?") and a scoreable
"none of the above" can.
*Evidence:* `evaluation/final-analysis.json` (unresolvable stratum);
README "Results".

- [ ] Any system choosing among options — classifier, router, retriever,
      candidate ranker — needs an explicit, *scored* none-of-the-above path.
- [ ] Add an absolute goodness-of-fit / adequacy signal beside relative
      scores.
- [ ] Include unanswerable cases in every eval set and report behavior on
      them separately.

## 13. Protocol compliance is a capability

The semicolon. A protocol an agent cannot reliably follow under load is a
protocol that will disqualify it in production. Prompt v2's first rule
became rationale hygiene; violations went from one to zero across 48
subsequent official and dev runs.

- [ ] Put protocol rules first in the instructions and explain the
      consequence.
- [ ] Measure violations as a metric, not an anecdote.

## 14. Orchestration lessons

- An independent reviewer from a **different model family** catches
  different things; when two models ideate blind and converge, that
  convergence is a decision signal.
- Fresh subagents with well-specified briefs are excellent for parallel,
  bounded work (tests, packaging, explainers); the orchestrator keeps the
  context-heavy critical path.
- Every phase closes with an artifact, a journal row, and a commit — the
  changelog then writes itself.
- **Never edit code under a running experiment.** One mid-flight CLI edit
  broke a live run; pin experiments to a commit or run them from a worktree.
- The human's highest-leverage moments were direction (the domain pivot),
  taste (which idea to pick), and the request for an adversarial mock
  review — not code.
