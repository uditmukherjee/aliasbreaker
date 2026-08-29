# Codex Diff-Gate 2 — Pre-Freeze

## Verdict

**APPROVE-WITH-CHANGES.** The generator’s scan is deterministic in structure and does not consume policy or arm performance, so there is no direct outcome-based cherry-picking. However, this exact revision should not be frozen: oracle labels currently determine admission despite charter §4 saying otherwise; several predicates do not fully establish their named behavior; the ordinary σ mixture is not guaranteed; and top-level stratum metadata creates an avoidable, high-impact leak surface. The production prompt also contains dev-result coaching that should remain in the journal, not the runtime instructions. These are bounded pre-freeze corrections rather than a redesign, so they should be completed without consuming the reserved official-run window.

## Findings

1. **Severity: High, freeze-blocking / File-area: `docs/evaluation-charter.md` §4–5, `src/make_cases.py::classify_stratum` / Issue:** The implementation contradicts the charter’s statement that oracle labels are “never used to filter final cases.” `is_resolvable` sends every oracle-negative case to `unresolvable`, while all other strata require oracle-positive cases. With the declared quotas, the generator deliberately admits exactly ten resolvable and two unresolvable cases. This is arm-independent, but it is still oracle-based selection rather than reporting-only stratification. **Suggested fix:** Resolve the contradiction explicitly before examining final seeds. Given the predeclared unsafe-resolution analysis, the cleanest option is to amend §4–5 to authorize oracle use solely for the exact predeclared 10/2 composition, state the complete quota vector, and prohibit using oracle or arm outcomes to rank or swap cases within a stratum. The alternative is to remove `is_resolvable` from admission and select a structurally defined near-equivalent stratum, accepting whatever oracle mix results. Do not freeze the present text and code together.

2. **Severity: High, freeze-blocking / File-area: `src/make_cases.py::_structure`, `classify_stratum` / Issue:** The named special strata are currently weaker proxies than charter §5 describes.

   - `misleading_obs` tests one residual against fixed initial-fit curves. The matched wrong candidate may already have negligible support, the observation need not make it lead or materially gain support, and no later confirmation capable of reversing the effect is required. It therefore does not establish “supports a wrong candidate until confirmed.”
   - `tempting_early` can be triggered by two effectively dead wrong candidates. That can disproportionately distract an unweighted pair-coverage policy while the LLM prompt explicitly tells the agent to consider `support_product`.
   - `scarce_window` defines “late” by position in the available-slot array and “narrow” only as at most three slots. Those slots can be widely separated in actual time, and the relevant rival need not remain operationally live.

   **Suggested fix:** Define these using shared evaluator/diagnostic computations rather than duplicate approximations. Require a live wrong rival or wrong pair under an exact predeclared support rule. For `misleading_obs`, require an arm-neutral support transition after the early realized outcome and the existence of a later legal confirmation outcome that restores the true candidate. For `scarce_window`, define lateness and maximum window width using `slot_t`, as well as the number of qualifying slots. Predeclare all thresholds before scanning seeds. Hidden truth and potential outcomes are acceptable here; policy actions and results are not.

3. **Severity: Medium / File-area: `src/make_cases.py::QUOTAS`, `gen_final` / Issue:** The ordinary stratum does not guarantee the charter’s mixed-σ requirement. Cycling σ across attempted seeds does not ensure that the four accepted ordinary cases contain all four values. Predicate precedence is deterministic, but when a higher-precedence quota is full, overlapping cases remain classified into that full stratum and are discarded rather than considered for lower strata. That materially defines the selected population and currently appears only in code. **Suggested fix:** Give `ordinary` an explicit one-case subquota for each of σ = 2, 3, 4, and 5. Put the exact quotas, precedence, overlap treatment, and thresholds in §5. Record every predicate flag evaluator-side in addition to the primary assigned stratum so the precedence can be audited.

