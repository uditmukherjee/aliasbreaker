"""Trace auditor v2 (post diff-gate 1): verifies a runtime-agent transcript
stayed in protocol. Fail-closed.

Rules:
- Forbidden anywhere in a Bash command (quotes included): $, backtick, CR, LF,
  ; | < > and any '&' outside the single optional `cd <runtime> &&` joiner —
  no shell expansion or chaining can hide in quoted rationales.
- Allowed tool calls: Bash running exactly one World CLI command (optional
  cd-to-runtime prefix), plus at most one Skill invocation of "aliasbreaker".
- Command grammar parsed with shlex: --theta is forbidden; --run must equal
  the assigned run; start must reference the assigned case and appear exactly
  once, first; finalize exactly once, last; no CLI call after finalize.
- Transcript completeness: non-empty, parseable, and contains a terminal
  "result" event. Malformed lines are violations.

Usage:
  python scripts/audit_trace.py <transcript.jsonl> [--run <run_id>] [--case <case_id>]
Importable: audit(path, expected_run=None, expected_case=None) -> dict
"""

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

RAW_FORBIDDEN = re.compile(r"[$`\r\n;|<>]")
CD_RUNTIME_RE = re.compile(r'^cd\s+"?[^&]*runtime[/\\]?"?$')
SUBCOMMANDS = ("start", "state", "diagnostics", "observe", "finalize")


def _parse_cli(command):
    """Return (subcommand, flags) if the command is exactly one World CLI
    call (optional cd-to-runtime prefix), else None."""
    if RAW_FORBIDDEN.search(command):
        return None
    parts = [p.strip() for p in command.strip().split("&&")]
    if any("&" in p for p in parts):
        return None
    if len(parts) == 2:
        if not CD_RUNTIME_RE.match(parts[0]):
            return None
        cli = parts[1]
    elif len(parts) == 1:
        cli = parts[0]
    else:
        return None
    try:
        tokens = shlex.split(cli)
    except ValueError:
        return None
    if tokens[:3] != ["python", "-m", "aliasbreaker.cli"] or len(tokens) < 4:
        return None
    sub = tokens[3]
    if sub not in SUBCOMMANDS:
        return None
    flags, i = {}, 4
    while i < len(tokens):
        if not tokens[i].startswith("--") or i + 1 >= len(tokens):
            return None
        flags[tokens[i][2:]] = tokens[i + 1]
        i += 2
    return sub, flags


def _iter_tool_uses(obj):
    if isinstance(obj, dict):
        if obj.get("type") == "tool_use":
            yield obj
        for v in obj.values():
            yield from _iter_tool_uses(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_tool_uses(v)


def _find_model(obj):
    if isinstance(obj, dict):
        if isinstance(obj.get("model"), str):
            return obj["model"]
        for v in obj.values():
            m = _find_model(v)
            if m:
                return m
    elif isinstance(obj, list):
        for v in obj:
            m = _find_model(v)
            if m:
                return m
    return None


def audit(path, expected_run=None, expected_case=None):
    path = Path(path)
    violations, sequence, model = [], [], None
    n_calls = skill_uses = 0
    has_result_event = False

    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        violations.append({"issue": "empty or missing transcript"})

    for ln in lines:
        try:
            event = json.loads(ln)
        except json.JSONDecodeError:
            violations.append({"issue": "malformed transcript line",
                               "line": ln[:120]})
            continue
        if model is None:
            model = _find_model(event)
        if event.get("type") == "result":
            has_result_event = True
        for tu in _iter_tool_uses(event):
            n_calls += 1
            name = tu.get("name", "?")
            inp = tu.get("input") or {}
            if name == "Skill":
                skill_uses += 1
                if inp.get("skill") != "aliasbreaker" or skill_uses > 1:
                    violations.append({"tool": "Skill", "input": inp})
                continue
            if name != "Bash":
                violations.append({"tool": name, "input": inp})
                continue
            command = inp.get("command", "")
            parsed = _parse_cli(command)
            if parsed is None:
                violations.append({"tool": "Bash", "command": command})
                continue
            sub, flags = parsed
            if "theta" in flags:
                violations.append({"issue": "theta override attempted",
                                   "command": command})
            if expected_run is not None and sub != "start" and \
                    flags.get("run", "").strip("/") != f"runs/{expected_run}":
                violations.append({"issue": "wrong run directory",
                                   "command": command})
            if sub == "start":
                if expected_run is not None and \
                        flags.get("run", "").strip("/") != f"runs/{expected_run}":
                    violations.append({"issue": "start on wrong run",
                                       "command": command})
                if expected_case is not None and \
                        Path(flags.get("case", "")).stem != expected_case:
                    violations.append({"issue": "start on wrong case",
                                       "command": command})
            sequence.append(sub)

    if lines and not has_result_event:
        violations.append({"issue": "no terminal result event (truncated?)"})
    if sequence.count("start") != 1:
        violations.append({"issue": f"start count = {sequence.count('start')}"})
    elif sequence[0] != "start":
        violations.append({"issue": "first CLI call is not start"})
    if sequence.count("finalize") != 1:
        violations.append(
            {"issue": f"finalize count = {sequence.count('finalize')}"})
    elif sequence[-1] != "finalize":
        violations.append({"issue": "CLI activity after finalize"})

    return {
        "transcript": str(path),
        "ok": not violations,
        "n_tool_calls": n_calls,
        "model_reported": model,
        "cli_sequence": sequence,
        "cli_command_counts": {s: sequence.count(s)
                               for s in sorted(set(sequence))},
        "violations": violations,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("transcripts", nargs="+")
    ap.add_argument("--run", default=None)
    ap.add_argument("--case", default=None)
    a = ap.parse_args()
    results = [audit(p, expected_run=a.run, expected_case=a.case)
               for p in a.transcripts]
    print(json.dumps(results if len(results) != 1 else results[0], indent=2))
    sys.exit(0 if all(r["ok"] for r in results) else 1)
