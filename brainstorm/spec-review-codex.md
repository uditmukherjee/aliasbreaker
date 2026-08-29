# Codex Plan-Gate Review — AliasBreaker Spec v1

## Verdict

**NEEDS-REWORK.** AliasBreaker remains a strong direction, but this specification is not safe to implement unchanged. The largest problems are an evaluation set conditioned on hidden truth and baseline performance, an undefined and potentially vacuous “relative likelihood ≥ 0.9” rule, confounded arm comparisons, fragile six-parameter fitting from roughly eight measurements, and a recorded-replay claim that does not yet establish trace provenance. A skeptical judge’s first attacks will be “the benchmark was manufactured to produce the claimed gain” and “the LLM merely chooses an option already scored by deterministic code.” Lock a defensible evaluation protocol, simplify or harden the physics, and design the evidence package before implementation.

## Findings

1. **Severity:** Critical  
   **Where:** §§3, 6, 9  
   **Issue:** Candidate sets are derived from the hidden true period, forced to contain the true orbit, and then cases are retained only if adaptivity beats batch on at least 3 of 12. That is outcome-conditioned benchmark construction. The proposed “difficulty knobs” make it easy—even unintentionally—to manufacture the desired improvement.  
   **Suggested fix:** Separate development and final evaluation. Build candidates from initial observations alone using a documented period-search procedure, or explicitly define the benchmark as conditional on a supplied candidate set. Use hidden truth only for simulation and scoring. Calibrate on development cases, then generate and freeze a fresh evaluation manifest using arm-independent criteria. Never filter final cases according to which policy wins.

2. **Severity:** Critical  
   **Where:** §6, primary metric  
   **Issue:** “Relative likelihood ≥ 0.9” is undefined. If it means likelihood relative to the best candidate, the winner always has value 1 and the threshold is vacuous. If it means normalized `exp(-Δχ²/2)` over candidates, it is candidate-set-dependent support, not a calibrated probability that the orbit is correct. Refitting parameters, optional stopping, incomplete candidate coverage, and priors further invalidate calling it confidence.  
   **Suggested fix:** Define the exact formula and call it normalized candidate support, not confidence. Compute it independently of the LLM. Calibrate the decision threshold by running the complete selection-and-stopping procedure over a large independent synthetic calibration set, and report its false-resolution rate. Do not choose 0.9 merely because it sounds conservative.

3. **Severity:** High  
   **Where:** §§3, 8  
   **Issue:** Roughly eight initial observations are insufficient for an unconstrained Keplerian fit with period, eccentricity, amplitude, phase/periastron time, argument of periastron, and systemic velocity. Comparable χ² values may reflect near-zero degrees of freedom and overfitting rather than genuine alias ambiguity. Reported parameter uncertainties will be especially unreliable.  
   **Suggested fix:** For the MVP, use circular orbits with fixed candidate periods and linear fits for `γ`, sine, and cosine coefficients. If eccentricity is essential, increase the number of initial observations, constrain priors/bounds, keep equal parameter dimensions across candidates, and validate identifiability. Report within-alias parameter uncertainty separately from between-alias uncertainty.

4. **Severity:** High  
   **Where:** §§3, 10, R3  
   **Issue:** “Our own” Newton Kepler solver and an unspecified nonlinear refitter are unnecessary correctness risks under a two-day deadline. Newton iteration needs robust initialization, angle reduction, convergence limits, high-eccentricity handling, and correct quadrant conversion from eccentric to true anomaly. The spec tests only easy limits.  
   **Suggested fix:** Either remove eccentricity for v1 or use a tested numerical routine. If retaining the implementation, add residual-based convergence checks, safeguarded fallback, randomized property tests across the supported eccentricity range, comparison against an independent reference implementation, and end-to-end recovery tests. Specify the optimizer, bounds, initialization grid, tie-breaking, and failure behavior.

