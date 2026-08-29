# AliasBreaker Evaluation Charter — v1 (DRAFT until freeze commit)

This charter predeclares the evaluation protocol. At freeze time, the
generator version, this charter, prompts, tool schemas, policies, the final
case manifest, and fixture content hashes are committed BEFORE any final arm
outcome is observed. After the freeze, only correctness fixes are allowed; any
change requires rerunning every arm and documenting it in the changelog.

## 1. World and fixtures

- Circular Keplerian RV model: v(t) = γ + A·cos(2πft) + B·sin(2πft),
  f = 1/P. White Gaussian measurement noise, constant per-case σ —
  declared as an idealized benchmark (no jitter, no correlated noise, no
  heteroscedasticity; disclosed limitation).
- Each case fixture stores REALIZED potential outcomes: the noisy measurement
  for every legal slot, precomputed at generation. No runtime RNG anywhere in
  evaluation. Content-hashed JSON.
- Chronology: follow-up nights advance monotonically. At each available night
  the acting policy chooses observe / skip; stop is available any time.
  Observed slots cannot be revisited; future information never leaks.
  Availability is *scheduled observatory availability*, known in advance
  (disclosed simplification — not weather prediction).
- Budget: 6 observations; horizon: nights 31–90.

## 2. Candidate construction (data-derived, truth-blind)

Candidates come from a least-squares periodogram of the INITIAL observations
only: frequency grid f ∈ [1/100, 1.2] cycles/day, step 1/(4·T_span); for each
f, exact linear fit of (A, B, γ); Δχ² vs the constant-only model; candidate
periods = top local maxima separated by ≥ 5 grid steps, within Δχ²_keep of the
best peak, max 6. A candidate's identity is its frequency BASIN (±2 grid steps
around its peak); with ≥5-step separation, closed basins are strictly disjoint
(no shared boundary frequency), so identities are stable. [Amended pre-freeze
2026-08-29 from ≥4 after diff-gate 1 flagged that two centers exactly 4 steps
apart share a boundary point.] The hidden truth is used ONLY
to generate measurements and to score. Whether the true period's basin is in
the candidate set is an evaluator-side fact.

## 3. Verdict rule (shared, deterministic, evaluator-owned)

After a campaign ends, the evaluator refits every candidate on all acquired
data (linear fit with the period refined within the candidate's basin: ±2
grid steps, 25-point fine grid) and computes normalized candidate support:

    S_i = exp(-0.5·(χ²_i − χ²_min)) / Σ_j exp(-0.5·(χ²_j − χ²_min))

S is candidate-set-relative support, NOT a calibrated probability, and is
labeled as such everywhere. Verdict: RESOLVED on candidate argmax(S) iff
S_max ≥ θ, else UNRESOLVED (abstain). No arm supplies its own confidence; the
LLM controls scheduling and stopping only.

**θ calibration:** θ is chosen before the freeze by running the complete
procedure (all non-LLM campaign classes) on ≥100 development cases and
selecting the smallest θ ∈ {0.85, 0.9, 0.95, 0.99, 0.997} whose WORST-ARM
false-resolution rate (resolved on a wrong candidate, or resolved when truth's
basin is absent) is ≤ 5%. The calibration table is committed.
[Amended pre-freeze 2026-08-29: grid extended by 0.997 because no member of
the original grid met the bound (0.99 → 5.8% worst-arm FRR); selection rule
unchanged; chosen θ = 0.997. FRR decays slowly in θ because false resolutions
are dominated by decisively wrong fits, which no threshold can veto — the
operative defense against those is confirmation observations, an agent-side
behavior the benchmark measures. See evaluation/theta-calibration.json.]

## 4. Resolvability oracle (arm-independent, predeclared)

A case is RESOLVABLE iff (a) the true period's basin is in the candidate set,
and (b) a search over legal 6-slot chronological designs — joint greedy design
plus 2,000 seeded random designs — finds at least one whose realized outcomes
yield a correct RESOLVED verdict under §3. Oracle labels are computed at
generation time and stored hidden from all arms. [Amended pre-freeze
2026-08-29, diff-gate 2 finding 1: oracle labels ARE used at final-set
generation for exactly one purpose — enforcing the predeclared composition of
10 resolvable + 2 unresolvable cases (§5 quotas). They are never used to
rank, compare, or swap cases within a stratum, and never expose any policy's
performance. All other uses remain reporting-only stratification.]

## 5. Strata for the final set (12 cases, generation rules predeclared)

