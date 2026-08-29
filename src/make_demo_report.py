"""Build a demo campaign run and render its HTML report.

Drives the World CLI exactly as an agent would (separate processes, JSON I/O),
picking follow-up slots from the diagnostics output, then renders the campaign
report.

    # from the repo root
    PYTHONPATH=src python src/make_demo_report.py          # bash
    $env:PYTHONPATH="src"; python src/make_demo_report.py  # PowerShell

Outputs:
  tmp/demo-run-case-101/           run directory (recreated on each invocation)
  evaluation/reports/demo-case-101.html
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
CASE = ROOT / "data" / "cases" / "dev" / "case-101.json"
RUN = ROOT / "tmp" / "demo-run-case-101"
OUT = ROOT / "evaluation" / "reports" / "demo-case-101.html"
N_OBS = 3


def cli(*args):
    """Run one World CLI command and return its parsed JSON stdout."""
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    cmd = [sys.executable, "-m", "aliasbreaker.cli", *map(str, args)]
    p = subprocess.run(cmd, cwd=str(ROOT), env=env, capture_output=True,
                       text=True)
    if p.returncode != 0:
        raise SystemExit(
            f"world CLI failed ({p.returncode}): {' '.join(cmd)}\n"
            f"stdout: {p.stdout}\nstderr: {p.stderr}")
    return json.loads(p.stdout)


def pick_slot(diag, taken):
    """Highest predicted separation among future slots, over the pair with the
    largest support product. Diagnostics only — the choice is made here."""
    best = None
    for pair in diag.get("pairs", []):
        for cand in pair["best_future_slots"]:
            if cand["slot"] in taken:
                continue
            score = (pair["support_product"], cand["separation_sigma"])
            if best is None or score > best[0]:
                best = (score, cand, pair["pair"])
    return best


def main():
    if RUN.exists():
        shutil.rmtree(RUN)  # `start` refuses an already-initialized run dir
    RUN.parent.mkdir(parents=True, exist_ok=True)

    state = cli("start", "--case", CASE, "--run", RUN)
    print(f"start: {state['case_id']}, "
          f"{len(state['candidates'])} candidates, "
          f"budget {state['budget_left']}")

    taken = []
    for step in range(1, N_OBS + 1):
        diag = cli("diagnostics", "--run", RUN)
        choice = pick_slot(diag, taken)
        if choice is None:
            print("no discriminating future slot left; stopping early")
            break
        (_sp, sep), cand, pair = choice
        why = (f"Step {step}: candidates {pair[0]} and {pair[1]} carry the "
               f"largest remaining support product; slot {cand['slot']} "
               f"(t = {cand['t']:.2f} d) is where their predicted RVs differ "
               f"most ({sep:.2f} sigma), so this night should separate them "
               f"rather than resample a phase we already covered.")
        res = cli("observe", "--run", RUN, "--slot", cand["slot"], "--why", why)
        taken.append(cand["slot"])
        print(f"observe slot {res['slot']} @ t={res['t']}: "
              f"rv={res['rv']} m/s, support={res['support']}")

    why_stop = (f"Stopping after {len(taken)} of the 6 budgeted visits: the "
                f"support table is no longer moving materially and the "
                f"remaining discriminating separations are below the level "
                f"that would change the ranking. Handing the verdict to the "
                f"evaluator rule.")
    v = cli("finalize", "--run", RUN, "--why", why_stop)
    print(f"finalize: resolved={v['resolved']} "
          f"max_support={v['max_support']:.4f} theta={v['theta']}")

    sys.path.insert(0, str(SRC))
    from aliasbreaker.report import render_report
    out = render_report(str(CASE), str(RUN), str(OUT), reveal=True)
    print(f"report written: {out} ({Path(out).stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
