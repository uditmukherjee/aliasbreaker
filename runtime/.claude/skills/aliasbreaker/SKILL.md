---
name: aliasbreaker
description: Run one AliasBreaker follow-up campaign on a case fixture. Usage - /aliasbreaker <case-fixture-path> [run-id]
---

Run one AliasBreaker campaign following the protocol in CLAUDE.md exactly.

- CASE = the fixture path given in the arguments (e.g.
  `../data/cases/dev/case-101.json`).
- RUN = `runs/<run-id>` if a run id was given, else `runs/<case-id>-manual`.

Begin with `start`, follow the decision guidance, and end with `finalize`.
All hard rules in CLAUDE.md apply unchanged.
