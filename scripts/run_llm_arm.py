"""Headless launcher for the AliasBreaker runtime agent (LLM arm) — v2.

Eligibility (post diff-gate 1): a run's verdict counts only if ALL hold —
provider process exited 0 within timeout, transcript audits clean against the
assigned case+run, and the recorded campaign replays exactly (fixture hash,
measurements, verdict recomputation). Anything else scores as
noncompletion/unresolved; the raw record is retained, never retried silently.

Usage (repo root):
  python scripts/run_llm_arm.py --cases data/cases/dev --label dev-v1 \
      [--replicates 1] [--model claude-sonnet-5] [--timeout 900] [--only case-101]
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "runtime"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from audit_trace import audit  # noqa: E402
from aliasbreaker.replay import replay  # noqa: E402

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def claude_argv(prompt, model):
    exe = shutil.which("claude")
    if exe is None:
        raise SystemExit("claude CLI not found on PATH")
    argv = [exe, "-p", prompt, "--model", model,
            "--output-format", "stream-json", "--verbose"]
    if exe.lower().endswith((".cmd", ".bat")):
        argv = ["cmd", "/c"] + argv
    return argv


def _kill_tree(proc):
    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                   capture_output=True)


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
    stderr_file = RUNTIME / "runs" / f"{run_id}.stderr.log"
    t0 = time.time()
    status, exit_code = "completed", None
    with open(transcript, "w", encoding="utf-8") as out, \
            open(stderr_file, "w", encoding="utf-8") as err:
        proc = subprocess.Popen(claude_argv(prompt, model), cwd=RUNTIME,
                                stdout=out, stderr=err,
                                stdin=subprocess.DEVNULL)
        try:
            exit_code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            status = "timeout"
    elapsed = round(time.time() - t0, 1)
    if status == "completed" and exit_code != 0:
        status = "provider_error"

    verdict_path = run_dir / "verdict.json"
    public_verdict = (json.loads(verdict_path.read_text())
                      if verdict_path.exists() else None)
    if public_verdict is None and status == "completed":
        status = "noncompletion"
    audit_result = audit(transcript, expected_run=run_id,
                         expected_case=case_path.stem,
                         expected_cwd=str(RUNTIME))
    replay_result = replay(run_dir) if verdict_path.exists() else {"ok": False}
    # Truth-side outcome comes ONLY from the evaluator's fresh recomputation
    # during replay — never from files in the agent's workspace.
    fresh = replay_result.get("fresh_verdict") or {}

    reported = audit_result.get("model_reported") or ""
    model_ok = reported.startswith(model)
    eligible = (status == "completed" and audit_result["ok"]
                and replay_result["ok"] and model_ok)
    outcome = {
        "eligible": eligible,
        "model_ok": model_ok,
        "correct": bool(fresh.get("correct")) if eligible else False,
        "false_resolution": bool(fresh.get("false_resolution")) if eligible else False,
        "abstained": bool(fresh.get("abstained")) if eligible else None,
        "scored_as": ("verdict" if eligible else "noncompletion/unresolved"),
    }
    return {
        "run_id": run_id, "case": case_path.stem, "status": status,
        "exit_code": exit_code, "elapsed_s": elapsed,
        "model_requested": None,  # filled by caller
        "model_reported": audit_result.get("model_reported"),
        "audit_ok": audit_result["ok"],
        "replay_ok": replay_result.get("ok", False),
        "outcome": outcome,
        "audit": audit_result, "replay": replay_result,
        "verdict_raw": public_verdict,
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
    if not SLUG.match(args.label):
        raise SystemExit("label must be a lowercase slug ([a-z0-9-])")
    if shutil.which("claude") is None:
        raise SystemExit(
            "PRECONDITION FAILED: the Claude Code CLI ('claude') is not on "
            "PATH. The LLM arm requires Claude Code with authentication "
            "(subscription login or ANTHROPIC_API_KEY). The deterministic "
            "arms (src/run_arms.py) and audit replay (aliasbreaker.replay) "
            "run without it. No summary was written.")

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
            r["model_requested"] = args.model
            o = r["outcome"]
            print(f"  -> {r['status']} in {r['elapsed_s']}s  "
                  f"audit={r['audit_ok']} replay={r['replay_ok']} "
                  f"eligible={o['eligible']} correct={o['correct']}",
                  flush=True)
            results.append(r)

    import hashlib
    prompt_bytes = (RUNTIME / "CLAUDE.md").read_bytes()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    n_eligible = sum(r["outcome"]["eligible"] for r in results)
    summary = {
        "label": args.label, "model_requested": args.model,
        "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
        "code_commit": commit,
        "models_reported": sorted({r["model_reported"] for r in results
                                   if r["model_reported"]}),
        "n_runs": len(results),
        "n_eligible": n_eligible,
        "ineligible": [r["run_id"] for r in results
                       if not r["outcome"]["eligible"]],
        "correct": sum(r["outcome"]["correct"] for r in results),
        "false_resolutions": sum(r["outcome"]["false_resolution"]
                                 for r in results),
        "results": results,
    }
    out = ROOT / "evaluation" / f"llm-arm-{args.label}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(summary, indent=2))
    print(f"\nsummary -> {out}")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"},
                     indent=2))


if __name__ == "__main__":
    main()
