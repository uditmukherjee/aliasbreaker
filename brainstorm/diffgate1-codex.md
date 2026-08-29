# Codex Diff-Gate 1 — Runtime Core

## Verdict

**NEEDS-REWORK.** The evaluator call sites and calibrated default are directionally aligned with the charter, but the runtime boundary is not qualification-safe. Commands that execute arbitrary shell operations can pass the auditor; the agent can create probe runs, inspect earlier replicates, substitute another case, or change θ while remaining “audit clean”; and the launcher counts verdicts from failed or disqualified runs. In addition, charter §8 replay, fixture binding, and tamper detection are not implemented. These are outcome-changing integrity failures, not presentation issues.

## Findings

1. **Severity:** Critical  
   **File/area:** `scripts/audit_trace.py`, `runtime/.claude/settings.json`  
   **Issue:** `_bash_ok` treats double-quoted content as inert, but Bash performs command substitution inside double quotes. For example, this begins with the allowlisted prefix and passes the auditor:

   ```bash
   python -m aliasbreaker.cli finalize --run runs/X --why "$(cat ../data/cases/final/case.json >&2)"
   ```

   The regex removes the quoted section before scanning, while Bash executes `cat` and exposes the hidden fixture on stderr. Backticks and `$()` are not forbidden; an embedded newline also passes `CLI_RE.match` and can introduce a second command. The optional `cd` expression permits substitutions too. Thus arbitrary reads, writes, network calls, and code execution can be marked protocol-clean.  
   **Suggested fix:** Do not expose a shell as the agent tool. Prefer a structured World tool/MCP interface with typed `start`, `state`, `diagnostics`, `observe`, and `finalize` calls. If Bash must remain temporarily, validate the entire command using a strict grammar, reject all shell expansion syntax—including `$`, backticks, CR/LF, globbing, parentheses, escapes, and substitutions—and remove the `cd` allowance. Never erase quoted content before validation.

2. **Severity:** Critical  
   **File/area:** `src/aliasbreaker/cli.py`, `scripts/audit_trace.py`, `scripts/run_llm_arm.py`  
   **Issue:** The World CLI is not bound to the launcher-assigned case and run. An agent can start unlimited side runs on the target fixture, observe six different slots in each, and thereby enumerate every hidden potential outcome before scheduling the official run. Replicate 2 can also call `state` on the predictable replicate-1 directory and learn its measurements. All such calls pass the auditor because it checks only the subcommand prefix. The agent can additionally:

   - Start the official run with a different fixture.
   - Supply `--theta 0` despite the frozen threshold.
   - Read or finalize another run via `--run`.
   - Use `../` or absolute paths to write outside `runtime/runs`.
   - Invoke extra `start`/`finalize` commands in any order.

   The launcher labels the resulting verdict as belonging to the requested case without checking its case identity.  
   **Suggested fix:** Make each official process capability-bound to one immutable case hash and one run ID supplied outside the model-controlled arguments. Refuse every other case/run and remove runtime access to `--theta`. Resolve and containment-check all paths. Run each replicate in an isolated directory with no prior runs. The auditor must enforce exactly one assigned `start`, only assigned-run operations, and exactly one final `finalize`.

3. **Severity:** Critical  
   **File/area:** `scripts/run_llm_arm.py`  
   **Issue:** Failure and disqualification do not affect scoring. `subprocess.run(..., check=False)` is discarded, so a nonzero Claude exit can remain `completed`. An audit failure leaves `status == "completed"`. The aggregate then counts `correct` and `false_resolution` from every available verdict regardless of timeout, process failure, audit failure, or protocol validity. This directly contradicts charter §7, which scores protocol failures and exhausted retries as noncompletion/unresolved.  
   **Suggested fix:** Define a single eligibility predicate: successful provider exit, structurally complete transcript, clean protocol audit, valid replay, expected case/run/model/θ binding, and a recomputed verdict. Only eligible runs may contribute their verdict. Every other run must contribute unresolved/noncompletion while retaining the raw failure record. Never aggregate correctness directly from an unvalidated `verdict.json`.

4. **Severity:** High  
   **File/area:** World run artifacts; charter §8; `src/aliasbreaker/cli.py`  
   **Issue:** The required audit replay path is absent. `_load_run` reconstructs from mutable `state.json`; it does not replay the transcript or authoritative action log, compare tool results, reject altered actions, or recompute the recorded verdict. `meta.json` stores no fixture hash and uses an absolute case path, making a copied run nonportable. Every invocation rereads that path, so a fixture change mid-campaign silently changes prior and future outcomes. State, actions, metadata, and verdict can be edited independently without detection. The artifacts also lack a bound prompt/version hash, code commit, final-manifest identity, and externally anchored artifact hashes.  
   **Suggested fix:** Implement charter §8 before running another official arm. Pin the fixture SHA-256, frozen configuration, prompt/skill hashes, θ, code commit, case ID, run ID, requested and reported model, and replicate ID at start. Replay the canonical action sequence against the hashed fixture and compare every measurement, legality result, support table, and verdict. Store portable fixture identity rather than an absolute path, and gate scoring on successful replay.