4. **Severity: High / File-area: final fixture serialization and runtime information boundary / Issue:** `d["stratum"]` is not demonstrated to be agent-visible under the stated runtime capability boundary, and the shown `print` executes during generation rather than during a campaign. Nevertheless, the field is unnecessary at fixture top level. In particular, `stratum="unresolvable"` reveals the correct behavior immediately if a generic serializer, diagnostic error, replay message, or future loader exposes unknown top-level fields. The public manifest also maps case IDs to this information, making filesystem isolation part of the scientific validity boundary. **Suggested fix:** Remove `d["stratum"]` from the fixture and keep the label only in evaluator-owned manifest/hidden metadata. Add negative tests proving that state, diagnostics, normal and error output, policy inputs, transcripts, and replay results contain none of `stratum`, `oracle`, hidden truth, or unvisited outcomes. Official launchers must not grant access to the manifest or arbitrary repository files.

5. **Severity: Medium / File-area: `src/make_cases.py::gen_final` and manifest generation / Issue:** The selection control flow is deterministic and contains no arm-performance dependency, but freeze hygiene has several gaps:

   - The first scanned seed is 5001, while `generated_from_seed` says 5000.
   - The output directory may already contain stale JSON files; generation neither fails on a nonempty directory nor proves a manifest-directory bijection.
   - Classification uses `ORACLE_CFG["theta"]`, while the manifest separately records `THETA_DEFAULT`.
   - Regeneration metadata does not identify the last scanned seed, generator commit, Python/NumPy environment, or canonical serialization rules.

   **Suggested fix:** Generate into a verified-empty staging directory and fail closed on existing outputs. Make the official runner consume only the manifest and assert that its twelve entries exactly equal the fixture directory. Use one θ source with an equality assertion. Record first and last scanned seed, rejected/accepted counts, generator SHA, environment lock, and schema version. Use deterministic JSON serialization with explicit UTF-8, finite-number validation, and stable key/newline handling before hashing.

6. **Severity: Medium / File-area: `runtime/CLAUDE.md` prompt v2 / Issue:** The operational guidance is generally legitimate and reveals no final truth, but the production prompt includes development-history coaching: the `[v1 -> v2 changes…]` paragraph and “This behavior resolved cases in the shakedown; keep it.” Those statements invite a skeptical judge to characterize the prompt as case-conditioned, particularly because two final quotas test cursor reservation and confirmation. The phrase “within ~20% of the best separation score” also lacks a precisely named visible metric, and “never abstain while a discriminating slot is still reachable” can force useless observations for irrelevant pairs. “No quotes” should clearly refer to rationale content, not required shell quoting. **Suggested fix:** Keep the development rationale in `docs/build-journal.md`; remove it from the runtime prompt. Retain the general rules, but tie “comparable” to an exact displayed diagnostic and scope continued observing to a materially live pair where another observation could affect the verdict. Clarify the distinction between forbidden rationale characters and CLI argument delimiters. Stating eligibility consequences is acceptable because that is a transparent interface contract.

7. **Severity: Medium / File-area: `docs/build-journal.md` dev-v2 ledger / Issue:** Same-fixture pairing controls case difficulty, but one LLM realization per prompt does not isolate the prompt effect. “Converted,” “no regressions,” and the case-specific causal attributions are defensible only as descriptions of these two observed traces, not evidence of a stable improvement. The comparison also mixes scientific and protocol effects: v1 was 9/12 under gate scoring but 10/12 at the raw scientific-outcome level because case 103 was correct and disqualified. These are adaptively inspected development cases, so the 11/12 result is in-sample prompt-development evidence. **Suggested fix:** Say “an observed +2 gated-score difference in one paired development draw,” “no regressions observed in this draw,” and “trace-consistent hypotheses” rather than causal conversions. Report eligibility and raw scientific outcomes separately, define the denominator for mean observations, identify model/sampling/request configuration, and state that no uncertainty or generalization claim is supported by one replicate. “Zero false resolutions” must remain “zero observed,” not a safety estimate.

