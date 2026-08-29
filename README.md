# AliasBreaker

**An agentic workflow that decides *when to look* — allocating scarce
telescope follow-up observations to break orbital-period aliases in
radial-velocity (RV) exoplanet data.**

Built solo (with Claude Code as development harness and runtime, and Codex as
an independent review gate) for the micro1 Frontier Engineering Challenge
2026. Everything in this repository was created during the hackathon window;
see [Disclosures](#disclosures).

> **SYNTHETIC BENCHMARK — DECISION SUPPORT ONLY.** All data is generated from
> a real Keplerian physics model; no real telescope data is used and no real
> observations are scheduled. Not validated for operational telescope
> scheduling; any real-world use requires astronomer review.

## The user and the bottleneck

**User:** a radial-velocity follow-up observer who, after an initial sparse
campaign shows a periodic signal, must allocate a small budget of follow-up
visits on a ground-based spectrograph.

**Bottleneck:** observing roughly once per night samples the RV sinusoid so
sparsely that a slow orbit and a fast *alias* (frequency 1/P ± k cycles/day)
pass through the same nightly points. Several candidate orbits fit equally
well; telescope nights are scarce and scheduled in advance; each visit should
be chosen to maximally discriminate the survivors. Choosing wrongly wastes
allocation — and published planet claims have been retracted over exactly
this failure (period aliasing from diurnal sampling; see Dawson & Fabrycky
2010, ApJ 722, 937, "Radial Velocity Planets De-aliased").

**What the workflow produces:** a night-by-night observation campaign with a
written rationale per visit, an evidence-backed resolution (or honest
abstention), and an observer-facing report (support table, folded RV plot,
campaign log, limitations).

## The experiment: four arms, one world

A synthetic world with **ground truth by construction**: circular-orbit RV
model with realistic parameters (P 3–20 d, K 8–30 m/s, σ 2–5 m/s), white
Gaussian noise, fixture-stored realized outcomes for every legal slot (no
runtime RNG anywhere). Candidates come from a truth-blind periodogram of the
initial data. Time is chronological: skipped nights are gone forever; budget
is 6 observations. An independent evaluator refits every candidate and
resolves only when normalized support ≥ θ = 0.997 (calibrated; see
`evaluation/theta-calibration.json`).

| Arm | What it is |
| --- | --- |
| **Even spacing** | 6 evenly spread nights (the naive floor) |
| **Batch baseline** | Joint greedy χ²-shaped 6-night design, committed upfront — the strongest of 8 scoring variants we swept, adopted deliberately to avoid a strawman |
| **Scripted-adaptive** | Same scoring re-planned after every observation (isolates the value of adaptivity itself) |
| **LLM agent** | A Claude (Sonnet 5) session in a locked-down Claude Code project: it may ONLY call the World CLI, decides observe/skip/stop night by night, and cannot see hidden truth, score its own confidence, or bypass chronology |

All arms share the same fitter, verdict rule, and pre-stored measurements
(noise keyed per slot: identical requests receive identical values). Every
LLM run is gated by a **trace auditor** (any out-of-protocol tool call
disqualifies) and **audit replay** (fixture hash, measurement match, verdict
recomputation — tamper-detecting). Ineligible runs score as noncompletion.

## Results

### Final evaluation (frozen set, 12 cases, 5 strata, 3 LLM replicates)

<!-- FINAL RESULTS TABLE — inserted from evaluation/final-analysis.json after
the frozen run completes. -->
*(being generated from the frozen commit `freeze-v1`)*

### Development ledger (12 dev cases, single replicate, in-sample)

| Arm | Correct | False res. | Mean obs |
| --- | ---: | ---: | ---: |
| Even spacing | 4/12 | 0 | 5.5 |
| Scripted-adaptive | 4/12 | 0 | 4.25 |
| Batch baseline (fair) | 7/12 | 0 | 5.17 |
| LLM agent (prompt v2) | 11/12 | 0 | ~4.4 |

Dev numbers are development evidence (cases inspected during prompt design,
one replicate); the frozen final evaluation is the headline.

## Improvement Changelog

Full evidence trail in [`docs/build-journal.md`](docs/build-journal.md);
every row links to a machine-readable artifact in `evaluation/` and a commit.

| Stage | What we tried and why | Evidence | Decision / learning |
| --- | --- | --- | --- |
| Ideation | 6 real-data science ideas (exoplanet vetting, quantum, grav waves…) | `brainstorm/` | All killed by data logistics / fuzzy ground truth; pivoted to synthetic worlds with ground truth by construction |
| Feasibility | World + candidate construction + 2 arms | `evaluation/feasibility-results.json` | Caught the basin-drift bug: candidates frozen at periodogram grid peaks accumulate phase error → false resolutions everywhere. Fix: basin-refit |
| θ calibration | 120 fresh cases, 5 thresholds, worst-arm FRR ≤ 5% | `evaluation/theta-calibration.json` | θ = 0.997; FRR decays slowly because false resolutions come from decisively wrong fits — thresholds can't veto them, confirmation behavior can |
| **Removed experiment** | Eccentric-orbit fitting (grid + linear LS over e, T0) | `evaluation/killtest-results.json` @ `ffd8e19` | Removed: ~5 effective params from 6–8 points overfits, and the coarse-T0 χ² plateau actively misled the adaptive arm (case-006, truth-weight 0.09) |
| LLM v1 | Runtime agent, protocol v1 | `evaluation/llm-arm-dev-v1b.json` | 9/12; one otherwise-correct run disqualified for a semicolon in a rationale (the eligibility gate working); two abstentions traced to cursor-stranding |
| LLM v2 | Rationale hygiene + cursor thrift, from observed failures | `evaluation/llm-arm-dev-v2.json` | 11/12, no protocol violations; single-replicate caveats apply |
| Mock judging | Adversarial evaluator-role review | `docs/build-journal.md` 2026-08-29 | **Our baseline was accidentally degenerate** (score saturation → slots picked by array index). Rebuilt χ²-shaped, swept 8 variants, adopted the strongest; margin honestly shrank |
| Strata probe | 200-case predicate distribution probe | `scripts/predicate_probe.py` | Two hypothesized adversarial strata are structurally absent in this world; charter amended pre-freeze (crowded stratum + constructed scarce-window) |
| Freeze + final | Frozen protocol, fresh stratified cases | `evaluation/final-manifest.json`, tag `freeze-v1` | Results below are whatever the frozen run produced |

**Main observed failure mode:** decisively wrong fits — a wrong candidate
that fits the acquired data *better than the truth* (from an unlucky noise
draw or a misleading early observation). No support threshold can veto these;
the effective defenses are behavioral: confirmation observations before
committing, and honest abstention. The scripted arm lacks that judgment; the
LLM agent demonstrates it in its trajectories.

**Hot take:** *protocol compliance is a capability, not paperwork.* Our
strict fail-closed eligibility gate cost the agent an otherwise-correct case
over a semicolon in a rationale — and that is the right trade. An agent that
cannot follow a declared protocol under pressure cannot be trusted with a
telescope queue, a trading book, or a production deploy. Separately: the most
valuable reviews in this project were adversarial ones pointed at *our own
evaluation* — they found a degenerate baseline and two impossible strata that
friendly review had waved through.

## Repository map

```
data/cases/          dev + final fixtures (JSON, hidden truth under "hidden")
docs/                charter (the evaluation authority), spec, build journal
runtime/             the runtime agent: CLAUDE.md protocol, locked settings,
                     /aliasbreaker skill; runs/ holds trajectories + verdicts
src/aliasbreaker/    world, fitting, evaluator, planners, CLI, replay, report
src/                 make_cases, run_arms, calibrate_theta, analyze_final
scripts/             run_llm_arm (launcher), audit_trace (auditor), probe
tests/               199 stdlib unittest tests incl. leakage + tamper proofs
evaluation/          every result artifact, manifests, calibration, analysis
brainstorm/          ideation + independent Codex gate reviews (verbatim)
```

## Reproduction

See [`docs/reproduction.md`](docs/reproduction.md) for the clean-environment
guide (setup, exact commands per arm, audit replay without any API key,
expected outputs, runtime, cost, troubleshooting).

## Disclosures

- **Individual participation** by Udit Mukherjee. Coding agents were used
  throughout (required by the challenge): Claude Code (orchestration +
  implementation; also the runtime harness for the LLM arm) and OpenAI Codex
  CLI as an independent review gate (plan-gate, two diff-gates — its verbatim
  reviews are in `brainstorm/`). Development trajectories: `runtime/runs/`
  and the gate documents.
- **Pre-existing components:** none beyond public libraries (NumPy,
  matplotlib, Anthropic tooling). All code, prompts, fixtures, and documents
  were created during the hackathon window. The multi-agent development
  process (planner/reviewer gating) follows a working pattern from the
  author's prior practice; no prior code was reused.
- **Data:** 100% synthetic, generated by committed seeded code from a real
  physics model. No personal data, no external data, no credentials.
- **Safety/ground rules:** no consequential real-world actions; outputs are
  labeled decision-support-only with a human-approval field; the runtime
  agent operates in a permission-locked profile with an auditable transcript.

## License

MIT (see `LICENSE`).
