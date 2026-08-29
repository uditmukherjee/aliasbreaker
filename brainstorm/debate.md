# Codex Round 1 — Debate

## Codex Round 1 Critique

One cross-cutting problem applies to every LLM-based proposal: deterministic scientific verification does not make the overall agent reproducible. The model, version, temperature, prompt, retry budget, and provider must be fixed and disclosed. Recorded trajectories are evidence, but a replay mode is not a reproduction of the live workflow. Baseline and advanced runs must use the same model unless resource differences are explicitly justified.

### Idea 1 — Exoplanet Transit-Recovery Agent

**(a) What breaks first in 2.5 days?**

The data and vetting scope break before the BLS search does.

- A single TESS light-curve FITS file may be manageable, but several sectors across 12–15 targets can consume most of the 50 MB archive. Target-pixel files needed for a genuine centroid test are much larger and effectively incompatible with this scope.
- Trimming or binning the fixtures solves packaging but can quietly make the benchmark easier by removing gaps, systematics, or out-of-transit context. Every transformation must be scripted and documented.
- `lightkurve` pulls in Astropy, SciPy, NumPy, Matplotlib, and archive-related dependencies. These usually have Windows wheels on supported Python versions, but an unpinned Python 3.13/NumPy combination could derail setup.
- TLS adds more dependency and runtime risk, particularly around `numba`/`llvmlite`. It is not justified until BLS is working end to end.
- Centroid vetting cannot honestly be claimed from a one-dimensional flux series.
- “Quiet star” is not reliable ground truth. A star without a cataloged planet is not a confirmed negative.
- A 12-case F1 score is extremely coarse: one changed result moves the score by roughly eight percentage points.

**(b) Is the baseline credible or a strawman?**

It is borderline. A one-pass BLS is credible; “single-prompt LLM plus naive BLS defaults” is muddled.

A credible baseline should receive the same extracted light curve, use a reasonable fixed quality mask, a documented fixed detrending method, a sensible period range, and one BLS search with a fixed threshold. Deliberately omitting elementary preprocessing would make it a strawman. The LLM contributes little to this baseline and may make it less realistic.

The likely calibration problem is the opposite: BLS will recover the obvious short-period planets easily. The advanced system then has to earn its improvement mainly by rejecting eclipsing binaries, resolving period aliases, and abstaining on weak evidence. If the cases are curated after seeing which ones create a large gap, judges may reasonably call the benchmark cherry-picked.

**(c) Can a judge reproduce the evaluation cleanly?**

Not as currently described.

It becomes reproducible only if:

- Runtime evaluation never calls MAST or the NASA Exoplanet Archive.
- The repository contains small, pre-extracted arrays plus target provenance, cadence, sector, source URL, license information, checksums, and an immutable catalog snapshot.
- Python is pinned to a known-good version, preferably 3.11.
- TLS and target-pixel dependencies are removed.
- Ground-truth rules explicitly handle period aliases, multi-planet stars, catalog updates, and false-positive dispositions.

Confirmed planet periods are strong positive truth. Cataloged eclipsing binaries can provide useful negative dispositions. Uncataloged “quiet stars” cannot. Definitive null cases should be synthetic no-transit controls or injection/recovery fixtures with known labels.

**(d) Is the user and bottleneck story honest?**

Only after narrowing it. Professional TESS vetting does not begin with an LLM and raw BLS; mature pipelines already generate threshold-crossing events and diagnostics. Claiming that the agent replaces transit detection or production vetting would be inflated.

An honest user is a student, citizen-science mentor, or small research group examining a preselected list of threshold-crossing events and manually assembling several vetting diagnostics. The useful artifact is a consistent evidence bundle and triage recommendation, not a discovery claim.

**(e) What should be cut?**

Cut:

- TLS.
- Centroid analysis.
- Live archive access during evaluation.
- Long-period and multi-sector targets.
- Multi-planet interpretation.
- Claims of discovering planets.
- A web application unless the evaluation harness is already complete.

Keep one principal agent, cached one-dimensional arrays, BLS, two bounded detrending choices, harmonic checks, odd/even depth, secondary-eclipse evidence, an abstention state, plots, and a structured report.

### Idea 2 — Spec-to-Quantum-Circuit Agent

**(a) What breaks first in 2.5 days?**

