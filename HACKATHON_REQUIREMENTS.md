# micro1 Frontier Engineering Challenge 2026 - Requirements and Working Guide

Last verified: 2026-08-29 (Asia/Kolkata)

This document is the working source of truth for choosing, building, evaluating, and submitting our hackathon project. It consolidates the official HackerEarth page, the downloaded 10-page micro1 brief, and the fields visible in the signed-in HackerEarth submission flow.

It intentionally does not commit us to a project idea. The idea-selection requirements near the end are meant to guide the brainstorming phase.

## 1. Authoritative sources

- Official challenge page: <https://www.hackerearth.com/community/challenges/hackathon/micro1-frontier-engineering-challenge-2026/>
- Official hosted instruction PDF: <https://uc.hackerearth.com/he-public-ap-south-1/micro1%20-%20First%20Hackathon97ce7c5.pdf>
- Downloaded instruction PDF in this repository: `micro1 - First Hackathon97ce7c5.pdf`
- Submission dashboard: available from the registered HackerEarth account
- Organizer contact listed by HackerEarth: `yeison@micro1.ai`

If this document conflicts with a later official clarification, updated challenge page, participation agreement, or HackerEarth submission form, the later official source controls.

## 2. Event summary

- Event: micro1 Frontier Engineering Challenge 2026 / Agentic Workflows Hackathon
- Format: free, global, online hackathon
- Participation: individual only; team size is one
- Core theme: build at the frontier of agentic AI
- Build period: August 28-31, 2026
- Registration status at the time of verification: registered
- Submission status at the time of verification: no submission created
- Coding-agent use: required
- Model/API credits: not supplied; participants use their own agent setup

The challenge is not simply to make an impressive AI demo. The expected project is a useful, technically sound agentic workflow whose improvement can be measured and whose result can be reproduced by another person.

## 3. Official schedule

Times below include the official UTC time and the corresponding Asia/Kolkata time.

| Stage | Official time (UTC) | Asia/Kolkata | What happens |
| --- | --- | --- | --- |
| Registration opened | Fri, Aug 21 at 15:00 | Fri, Aug 21 at 20:30 | HackerEarth page and direct registration opened |
| Pre-event briefing | Thu, Aug 27 at 15:00 | Thu, Aug 27 at 20:30 | Rules, submission format, support process, and logistics; no problem details |
| Hackathon kickoff | Fri, Aug 28 at 15:00 | Fri, Aug 28 at 20:30 | Problem document and starter information released |
| Registration closes | Sat, Aug 29 at 23:59 | Sun, Aug 30 at 05:29 | Last registration time shown in the official process graphic |
| Final-day checkpoint | Sun, Aug 30 at 23:59 | Mon, Aug 31 at 05:29 | Submission reminder, known issues, and support escalation window |
| Submission deadline | Mon, Aug 31 at 18:00 | Mon, Aug 31 at 23:30 | Submissions close; late or incomplete entries are not accepted |
| Validation screen | Aug 31-Sep 1 | Aug 31-Sep 1 | Eligibility, completeness, reproducibility, plagiarism, and trace-integrity checks |
| Judge review | Sep 2-Sep 4 | Sep 2-Sep 4 | Qualified submissions are scored using the published rubric |
| Winners announced | Mon, Sep 7 at 17:00 | Mon, Sep 7 at 22:30 | Winners, certificates, and next-step notifications released |

Operational rule: treat August 31 at 23:30 IST as a hard deadline, not a target upload time. We should have a complete draft submission and tested archive substantially earlier.

## 4. The actual challenge

Choose a specific and meaningful problem that we understand. Use an agentic workflow to solve it, then provide clear evidence that the solution improves how the task is handled today.

The intended outcome should be something a real person would genuinely want to use.

Every idea and implementation must answer four questions:

1. Who has this problem?
2. What bottleneck makes it worth solving?
3. Does the agent solve it well?
4. Can another person reproduce the result?

The challenge permits use cases across industries. Official examples of broad areas include engineering/science, forecasting, game development, media generation, office work, professional work, finance/trading, recruiting/HR, legal/compliance, research, e-commerce, and customer support.

The PDF provides three non-binding example concepts:

- Evidence-based codebase quality assessment
- Human-reviewed candidate evaluation using multiple evidence sources
- Consistent podcast translation across episodes and languages

These examples illustrate the desired framing; they are not required project categories.

## 5. Mandatory baseline and advanced solution

