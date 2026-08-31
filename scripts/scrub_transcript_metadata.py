"""Redact developer-machine metadata from recorded Claude Code transcripts
before publication. Touches ONLY the harness init record (line 1 of each
*.transcript.jsonl): memory_paths (local account name), mcp_servers (names of
the developer's connected services), messaging_socket_path. Tool calls,
model outputs, actions, and results are untouched, so the trace auditor and
audit replay are unaffected — re-run them after scrubbing to prove it.

Idempotent. Usage (repo root): python scripts/scrub_transcript_metadata.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runtime" / "runs"
REDACTED_FIELDS = ("memory_paths", "mcp_servers", "messaging_socket_path")


def scrub(path):
    """Redact the harness init record wherever it sits (a rate-limit event
    can precede it), leaving every other line byte-identical."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    changed = False
    for i, line in enumerate(lines):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict) or not any(f in rec for f in REDACTED_FIELDS):
            continue
        rec_changed = False
        for field in REDACTED_FIELDS:
            if field in rec and rec[field] != "<redacted for publication>":
                rec[field] = "<redacted for publication>"
                rec_changed = True
        if rec_changed:
            rec["_redaction_note"] = (
                "memory_paths, mcp_servers, messaging_socket_path replaced by "
                "scripts/scrub_transcript_metadata.py before publication; all "
                "tool calls and results are verbatim")
            lines[i] = json.dumps(rec) + "\n"
            changed = True
    if changed:
        path.write_text("".join(lines), encoding="utf-8")
    return changed


if __name__ == "__main__":
    n_changed = 0
    files = sorted(RUNS.glob("*.transcript.jsonl"))
    for p in files:
        if scrub(p):
            n_changed += 1
    print(f"scrubbed {n_changed} of {len(files)} transcripts")