5. **Severity:** High  
   **File/area:** `src/aliasbreaker/cli.py` state machine  
   **Issue:** State updates are not transactional. `observe` saves the new state before logging the action; `finalize` marks the run finalized before writing `verdict.json` or the finalize log. A crash in either window leaves an unreplayable or permanently bricked run. Concurrent invocations can both load the same state and create lost updates. Several illegal actions—repeat start/finalize, operations after finalization, missing run files, parser errors—are not logged, and many produce raw argparse output or tracebacks rather than the promised JSON error. `--why` is optional and may be empty despite the runtime protocol requiring it. `state` remains legal after finalization.  
   **Suggested fix:** Use a transactional event store, such as SQLite, or an authoritative append-only event log with atomic materialization and recovery. Record every attempted action and result, including parser/protocol failures. Make finalization idempotently recoverable, lock each run during mutation, require a nonempty single-line rationale, and enforce the declared state sequence world-side.

6. **Severity:** High  
   **File/area:** `scripts/run_llm_arm.py` launcher and Windows execution  
   **Issue:** The launcher does not enforce charter §7’s official replicate protocol. It defaults to one replicate, permits arbitrary `--model`, derives replicate IDs from mutable operator input rather than a frozen manifest, and records only the requested model—not the provider-reported model/version. It does not classify attempts as transport versus protocol failures or preserve a retry ledger, so “first valid response” cannot be demonstrated. Token usage, cost, request IDs, and stderr are not collected into the run record. On Windows, passing model- and label-derived text through `cmd /c` crosses a second command parser; standard subprocess list quoting is not a safe escaping boundary for arbitrary `cmd.exe` metacharacters. Labels are also accepted as path components without validation. A timeout may kill the `.cmd` wrapper while leaving a descendant Claude process writing to the run.  
   **Suggested fix:** Add an official-run mode driven solely by a frozen manifest containing exactly three replicate IDs, allowed cases, model, prompt hash, and timeout/retry policy. Validate all identifiers as conservative slugs and containment-check resolved paths. Invoke a real executable rather than a batch shim where possible; otherwise use a reviewed Windows wrapper with no untrusted command text. Capture exit code, stderr, request/attempt metadata, usage, actual model/version, and terminate the entire process tree on timeout.

7. **Severity:** High  
   **File/area:** `scripts/audit_trace.py`  
   **Issue:** Transcript auditing fails open. Malformed JSON lines are silently ignored, and an empty transcript returns `ok: true`. The auditor does not require a complete provider result, pair tool calls with results, validate CLI exit status, enforce start/finalize ordering, require rationales, or correlate transcript calls with `actions.jsonl`, state, and verdict. A truncated or edited transcript can therefore audit clean. The unrestricted `Skill(aliasbreaker)` exemption is also not checked for placement, repetition, or arguments.  
   **Suggested fix:** Treat every malformed or unknown event as a failure unless explicitly documented as part of the provider schema. Require stream start and terminal events, tool-use/result pairing, exact action grammar and sequence, and equality with the replayed world log. Empty, truncated, duplicate, or post-finalize activity must fail closed.

8. **Severity:** High  
   **File/area:** `tests/test_leakage.py`; missing runtime integration tests  
   **Issue:** The main leakage test does not poison `slot_y`, even though unvisited `slot_y` values are the most important hidden information. A planner could read every future realized outcome directly and still pass every shown “truth-blind scheduling” test because the clean and poisoned cases retain identical `slot_y`. The displayed suite also has no adversarial integration tests for the new CLI, auditor, launcher, report binding, or calibration artifact. The 94 green tests therefore do not exercise the qualification boundary where the critical failures occur.  
   **Suggested fix:** Give planners a public-world interface rather than a raw `Case`, or use a proxy that raises on access to unobserved outcomes. For batch/even arms, change every `slot_y` and require identical designs. For adaptive arms, preserve only outcomes already legally revealed and perturb all future outcomes before each decision. Add regression cases for substitutions, backticks, newlines, duplicate options, wrong run/case, θ override, traversal, malformed transcripts, invalid sequencing, audit-failure scoring, and crash recovery.

9. **Severity:** Medium  
   **File/area:** `src/aliasbreaker/cli.py`, arm information parity  
   **Issue:** The LLM does not receive the same numerical information used by the evaluator and scripted arms. RVs are rounded to two decimals, χ² to two, supports to four, and diagnostic separations to two, while non-LLM arms schedule and stop using full-precision values. The action log stores RVs at only three decimals. Near θ = 0.997, support rounding can obscure whether the shared threshold has actually been crossed. The exact pinned θ is not included in `start` or `state`; the prompt merely says “~0.997.” This is an undisclosed “all else equal” divergence and makes log-only recomputation inexact.  
   **Suggested fix:** Either publish full deterministic precision to every arm or predeclare a canonical quantization and apply it identically to the LLM, scripted policies, and evaluator. Include exact θ in every public state and preserve exact realized values in replay artifacts.

