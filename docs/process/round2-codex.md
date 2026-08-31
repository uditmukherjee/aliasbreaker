# Codex Round 2 — Direction and Fresh Ideas

## Proposed exploration direction

Build a **budgeted active-science agent inside a tiny virtual laboratory**. Each evaluation case is a small generative model with hidden parameters, a menu of legal measurements, and a strict measurement budget. The agent must maintain hypotheses, choose the next experiment, observe the seeded result, update its beliefs, and either diagnose or abstain. This avoids the earlier traps by construction: cases are kilobyte-scale equations and seeds rather than datasets; the simulator supplies exact hidden truth; a one-shot LLM cannot infer unobserved state; and the agent cannot be dismissed as a reporting wrapper because its case-dependent actions determine which evidence exists. Baseline and advanced systems can share the same fitter and verifier, isolating the value of adaptive planning. The scored agent can be a deterministic belief–action–verification controller, with coding-agent use documented separately in development trajectories; no runtime API, model download, native extension, or network access is necessary. Pure Python, action-keyed noise, and JSONL decision traces give genuine offline reproduction on Windows.

## Fresh idea briefs (4–5)

### 1. AliasBreaker — Adaptive Radial-Velocity Follow-Up

**One-liner:** Given several plausible orbital aliases, the agent allocates a limited number of future radial-velocity observations to identify the correct orbit.

- **User:** A small-observatory astronomer or astronomy student planning follow-up observations after sparse measurements produce several plausible periods.

- **Bottleneck:** Telescope visits are scarce. Ordinary nightly or evenly spaced observations can repeatedly sample the same orbital phase, leaving daily and harmonic aliases unresolved.

- **Baseline:** A strong non-adaptive batch planner selects all six future observation times at once by greedily maximizing prior-weighted separation among the candidate curves. After collecting them, the shared fitter selects the lowest-error candidate.

- **Advanced agentic workflow:** The agent begins with the same candidates, feasible observing windows, simulator, fitter, and six-visit budget. After each observation it updates candidate likelihoods, removes contradicted aliases, and chooses the next feasible time where the surviving models disagree most relative to noise and scheduling cost. It can switch from broad discrimination to a targeted periastron observation, reserve a final confirmation visit, stop early when one model is uniquely supported, or abstain when weather windows make the candidates observationally equivalent. Its decisions matter because each chosen time produces different evidence and therefore a different subsequent trajectory.

- **Primary metric:** Correct alias-resolution rate within six added observations. A case passes only if the hidden orbital model is selected uniquely above a fixed confidence threshold; incorrect selections and unresolved abstentions fail.

- **Evaluation design:** Ten frozen systems containing circular and eccentric orbits, daily and harmonic aliases, uneven initial sampling, differing noise levels, and restricted observing windows. The adversarial case has two aliases that agree at every obvious integer-night slot but diverge during one short off-cadence window.

- **Verification mechanism:** The evaluator holds the hidden model ID and scores the selected candidate directly. It also compares the returned orbit against a dense hidden radial-velocity curve. Measurement noise is deterministically keyed by case and time slot, so both policies receive identical evidence whenever they request the same observation.

- **Reproduction story:** Python 3.11 with standard-library `math`, `random`, `json`, and `unittest`; a small Newton solver handles Kepler’s equation. Plots can be emitted as dependency-free SVG. No API, package installation, data fetch, or native binary is required.

- **Estimated fixture size:** Approximately 50–100 KB for all candidate ephemerides, observing windows, seeds, and hidden labels; complete generated traces and SVGs should remain below 2 MB.

- **Demo/video appeal:** Excellent. Show several colored orbital curves overlapping, let the agent place observations one by one, and visibly watch the wrong aliases disappear.

- **Learning payoff:** Keplerian radial velocities, orbital phase, cadence aliasing, likelihood updates, and information-driven telescope scheduling.

- **Improvement evidence:** Freeze the advanced planner’s schedule before its first observation as the principal ablation. A two-step Monte Carlo lookahead is a natural removed experiment if it costs substantially more without resolving additional cases.

- **Single biggest kill risk:** A finite candidate set may let the strong batch baseline saturate, eliminating both the measured adaptive gain and the sense that this represents real orbital inference.