5. **Severity:** High  
   **Where:** §3, candidate construction  
   **Issue:** The alias-family description is too loose. `1/P ± k/day` can generate negative frequencies, duplicates, aliases outside the search domain, and candidates that would never appear in a periodogram. “Harmonics” are not interchangeable with daily sampling aliases. Refitting can also cause candidate basins to cross, making “the true candidate” ambiguous.  
   **Suggested fix:** Define aliases in frequency space with valid bounds, de-duplicate within a stated tolerance, and derive candidate peaks from the sampling window and initial-data periodogram. Anchor each candidate to a non-overlapping period basin and score recovery by basin or period tolerance, not a mutable candidate ID. Randomize neutral candidate labels and ordering.

6. **Severity:** High  
   **Where:** §3, noise model  
   **Issue:** “Deterministic noise” establishes fairness but says nothing about statistical honesty. The distribution, uncertainty supplied to the fitter, heteroscedasticity, stellar jitter, correlated noise, and outliers are unspecified. White Gaussian noise would be acceptable for scope, but only if explicitly acknowledged as an idealized benchmark.  
   **Suggested fix:** Declare the complete generative model and units: measurement variance, whether errors vary by slot, jitter treatment, independence assumptions, and initial-observation noise. Store realized potential outcomes in fixtures rather than depending on cross-version RNG behavior. Include at least one arm-independent stress case with an outlier or variance mismatch, or explicitly defer both and limit the claims.

7. **Severity:** Critical  
   **Where:** §6, abstention scoring  
   **Issue:** “Constructed-equivalent” is not a scoring definition. Mixing successful resolutions and correct abstentions into one resolution-rate metric creates gaming incentives, especially if the equivalent cases have recognizable construction signatures. Other accidentally unresolvable cases are not addressed.  
   **Suggested fix:** Define resolvability before policy execution using an oracle diagnostic, such as the best legal six-slot design under the simulator and a predeclared evidence criterion. Keep labels hidden from all arms. Report resolution rate on resolvable cases and unsafe-resolution/abstention behavior on unresolvable cases separately, or define a fixed decision-utility score with an explicit penalty for confidently wrong answers.

8. **Severity:** High  
   **Where:** §§3, 5  
   **Issue:** The environment does not specify chronological execution. An adaptive agent could observe at night 80 and then select night 40 using information from the future. The status of weather is also incoherent: real future weather is not a known mask.  
   **Suggested fix:** Implement a state machine that only exposes future legal slots after the current time, enforces monotonic observation time, and rejects illegal/repeated slots without leaking measurements. Rename the known mask “observatory availability,” or model weather as an availability event revealed only when its date arrives. Define whether a failed weather opportunity spends budget.

9. **Severity:** Critical  
   **Where:** §§4–6  
   **Issue:** The three arms do not yet have an enforceable information contract. “Same fitter, verifier, noise, and slots” is insufficient. The LLM appears to receive candidate weights, complete predicted curves, and pairwise diagnostics, while the deterministic policies are described only by a vague score. Verdict, confidence, early stopping, and abstention rules also differ.  
   **Suggested fix:** Define a common observation-state schema and an independent evaluator. At each corresponding state, every eligible arm must have access to the same candidates, legal-slot metadata, measurements acquired so far, predictions, and uncertainty information. List every intentional difference in information, computation, calls, time, and budget.

10. **Severity:** High  
    **Where:** §4, baseline  
    **Issue:** “Selects all 6 upfront by greedy prior-weighted discrimination” is not precise enough to establish a strong baseline. Taking the six highest individual scores would repeatedly target the same candidate pair and would be a strawman.  
    **Suggested fix:** Specify a nonadaptive greedy set-design algorithm that chooses each additional slot by marginal gain to the entire six-slot plan, with deterministic tie-breaking. An expected entropy-reduction, pair-coverage, or D-optimality objective would be credible. Preserve the simple evenly spaced schedule only as an extra contextual baseline if time permits.

