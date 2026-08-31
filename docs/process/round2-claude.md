# Claude Round 2 — Direction and Fresh Ideas

Written independently, before seeing Codex's round-2 output.

## Proposed exploration direction: Synthetic worlds — ground truth by construction

**The agent as experimental scientist: interrogating hidden physical systems whose
true laws/parameters WE generate, so ground truth is exact, sealed, and free.**

Round 1 died a death of a thousand logistics: fixture sizes vs the 50 MB cap,
fuzzy negative labels ("quiet star" isn't proof of no planet), Windows dependency
pain from observatory-grade libraries, and the wrapper criticism (deterministic
tools do the science, the LLM narrates). All four traps share one root cause:
**we were borrowing ground truth from the real world**, which makes it heavy,
fuzzy, and expensive.

Flip it. Generate the world ourselves:

- **Fixtures become kilobytes** — a generator script + seed, not FITS files.
- **Ground truth is exact by construction** — the evaluator knows the hidden law
  or parameters because it created them. No catalog fuzz, no disputed negatives.
- **Difficulty is tunable honestly** — we can make systems hard enough that the
  one-shot baseline fails *naturally*, no strawman needed; calibrate before
  freezing cases, disclose the calibration in the changelog.
- **The wrapper criticism dies structurally** — in these tasks the agent's
  *sequential decisions* (what to measure next, which hypothesis to revise, when
  to stop) ARE the product. Remove the adaptivity and performance collapses;
  that ablation is built in.
- **Pure NumPy/SciPy/SymPy** — no archives, no compiled exotica, Windows-safe,
  fully offline.
- **Anti-leakage control** — procedurally generated laws with anonymized
  variables prevent the LLM from "solving" cases by recognizing textbook physics
  from memory rather than from the data.

Honest weakness to manage: the "who has this problem?" story is one step removed
— synthetic worlds are a validation environment, not a user's desk. The
defensible framing: scientists and engineers do *system identification* and
*model fitting* constantly (fit a model to experimental data, decide what to
measure next, decide when two models can't be distinguished), and the standard
way to validate any such tool is exactly this — test it on systems with known
truth before trusting it on unknown ones. We are building and validating the
tool the way the field itself would.

## Fresh idea briefs

### C1 — The Autonomous Experimentalist ("black-box lab")

**One-liner:** A hidden physical simulator (e.g., a damped driven oscillator, a
projectile with drag, an RC circuit — the agent isn't told which) exposes only an
experiment API: choose inputs, get noisy measurements, spend budget. The agent
must design experiments, identify the governing model and its parameters, and
produce a lab report — within a fixed query budget.

- **User:** Scientists/engineers doing system identification with costly
  measurements (every real experiment has a budget); also a validation testbed
  for lab-automation workflows.
- **Bottleneck:** Choosing *which* measurement to take next is the expensive
  human skill; naive grid sampling wastes budget and misses identifiability
  problems.
- **Baseline:** Fixed uniform grid of experiments + least-squares fit over all
  candidate models, pick best AIC. Credible — this is genuinely what a first
  pass looks like — and NOT weak.
- **Advanced:** Agent loop: propose hypothesis set → design the next experiment
  to maximally discriminate (reason about where models disagree) → observe →
  update fits/residuals → decide: another experiment, a different regime, or
  stop and report; must state uncertainty and abstain when models are
  indistinguishable within budget.
- **Where the agent genuinely matters:** Experiment *selection* under budget is
  a sequential decision problem; the ablation (same tools, fixed script order)
  is the built-in answer to the wrapper criticism.
- **Primary metric:** Identification accuracy (correct model + parameters within
  tolerance) at fixed budget; secondary: budget-to-identification, abstention
  correctness.
- **Eval (~10 cases):** Different hidden systems across noise levels and
  identifiability difficulty. **Adversarial:** two candidate models that are
  observationally identical in the reachable input range — correct answer is
  a justified abstention, not a guess.
- **Verification:** Evaluator compares to the generating truth. Exact.
- **Repro:** Generator + seeds in repo; NumPy/SciPy only; fixtures ≈ a few KB.
- **Demo appeal:** Watch the agent get curious — plots of chosen experiment
  points, uncertainty collapsing round by round. Strong.
- **Learning payoff:** Active learning / optimal experiment design + system
  identification — deeply transferable to any future agent work.
- **Kill risk:** Designing candidate-model families where discrimination is
  neither trivial nor impossible takes tuning time.

### C2 — Hidden-Law Symbolic Discovery Agent ("Kepler in a box")

**One-liner:** Given raw data tables generated from a hidden law (procedurally
composed — NOT textbook laws, to block memorization), the agent must recover the
symbolic form, verified by SymPy equivalence + held-out prediction error.

- **Baseline:** One-shot LLM "guess the law from this table" + a standard
  polynomial/power-law fit.
- **Advanced:** Propose → fit constants → residual analysis → dimensional-
  consistency constraint → revise structure → cross-validate → report with
  confidence; abstain if held-out error stays high.
- **Metric:** Exact-recovery rate (symbolic equivalence) + held-out RMSE.
- **Adversarial:** A law with a regime change (piecewise behavior) — does the
  agent notice the residual structure instead of forcing one global form?
- **Anti-leakage:** Random exponents/coefficients/compositions, anonymized
  variable names; textbook laws appear only as a disclosed "famous cases" side
  table (fun for the demo: it literally rediscovers Kepler's third law).
- **Repro/fixtures:** Trivial — CSVs from a seeded generator. NumPy/SymPy.
- **Kill risk:** Symbolic regression is genuinely hard; if the LLM can't beat
  the baseline on non-textbook forms, there's no measured improvement. Needs an
  early feasibility probe.
- **Learning payoff:** Symbolic regression + the "AI scientist" literature.

### C3 — Systematic-Error Forensics Agent ("the calibration detective")

**One-liner:** Synthetic instrument data with one injected systematic (clock
drift, aliasing, unit mix-up, saturation, calibration offset, cosmic-ray hits);
the agent must diagnose WHICH pathology, correct it, and the evaluator scores
recovery of the clean signal it generated.

- **User:** Experimentalists — "why does my data look wrong" is a universal,
  recurring, well-documented time sink.
- **Baseline:** One-shot LLM shown the data + summary stats, asked to diagnose.
- **Advanced:** Hypothesis-driven loop: run diagnostic probes (FFT, residuals
  vs time, histogram tails), form pathology hypothesis, apply correction,
  verify improvement, iterate or abstain.
- **Metric:** Diagnosis accuracy + post-correction error vs clean truth.
- **Adversarial:** Two stacked systematics, or a dataset that is actually clean
  (does it invent a pathology? false-positive test).
- **Kill risk:** Diagnosis may reduce to pattern-matching the LLM is already
  great at → baseline too strong. Needs probing.

### C4 — Sparse-Observation Orbit Determination Agent

**One-liner:** From a handful of synthetic telescope observations (RA/Dec at
times) of a made-up asteroid, determine the orbit and predict its future
position; evaluator checks against the generating orbit.

- Keeps the astronomy romance from round 1 with zero data logistics (we
  generate observations from a Keplerian propagator we write — good learning).
- **Baseline:** One-shot fit with a standard method; **Advanced:** agent handles
  outlier observations, short-arc degeneracy (abstain/request more data),
  iterative refinement.
- **Adversarial:** An outlier observation + a short arc consistent with two
  orbits.
- **Kill risk:** Orbit determination math (Gauss method) is a real climb in the
  window; the deterministic core might dominate the agent's contribution →
  wrapper criticism returns.

### C5 — Composition: "PhysLab" (C1 as the frame, C3 as extra case types)

The autonomous-experimentalist frame (C1) naturally hosts forensics cases (C3)
as "your instrument is lying to you" scenarios. One coherent product — *an agent
you point at an unknown system, that experiments until it can write a defensible
lab report* — with case diversity that makes the eval set interesting. Only
worth it if C1 lands early; otherwise scope-creep bait.

## Claude self-stack-rank

1. **C1 (Autonomous Experimentalist)** — the agentic contribution is structural,
   the eval is exact, fixtures are kilobytes, and it's the best learning payoff
   (active experiment design). Top pick.
2. **C3 (Forensics)** — most honest user story, but baseline-too-strong risk.
3. **C2 (Hidden-Law Discovery)** — most romantic, best demo moment (rediscover
   Kepler), but feasibility unknown without a probe.
4. **C5 (PhysLab)** — great if C1 lands fast; a trap if it doesn't.
5. **C4 (Orbit Determination)** — beautiful but the math climb + wrapper risk in
   2 days.