The specification language and verifier semantics break first, not circuit generation.

Natural-language quantum requirements contain ambiguities about qubit ordering, little-endian conventions, global phase, allowed gates, ancillary qubits, measurement, and whether the target is a state, unitary, or output distribution. A verifier that mishandles one convention will mark correct circuits wrong or incorrect circuits correct.

Qiskit API churn is another risk. `qiskit-aer` introduces a compiled binary dependency and a larger Windows installation surface. Transpiled depth and gate counts can change across Qiskit versions, seeds, backends, and optimization levels.

The proposed unsatisfiable depth-budget case is especially dangerous. Failing to find a circuit does not prove impossibility. A defensible impossibility result would need a tiny exhaustively searchable gate set, which is a separate project.

**(b) Is the baseline credible or a strawman?**

A one-shot “write Qiskit code” baseline is credible, but current models are already very good at GHZ, Bell states, textbook QFT, teleportation, and small Grover examples. Twelve familiar textbook tasks may produce a ceiling result.

Making the prompts obscure or adding arbitrary depth constraints purely to defeat the baseline would create a benchmark rather than a believable beginner workflow. Both systems must receive identical formal details; the advanced workflow cannot quietly benefit from a hand-authored expected state that the baseline never sees.

**(c) Can a judge reproduce the evaluation cleanly?**

Mostly, if Aer is removed.

Use Qiskit’s statevector functionality or a small NumPy simulator, pin Qiskit exactly, fix transpiler seeds, and avoid backend-specific gates. The evaluator must normalize global phase and state precisely how qubits map to basis-state indices. Measurement distributions cannot verify relative phase, so they are insufficient for several tasks.

The live LLM result remains stochastic. Store all outputs and trajectories, define a retry budget, and ideally report repeated-run success in addition to the headline run.

**(d) Is the user and bottleneck story honest?**

The beginner user is plausible, but “translating textbook specs into circuits” is often a learning exercise rather than a recurring operational bottleneck. A stronger framing is a learner who has attempted a circuit and needs an executable diagnosis explaining why its output violates the intended quantum state.

The advanced system’s most honest value is verified debugging, not code generation.

**(e) What should be cut?**

Cut:

- Noise models.
- Hardware backends.
- General natural-language mathematics.
- Claims of proving arbitrary depth-budget impossibility.
- Circuit optimization across arbitrary gate sets.
- Aer unless it is already proven reliable on a clean Windows installation.

Use a small structured spec schema, two to four qubits, statevector fidelity, fixed native gates, and a generate–simulate–diagnose–repair loop. A corrupted-circuit repair benchmark would probably show a more credible baseline gap than textbook generation.

### Idea 3 — Physics Derivation and Dimensional-Analysis Auditor

**(a) What breaks first in 2.5 days?**

LaTeX-to-SymPy parsing becomes the project.

Real derivations contain implicit multiplication, overloaded notation, vectors, tensors, derivatives, omitted assumptions, defined substitutions, approximations, and prose between equations. SymPy cannot automatically determine equivalence for all such expressions. Branch cuts, domains, nonzero assumptions, identities, and simplification timeouts create false error reports.

SymPy’s LaTeX parser also adds parser-version fragility. Dimensional analysis is not automatically meaningful when authors nondimensionalize variables or omit unit declarations.

**(b) Is the baseline credible or a strawman?**

A single LLM review is credible, but modern models may already find obvious sign, exponent, and unit errors. If the benchmark uses simple high-school algebra, the baseline may be too strong. If it uses genuinely difficult derivations, the parser and verifier may be weaker than the baseline.

The benchmark could also become artificial if every derivation contains exactly one conveniently parseable injected error.

**(c) Can a judge reproduce the evaluation cleanly?**

The fixtures are tiny and offline, but deterministic reproducibility is weaker than advertised. `simplify(lhs-rhs) == 0` is not a complete equivalence test. A timeout or unevaluated expression is “unknown,” not “wrong.”

Reproduction is credible only with a restricted expression grammar, explicit symbol assumptions, explicit dimensions, fixed timeouts, and a three-way verifier result: equivalent, inconsistent, or unresolved. The expected first-broken-step labels should be stored independently of the agent.

**(d) Is the user and bottleneck story honest?**

