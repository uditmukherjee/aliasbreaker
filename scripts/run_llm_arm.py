"""Headless launcher for the AliasBreaker runtime agent (LLM arm).

For each case x replicate: spawns a locked-down Claude Code session in
runtime/ (`claude -p`), captures the stream-json transcript, then checks
completion (verdict.json exists), runs the trace auditor, and collects the
evaluator verdict. Replicate IDs are fixed up front (charter §7); a session
that times out, errors, or fails audit scores as noncompletion/disqualified —
recorded, never retried silently.

Usage (repo root):
  python scripts/run_llm_arm.py --cases data/cases/dev --label dev-shakedown \
      [--replicates 1] [--model claude-sonnet-5] [--timeout 900] [--only case-101]
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_trace import audit  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"


def claude_argv(prompt, model):
    exe = shutil.which("claude")
    if exe is None:
        raise SystemExit("claude CLI not found on PATH")
    argv = [exe, "-p", prompt, "--model", model,
            "--output-format", "stream-json", "--verbose"]
    if exe.lower().endswith((".cmd", ".bat")):
        argv = ["cmd", "/c"] + argv
    return argv


def run_one(case_path, run_id, model, timeout):
    run_dir = RUNTIME / "runs" / run_id
    if run_dir.exists():
        raise SystemExit(f"run dir already exists: {run_dir} (fresh IDs only)")
    (RUNTIME / "runs").mkdir(exist_ok=True)
    rel_case = "../" + case_path.relative_to(ROOT).as_posix()
    prompt = (f"Run one AliasBreaker campaign. CASE: {rel_case} "
              f"RUN: runs/{run_id} . Follow the protocol in CLAUDE.md "
              f"exactly. Begin with start; end with finalize.")
    transcript = RUNTIME / "runs" / f"{run_id}.transcript.jsonl"
    t0 = time.time()
    status = "completed"
    try:
        with open(transcript, "w", encoding="utf-8") as out:
            subprocess.run(claude_argv(prompt, model), cwd=RUNTIME,
                           stdout=out, stderr=subprocess.PIPE,
                           stdin=subprocess.DEVNULL, timeout=timeout,
                           check=False)
    except subprocess.TimeoutExpired:
        status = "timeout"
    elapsed = round(time.time() - t0, 1)

    verdict_path = run_dir / "verdict.json"
    verdict = json.loads(verdict_path.read_text()) if verdict_path.exists() else None
    if verdict is None and status == "completed":
        status = "noncompletion"
    audit_result = audit(transcript) if transcript.exists() else {"ok": False}
    return {
        "run_id": run_id, "case": case_path.stem, "status": status,
        "elapsed_s": elapsed, "audit_ok": audit_result.get("ok", False),
        "audit": audit_result, "verdict": verdict,
        "transcript": str(transcript.relative_to(ROOT)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--replicates", type=int, default=1)
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    case_paths = sorted(Path(args.cases).resolve().glob("*.json"))
    if args.only:
        case_paths = [p for p in case_paths if p.stem == args.only]
    if not case_paths:
        raise SystemExit("no case fixtures matched")

    results = []
    for case_path in case_paths:
        for rep in range(1, args.replicates + 1):
            run_id = f"{args.label}-{case_path.stem}-r{rep}"
            print(f"running {run_id} ...", flush=True)
            r = run_one(case_path, run_id, args.model, args.timeout)
            v = r["verdict"] or {}
            print(f"  -> {r['status']} in {r['elapsed_s']}s  audit_ok="
                  f"{r['audit_ok']}  resolved={v.get('resolved')}  "
                  f"correct={v.get('correct')}  n_obs={v.get('n_obs')}",
                  flush=True)
            results.append(r)

    out = ROOT / "evaluation" / f"llm-arm-{args.label}.json"
    out.parent.mkdir(exist_ok=True)
    summary = {
        "label": args.label, "model": args.model,
        "n_runs": len(results),
        "completed": sum(r["status"] == "completed" for r in results),
        "audit_ok": sum(r["audit_ok"] for r in results),
        "correct": sum(bool((r["verdict"] or {}).get("correct"))
                       for r in results),
        "false_resolutions": sum(bool((r["verdict"] or {}).get(
            "false_resolution")) for r in results),
        "results": results,
    }
    out.write_text(json.dumps(summary, indent=2))
    print(f"\nsummary -> {out}")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"},
                     indent=2))


if __name__ == "__main__":
    main()
