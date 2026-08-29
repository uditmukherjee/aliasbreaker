# Plan-Gate Triage — Codex review of spec v1 (32 findings)

Verdict was NEEDS-REWORK. Orchestrator triage; severity rule: Critical/High must
be resolved or explicitly justified; Medium judgment; Low recorded.

## Accepted — drive spec v2 and code rework

- **F1/F17/F27 (Critical) benchmark integrity:** separate development vs final
  evaluation fixtures; candidates built from initial data ONLY via a documented
  periodogram procedure (never from hidden truth); final case manifest + hashes
  frozen (committed) before any final arm outcome is observed; no filtering of
  final cases by which policy wins. Kill test reframed as feasibility-only (its
  purpose retroactively: world validity + runtime, not headroom hunting).
- **F2/F14 (Critical) metric definition:** "normalized candidate support"
  S_i = exp(-0.5·Δχ²_i)/Σ_j exp(-0.5·Δχ²_j), computed by the evaluator only;
  threshold θ calibrated on a large dev-set run to bound false-resolution rate;
  the LLM never supplies confidence — verdicts are computed deterministically
  from the acquired data for every arm. Agents control only scheduling and
  stopping.
- **F7 (Critical) abstention:** predeclared arm-independent resolvability
  oracle (best legal design search on fixture-stored outcomes); resolvable and
  unresolvable strata scored and reported separately.
- **F9/F8/F11/F12 (Critical/High) arm contract:** one chronological state
  machine (nights advance monotonically; observe/skip/stop; no time travel);
  common information surface documented; shared deterministic verdict rule;
  factorial framing — scheduling policy and stopping policy measured
  separately; "batch cannot stop early" reported as a disclosed structural
  property, not smuggled into the headline; discrimination tools return
  diagnostics, never a recommended action.
- **F3/F4 (High) physics scope:** v1 world and fits are CIRCULAR orbits —
  linear fitter only (3 params), healthy dof with 6-8 initial points, no
  nonlinear optimizer. Eccentric machinery (built during kill test) is retained
  in-repo as the documented REMOVED EXPERIMENT with evidence (chi2-plateau
  anomaly, overfitting risk) — satisfying the changelog requirement honestly.
- **F5 (High) candidate construction:** least-squares periodogram over a
  declared frequency grid; top non-overlapping basins; dedupe tolerance;
  data-derived only.
- **F6/F19 (High) noise/versioning honesty:** fixtures store realized
  potential outcomes for every slot (no cross-version RNG dependence); white
  Gaussian noise declared as idealized benchmark; patch-version pinning;
  content hashes.
- **F16/F15 (High) LLM run protocol:** 3 replicate IDs predeclared; first
  valid response kept; retry policy split (transport vs protocol); exhausted
  retries = failure; paired per-case reporting, mean over replicates,
  case-clustered bootstrap; no significance overclaims.
- **F18 (Critical) replay framing:** renamed AUDIT REPLAY; stores raw
  responses, request metadata, prompts, hashes, commit; disclosed that
  provenance ultimately rests on recorded provider output; official run from a
  pushed commit.
- **F20/F21 (High) trajectory + protocol:** full trajectory schema (incl.
  invalid actions, retries, recovery, token/cost); finite-state agent protocol
  with max turns, illegal-action handling, noncompletion scoring; all
  recoveries logged.
- **F22/F23/F31 (High) framing/safety:** single persona (RV follow-up observer
  allocating visits on a small spectrograph); simplifications disclosed
  (scheduled availability, not weather; fixed precision; no airmass); outputs
  labeled "synthetic benchmark / decision support only"; human-review field in
  reports.
- **F24 (High) report:** concrete artifact schema; matplotlib pinned for
  plots.
- **F25 (Medium) adversarial strata:** five mechanism strata (tempting early
  slot, scarce future window, misleading observation needing confirmation,
  near-equivalent case, availability drought).
- **F26 (High) resource accounting:** tokens, cost, tool calls, wall time,
  observations attempted/obtained, human time — per arm, failures retained.
- **F28/F30/F32 (Critical) ops:** final ~10-12h reserved for clean-run
  verification, docs, video, ZIP, submission; changelog/disclosures/safety
  docs created during build; video script covers all mandated segments.
- **F13 (High):** advanced solution predeclared as the hybrid workflow (LLM
  strategic control + deterministic estimation/verification); scripted-adaptive
  reported as ablation even if it wins.
- **F10 (High):** batch baseline = joint greedy set design by marginal gain
  with deterministic tie-breaking (earliest night); evenly-spaced schedule as
  extra context baseline.
- **F29 (High):** judge-facing evidence chain made explicit in README; hot
  take must emerge from observed failures (case-006-type events), not
  pre-scripted.

## Modified acceptance

- **F27 fallback clause:** Circuit Sleuth fallback is dropped (agree: no
  domain switch this late); simplification happens WITHIN AliasBreaker.
- **F11 efficiency claim:** we keep "adaptive scheduling enables early
  stopping" as a *disclosed structural finding* about feedback — stated as a
  property of the workflow class, never as measured intelligence.

## Recorded (Low / no action beyond documentation)

- None marked Low by reviewer; all 32 were Critical/High/Medium and are
  addressed above.