The student story is honest. The manuscript-author story is not, unless the supported notation becomes vastly broader. Researchers will not rewrite a manuscript into a constrained CAS dialect merely to use a lightweight checker.

The honest product is a guided checker for structured mechanics or electromagnetism exercises.

**(e) What should be cut?**

Cut:

- Arbitrary LaTeX.
- Manuscript auditing.
- Vectors and tensors.
- Integrals requiring identities or boundary assumptions.
- Multiple simultaneous errors.
- Automatic inference of physical dimensions.

Accept a small markdown/JSON derivation format with declared symbols, assumptions, and units. Support scalar algebraic steps and perhaps elementary derivatives. Preserve “unresolved” rather than hallucinating an error.

### Idea 4 — Paper-Figure Reproduction Agent

**(a) What breaks first in 2.5 days?**

Case curation, immediately. Ten papers mean ten environments, ten dependency histories, ten data-provenance stories, ten sets of ambiguous methodological choices, and ten different definitions of “matching.” One broken package or dead data link can consume the remaining event window.

Even one paper can require large datasets, GPU code, proprietary preprocessing, an obsolete compiler, or manual interpretation that the paper never documented.

**(b) Is the baseline credible or a strawman?**

No baseline is actually specified. “A human follows the paper” is difficult to implement, time, and compare fairly. A one-shot LLM asked to reproduce a paper would be an obviously weak baseline because the task inherently requires tools, code execution, and data access.

Without a concrete baseline, measured improvement is likely to collapse into a demo narrative.

**(c) Can a judge reproduce the evaluation cleanly?**

No. Live paper links, repositories, package registries, and datasets are exactly the flaky external dependencies the qualification gate punishes. Shipping all environments and data is incompatible with the 50 MB ZIP cap.

Figure similarity is also fuzzy: pixel distance penalizes harmless styling, while a loose visual rubric can miss numerically wrong results.

**(d) Is the user and bottleneck story honest?**

The reproducibility crisis is real, but it is too broad to serve as a product definition. Researchers do not merely need an agent to run code; they need missing data, undocumented preprocessing, compatible environments, and scientific judgment recovered. The proposed workflow cannot honestly guarantee that.

**(e) What should be cut?**

Cut the paper-level claim entirely. Reduce it to one controlled scientific notebook or codebase with ten seeded reproduction failures and deterministic scientific invariants. At that point it is a notebook-repair benchmark, not a paper-reproduction agent—and that narrower version is proposed below.

### Idea 5 — Gravitational-Wave Event Detection Agent

**(a) What breaks first in 2.5 days?**

Native Windows installation and data handling.

PyCBC and the LIGO software ecosystem have compiled dependencies and are far less predictable on native Windows than NumPy/SciPy. A solution that silently requires WSL or Conda weakens clean reproduction. GWpy, HDF5, FFT libraries, waveform generation, and PSD estimation create a much larger setup surface than Idea 1.

Short clips are small enough to ship but may be scientifically inadequate for PSD estimation and whitening. Longer 4 kHz segments across ten cases can exceed the archive budget. Cropping around a known event risks leaking the label and making detection trivial.

**(b) Is the baseline credible or a strawman?**

The brief does not define it. A spectrogram threshold would be a strawman; a matched filter supplied with the correct event template would be overly advantaged. A credible baseline needs a fixed template bank, fixed whitening procedure, and fixed SNR threshold.

If the advanced agent merely changes the template after being told which event family it is examining, the comparison is contaminated.

**(c) Can a judge reproduce the evaluation cleanly?**

Not reliably with live GWOSC downloads or a full PyCBC stack. Known catalog events provide positive labels, but arbitrary off-source segments are not guaranteed signal-free. Negative examples should be controlled noise or fixed injection datasets.

A NumPy/SciPy-only implementation using pre-whitened, downsampled clips would be more reproducible, but it would no longer represent a realistic search pipeline.

**(d) Is the user and bottleneck story honest?**

“Students learning the pipeline” is a valid educational user, but it is not a strong recurring productivity bottleneck. Actual gravitational-wave searches use mature pipelines and large-scale infrastructure; this hackathon project would not replace them.

The honest value is an interactive teaching and diagnostic tool for small, preselected segments.

**(e) What should be cut?**

Cut:

