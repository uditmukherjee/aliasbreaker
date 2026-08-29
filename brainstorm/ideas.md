# Brainstorm Round 1 — Science-Domain Idea Briefs

> **For codex (and any critic):** Attack each brief below. For each one, answer:
> (a) What breaks first in 2.5 days? (b) Is the baseline credible or a strawman?
> (c) Can a judge reproduce the eval from a clean machine without flaky downloads?
> (d) Is the "user + bottleneck" story honest or hand-wavy? (e) What would you cut
> to make it finishable? Write critiques into `brainstorm/debate.md` under a
> heading per idea. Propose new ideas only if they beat these on the filters.

Context: micro1 Frontier Engineering Challenge 2026 (see `../HACKATHON_REQUIREMENTS.md`).
Deadline Aug 31, 23:30 IST. Must ship: credible baseline + advanced agentic workflow,
fixed eval set (~10 cases incl. 1 adversarial), primary metric defined up front,
improvement changelog with a removed experiment, agent trajectories, 5-min video,
clean-environment repro. Direction constraint from the human: sciences (physics /
astrophysics / quantum / adjacent), explicitly OUTSIDE prior domains (no trading,
no WireFlow-style consulting work, no hospital/health).

Scoring key per §16 filters: ✅ satisfied, ⚠️ needs work, ❌ problem.

---

## Idea 1 — Exoplanet Transit-Recovery Agent

**One-liner:** An agent that takes a star's light curve from TESS/Kepler public data
and produces a vetted verdict: planet candidate or not, with period, depth, and a
vetting report — validated against NASA's confirmed-planet catalog.

- **User:** Astronomy grad students / citizen-science vetters triaging candidate
  light curves (documented bottleneck: TESS produces far more candidates than
  humans can vet; this is why Planet Hunters exists).
- **Bottleneck:** Manual vetting of light curves is slow and error-prone;
  false positives (eclipsing binaries, systematics) dominate raw detections.
- **Baseline:** A single-prompt LLM run given the raw light curve summary + a naive
  BLS (Box Least Squares) script with default parameters. Credible — this is
  genuinely how a first attempt looks.
- **Advanced:** Agent with tools: `lightkurve` data fetch, detrending choices,
  BLS/TLS period search, vetting checks (odd-even depth test, secondary-eclipse
  test, centroid sanity), iterative retry on low-SNR, self-consistency check,
  final structured verdict + human-readable vetting report.
- **Primary metric:** Recovery F1 over a fixed set of ~12-15 targets: confirmed
  planets (should detect, with period within tolerance) + known false positives
  (eclipsing binaries — should reject) + quiet stars (should report null).
- **Adversarial case:** An eclipsing binary that passes naive BLS; and/or a
  planet whose transit is buried in stellar variability.
- **Verification:** Deterministic — compare against NASA Exoplanet Archive
  ground truth. Period match is numeric, not vibes.
- **Repro story:** Cache the FITS light-curve fixtures in-repo (small, public,
  license-clean) so judges never hit MAST live. ✅
- **Demo:** Light-curve plots with folded transits — visually stunning, instantly
  understandable in a 5-min video. ✅
- **Learning payoff:** Real astro data analysis, time-series signal processing,
  agent-with-scientific-tools pattern.
- **Filter flags:** All ✅ except ⚠️ compute time per target (keep targets small)
  and ⚠️ fixture file sizes vs 50 MB ZIP cap (trim/cut cadence).

## Idea 2 — Spec-to-Quantum-Circuit Agent