---

### 2. Circuit Sleuth — Active Fault Interrogation

**One-liner:** The agent diagnoses a hidden fault in a known low-voltage circuit by choosing the safest and most informative sequence of meter probes.

- **User:** An electronics repair technician working repeatedly on one board family, or a lab instructor teaching model-based troubleshooting.

- **Bottleneck:** Fixed troubleshooting checklists waste probes and can misdiagnose faults with similar output symptoms. The useful next measurement depends on what previous measurements ruled out.

- **Baseline:** A credible manufacturer-style checklist measures supply, output, and two designated internal test points in a fixed order, then uses the shared forward model to select the closest single-fault hypothesis.

- **Advanced agentic workflow:** The agent enumerates the healthy circuit and allowed open, short, and component-drift hypotheses. At each step it considers legal node-voltage or frequency-response measurements, estimates how robustly each would split the surviving hypotheses under component tolerance, and chooses one subject to probe cost and safety rules. It updates its hypothesis set from the observation, changes excitation frequency only when DC evidence is ambiguous, performs an unused confirmation measurement before committing, and returns an equivalence class rather than inventing certainty when two faults are genuinely indistinguishable.

- **Primary metric:** Exact fault or verified equivalence-class diagnosis rate within four probes, with any unsafe action counted as failure.

- **Evaluation design:** Ten hidden worlds across three small resistor and RC networks: healthy controls, resistor drift, capacitor drift, open connections, shorts, and misleadingly similar output symptoms. The adversarial circuit is symmetric at DC, so two faults remain indistinguishable unless the agent requests an AC phase or magnitude measurement.

- **Verification mechanism:** The evaluator knows the injected fault. A small nodal-analysis engine independently checks Kirchhoff residuals and the diagnosis’s prediction at held-out probes. Exhaustive response comparison establishes which faults truly belong to the same observable equivalence class.

- **Reproduction story:** Pure Python complex arithmetic and Gaussian elimination, pinned to Python 3.11. Analytic divider and RC-filter golden tests validate the solver. Runs offline on native Windows and produces JSONL traces plus dependency-free SVG schematics.

- **Estimated fixture size:** Under 100 KB for netlists, legal probes, fault catalogs, tolerances, seeds, and labels.

- **Demo/video appeal:** Very good. Highlight each selected probe on a circuit schematic while a hypothesis counter falls from, for example, twelve possibilities to one.

- **Learning payoff:** Kirchhoff’s laws, nodal analysis, RC frequency response, component tolerances, observability, and decision-tree diagnosis.

- **Improvement evidence:** Compare the full agent against the same inference engine with the manufacturer checklist. A free-form LLM diagnosis layer is an obvious removable experiment if it adds unsupported explanations or reduces repeatability.

- **Single biggest kill risk:** Small single-fault circuits may admit one nearly perfect fixed probe panel, leaving too little room for adaptive planning to improve the baseline.

---

### 3. Mechanism Lab — Chemical-Kinetics Experiment Designer

**One-liner:** The agent chooses initial concentrations and sampling times that distinguish competing chemical reaction mechanisms under a fixed assay budget.

- **User:** A physical-chemistry student, lab instructor, or bench chemist deciding which small follow-up experiment can discriminate between two or more plausible kinetic models.

- **Bottleneck:** Several mechanisms can fit one standard time course. Repeating the same initial conditions produces more precise data without resolving the underlying ambiguity.

- **Baseline:** Run one conventional equimolar experiment and take evenly spaced concentration readings. Fit every candidate mechanism with the same grid-search fitter and select the lowest-error model.

- **Advanced agentic workflow:** The agent maintains mechanism-and-rate hypotheses, then chooses among bounded virtual interventions such as changing a reactant concentration, adding initial product, or moving sample times earlier or later. After each result it refits the surviving hypotheses, rejects candidates that violate mass balance or fail the observation likelihood, and selects the next experiment where their predicted trajectories diverge most. It finishes with a distinct confirmation condition and abstains if the allowed experiments cannot establish identifiability.

- **Primary metric:** Correct mechanism-family resolution rate within a fixed budget of 24 concentration readings; the selected model must also stay below a predefined error on a hidden validation experiment.