- Native PyCBC unless it is already installed and validated.
- Live GWOSC fetching.
- Full template-bank searches.
- Multiple detectors and sky localization.
- Claims resembling production event detection.
- Audio generation until evaluation is complete.

The surviving NumPy tutorial version is reproducible, but it offers little advantage over the safer exoplanet idea. I would walk away.

### Idea 6 — Orbital-Dynamics Stability Agent

**(a) What breaks first in 2.5 days?**

Ground-truth definition. “Stable” depends on integration duration, integrator, timestep, collision policy, ejection threshold, and the particular perturbation. A system can look stable over the chosen horizon and diverge later.

REBOUND is a compiled extension. It may install smoothly from a wheel, but an unsupported Python/Windows combination can require a C toolchain. Agent-generated simulation code also needs safe execution, timeouts, and limits.

**(b) Is the baseline credible or a strawman?**

A one-shot REBOUND script is credible, but common two-body and Solar System examples are easy for current models. If scenarios are already supplied as structured masses and orbital elements, a deterministic constructor is a stronger baseline than an LLM.

If the advanced agent receives analytic sanity checks or expected invariants that the baseline does not, those additional resources must be disclosed as the actual intervention.

**(c) Can a judge reproduce the evaluation cleanly?**

The data footprint is excellent, but runtime and platform reproduction are only moderate. Long chaotic integrations can vary with numerical tolerances and take too long. Orbit animations add rendering dependencies without improving the evaluation.

Energy conservation is not ground truth for correct setup. A completely wrong system can conserve its own energy beautifully. Conservation tests only validate numerical integration, not whether the described physical scenario was encoded correctly.

**(d) Is the user and bottleneck story honest?**

Simulation-setup mistakes are real. The “astro students and educators” framing is plausible, although it describes an educational aid more than a high-value recurring workflow.

The final artifact becomes genuinely useful if it reports the translated initial conditions, unit system, integration choices, conservation evidence, and limitations—not merely “stable” or “unstable.”

**(e) What should be cut?**

Cut:

- General free-form scenarios.
- Long-term chaos claims.
- Large-N systems.
- Literature-dependent stability labels.
- Production animation.
- Any scenario whose expected result is based only on the project author’s intuition.

Restrict the benchmark to a few analytically understood families: two-body ellipses, escape trajectories, simple Hill-stability violations, and perhaps one short resonance case. Score setup correctness separately from integration health.

## Special stress-test: Idea 1 (exoplanets)

### Ways it fails or underwhelms

1. **The fixtures exceed the archive budget.** Full FITS files across multiple sectors add up quickly. Target-pixel files needed for centroid motion are much larger. Git LFS or a download script does not solve clean offline reproduction.

2. **The fixtures become scientifically misleading after trimming.** Cropping tightly around transits leaks their location. Aggressive binning erases ingress/egress shape and short events. Removing gaps or bad cadences makes detrending artificially easy.

3. **Long-period planets do not fit the scope.** A short cached window may contain one transit, while BLS period recovery requires repeated events. Restricting the set to short-period planets is necessary but reduces breadth.

4. **`lightkurve` becomes dependency ballast.** Runtime archive querying is unnecessary once the arrays are cached. Its dependency tree increases installation time and version risk without improving the submitted evaluation.

5. **TLS creates avoidable Windows pain.** `numba`/`llvmlite` compatibility and compilation-related failures are an unacceptable risk this late. The project does not need two period-search libraries.

6. **Centroid vetting is falsely advertised.** A one-dimensional flux array contains no centroid evidence. Including a “centroid sanity” checkbox without target-pixel data would be scientifically dishonest.

7. **Negative labels are fuzzy.** “No confirmed planet” is not equivalent to “no transit.” A catalog snapshot can establish confirmed planets and known false positives, but not quiet-star negatives.

8. **Catalog truth can leak into the agent.** Target identifiers, known periods, dispositions, or recognizable names must not enter the workflow prompt. Ground truth belongs only in the evaluator.

9. **Harmonics make the metric ambiguous.** Eclipsing binaries frequently produce half-period or double-period peaks. The evaluator must state whether those are accepted for detection and whether correct physical-period resolution is part of the required result.

10. **The baseline is easy to manipulate.** A baseline with no detrending or absurd default period bounds will look bad for the wrong reason. A properly configured one-pass BLS may already recover most obvious planets.

