"""Trace auditor (A4): verifies a runtime-agent transcript stayed in protocol.

A run is protocol-clean iff every tool call in the transcript is a Bash
invocation of the World CLI. Anything else (file reads, other commands, other
tools) is a violation — the run is disqualified from the evaluation and the
violation is reported, never silently repaired.

Usage:
  python scripts/audit_trace.py <transcript.jsonl> [more transcripts...]
Importable: audit(path) -> dict
"""

import json
import re
import sys
from pathlib import Path

CLI_RE = re.compile(
    r"^python -m aliasbreaker\.cli (start|state|diagnostics|observe|finalize)\b")
CD_RUNTIME_RE = re.compile(r'^cd\s+"?[^;|&<>]*runtime[/\\]?"?$')
FORBIDDEN_SHELL = re.compile(r"[;|<>]")


def _bash_ok(command):
    """Allow exactly: an optional `cd <...runtime>` prefix joined by one `&&`,
    then a single World CLI invocation. No pipes, chains, or redirection.
    Double-quoted content (--why rationales) is exempt from the shell-
    metacharacter scan — quoted text cannot chain commands."""
    stripped = re.sub(r'"[^"]*"', '""', command.strip())
    if FORBIDDEN_SHELL.search(stripped):
        return False
    parts = [p.strip() for p in stripped.split("&&")]
    if any("&" in p for p in parts):
        return False
    if len(parts) == 1:
        return bool(CLI_RE.match(parts[0]))
    if len(parts) == 2:
        return bool(CD_RUNTIME_RE.match(parts[0])) and bool(CLI_RE.match(parts[1]))
    return False


def _iter_tool_uses(obj):
    if isinstance(obj, dict):
        if obj.get("type") == "tool_use":
            yield obj
        for v in obj.values():
            yield from _iter_tool_uses(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_tool_uses(v)


def audit(path):
    path = Path(path)
    n_calls, violations, cli_commands = 0, [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        for tu in _iter_tool_uses(event):
            n_calls += 1
            name = tu.get("name", "?")
            inp = tu.get("input") or {}
            if name == "Skill" and inp.get("skill") == "aliasbreaker":
                continue  # invoking our own campaign skill is protocol
            command = inp.get("command", "")
            if name != "Bash":
                violations.append({"tool": name, "input": inp})
            elif not _bash_ok(command):
                violations.append({"tool": "Bash", "command": command})
            else:
                cli = command.strip().split("&&")[-1].strip()
                cli_commands.append(cli.split()[3])
    return {
        "transcript": str(path),
        "ok": not violations,
        "n_tool_calls": n_calls,
        "cli_command_counts": {c: cli_commands.count(c)
                               for c in sorted(set(cli_commands))},
        "violations": violations,
    }


if __name__ == "__main__":
    results = [audit(p) for p in sys.argv[1:]]
    print(json.dumps(results if len(results) != 1 else results[0], indent=2))
    sys.exit(0 if all(r["ok"] for r in results) else 1)