**One-liner:** An agent that takes a natural-language/mathematical spec ("prepare a
3-qubit GHZ state", "implement Grover for this 2-bit oracle", "QFT on 4 qubits with
depth budget D") and produces a working Qiskit circuit, verified by statevector
simulation against the spec's expected output.

- **User:** Quantum-computing students and engineers onboarding to QC; translating
  textbook specs into correct circuits is the standing beginner bottleneck.
- **Baseline:** Single prompt to an LLM: "write Qiskit code for X" — run once,
  report pass/fail. Credible and famously unreliable for QC.
- **Advanced:** Agent loop: generate circuit → simulate (statevector /
  measurement distribution) → compare to spec's expected state/distribution
  (fidelity threshold) → diagnose mismatch → repair → retry, with a gate/depth
  budget verifier and a final explanation artifact.
- **Primary metric:** Spec-satisfaction rate (fidelity ≥ threshold) over ~12 fixed
  specs; secondary: gate count / depth vs budget, retries needed.
- **Adversarial case:** A spec that is subtly unsatisfiable under the constraints
  (e.g., depth budget too tight) — does the agent detect impossibility instead of
  hallucinating success?
- **Verification:** Fully deterministic — the simulator is the judge, not us. ✅
- **Repro story:** Pure-Python (qiskit + qiskit-aer), no data downloads, seeds
  fixed. Strongest repro story of all six. ✅
- **Demo:** Circuit diagrams + fidelity numbers; clear but less visually dramatic
  than telescope data. ⚠️
- **Learning payoff:** Actual quantum computing fundamentals + the
  generate-verify-repair loop pattern (transfers everywhere).
- **Filter flags:** All ✅; watch ⚠️ "is the LLM already too good at textbook
  circuits?" — if baseline passes 90%, there's no improvement to show. Mitigate
  with harder specs (constraints, budgets, noise models).

## Idea 3 — Physics Derivation & Dimensional-Analysis Auditor

**One-liner:** An agent that audits a step-by-step physics derivation (LaTeX/markdown)
for algebraic errors, dropped terms, and dimensional inconsistencies, using SymPy as
the deterministic checker.

- **User:** Physics students self-checking problem sets; authors checking
  manuscripts before posting.
- **Baseline:** Single-prompt LLM review of the derivation. Credible.
- **Advanced:** Agent parses each step into SymPy, verifies step-to-step
  equivalence symbolically, runs dimensional analysis, localizes the first
  broken step, proposes the fix, re-verifies.
- **Primary metric:** Seeded-error localization accuracy over ~15 derivations with
  known injected errors (+ clean derivations to measure false-positive rate).
- **Adversarial case:** An error that is dimensionally consistent but algebraically
  wrong; a step requiring a non-obvious identity (tests false-positive behavior).
- **Verification:** Deterministic (SymPy). ✅
- **Repro story:** Pure Python, no data, no downloads. ✅ Best-in-class.
- **Demo:** Text-heavy; hardest to make visually exciting in 5 minutes. ⚠️
- **Learning payoff:** Symbolic computation, LaTeX→CAS parsing (genuinely hard),
  verifier-first agent design.
- **Filter flags:** ⚠️ LaTeX→SymPy parsing is a tarpit that could eat a full day;
  ⚠️ risk of feeling like a "homework checker" (lower perceived ambition);
  otherwise ✅.

## Idea 4 — Paper-Figure Reproduction Agent

**One-liner:** An agent that takes a computational-physics paper (with public code
or well-specified methods) and reproduces a target figure/number, reporting
match/mismatch — a reproducibility agent judged on reproducibility.

- **User:** Researchers/reviewers; the reproducibility crisis is heavily documented.
- **Why it's seductive:** Perfect narrative alignment with this hackathon's values.
- **Why it's dangerous:** Curating ~10 papers whose results reproduce in minutes on
  a laptop is itself a research project; failure modes are unbounded (missing data,
  dead dependencies, ambiguous methods); eval "ground truth" (does the figure
  match?) is itself fuzzy without pixel/numeric tolerance decisions per paper.
- **Filter flags:** ❌ realistic end-to-end within window, ❌ ≥10 repeatable cases
  without heroic curation, ⚠️ everything else. **Recommend: admire, then walk away
  — or shrink to "reproduce 10 known results from ONE well-behaved domain with
  provided data" which is basically Idea 1/6 wearing a trench coat.**

## Idea 5 — Gravitational-Wave Event Detection Agent

**One-liner:** Agent performs matched-filter searches on LIGO open data (GWOSC)
segments to find/characterize known events vs noise segments.

- **User:** GW astronomy students learning the pipeline.
- **Verification:** Known event catalog (GWTC) = ground truth. ✅
- **Filter flags:** ⚠️ PyCBC/GWpy learning curve is steeper than lightkurve;
  ⚠️ data segments are larger; ⚠️ compute per case is heavier; demo is good
  (spectrograms, chirps — could literally play the sound of a black-hole merger
  in the video ✅). Essentially Idea 1's shape with higher setup risk and higher
  coolness ceiling. A deliberate risk/reward tradeoff vs Idea 1.

## Idea 6 — Orbital-Dynamics Stability Agent

**One-liner:** Agent translates a described gravitational scenario ("Sun, Jupiter,
and a test asteroid at 2:1 resonance…") into a correct REBOUND n-body simulation,
runs it, and reports stability with evidence — verified by energy/momentum
conservation and known analytic/catalog results.

- **User:** Astro students / educators building intuition; simulation-setup errors
  are the classic silent failure.
- **Baseline:** Single-prompt "write a REBOUND script for X".
- **Advanced:** Agent with setup → conservation-law self-check (energy drift
  threshold as deterministic verifier) → known-limit sanity tests (two-body
  analytic orbit) → run → structured stability verdict.
- **Primary metric:** Correct-verdict rate over ~12 scenarios with known outcomes
  (stable resonances, unstable configs, Hill-sphere violations).
- **Adversarial case:** A scenario that looks stable on short timescales but
  diverges (integration-time trap); a prompt with physically inconsistent inputs.
- **Verification:** Conservation laws + known results. ✅
- **Repro story:** Pure Python + REBOUND, no data downloads. ✅
- **Demo:** Orbit animations — very watchable. ✅
- **Filter flags:** ⚠️ "known outcome" curation needs care (we must source ground
  truth from literature/analytics, not our own intuition); ⚠️ long integrations
  vs runtime budget. Otherwise ✅.

---

## Current stack-rank (Claude, round 1 — to be debated, not final)

1. **Idea 1 (exoplanets)** — best demo + airtight ground truth; watch fixture size.
2. **Idea 2 (quantum circuits)** — best repro + best learning payoff; watch
   baseline-too-strong risk.
3. **Idea 6 (orbital dynamics)** — strong, slightly softer ground-truth curation.
4. **Idea 5 (grav waves)** — Idea 1 with more setup risk; pick only if the coolness
   is worth a day of pipeline fighting.
5. **Idea 3 (derivation auditor)** — safest build, weakest wow.
6. **Idea 4 (paper reproduction)** — beautiful narrative, unshippable in the window.

## Open questions for the human

- Which flavor of "new" itches most: telescope data (1/5), quantum (2), symbolic
  math (3), or simulation (6)?
- Tolerance for a data-pipeline fight (5) vs a guaranteed-clean build (2/3)?
- Does the video/demo "wow" factor matter to you personally, or is learning payoff
  the only currency?