8. **Severity: High, freeze-protocol / File-area: selection provenance and charter §9 / Issue:** The broad strata predate prompt v2, which helps, and the first-hit quota scan has no direct LLM-performance hook. The remaining manufactured-evaluation concern is that the exact thresholds, precedence, and quota counts were introduced after the dev findings and could otherwise be edited after previewing candidate seeds. A freeze commit containing both newly finalized selection logic and its outputs does not by itself demonstrate that the outputs were generated from previously locked rules. **Suggested fix:** Make and push a pre-generation selection-lock commit containing the final charter, generator, predicates, quotas, prompts, policies, evaluator, and analysis code. Generate the final set once from a clean checkout of that SHA, preserve the scan log, make no arm run against the final fixtures, and let the freeze commit add only the generated fixtures/manifest plus immutable provenance metadata. Disclose that the dev prompt was tuned and that the final sample is a deliberately stratified benchmark, not a population prevalence estimate.

9. **Severity: High, freeze-protocol / File-area: freeze commit as a whole / Issue:** The diff does not yet arrange the final fixtures/manifest, exact LLM replicate IDs, full execution configuration, or frozen analysis path. Without those, final-run choices remain available after outcomes are seen. **Suggested fix:** The freeze must include the four arm implementations and configurations, prompt bytes/version, tool schemas, eligibility rules, θ calibration and its source hashes, final fixtures and hashes, model/provider and sampling settings, the three fixed LLM replicate IDs, retry/noncompletion rules, dependency environment, scoring/reporting code, and the case-clustered bootstrap seed. The analysis must average the three LLM replicates within case before forming the paired LLM-minus-batch case difference and bootstrapping cases.

## Freeze checklist

1. Resolve the §4 oracle-selection contradiction and amend the charter with the exact intended resolvable/unresolvable composition.

2. Replace the special-stratum proxies with exact, arm-neutral predicates that establish live-pair temptation, actual support reversal/confirmation, and a genuinely late narrow window.

3. Declare the full quota vector, precedence, overlap behavior, numeric thresholds, seed rule, and ordinary one-per-σ requirement in charter §5.

4. Remove development-result commentary from the runtime prompt, clarify its visible metrics and rationale syntax, assign the final prompt version, and record its hash.

5. Remove top-level stratum metadata and add fail-closed tests proving that all four arms, transcripts, errors, and replay paths cannot receive stratum, oracle, truth, or unvisited outcomes.

6. Harden generation: one θ source, exact seed-bound metadata, empty staging output, canonical finite JSON, manifest-directory bijection, and pinned environment/version information.

7. Amend the dev ledger to distinguish gated score from raw scientific outcome and characterize v1→v2 as a single-replicate, adaptively tuned development observation.

8. Freeze the complete executable protocol: world and fixture schema, generator, evaluator/refinement rule, oracle, all four policies, launcher, auditor, replay, prompt, tool schemas, eligibility logic, analysis/reporting code, bootstrap seed, dependency lock, and official commands.

9. Commit the complete θ-calibration evidence: calibration cases and hashes, configuration, all non-LLM arm results, worst-arm FRR table, and the deterministic selection of θ = 0.997.

10. Fix the three LLM replicate IDs and lock model identifier, sampling parameters, provider retry policy, request logging, noncompletion scoring, token/cost accounting, and transport-failure treatment.

11. Run the qualification suite only on development fixtures, including the new privacy, predicate, regeneration, manifest, and analysis tests. Record the command, environment, and result.

12. Create and push a public pre-generation selection-lock commit. Do not inspect final potential outcomes or run any arm on final seeds before this lock.

13. From a clean checkout of that SHA, generate the final set exactly once into an empty directory. Preserve the full scan receipt, including seed range and predicate counts; make no swaps.

14. Verify all twelve fixture hashes, the exact quota and σ composition, schema validity, hidden-field isolation, manifest ordering, and reproducibility in the pinned environment.

15. Create and push/tag the freeze commit containing the locked protocol, calibration evidence, final fixtures, manifest, content hashes, run configuration, and replicate IDs. No final arm outcome may exist before this commit.

16. Run even-spacing, scripted-adaptive, and batch once per case, and the LLM arm for the three fixed replicates per case, all from the exact freeze SHA. Retain every failure and archive complete replayable artifacts keyed to that SHA.

17. If any frozen code, prompt, fixture, policy, threshold, schema, scoring, or analysis setting must change, invalidate the freeze and rerun every arm; do not patch around an observed result.

18. freeze commit -> final runs -> no further changes.