Every valid entry must include both a baseline and an advanced solution.

### 5.1 Baseline

The baseline should be a reasonable, simple way to handle the task before the advanced workflow. Acceptable patterns include:

- One direct prompt with basic instructions
- One general-purpose agent with basic tools
- A simple script or template
- The manual process currently used by the intended user

The baseline must be credible. It must not be deliberately weakened to exaggerate the final result.

### 5.2 Advanced solution

The advanced solution must provide a meaningful improvement in at least one of the following:

- Capability
- Reliability
- Efficiency
- Coverage
- Engineering quality

A cosmetic variation is insufficient.

Possible agent capabilities include better context, better tools, memory, verification, specialized skills, or orchestration. We should use only the components justified by the problem. The brief explicitly says purposeful choices matter more than the number of components.

### 5.3 Fair comparison requirements

- Run the baseline and advanced solution on the same tasks and evaluation cases.
- Use the same evaluation method for both.
- Define success before running the final evaluation.
- Explain meaningful differences in models, tools, context, budgets, time, or other resources.
- Report failures and unfavorable cases, not only successful examples.
- Connect each claimed improvement to submitted evidence.

## 6. Evaluation requirements

Evaluation is a first-class deliverable, not an optional appendix.

### 6.1 Primary metric

Choose one primary metric that reflects success for the intended user. Examples from the brief include:

- Tests passed for a developer workflow
- Human time saved for an operations workflow
- Cost per task
- Forecast calibration

If no standard metric fits, define a clear scoring rubric before running the evaluation so judges can understand and reuse it.

### 6.2 Evaluation set

- Ten or more cases are the recommended target when the task permits it.
- Include at least one challenging or adversarial case.
- Explain what the challenging case revealed.
- Keep cases fixed between the baseline and advanced solution.
- Prefer public, synthetic, or approved anonymous data.
- Preserve all results, including failures.

### 6.3 Recommended result table

At minimum, track:

| Metric | Baseline | Advanced solution | Change |
| --- | ---: | ---: | ---: |
| Primary user outcome | TBD | TBD | TBD |
| Human time per task | TBD | TBD | TBD |
| Cost per task | TBD | TBD | TBD |

Additional project-specific metrics should capture false positives, false negatives, reliability, coverage, quality, or repeatability where relevant.

### 6.4 Evidence standard

Every important claim should be traceable to an artifact such as:

- Machine-readable evaluation result
- Test or build output
- Command log
- Input/output pair
- Rubric score
- Source file or source excerpt
- Agent trajectory
- Repeated-run result
- Human-review record, when appropriate

Avoid claims based only on subjective impressions or cherry-picked demos.

## 7. Improvement changelog

The README must contain a clearly labeled Improvement Changelog that tells the story from baseline to final solution.

Create an entry for every important experiment, including experiments removed from the final solution.

Recommended structure:

| Stage | What we tried and why | Evidence/result | Decision or learning |
| --- | --- | --- | --- |
| Baseline | Initial basic approach | Baseline result | Established starting point |
| Iteration 1 | First meaningful change | New result | Kept, revised, or removed |
| Iteration 2 | Change prompted by an observed failure | New result | Kept, revised, or removed |
| Iteration 3 | Further engineering improvement | New result | Kept, revised, or removed |
| Final | Combination of the changes that worked | Final result | Main contribution identified |

Each entry should explain:

- What changed
- Why it changed
- Which evidence motivated it
- What happened under the same evaluation method
- What we decided to do next

The final entry must identify the main failure mode and support the project's hot take or practical insight.

## 8. Judging rubric

Projects are scored out of 100 by micro1's engineering team.

| Criterion | Points | What strong work looks like | Our acceptance question |
| --- | ---: | --- | --- |
| Problem and User Value | 15 | Solves a meaningful problem for a clearly defined user | Who experiences the bottleneck, and why does solving it matter? |
| Agent Solution and Engineering | 30 | Uses agents purposefully and is technically sound | Which design choices materially help the agent solve the problem? |
| End-to-End Quality | 20 | Completes a realistic, self-contained execution and produces a polished result the user can use | Would the intended user sign their name to this output? |
| Measured Improvement | 15 | Demonstrates gains over a fair baseline and links iterations to evidence | Which changes truly improved the outcome? |
| Reproducibility | 15 | Gives another person a clear path to run the baseline and final solution from a clean environment | Can someone reproduce the main result without our help? |
| Hot Take / Insights | 5 | Turns an observed failure mode into a practical lesson about reliable agents | What did we learn, and how should it change future systems? |
| Total | 100 |  |  |