11. **The advanced gain may be tiny.** Obvious planets are easy, while difficult low-SNR planets may remain impossible. The best opportunity for improvement is false-positive rejection, not raw recovery.

12. **The benchmark may be visibly curated for success.** Selecting targets after running both systems undermines the comparison. Case IDs and success rules must be frozen before final tuning.

13. **F1 hides multiple tasks.** Detecting an event, recovering its period, and classifying it as planet-like are different outcomes. One F1 number can obscure whether the system merely finds periodic dips.

14. **Free-form agent decisions reduce repeatability.** Letting the LLM invent detrending windows or thresholds can create run-to-run variation and scientifically indefensible choices.

15. **The agent may be only a wrapper around BLS.** BLS finds the periodic signal. Odd/even and secondary-eclipse statistics can be deterministic functions. An LLM that reads those numbers and writes prose is not the main scientific engine.

16. **The polished report may overclaim.** The output must say “planet-like transit candidate,” “likely eclipsing binary,” “null,” or “insufficient evidence.” It must never assert that a planet has been confirmed.

17. **The real user already has better tooling.** Professional TESS pipelines already compute many of these diagnostics. The project must be positioned as small-batch evidence synthesis or education, not as a replacement for mission vetting infrastructure.

### Where the agentic part is genuine

The agent adds genuine value when it:

- Chooses between a small, predeclared set of detrending strategies using diagnostics rather than truth.
- Notices that the strongest BLS peak is a likely harmonic and requests a targeted alternative fold.
- Orders additional tests based on conflicting evidence.
- Retries within a fixed budget after a verifier reports insufficient transits or excessive residual structure.
- Distinguishes failure to detect from evidence of absence.
- Abstains when diagnostics disagree.
- Produces a trace connecting each verdict to numeric evidence.

This value must be demonstrated through cases with different trajectories and through an ablation showing that case-adaptive decisions improve results.

### Where the agentic part is decoration

It is decoration when:

- BLS computes the candidate and a fixed threshold determines the label.
- Every case runs the same tools in the same order.
- The LLM only turns a JSON result into prose.
- “Self-reflection” repeats the same computation without new evidence.
- The model is permitted to override failed numeric checks based on intuition.
- A deterministic decision tree would be simpler, faster, and more reliable.

The project should acknowledge that deterministic signal-processing tools do most of the scientific work. The agent’s claimed contribution is bounded orchestration and evidence-aware abstention.

### Maximally strong 2.5-day version

Build an **offline TESS threshold-crossing-event vetting agent**, not a general exoplanet discovery system.

- **User:** A student or small astronomy team vetting a preselected batch of transit-like signals.
- **Fixtures:** Ten compressed one-dimensional arrays containing only time, normalized flux, uncertainty, and quality flags. Target a total fixture size below 10 MB.
- **Cases:** Four confirmed short-period planets, three cataloged eclipsing-binary/false-positive cases, two synthetic no-transit controls created from real residual noise, and one adversarial variable-star or half-period alias case.
- **Ground truth:** An immutable JSON snapshot with provenance. It is read only by the evaluator.
- **Baseline:** One fixed quality mask, one reasonable detrending configuration, one BLS search, top peak, fixed SNR threshold, and a simple planet-like/null decision.
- **Advanced workflow:** Data-quality audit; bounded choice between two detrenders; BLS candidate list; harmonic resolution; odd/even and secondary-eclipse checks; duration/depth sanity; one targeted retry; evidence reconciliation; explicit abstention.
- **Primary metric:** Case pass rate. A planet case passes only when the class is correct and its physical period is within a predefined tolerance. False-positive and null cases pass only with the correct disposition.
- **Secondary metrics:** Classification macro-F1, median planet-period error, abstention count, runtime, and per-case cost.
- **Packaging:** No FITS, target-pixel files, Lightkurve, TLS, or live downloads in the main evaluation path. Use pinned Python 3.11, NumPy, SciPy, Astropy BLS, and Matplotlib.
- **Output:** A folded-light-curve plot, compact diagnostic panel, machine-readable verdict, and cautious human-readable report.
- **Agent design:** One principal agent invoking deterministic tools through a strict schema. It cannot access target names or catalog labels.
- **Required ablation:** Remove case-adaptive harmonic/detrending decisions and measure the result. This is necessary to answer the “BLS wrapper” criticism.
- **Removed experiment:** A free-form self-reflection retry or TLS path that is removed because it adds cost or nondeterminism without measurable improvement.
- **Hard kill test:** Do not commit unless a clean machine can install the pinned environment, evaluate all ten cached fixtures, and demonstrate at least two naturally occurring advanced-over-baseline recoveries within the first few hours.

