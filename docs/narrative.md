# How it actually went

A three-day account of building AliasBreaker — one human, Claude Code as
orchestrator and runtime, Codex as an independent reviewer — written to be
read alongside the [playbook](playbook.md). The real-time log is
[`build-journal.md`](build-journal.md); this is the shape of it.

## Day one: choosing a problem by falsifying six others

We started with a constraint and a wish. The constraint: whatever we built had
to be reproducible by a stranger, with a fair baseline and a measured
improvement. The wish: learn something new — the sciences, deliberately
outside the author's professional domains.

The first six ideas all borrowed ground truth from the real world: vetting
exoplanet candidates in telescope archives, gravitational-wave detection,
quantum-circuit synthesis, paper reproduction. An adversarial critique from
Codex dismantled them on logistics rather than romance — fixture sizes,
fuzzy negative labels, reviewers who cannot download archives, and the
question that haunted the whole project: *is the agent doing science, or
narrating a deterministic tool?*

So we ran a second ideation round blind: Claude and Codex each proposed
fresh directions without seeing the other's. Both proposed the same thing —
a budgeted active-science agent inside a synthetic world whose hidden truth
we generate. Independent convergence became our decision rule. Codex's
instantiation was the one we chose: an agent that decides *when to look*,
allocating six telescope visits to break orbital-period aliases in
radial-velocity data. Real physics, real documented failure mode, exact
truth by construction, kilobytes of fixtures.

The spec went to a plan-gate and came back NEEDS-REWORK with 32 findings.
Most were right: an undefined "confidence ≥ 0.9" that would have let the
agent grade itself; a world without chronology where an agent could observe
night 80 and then night 40; an efficiency claim structurally gifted to the
adaptive arms. The rewritten charter became the authority for everything
that followed, and the first feasibility run of the rebuilt core caught a
real physics bug an hour later — exactly the kind of bug the gate had
predicted abstractly.

## Day two: an agent that lives inside its own harness

The author made the architectural call that defined the project: the runtime
agent would *be* a Claude Code project — a locked-down session whose only
tool is a five-command World CLI, invoked headlessly for evaluation and
interactively for demos. No API keys, the richest possible trajectories, and
a meta-story we did not plan: the runtime was built in the harness that
built it. The leakage worry ("it could read the answer from disk") became a
design driver: permission lockdown, a trace auditor that disqualifies any
out-of-protocol call, and later a verdict split so truth-side facts are never
written where a sibling run could read them.

The first headless run resolved its case correctly in four observations and
did something we had only hoped for: after support crossed the threshold on
a single point, it spent one more observation to confirm before committing.
Then the dev shakedown taught the two lessons that became prompt v2. A run
was disqualified — correct answer, semicolon in a rationale. And two
abstentions traced to the same pathology that sank the scripted planner:
jumping deep into the horizon early and stranding a cursor that only moves
forward. Both fixes were evidence-driven; v2 scored 11/12 on the same cases.

A second diff-gate said the auditor's quoted-text exemption was a shell hole
(`$(...)` executes inside double quotes), the CLI was not bound to its
assigned case, and the launcher counted verdicts from failed runs. All
fixed; a 198-test suite followed with proofs that planners read hidden
outcomes zero times and that replay detects nine tamper types.

## Day three: the review that shrank our result

Before freezing, the author asked for something unusual: a subagent playing
the *judge*, instructed to try to disqualify us. It instrumented the baseline
and found that its score saturated after two picks, after which it chose
telescope nights by array index. Thirty-five of seventy-two baseline
observations were tie-breaks. A fair χ²-shaped baseline, chosen as the
strongest of eight swept variants, cut our dev margin from +5 cases to +4 —
and it was the best thing that happened to the project. The same review
found the answer key sitting in the agent's workspace and a compliance
problem in a document that named a private client repository. All three
were fixed before the freeze.

The freeze itself failed closed. Two of the five adversarial strata we had
promised were structurally impossible in this world — a 200-case probe found
zero instances at any threshold. We replaced one, constructed the other by
masking schedules, amended the charter *before any arm saw a final seed*,
and generated the set from a pushed lock commit. Twelve cases, thirty-four
kilobytes, hashes in a manifest.

Then the official run: 36 sessions, every one audit- and replay-clean.
On the ten resolvable cases the agent resolved 77% against the baseline's
20%, beat the planted misleading-observation trap six of six, and passed
the constructed reservation test five of six. And on the two cases whose
true period was not on the candidate menu, it confidently resolved the wrong
answer every single time — while the dumber scripted planner abstained.
Better evidence-gathering had amplified confidence in a broken option set.
We named it, reported it unretouched, and it became the most transferable
finding of the whole exercise: relative confidence is a trap, and "none of
the above" has to be a first-class, scoreable answer.

## What we would tell ourselves at the start

Build the table before the product. Instrument the baseline as if an
adversary wrote it. Hire your harshest reviewer from a different model
family and let it see everything. Lock the rules before you look. And when
the agent is wrong with total confidence, that is the result worth writing
about.