Quota vector: **4 ordinary** (one case per σ ∈ {2,3,4,5} m/s), **2
tempting-early**, **2 scarce-window**, **2 misleading-observation**, **2
unresolvable**. Structural predicates (arm-independent: they may consult
hidden truth and realized outcomes, never any policy's behavior), with all
numeric thresholds fixed here and echoed in the manifest:

1. **Ordinary**: resolvable, ≥3 candidate basins, no special predicate fires.
2. **Tempting-early**: the strongest separation in the first third of slots
   belongs to a pair of LIVE wrong candidates (initial support ≥ 0.10 each,
   separation > 2.5σ) while every truth-involving pair stays weak early
   (< 1.5σ).
3. **Scarce-window**: for the best-fitting live rival vs truth, all
   discriminating slots (separation > 2σ) number ≤ 3, sit within the last 20
   days of the horizon, and span ≤ 5 days.
4. **Misleading-observation**: adding one early realized outcome (first half
   of slots) to the initial data makes a LIVE wrong candidate OVERTAKE the
   truth under the shared support rule (its support > truth's and ≥ 0.5).
5. **Unresolvable**: oracle label false (used per the §4 amendment solely for
   the 10/2 composition); correct behavior is abstention.

Precedence when several predicates fire: unresolvable > misleading-obs >
scarce-window > tempting-early > ordinary. A case matching a full stratum is
DISCARDED, never demoted to a lower stratum. Seeds are scanned sequentially
from 5000; first-fit fills quotas; predicate flags for every accepted case
are recorded evaluator-side in the manifest for audit.

Final cases are generated from fresh seeds by these rules AFTER all policies,
prompts, and thresholds are locked (a pushed selection-lock commit precedes
generation); no post-generation case swaps. The final set is a deliberately
stratified benchmark, not a population prevalence estimate.

## 6. Arms and information contract

All arms see, at each state: candidate periods and current fits, all
measurements so far, legal remaining slots with times, budget remaining, σ.
None see: hidden truth, oracle labels, potential outcomes for unvisited slots.
Deterministic computations available to every arm: periodogram, fixed-period
linear fit, χ²/support table, pairwise predicted separations per slot,
remaining-window scarcity diagnostics (diagnostics only — never a recommended
action).

| Arm | Scheduling | Stopping |
| --- | --- | --- |
| Baseline (batch) | Joint greedy 6-slot set design by marginal pair-coverage gain, deterministic earliest-night tie-break; committed upfront | None (structural: no feedback) |
| Even-spacing (context baseline) | 6 evenly spaced available nights | None |
| Scripted-adaptive (ablation) | Greedy next-slot by same pair-coverage score, recomputed after each observation | Stops when shared verdict rule would resolve |
| LLM agent (advanced) | LLM decides observe/skip/stop via tool calls over the same diagnostics | LLM decides, verdict still evaluator-computed |

Intentional differences (disclosed): adaptive arms receive feedback and may
stop; the LLM arm consumes API tokens/cost; all else equal.

## 7. Headline comparison and aggregation (predeclared)

- **Primary:** correct-resolution rate on RESOLVABLE final cases, LLM agent vs
  batch baseline, both at budget ≤ 6, shared verdict rule. Paired per-case
  comparison; LLM = mean over 3 predeclared replicates (replicate IDs fixed
  before execution; first valid provider response per replicate; transport
  retries allowed and logged; protocol failures and exhausted retries score
  as noncompletion = unresolved).
- **Secondary:** unsafe-resolution rate on unresolvable stratum; observations
  used by adaptive arms among correct resolutions (with the structural-stopping
  disclosure); scripted-adaptive ablation deltas; tokens, API cost, tool
  calls, wall time per arm; all failures retained and reported.
- **Uncertainty:** case-clustered bootstrap interval on the paired difference;
  no significance claims beyond what ~12 cases support (stated plainly).

## 8. Audit replay (reproducibility path without an API key)

Recorded runs store: prompts and prompt version, raw assistant messages, tool
calls/results, invalid actions and recoveries, request IDs where available,
model ID and reported version, token/cost, timestamps, fixture hashes, code
commit. `replay` re-executes the recorded actions against the deterministic
world, recomputes every measurement, support value, and metric, and rejects
illegal or altered actions. Disclosed honestly: replay verifies integrity and
recomputability of the recorded campaign; ultimate provenance of the model's
outputs rests on the recorded provider responses; the official runs are made
from a pushed public commit to timestamp them.

## 9. Freeze checklist

- [ ] Generator + charter + prompts + tool schemas + all policies committed
- [ ] θ calibration table committed (dev cases)
- [ ] Final manifest (seeds, strata, hashes) committed
- [ ] All arms rerun once from the frozen commit; results are the results