10. **Severity:** Medium  
    **File/area:** Candidate basin construction; `tests/test_periodogram.py`  
    **Issue:** Candidate centers are accepted at separation `>= 4·df`, while each closed refit basin extends `±2·df`. Candidates exactly four steps apart therefore share their boundary frequency; a 25-point grid including both endpoints can assign the same refined frequency to two candidate identities. This does not satisfy the charter’s statement that basins are disjoint.  
    **Suggested fix:** Before freeze, define boundary ownership explicitly. Either require centers to be at least five grid indices apart or use half-open/nonoverlapping basin bounds with a deterministic tie rule. Add a constructed exactly-four-step regression case.

11. **Severity:** Medium  
    **File/area:** `tests/test_periodogram.py`, `tests/test_verdict.py`, mathematical contract  
    **Issue:** The tests do not lock several exact charter formulas. The support tests would pass with the wrong softmax temperature because they check only ordering, normalization, and stability—not the required `exp(-0.5·Δχ²)`. Basin tests check only bounds and determinism, not exactly 25 fine-grid points. Candidate tests do not fully assert local maxima, `Δχ²_keep`, initial-observations-only construction, or the six-candidate selection rule. Consequently, a material formula regression could retain a green suite.  
    **Suggested fix:** Add golden numerical tests for the `-0.5` coefficient, exact 25-point basin frequencies, known local-maximum/keep-threshold fixtures, deterministic tie handling, and a generator test proving candidates are unchanged when all follow-up potential outcomes change.

12. **Severity:** High  
    **File/area:** `src/aliasbreaker/world.py`, `src/make_cases.py`, oracle persistence  
    **Issue:** The charter requires the resolvability oracle label to be computed at generation and stored hidden. `case_to_dict` stores only potential outcomes, true parameters, and `true_basin_index`; no oracle label, oracle seed, search budget, θ, or oracle version is serialized. The provided case generator does not compute it. The oracle tests also use 200 random designs and do not establish that production generation executes the required joint-greedy-plus-2,000-design search.  
    **Suggested fix:** Implement the final generator now, serialize the hidden oracle label together with the exact oracle configuration and code/version hash, and include those fields in the fixture content hash. Add a production-configuration test confirming one joint-greedy design plus exactly 2,000 seeded legal six-slot designs.

13. **Severity:** Medium  
    **File/area:** `src/calibrate_theta.py`, `src/aliasbreaker/evaluator.py`  
    **Issue:** Threshold selection is performed on per-arm rates after rounding to four decimals, rather than on exact false-resolution counts. With the current denominator of 120, the reported 5% boundary is likely exactly 6/120, but the implementation is still brittle and does not literally implement the selection rule for other admissible sample sizes. The chosen value is then manually duplicated in `THETA_DEFAULT`; no assertion binds it to the committed calibration artifact, and the runtime CLI can override it.  
    **Suggested fix:** Select using integer counts or unrounded fractions and round only for presentation. Generate a frozen configuration artifact from the chosen result, fail if no grid value qualifies, import or verify that value everywhere, and assert at launch/replay that every official run used the committed θ.

14. **Severity:** Medium  
    **File/area:** `src/aliasbreaker/report.py`  
    **Issue:** The report accepts a case path independently of the run metadata and never verifies case ID or fixture hash. It reconstructs observations from mutable `state.json`, then trusts verdict fields from a separate mutable file without checking that they match the recomputed support. A caller can therefore render a plausible report for the wrong case or an altered verdict. Public-only reports reconstruct outcomes from three-decimal log values, which can change support relative to the evaluator.  
    **Suggested fix:** Generate reports only from a successfully replayed, hash-bound run bundle. Reject case/meta/state/log/verdict inconsistencies, recompute verdict fields rather than trusting them, and use exact replayed measurements. Keep reveal reports outside the runtime-visible filesystem until all replicates finish.

## The three highest-leverage fixes before the freeze

1. Replace the Bash-prefix security model with a structured, capability-bound World interface restricted to one case hash and one run ID. Isolate replicates, remove runtime θ/case/run overrides, and enforce the complete action sequence.

2. Implement charter §8 as the authority for results: hashed portable fixtures, transactional actions, immutable run metadata, exact deterministic replay, transcript/action correlation, and evaluator verdict recomputation.

3. Make the launcher fail closed under a frozen official manifest. Require exactly three fixed replicates and the pinned model, harden Windows execution and timeouts, preserve attempt metadata, and score every failed, unaudited, or unreplayable run as noncompletion/unresolved.