11. **Severity:** High  
    **Where:** §4, observations-used comparison  
    **Issue:** The batch arm always books six observations while the advanced arm can stop early. This structurally guarantees an efficiency advantage, independent of intelligent scheduling. Whether booked observations can be cancelled is a user-domain question, not a metric detail.  
    **Suggested fix:** Either give every arm the same deterministic stopping and verdict rule while varying only slot selection, or state that batch reservations cannot be recovered and do not compare “observations used” as if execution resources were equal. A clean factorial comparison is: scheduling policy, stopping policy, and verdict policy measured separately.

12. **Severity:** High  
    **Where:** §§4–5  
    **Issue:** `evaluate_discrimination` risks solving the central decision before the LLM sees it. If the tool returns a ranked best slot, the agent is an expensive argmax wrapper. Conversely, if the scripted adaptive arm uses a deliberately myopic score, it becomes a weak foil created to make LLM planning look strategic.  
    **Suggested fix:** Make the deterministic tool return auditable diagnostics—pairwise separations, candidate weights, and future-window scarcity—rather than a single recommended action. Predefine the scripted policy completely. Demonstrate that the LLM contributes a specific capability such as multi-pair coverage, reservation of scarce future windows, confirmation planning, or calibrated abstention.

13. **Severity:** High  
    **Where:** §§4, 5, R2  
    **Issue:** The final “advanced solution” is not defined if the LLM loses to the scripted adaptive arm. An honest negative finding can earn Hot Take points, but it weakens the 30-point Agent Solution category and may leave no demonstrated agentic improvement.  
    **Suggested fix:** Define the advanced workflow as a hybrid with deterministic estimation and verification plus LLM control over the genuinely strategic decisions. Predeclare which comparison supports the main improvement claim. Keep the scripted adaptive arm as an ablation and report it even if it wins; do not retrofit the benchmark or omit the result.

14. **Severity:** High  
    **Where:** §§5–6  
    **Issue:** The LLM supplies its own confidence, creating a direct gaming path. It can assert 0.9 without statistical basis, and the verifier requirement only says the verdict must cite a Δχ² table.  
    **Suggested fix:** Remove agent-provided confidence from scoring. The independent evaluator must calculate support, validate the cited evidence, and accept or reject the verdict. The LLM may provide a clearly labeled qualitative rationale, but it cannot control the numerical eligibility threshold.

15. **Severity:** High  
    **Where:** §6  
    **Issue:** The primary comparison, aggregation rule, and uncertainty analysis are missing. Twelve cases are paired; three LLM runs on each case do not create 36 independent cases. Reporting the best run would be invalid, and a three-case swing can dominate the headline.  
    **Suggested fix:** Predeclare the headline comparison, aggregation, and treatment of API failures. Report every case and repeat, the mean over repeats per case, the paired difference versus baseline, and a case-clustered bootstrap interval or an appropriately cautious exact summary. Do not claim statistical significance that this sample cannot support.

16. **Severity:** Medium  
    **Where:** §6, N=3 policy  
    **Issue:** “Run N=3 and report all runs” does not define sampling or retries. Temperature zero is still not guaranteed deterministic, provider-side seeds may be unsupported, and rerunning failed or unattractive outputs until three good traces remain would bias results.  
    **Suggested fix:** Assign three replicate IDs before execution, fix all available model parameters, and preserve the first valid provider response for each replicate. Predeclare retryable transport errors separately from model/protocol failures. Count exhausted retries as failures and publish all attempts and costs.

17. **Severity:** Critical  
    **Where:** §§6, 9  
    **Issue:** Freezing cases “before final runs” is too late if the cases have already influenced prompts, tools, thresholds, or baseline design. The kill test explicitly tunes difficulty using policy performance.  
    **Suggested fix:** Maintain clearly separated development and final-evaluation fixtures. Freeze the generator version, metric, prompt, tool schemas, policies, case manifest, and hashes before observing any final arm outcomes. Record the freeze in version control. After the freeze, only correctness fixes are allowed; any change requires rerunning every arm and documenting it.