That version is small enough to finish and strong enough to defend. Anything broader is likely to become a half-working astronomy pipeline with weak evidence.

## Codex counter-proposals

I believe the following two ideas beat most of the original set on the section-16 filters. The first also challenges Idea 1 directly by retaining real astronomy while eliminating large fixtures and fuzzy negative labels.

### Counter-proposal A — Astronomical Catalog Cross-Match Audit Agent

**One-liner:** Given two small astronomical catalogs, the agent produces a defensible cross-match after resolving coordinate units, reference frames, epochs, proper motion, match radius, and ambiguous neighbors.

- **User:** An astronomy graduate researcher or research assistant combining a follow-up target list with a Gaia-like reference catalog.
- **Bottleneck:** Naive nearest-neighbor matching silently produces wrong identities when catalogs use different epochs, coordinate conventions, uncertainties, or source densities. Diagnosing those failures requires repeated metadata inspection and residual analysis.
- **Baseline:** Interpret RA/Dec using declared columns, assume a common epoch, apply a fixed one-arcsecond nearest-neighbor match, and accept the closest candidate.
- **Advanced workflow:** Inspect schema and catalog cards; normalize units and frames; propagate coordinates when proper motion and epochs are available; estimate an appropriate bounded search radius from uncertainties; generate candidates; enforce mutual or one-to-one consistency; inspect separation residuals; flag ambiguity; retry a changed assumption only when a verifier identifies a specific inconsistency; produce a matched table and audit report.
- **Primary metric:** Pairwise match F1 against hidden entity identities.
- **Secondary metrics:** Incorrect automatic-match rate, ambiguity recall, number of unjustified assumptions, runtime, and cost.
- **Evaluation:** Ten tiny catalog-pair fixtures. Cases cover ordinary matching, radians-versus-degrees, sexagesimal coordinates, epoch shift, high proper motion, duplicate candidates, missing uncertainty, frame conversion, sparse no-match objects, and a crowded field.
- **Adversarial case:** A high-proper-motion object crosses close to another source between epochs. Raw nearest-neighbor matching chooses the wrong identity; epoch propagation and one-to-one checks recover the correct match or abstain.
- **Verification:** Hidden stable entity IDs generated before coordinate transformations; independent Astropy coordinate calculations; one-to-one constraints; numeric separation bounds; no subjective scoring.
- **Reproduction:** CSV/JSON fixtures well below 1 MB, fixed seeds, no network, and a pinned Python 3.11 environment using Astropy, NumPy, and optionally Pandas. Include a fixture generator so every transformation is inspectable.
- **Useful artifact:** A match table with confidence/ambiguity fields plus an audit describing transformations, assumptions, residuals, and rejected candidates.
- **Why it beats several originals:** It has tiny fixtures, exact labels, an honest astronomy bottleneck, a credible baseline, fast evaluation, and no questionable “quiet star” or long-term stability ground truth.
- **What could kill it:** Judges may see it as an Astropy wrapper. It survives only if cases require genuinely different plans and an ablation shows that metadata interpretation, epoch handling, and ambiguity checks materially improve the baseline. The agent must flag missing metadata rather than guess units from numerical ranges.

### Counter-proposal B — Scientific Notebook Recovery Agent

**One-liner:** An execution-grounded agent repairs small computational-physics notebooks and proves that the repaired result satisfies both software tests and scientific invariants.