- **Evaluation design:** Ten cases covering first- versus second-order reactions, consecutive versus parallel reactions, reversible reactions, autocatalysis, and different unknown rate regimes. In the adversarial case, a slow reversible reaction is almost indistinguishable from an irreversible reaction during the baseline run; starting with added product exposes the reverse pathway.

- **Verification mechanism:** The evaluator holds the true reaction graph and parameters. A fixed-step RK4 simulator produces action-keyed observations, while mass conservation and hidden-condition prediction provide independent scientific checks.

- **Reproduction story:** Standard-library Python with a deliberately small reaction grammar, fixed timestep, parameter grid, seeds, and numeric tolerances. Analytically solvable first-order cases serve as solver tests. No SciPy, compiled ODE solver, or external chemistry database is required.

- **Estimated fixture size:** Roughly 100–150 KB for mechanisms, action menus, parameter grids, seeds, and truth; generated curves and reports should remain below 2 MB.

- **Demo/video appeal:** Strong. Start with nearly identical concentration curves, let the agent change one initial condition, and show the candidate mechanisms separating dramatically.

- **Learning payoff:** Mass-action kinetics, reaction order, reversibility, parameter identifiability, intervention design, and numerical integration.

- **Improvement evidence:** Ablate concentration interventions while retaining adaptive sample timing to show which form of agency contributes the gain. Temperature selection should be a removable experiment if Arrhenius modeling introduces more ambiguity than useful discrimination.

- **Single biggest kill risk:** Calibrating the reaction simulator, parameter fitting, and numeric tolerances may consume the available build time and still leave the benchmark looking more like toy kinetics than a defensible laboratory aid.

---

### 4. Gravity Scout — Sparse Geophysical Survey Planner

**One-liner:** The agent chooses a small number of surface gravity measurements to locate and characterize a simulated buried ore body or void.

- **User:** A geophysics field-course instructor or an early-stage survey planner designing a sparse reconnaissance transect.

- **Bottleneck:** Uniformly spaced measurements waste limited field time, while depth, density, and size can produce deceptively similar gravity anomalies.

- **Baseline:** Measure six evenly spaced accessible stations, then select the candidate subsurface model with the lowest residual using the shared forward solver.

- **Advanced agentic workflow:** Starting with a prior over finite buried-body hypotheses, the agent selects stations where the surviving gravity profiles disagree most relative to sensor noise and walking cost. It adapts after every measurement, moves to anomaly flanks when the center measurement is ambiguous, preserves an exploration slot so it does not lock onto the first apparent peak, and reports a set of observationally equivalent models when the inverse problem cannot support a unique answer.

- **Primary metric:** Correct hidden-model or accepted equivalence-class identification rate within six stations.

- **Evaluation design:** Ten transects containing positive and negative anomalies, shallow and deep bodies, off-center targets, terrain access gaps, sensor drift, and weak anomalies. The adversarial case pairs a shallow low-density body with a deeper high-density body that matches at the center and coarse-grid locations but differs measurably on one flank.

- **Verification mechanism:** The scorer knows the hidden body parameters and compares the diagnosis against both the ID and a dense untouched gravity profile. An exhaustive comparison over all legal stations defines genuine equivalence classes instead of treating every abstention as failure.

- **Reproduction story:** The forward model for a buried sphere uses only standard-library arithmetic. Python 3.11, fixed action-keyed noise, JSON fixtures, and SVG output give a fully offline Windows run.

- **Estimated fixture size:** Approximately 30–50 KB for all terrain masks, candidate models, seeds, and hidden labels.

- **Demo/video appeal:** Excellent. Animate measurement stations appearing over a geological cross-section while uncertainty over the buried target visibly contracts.

- **Learning payoff:** Newtonian gravity, gravity anomalies, depth–density ambiguity, non-unique inverse problems, survey design, and scientifically honest abstention.

- **Improvement evidence:** Remove the exploration reserve to demonstrate how a purely greedy planner can become confidently wrong. A continuous gradient-based station optimizer is a suitable removed experiment if it is brittle and shows no advantage over the discrete legal grid.

- **Single biggest kill risk:** Restricting the world to one spherical body and a finite hypothesis library may make the workflow look like “twenty questions over curves,” with weak evidence that it transfers to real three-dimensional geophysics.