18. **Severity:** Critical  
    **Where:** §7, recorded replay  
    **Issue:** Replay proves that recorded actions are legal and that their scores recompute; it does not prove the LLM originally produced those actions. A locally generated hash chain can also be regenerated after editing. Calling replay a full reproduction path overstates what judges can verify.  
    **Suggested fix:** Call it an “audit replay.” Store the raw model response metadata, request IDs where available, prompts, tool exchanges, timestamps, token usage, fixture hash, code commit, and an append-only manifest. Use a publicly timestamped commit or CI artifact for the official run. The replay command must recompute measurements and metrics, reject impossible or altered actions, and disclose that provenance ultimately still relies on the recorded provider output.

19. **Severity:** High  
    **Where:** §7  
    **Issue:** “Python 3.11 + NumPy pinned” is not adequate versioning. RNG sequences, floating-point optimization, BLAS behavior, JSON precision, and model snapshots can differ across platforms. An Anthropic model ID may not guarantee immutable behavior.  
    **Suggested fix:** Pin Python patch version, NumPy and SDK versions, and package hashes where practical. Store generated observations and candidate inputs directly in versioned fixtures with schema and content hashes. Use tolerance-based result checks. Record the exact reported provider model version and state clearly that live outputs may vary.

20. **Severity:** High  
    **Where:** §§5, 7  
    **Issue:** Runtime trajectory logging omits several required elements: complete task input, raw assistant responses, retries, error recovery, model metadata, human checkpoints, and evidence of coding-agent use. It also lacks a redaction policy.  
    **Suggested fix:** Define a trajectory schema containing prompt/version, case and fixture hashes, assistant messages, tool calls and responses, invalid calls, retries, stopping decisions, final output, token/cost metadata, and harness version. Include representative development trajectories for Claude/Codex as well as runtime-agent traces. Strip credentials, headers, private paths, and unrelated personal data.

21. **Severity:** High  
    **Where:** §5  
    **Issue:** API and protocol failures are unspecified. The agent can omit a verdict, issue malformed JSON, exceed the observation budget, loop, choose an illegal slot, or call tools after submission. Silent harness recovery could materially improve its apparent reliability.  
    **Suggested fix:** Specify a finite-state protocol, maximum tool turns, schema-repair allowance, transport retry policy, timeouts, invalid-action handling, terminal states, and scoring for noncompletion. Log every recovery. Test these paths explicitly.

22. **Severity:** High  
    **Where:** §2  
    **Issue:** “Astronomer (or astronomy student / small-observatory scheduler)” is not a precise user. Those users have different expertise, constraints, and acceptable artifacts. The value and “well-documented” alias problem have no actual references or user-workflow evidence in the spec.  
    **Suggested fix:** Choose one persona, such as an RV observer responsible for allocating six follow-up visits on a small ground-based spectrograph. Cite primary astronomy sources for diurnal aliases and follow-up scheduling, state the decisions the report supports, and avoid claiming professional validation beyond the synthetic benchmark.

23. **Severity:** High  
    **Where:** §§3, 8  
    **Issue:** The synthetic scheduling world is more idealized than the framing admits. Known future weather, arbitrary legal fractional-night slots, fixed precision, no exposure duration, and no airmass or visibility geometry can make the planner’s task unlike real telescope scheduling.  
    **Suggested fix:** Keep the benchmark narrow and disclose each simplification. Use deterministic observatory-availability windows rather than predicted weather, include basic time ordering and visibility constraints, and describe the output as an alias-discrimination campaign in a synthetic observatory—not a validated telescope scheduler.

24. **Severity:** High  
    **Where:** §8  
    **Issue:** The final report is underspecified and partly retrospective. A calendar of observations already taken is not itself an actionable planning artifact. Parameter “uncertainties” and the folded-RV plot are promised without a method or plotting dependency; this conflicts with the claimed NumPy-only stack.  
    **Suggested fix:** Specify a concrete HTML/SVG or PDF report schema containing the campaign log, next recommended action or stop decision, legal-window context, normalized support table, residuals, limitations, and human-review status. Either pin a plotting dependency or implement a deterministic SVG renderer. Omit uncertainties unless they are statistically defensible.