- **User:** A computational-physics student or researcher whose previously working analysis notebook has broken after a parameter, dependency, or dataset-schema change.
- **Bottleneck:** One-shot code suggestions often fix the exception while leaving a scientifically wrong calculation. Users repeatedly execute cells, inspect intermediate values, compare conservation laws or analytic limits, and repair downstream assumptions.
- **Baseline:** Give the same notebook, task description, and allowed dependencies to an LLM once; apply its proposed patch; execute the notebook once; score the result.
- **Advanced workflow:** Execute cell by cell in an offline subprocess; classify runtime versus scientific failures; inspect only relevant cells and outputs; make a minimal patch; rerun from a clean kernel; invoke domain-specific invariant checks; retry within a fixed budget; return the repaired notebook, diff, and verification report.
- **Primary metric:** Notebook recovery rate—the fraction of notebooks that execute cleanly and pass all independent scientific invariants.
- **Secondary metrics:** Runtime-only pass rate, regression count, changed-line count, retries, cost, and human-review flags.
- **Evaluation:** Ten small notebooks covering projectile motion, harmonic oscillation, orbital energy, numerical integration, diffusion, Fourier analysis, pendulum dynamics, a two-level quantum system, dimensional conversion, and curve fitting.
- **Adversarial case:** A notebook executes and produces a plausible plot but treats degrees as radians or uses the wrong sign in a conserved-energy expression. Runtime checks pass; an analytic-limit or conservation invariant catches it.
- **Verification:** Separate test modules compare numerical outputs with analytic solutions, conservation tolerances, dimensional expectations, and seeded reference arrays. The evaluator, not the agent’s prose, determines success.
- **Reproduction:** Tiny notebooks and fixtures, fixed seeds, headless Matplotlib, no network, pinned NumPy/SciPy/Matplotlib/`nbclient` versions, strict subprocess timeouts, and an exact evaluation command.
- **Useful artifact:** A repaired notebook a scientist can inspect, accompanied by a minimal diff and evidence that the scientific result remains valid.
- **Why it beats several originals:** The execution–diagnosis–repair loop is unmistakably agentic, the baseline gap should be measurable, fixtures are tiny, verification is programmatic, and before/after plots make a clear demo.
- **What could kill it:** It may look like generic code repair wearing a physics costume. The benchmark must emphasize scientific invariants that ordinary unit tests miss. Executing generated code also requires a fixed offline fixture set, blocked networking, timeouts, and explicit documentation that arbitrary untrusted notebooks are outside scope. Jupyter kernel management on Windows must pass an early clean-install test.

## Codex stack-rank

1. **Counter-proposal A — Astronomical Catalog Cross-Match Audit Agent:** Best combination of authentic astronomy, tiny offline fixtures, exact ground truth, credible baseline, and achievable case-dependent orchestration.
2. **Idea 1 — Exoplanet Transit-Recovery Agent, maximally scoped:** Highest demo and learning upside, but only after removing live data, TLS, centroid claims, and fuzzy negative labels.
3. **Counter-proposal B — Scientific Notebook Recovery Agent:** Strongest generate–execute–verify–repair loop, offset by the risk that judges perceive it as generic code repair rather than a science workflow.
4. **Idea 2 — Spec-to-Quantum-Circuit Agent:** Excellent deterministic verification and packaging, but textbook baseline saturation and specification ambiguity threaten measured improvement.
5. **Idea 6 — Orbital-Dynamics Stability Agent:** Attractive visuals and offline computation, but “stability” ground truth is horizon-dependent and conservation does not verify correct scenario translation.
6. **Idea 3 — Physics Derivation Auditor:** Small and reproducible after severe grammar restrictions, but LaTeX parsing, symbolic undecidability, and a text-heavy demo constrain its ceiling.
7. **Idea 5 — Gravitational-Wave Event Detection Agent:** Excellent spectacle, but native Windows dependencies, data volume, PSD requirements, and unclear baseline make it unjustifiable in this window.
8. **Idea 4 — Paper-Figure Reproduction Agent:** Perfect thematic narrative and the worst execution risk; it fails the ten-case, clean-reproduction, objective-metric, and 2.5-day filters simultaneously.

**Recommended pick:** Counter-proposal A, the astronomical catalog cross-match audit agent. It has the cleanest qualification-gate story without abandoning real astronomy.

**Condition for switching:** Switch to the tightly scoped exoplanet project only if it passes an immediate feasibility kill test: ten offline fixtures below roughly 10 MB, a successful clean Python 3.11 installation, full evaluation in a practical runtime, defensible labels for every case, and at least two non-cherry-picked cases where the advanced workflow beats a reasonably configured BLS baseline.