---

### 5. Spectral Interrogator — Budgeted Mixture Identification

**One-liner:** The agent identifies gases in a mixture by adaptively choosing a handful of wavelength and sensitivity settings on a simulated tunable absorption sensor.

- **User:** An engineer prototyping a low-bandwidth tunable optical gas sensor, or an analytical-chemistry instructor teaching spectral interference.

- **Bottleneck:** When only a few wavelength dwells are affordable, measuring the strongest line of each expected species can fail because interferents overlap, readings saturate, and baseline drift mimics weak absorption.

- **Baseline:** Select all six wavelengths up front using a strong global maximum-variance batch rule, then fit candidate mixtures with the same non-negative concentration grid used by the advanced system.

- **Advanced agentic workflow:** The agent maintains viable species-and-concentration hypotheses and chooses the next wavelength plus detector gain or path-length setting. It balances candidate separation against saturation risk, requests a reference wavelength when readings suggest baseline drift, targets a weak sideband after overlapping primary lines remain ambiguous, and uses an orthogonal confirmation line before committing. If the available channels cannot separate two mixtures, it reports their equivalence instead of forcing a species label.

- **Primary metric:** Mixture recovery rate after six readings: the species set must be correct and every nonzero concentration must fall within a fixed relative tolerance.

- **Evaluation design:** Ten frozen mixtures spanning single gases, two- and three-species mixtures, low concentration, detector saturation, calibration offset, and overlapping bands. The adversarial pair is indistinguishable at the globally strongest wavelengths but separates at a weak sideband that becomes valuable only after the first observations narrow the hypotheses.

- **Verification mechanism:** A Beer–Lambert forward model holds the true mixture and generates deterministic noisy absorbance. The evaluator checks species IDs, concentrations, saturation rules, and error across a dense withheld spectrum.

- **Reproduction story:** Pure Python using a compact JSON line list and an explicitly documented Gaussian/Voigt approximation. All noise, tolerances, and action menus are fixed. SVG spectra and JSONL trajectories require no plotting or scientific package.

- **Estimated fixture size:** Approximately 100–200 KB, dominated by the compact spectral line parameters; all ten cases and golden outputs should remain well under 1 MB.

- **Demo/video appeal:** Very good. Show overlapping spectra, six measurement cursors selected sequentially, saturation avoidance, and the final reconstructed mixture.

- **Learning payoff:** Absorption spectroscopy, Beer–Lambert behavior, spectral interference, detector saturation, calibration references, and active sensing.

- **Improvement evidence:** Compare against both fixed wavelengths and an adaptive agent without gain/path-length control. A free-form continuous wavelength optimizer can be removed if it is unstable or irreproducible relative to the discrete action grid.

- **Single biggest kill risk:** A hand-built spectral line list could undermine the scientific and user-value story; using sufficiently credible real line parameters without introducing data-provenance or modeling scope problems is essential.

## Self-stack-rank

1. **AliasBreaker — Adaptive Radial-Velocity Follow-Up.** Best overall balance of authentic scientific scarcity, tiny exact fixtures, meaningful branching decisions, a compelling five-minute visualization, and substantial astrophysics learning; this is my **top pick**.

2. **Circuit Sleuth — Active Fault Interrogation.** It has the clearest real user and most legible agent trajectory, although a strong fixed probe set could erase the adaptive advantage on small circuits.

3. **Mechanism Lab — Chemical-Kinetics Experiment Designer.** The intervention choices are genuinely scientific and agentic, but numerical fitting and benchmark calibration create the highest implementation risk among the top three.

4. **Spectral Interrogator — Budgeted Mixture Identification.** It is compact, visual, and easy to verify, but its credibility depends heavily on the provenance and realism of the embedded spectral model.

5. **Gravity Scout — Sparse Geophysical Survey Planner.** It offers the simplest offline build and one of the best demos, but the gap between a finite spherical-body benchmark and real geophysical inversion is the hardest user-value objection to answer.

**Top pick: AliasBreaker.** Its core story fits in one sentence—“the agent decides when to look so aliases stop fooling us”—and the same sequential choices simultaneously provide the engineering contribution, evaluation evidence, trajectory narrative, and visual demo.