25. **Severity:** Medium  
    **Where:** §6, adversarial cases  
    **Issue:** The off-cadence case may be a theatrical one-step argmax rather than a meaningful adversarial test: the sole separating slot will be obvious after `predict_curves`. One equivalent case is also too little to characterize abstention reliability.  
    **Suggested fix:** Include failures that test distinct mechanisms: a tempting early slot that separates the wrong pair, a scarce future window requiring reservation, a noisy misleading observation requiring confirmation, a near-equivalent case, and an unavailable-window case. Freeze fixed counts by stratum and report results by stratum.

26. **Severity:** High  
    **Where:** §§6–7  
    **Issue:** Resource accounting is incomplete. Wall time and API cost are promised, but human review time, token/tool-call budgets, rate-limit exposure, and different computational budgets across policies are not specified. Observations used can also be misleading if failures are excluded.  
    **Suggested fix:** Record wall time, model tokens, API cost, tool calls, observations attempted and obtained, and estimated human-review time for every arm. Report efficiency over all cases and per successful resolution, with failures retained. Disclose deterministic computation available to each arm.

27. **Severity:** High  
    **Where:** §9  
    **Issue:** The kill test is both statistically weak and strategically dangerous. Requiring three adaptive wins encourages case selection; “a few hours” underestimates physics and fitting work; switching to Circuit Sleuth contradicts the committed direction and would waste the remaining window.  
    **Suggested fix:** Make the kill test a feasibility check only: valid candidate ambiguity, deterministic replay, legal state transitions, and tractable runtime. If headroom is small, simplify within AliasBreaker—prefer the circular-orbit benchmark and a sharper adaptive scheduling task. Do not change domains with less than two days remaining.

28. **Severity:** Critical  
    **Where:** R5 and overall plan  
    **Issue:** The schedule has no execution budget for nonlinear physics debugging, fixture design, three policies, approximately 36 LLM case runs, trace auditing, report rendering, clean-environment reproduction, README, changelog, video, ZIP verification, and upload. Documentation is currently treated as post-build work despite being qualification-critical.  
    **Suggested fix:** Reserve the final 10–12 hours exclusively for clean-run verification, documentation, video, archive testing, and submission. Cut eccentric fitting, fancy visualization, and nonessential UI first. Freeze the official evaluation early enough that all three arms can be rerun once after the last correctness fix.

29. **Severity:** High  
    **Where:** Rubric coverage across §§2, 5, 6, 8  
    **Issue:** As written, the likely score losses are broad: diffuse user and toy realism under Problem/User; a redundant LLM and unspecified fitter/state machine under Agent Engineering; an undefined report under End-to-End Quality; benchmark selection and an uncalibrated metric under Measured Improvement; weak replay provenance under Reproducibility; and a prewritten rather than discovered insight under Hot Take.  
    **Suggested fix:** Make the judge-facing evidence chain explicit: user decision → agent action → acquired observation → deterministic verification → final report → paired metric. Treat “LLM versus heuristic” as a hypothesis. The hot take must come from an observed failure and a documented removed experiment, not from a planned narrative.

30. **Severity:** Critical  
    **Where:** Overall submission planning  
    **Issue:** The spec does not include the mandatory Improvement Changelog, a removed experiment, pre-existing-versus-hackathon disclosure, or a complete safety/compliance section. These are not polish items; they are explicit submission and qualification requirements.  
    **Suggested fix:** Create these artifacts before implementation starts. Log every meaningful experiment as it occurs, preserve one genuinely rejected approach and its evidence, list all pre-existing code/assets and AI-assisted work, and document licenses, synthetic-data provenance, limitations, secret handling, and ownership considerations.

