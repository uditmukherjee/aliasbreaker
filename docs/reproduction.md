# Reproduction Guide — clean environment

Everything below assumes a clean machine. The **headline result reproduces
fully offline with no API key** via audit replay; re-running the LLM arm live
requires Claude Code + Anthropic auth (documented last).

## Environment

- OS: developed and verified on Windows 11 (PowerShell). The code is pure
  Python and should run on Linux/macOS; only the LLM-arm launcher's
  process-tree handling is Windows-specific.
- Python 3.12.x (developed on 3.12.6)
- Install pinned dependencies:

```powershell
python -m pip install -r requirements.txt
# numpy==2.5.1  matplotlib==3.11.1  anthropic==1.2.0
```

- Set the module path once per shell (repo root):

```powershell
$env:PYTHONPATH = "src"
```

No other environment variables are required for the offline path. No data
downloads: all fixtures are committed (`data/cases/`, ~34 KB for the final
set), hidden truth included under each fixture's `hidden` key, hashes pinned
in `evaluation/final-manifest.json`.

## 1. Test suite (~7 s)

```powershell
python -m unittest discover -s tests
```

Expected: `Ran 199 tests ... OK` — physics, truth-blind candidate
construction, chronology/budget enforcement, hidden-data leakage proofs,
auditor adversarial cases, replay tamper detection.

## 2. Baseline and deterministic arms on the frozen final set (~1 s)

```powershell
python src/run_arms.py --cases data/cases/final --label check
```

Expected: per-case lines and a summary matching
`evaluation/arms-final.json` (deterministic — identical numbers).

## 3. LLM-arm audit replay — no API key (~seconds)

Every official LLM campaign is recorded under `runtime/runs/final-*` (full
Claude Code transcript + action log + public verdict). Replay re-executes
each recorded campaign against the hashed fixture, verifies every
measurement, and recomputes the verdict:

```powershell
python -m aliasbreaker.replay --run runtime/runs/final-case-30000-r1
# ... or all of them:
Get-ChildItem runtime/runs -Directory -Filter "final-*" | ForEach-Object {
  python -m aliasbreaker.replay --run $_.FullName }
```

Expected: `"ok": true` with all seven checks passing per run. Editing any
byte of a fixture, action log, or verdict flips it to a named failure
(tamper detection — try it on a copy).

Trace audit of any transcript:

```powershell
python scripts/audit_trace.py runtime/runs/final-case-30000-r1.transcript.jsonl --run final-case-30000-r1 --case case-30000
```

## 4. Frozen analysis (~10 s)

```powershell
python src/analyze_final.py
```

Reads the committed manifest + arm results + LLM results, validates case
sets and fixture hashes, and reproduces `evaluation/final-analysis.json`
(paired comparison, two-stage case-clustered bootstrap, fixed seed 20260830).

## 5. Re-running the LLM arm live (optional; requires Claude Code)

```powershell
npm install -g @anthropic-ai/claude-code
# auth: `claude` login (subscription) OR $env:ANTHROPIC_API_KEY
python scripts/run_llm_arm.py --cases data/cases/final --label rerun --replicates 3 --timeout 900
```

- Model pinned: `claude-sonnet-5` (the launcher rejects runs whose
  provider-reported model differs).
- Runtime: ~1–3 min per campaign, ~1–2 h for 36.
- Cost: ~$0.20–0.35 per campaign at API pricing (≈ $10 for the full matrix);
  $0 marginal on a subscription.
- Live LLM output is stochastic (the harness does not expose temperature —
  disclosed); your correctness numbers may differ from the official run.
  The official numbers are the recorded, replay-verified ones.
- Without Claude Code on PATH the launcher refuses loudly and writes nothing.

## 6. Regenerating fixtures (optional, deterministic)

```powershell
python src/make_cases.py dev     # dev set
python src/make_cases.py final   # refuses if data/cases/final is non-empty
```

Generation is fully seeded: regenerating the final set reproduces
byte-identical fixtures (verified during the freeze; hashes in the manifest).

## Troubleshooting

- `ModuleNotFoundError: aliasbreaker` → `$env:PYTHONPATH="src"` not set (or
  use `python -m` from repo root with it set).
- `refusing to generate into non-empty ...` → intentional freeze hygiene;
  delete the directory only if you mean to regenerate.
- Replay `fixture_hash` failure → the fixture file changed since the run was
  recorded; restore it from git.
- PowerShell quoting: commands above avoid quotes needing escapes; on
  bash/zsh they run unchanged except `$env:` → `export PYTHONPATH=src`.