### 8.1 Qualification gate

A project is scored only after it passes checks for:

- Eligibility
- Submission completeness
- Originality and integrity
- Agent trajectory/trace integrity
- Reproducibility
- Plagiarism

A project that cannot be run or verified may be disqualified before rubric scoring.

### 8.2 Tie-break order

1. Higher Agent Solution and Engineering score
2. Higher Reproducibility score
3. Higher Measured Improvement score
4. Higher End-to-End Quality score
5. Final panel review of documented evidence

This ordering should influence prioritization: reliable engineering and clean reproduction are more valuable than adding another flashy feature.

## 9. Required submission package

All four official items below are required.

### 9.1 Complete solution code and improvement changelog

Include:

- Full project source
- Everything required to run it
- Instructions/prompts that shape every agent
- README describing the intended user, bottleneck, and practical value
- Clearly labeled Improvement Changelog
- Evidence linked to each meaningful iteration
- Main failure mode
- Hot take / engineering insight
- Clear disclosure of pre-existing components versus hackathon work

### 9.2 Reproduction guide

Write for someone starting from a clean environment. Include:

- Supported operating system/runtime assumptions
- Exact setup commands
- Exact command for the baseline
- Exact command for the advanced solution
- Exact evaluation command
- Required data and how it is obtained
- Expected outputs
- Relevant versions
- Approximate runtime
- Approximate model/API cost
- Required environment variables without including secrets
- Troubleshooting for likely setup failures

The main result should be reproducible without private data or undocumented manual intervention.

### 9.3 Solution video

Maximum duration: five minutes.

The video should:

1. Introduce the user and problem.
2. Show the simple baseline.
3. Walk through one realistic execution from start to finish.
4. Show the final baseline-versus-advanced comparison.
5. Briefly explain the improvement changelog.
6. Highlight the change that contributed the most.
7. Discuss one experiment that was removed and what it taught us.

The video should demonstrate a real execution rather than relying entirely on slides.

### 9.4 Agent trajectories

Provide representative trajectories for every agent used. Each trajectory should make it easy to follow:

- Agent instructions or system prompt
- User/task input
- Agent actions
- Tool calls
- Tool responses
- Intermediate feedback
- Retries and recovery behavior
- Human checkpoints
- Final result

Using more agents increases the trace and explanation burden. Every agent should have a clear, necessary role.

## 10. HackerEarth submission form requirements

The signed-in submission dialog currently requires:

- Title - required
- Description - required; supports formatting and links
- Video URL - required
- Source-code upload - required; maximum 50 MB

The public FAQ also describes a valid submission as including the required repository/archive, tests, README, agent-use evidence, and demo video.

Practical packaging plan:

- Keep the public or judge-accessible repository as the canonical source.
- Include the repository URL in the submission description.
- Upload a clean ZIP of the source code under 50 MB.
- Exclude secrets, caches, virtual environments, dependency folders, large generated files, and private data.
- Ensure the ZIP contains the README and everything necessary to understand setup.
- Verify the ZIP independently before uploading.
- Use HackerEarth's draft capability before the final deadline.

Only the latest complete submission is evaluated. Revisions are permitted until the deadline.

## 11. Technology policy

Explicitly supported/recommended languages include:

- Python
- TypeScript
- Java
- C++
- Go
- Rust

Common frameworks and libraries in those ecosystems are allowed if the project remains reproducible and license-compliant. Examples listed on the challenge page include FastAPI, Flask, Django, LangGraph, Node.js, Express, NestJS, Next.js, Spring Boot, CMake, Go modules, Tokio, Axum, and Actix.

The FAQ says any language is allowed, subject to runtime constraints. The released PDF does not impose a narrower starter repository, runtime, dependency, or acceptance-test requirement.

Technology-selection principles:

- Prefer a stack we can make reliable within the remaining time.
- Minimize external services and fragile integrations.
- Pin dependency versions.
- Provide a deterministic or recorded evaluation path where live model variability exists.
- Make any required model provider replaceable or clearly documented.
- Do not include API keys or credentials.

## 12. Ground rules and responsible-use requirements

These are baseline requirements for every eligible project:

1. Familiar tools and components are allowed.
2. Clearly identify what existed before the competition and what was added during it.
3. Follow every tool's and component's license and service terms.
4. Keep consequential actions inside a sandbox or simulation and require human approval before execution.
5. Include a qualified human reviewer in any workflow that could significantly affect a person.
6. Choose a legal and ethical use case that treats people and their data responsibly.
7. Use information we are allowed to share; public, synthetic, or approved anonymous data are preferred.
8. Keep credentials and private information outside the submission.
9. Connect every result claim to submitted evidence.
10. Give judges enough access to run the project and reproduce its main result.

Additional implementation rules derived from the above:

- Default high-impact operations to dry-run or simulation mode.
- Put explicit approval gates before external or irreversible actions.
- Record approvals in trajectories when they matter to the workflow.
- Redact secrets and personal data from logs and traces.
- Do not make unsupported decisions about employment, finance, health, law, safety, or access rights.
- Clearly expose uncertainty and limitations to the final user.

## 13. Eligibility

- Participant must be at least 18 at registration.
- Open globally except where prohibited by law, sanctions, export controls, organizer restrictions, or platform restrictions.
- Individual participation only.
- One registration and one final entry per participant.
- At least six months of practical software-building experience or equivalent hands-on evidence is expected.
- Professional employment is not required.
- Working engineers, founders, open-source contributors, competitive programmers, final-year students, graduate students, and recent graduates may participate if they meet the experience requirement.
- micro1 employees, event administrators, judges, challenge creators/testers, and their immediate household members are ineligible for prizes.
- Cash or trace payments require access to an approved payout rail in the participant's country.
- Identity, location, contact, and eligibility information must be accurate.
- Duplicate or false registrations may be disqualified.

## 14. Awards and opportunities

### 14.1 Cash prizes

- First place: USD 5,000
- Second place: USD 3,000
- Third place: USD 2,000
- Total prize pool: USD 10,000

### 14.2 Selective awards

- Best Engineering Workflow
- Most Useful Real-World Workflow
- Best Demonstrated Improvement

The page does not state an additional cash amount for these selective awards.

### 14.3 Other opportunities

- Up to 50 top performers may be considered for paid, flexible engineering work with micro1, subject to verification, eligibility, project availability, and further review.
- Additional strong performers may be invited to micro1's accelerated AI interview.
- Every eligible participant with a valid submission receives a digital participation certificate.

### 14.4 Conditional trajectory acquisition

micro1 may separately offer to acquire qualifying agent-use traces after validation:

- Indicative amount: USD 2-15 per trace
- Indicative participant cap: USD 100-200
- Separate from the USD 10,000 prize pool
- Does not affect judging
- Not guaranteed by registration or submission
- Subject to separate terms covering acquired artifacts, rights, use, compensation, privacy, validation, and payment timing

## 15. Ownership and legal notice

The challenge page states that submissions are governed by the Hackathon Participation Agreement accepted during registration, under which micro1 owns submissions and may use them for AI model training and evaluation.

Before submitting, we should:

- Avoid including anything we do not have the right to transfer or license.
- Review third-party dependency and dataset licenses.
- Avoid proprietary code, employer-owned materials, confidential information, and private credentials.
- Assume submitted code, prompts, trajectories, and related artifacts may be retained and used under the agreement.

This section records the published rule and is not legal advice.

## 16. Idea-selection requirements for brainstorming

Before building an idea, score it against the following filters.

### 16.1 Must-have filters

An idea should have:

- A specific user rather than "everyone"
- A recurring and credible bottleneck
- A clearly useful final artifact or action
- A credible simple baseline
- A primary metric we can define before implementation
- At least 10 repeatable evaluation cases or a strong justification for fewer
- A challenging case that exposes a meaningful failure mode
- A safe, legal path using public or synthetic data
- A clean-environment reproduction story
- A realistic end-to-end implementation within the event window
- A five-minute demo that is easy to understand

### 16.2 Strong preferences

Prefer ideas where:

- Correctness can be checked programmatically.
- The baseline-versus-advanced difference is visually or numerically obvious.
- Verification is integral to the workflow.
- External APIs are optional or replaceable.
- The workflow can run in a sandbox.
- The result remains valuable even if the model occasionally fails.
- Agent design choices can be individually evaluated in the changelog.
- One principal agent plus deterministic components is sufficient.

### 16.3 Warning signs

Avoid or heavily constrain ideas that:

- Are only a generic chat interface or prompt wrapper.
- Require private or difficult-to-license data.
- Depend on live services judges may not access.
- Need subjective evaluation without a defined rubric.
- Require many agents only for appearance.
- Automate consequential real-world actions without approval.
- Cannot produce a useful result in one realistic end-to-end run.
- Need a long explanation before the value is visible.
- Are too broad to evaluate on fixed cases.

## 17. Definition of done

The project is submission-ready only when every item below is satisfied.

### 17.1 Problem and product

- [ ] Intended user is named precisely.
- [ ] Bottleneck and practical value are documented.
- [ ] One realistic task completes end to end.
- [ ] Output is polished enough for the intended user.
- [ ] Limitations, uncertainty, and human-review needs are visible.

### 17.2 Baseline and advanced solution

- [ ] Baseline is implemented and documented.
- [ ] Advanced agentic workflow is implemented.
- [ ] Advanced design choices have explicit justifications.
- [ ] Both run on the same evaluation inputs.
- [ ] Resource differences are disclosed.

### 17.3 Evaluation and evidence

- [ ] Primary metric was defined before the final run.
- [ ] Evaluation set is fixed and versioned.
- [ ] Target is at least 10 cases where practical.
- [ ] At least one challenging case is included.
- [ ] Complete baseline results are saved.
- [ ] Complete advanced results are saved.
- [ ] Failures are retained and discussed.
- [ ] Runtime, human time, and approximate cost are recorded.
- [ ] Every headline claim points to evidence.

### 17.4 Reproducibility

- [ ] Dependencies and tool versions are pinned or documented.
- [ ] Clean setup is tested.
- [ ] Exact baseline command works.
- [ ] Exact advanced-solution command works.
- [ ] Exact evaluation command works.
- [ ] Expected outputs are documented.
- [ ] No private data or credentials are required.
- [ ] A second clean run reproduces the main result.

### 17.5 Documentation and trajectories

- [ ] README includes user, bottleneck, value, architecture, usage, evaluation, limitations, and hot take.
- [ ] Improvement Changelog includes baseline, meaningful iterations, final result, and a removed experiment.
- [ ] Agent prompts/instructions are included.
- [ ] Representative trajectories exist for every agent.
- [ ] Tool responses, retries, feedback, and human checkpoints are visible.
- [ ] Pre-existing versus hackathon-created work is disclosed.

### 17.6 Safety and compliance

- [ ] All code, data, models, and dependencies are permitted and license-compatible.
- [ ] Consequential actions are simulated or approval-gated.
- [ ] High-impact outcomes require qualified human review.
- [ ] Logs, traces, repository, and archive contain no secrets or private data.
- [ ] Ownership implications have been considered.

### 17.7 Submission

- [ ] Demo video is five minutes or less.
- [ ] Video shows the baseline, realistic run, comparison, key improvement, and removed experiment.
- [ ] Video URL is accessible to judges.
- [ ] Source ZIP is below 50 MB.
- [ ] Source ZIP has been extracted and tested independently.
- [ ] Submission title and description are complete.
- [ ] Repository link is included where appropriate.
- [ ] A draft is saved before the final hours.
- [ ] Final submission is completed before Aug 31 at 18:00 UTC / 23:30 IST.

## 18. Suggested repository artifacts

The exact structure will depend on the selected idea, but the final repository should make the required evidence easy to find. A useful starting layout is:

```text
README.md
LICENSE
.env.example
requirements.txt / pyproject.toml / package-lock.json
src/
tests/
data/
  README.md
  fixtures/
evaluation/
  rubric.md
  cases/
  results/
agents/
  prompts/
  trajectories/
docs/
  reproduction.md
  architecture.md
  improvement-changelog.md
  safety-and-limitations.md
scripts/
  run-baseline.*
  run-solution.*
  run-evaluation.*
```

Not every folder is mandatory. The governing principle is that a judge should immediately find the baseline, final workflow, evaluation, evidence, agent instructions, trajectories, and reproduction commands.

## 19. Final strategic principles

- Scope narrowly enough to finish and evaluate well.
- Optimize first for the 30-point engineering category and the qualification gate.
- Build the evaluation harness early, before polishing the product.
- Treat reproducibility as part of the architecture, not end-of-event documentation work.
- Prefer deterministic verification around probabilistic agent behavior.
- Capture trajectories and experiment evidence while building; reconstructing them later is risky.
- Keep one removed experiment so the changelog demonstrates actual learning.
- Make the final demo show a genuine end-to-end execution and an obvious measurable improvement.
- A small workflow with strong evidence is more competitive than a broad workflow with unverifiable claims.