31. **Severity:** High  
    **Where:** §§2, 5, 8  
    **Issue:** The workflow proposes scheduling use but has no human approval boundary. Even though evaluation is simulated, the polished report could be mistaken for a production-ready observation recommendation.  
    **Suggested fix:** Mark all outputs “synthetic benchmark / decision support only.” Do not integrate with a real observatory or submit bookings. Require explicit astronomer review before exporting any plan for real use, include the approval field in reports and trajectories, and expose model/statistical limitations prominently.

32. **Severity:** Critical  
    **Where:** Overall submission package  
    **Issue:** The video, source archive, submission form, and independent clean-run process are not operationally planned. The current video description omits several mandatory elements, including the baseline, improvement changelog, highest-impact change, and removed experiment.  
    **Suggested fix:** Prepare a sub-five-minute script covering all required segments, using a genuine recorded execution. Create and test a source ZIP under 50 MB in a clean directory, verify every documented command, ensure the video URL and repository are judge-accessible, complete the HackerEarth title/description fields, and save a draft well before the deadline.

## Missing requirements checklist

- [ ] A precisely named single user persona and cited evidence for the real bottleneck.
- [ ] A clearly labeled README Improvement Changelog.
- [ ] Evidence for every important iteration, including one genuinely removed experiment.
- [ ] The final observed failure mode and evidence-derived hot take.
- [ ] Disclosure of pre-existing components versus work created during the hackathon.
- [ ] Disclosure of Claude, Codex, and other coding-agent use consistent with individual participation.
- [ ] Complete prompts and representative trajectories for every runtime and development agent used.
- [ ] Trajectory coverage for retries, malformed actions, recovery, tool responses, and human checkpoints.
- [ ] A formal common-information and resource contract for all three arms.
- [ ] A predeclared primary comparison, aggregation rule, failure policy, and uncertainty analysis.
- [ ] Human time, runtime, API cost, model tokens, tool calls, and observation usage in the result table.
- [ ] Complete per-case results, including failures and unfavorable LLM repeats.
- [ ] A versioned evaluation manifest, fixture schema, content hashes, and documented freeze commit.
- [ ] A clean-environment reproduction guide with exact setup, baseline, advanced, replay, and evaluation commands.
- [ ] Supported OS/runtime details, expected outputs, approximate runtime/cost, environment variables, and troubleshooting.
- [ ] A second clean reproduction from an independently extracted archive.
- [ ] Tests for physics, refitting, leakage, chronology, budgets, deterministic outcomes, scoring, and replay tampering.
- [ ] Dependency, model, data, and license/terms review plus a repository license.
- [ ] Safety and limitations documentation, including synthetic-only scope and human approval before real scheduling.
- [ ] Trace and archive secret-redaction checks.
- [ ] A report-generation implementation and its pinned visualization dependencies.
- [ ] A five-minute-or-shorter video script covering baseline, live execution, comparison, changelog, key improvement, and removed experiment.
- [ ] Accessible video and repository URLs.
- [ ] HackerEarth title and description.
- [ ] A tested source ZIP below 50 MB.
- [ ] An upload/draft deadline with several hours of contingency before 23:30 IST.

## The three changes with highest leverage

1. **Replace the current kill-test/evaluation process with a frozen evaluation charter.** Define the candidate-building boundary, exact support formula, resolvability oracle, abstention utility, primary comparison, repeat aggregation, and failure policy. Use development cases for calibration and a fresh, arm-independent final set whose manifest and hashes are committed before any final result is viewed.

2. **Simplify and equalize the engineering core.** Use a circular fixed-period RV model with a stable linear fitter unless eccentricity is demonstrably necessary. Put all arms behind one chronological state machine, give them a documented common information surface, implement a genuinely strong joint batch planner, and keep all numerical confidence and verdict scoring outside the LLM.

3. **Build the qualification evidence path before feature work.** Implement tamper-detecting audit replay, complete trajectory manifests, an Improvement Changelog with a real removed experiment, pre-existing-work and safety disclosures, exact clean-run commands, and the required video/archive checklist. Reserve the final 10–12 hours for independent reproduction, video, ZIP verification, and submission.