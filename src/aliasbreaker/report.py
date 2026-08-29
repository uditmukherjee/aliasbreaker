"""Per-case campaign report (spec §6).

Renders ONE self-contained HTML file for a finished (or in-progress) campaign
run directory: banner, human-approval field, case summary, campaign log with
the agent's stated rationale (qualitative, never scored), support table,
verdict box, three embedded matplotlib plots, and the limitations block.

Everything the report shows is agent-visible information recomputed from the
fixture's public fields and the run directory, EXCEPT the optional evaluator
appendix (--reveal), which is clearly labeled as evaluator-side.

Usage:
  python -m aliasbreaker.report --case <fixture.json> --run <run_dir> \
      --out <report.html> [--reveal]
"""

import argparse
import base64
import html
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # noqa: E402  (must precede pyplot import)
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from .fitting import fit_basin, predict_circular, support_from_chi2  # noqa: E402
from .world import Campaign, case_from_dict  # noqa: E402

BANNER = ("SYNTHETIC BENCHMARK — DECISION SUPPORT ONLY. "
          "Not validated for real telescope scheduling. "
          "Requires astronomer review.")

LIMITATIONS = [
    "Circular-orbit model only: eccentric orbits are not represented.",
    "White Gaussian measurement noise at a fixed per-case sigma: no stellar "
    "jitter, no correlated noise, no heteroscedasticity.",
    "Slot availability is scheduled observatory availability known in advance "
    "— it is not a weather forecast.",
    "Support is candidate-set-relative, not a calibrated probability: it "
    "renormalizes over this candidate set and says nothing about periods "
    "outside it.",
]

C_INIT = "#1f4e79"
C_CAMP = "#c1440e"
C_MODEL = ["#4c72b0", "#dd8452", "#55a868", "#8172b3", "#937860", "#da8bc3"]
C_SEL = "#c1440e"


# ---------------------------------------------------------------- loading


def _load_case(case_path):
    """Load a fixture. Returns (case, has_hidden); a public-only fixture (no
    'hidden' block) still renders — its realized outcomes are then recovered
    from the run log instead."""
    d = json.loads(Path(case_path).read_text(encoding="utf-8"))
    has_hidden = "hidden" in d
    if not has_hidden:
        d = dict(d, hidden={"slot_y": [float("nan")] * len(d["slot_t"]),
                            "true_params": {}, "true_basin_index": -1})
    return case_from_dict(d), has_hidden


def _read_jsonl(path):
    if not Path(path).exists():
        return []
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def load_run(case_path, run_dir):
    """Replay a run directory into (case, campaign, meta, state, log, verdict)."""
    run = Path(run_dir)
    case, has_hidden = _load_case(case_path)
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))
    state = json.loads((run / "state.json").read_text(encoding="utf-8"))
    log = _read_jsonl(run / "actions.jsonl")
    vpath = run / "verdict.json"
    vd = json.loads(vpath.read_text(encoding="utf-8")) if vpath.exists() else None
    if not has_hidden:
        for e in log:  # recover the realized outcomes the world already showed
            if e.get("cmd") == "observe" and e.get("ok") and e.get("rv") is not None:
                case.slot_y[int(e["slot"])] = float(e["rv"])
    campaign = Campaign(case)
    for idx in state["observed_slots"]:
        campaign.observe(idx)
    return case, campaign, meta, state, log, vd


def _campaign_rows(campaign, log):
    """Pair each observed slot with the rationale recorded for it."""
    whys = {}
    for e in log:
        if e.get("cmd") == "observe" and e.get("ok"):
            whys.setdefault(int(e["slot"]), []).append(e.get("why") or "")
    used = {}
    rows = []
    for n, (idx, t, y) in enumerate(
            zip(campaign.obs_idx, campaign.obs_t, campaign.obs_y), start=1):
        k = used.get(idx, 0)
        used[idx] = k + 1
        cand = whys.get(idx, [])
        rows.append({"n": n, "slot": idx, "t": t, "rv": y,
                     "why": cand[k] if k < len(cand) else ""})
    return rows


def _finalize_entry(log):
    for e in reversed(log):
        if e.get("cmd") == "finalize":
            return e
    return None


# ------------------------------------------------------------------ plots


def _fig_b64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _style(ax):
    ax.grid(True, color="#e2e2e2", linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#999999")


def _draw_series(ax, case, campaign, fits, sel, xlim, label_models,
                 only_selected=False):
    lo, hi = xlim
    grid = np.linspace(lo, hi, 4000)
    for i, f in enumerate(fits):
        if only_selected and i != sel:
            continue
        ax.plot(grid, predict_circular(f, grid),
                color=C_MODEL[i % len(C_MODEL)],
                lw=1.9 if i == sel else 0.9,
                alpha=0.95 if i == sel else 0.6, zorder=2,
                label=(f"P = {f['P']:.3f} d"
                       + (" (selected)" if i == sel else ""))
                if label_models else None)
    ax.errorbar(case.init_t, case.init_y, yerr=case.sigma, fmt="o", ms=6,
                color=C_INIT, ecolor="#7f9fbf", elinewidth=1.2, capsize=2.5,
                zorder=4, label="initial observations" if not label_models else None)
    if campaign.obs_t:
        ax.errorbar(campaign.obs_t, campaign.obs_y, yerr=case.sigma, fmt="D",
                    ms=7, color=C_CAMP, ecolor="#e0a58c", elinewidth=1.2,
                    capsize=2.5, zorder=5,
                    label="campaign observations" if not label_models else None)
        for n, (t, y) in enumerate(zip(campaign.obs_t, campaign.obs_y), 1):
            if lo <= t <= hi:
                ax.annotate(str(n), (t, y), textcoords="offset points",
                            xytext=(0, 11), ha="center", fontsize=9,
                            fontweight="bold", color=C_CAMP, zorder=6)
    ax.set_xlim(lo, hi)
    ax.set_ylabel("RV (m/s)")


def plot_timeseries(case, campaign, fits, sel):
    """Full span on top; a zoom window below, where the short-period
    candidates are actually distinguishable by eye."""
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(9.2, 6.4), sharey=True,
        gridspec_kw={"hspace": 0.42})
    _style(ax1)
    _style(ax2)
    t_all, _ = campaign.data()
    lo = float(min(t_all.min(), case.slot_t.min()))
    hi = float(max(t_all.max(), case.slot_t.max()))
    pad = 0.03 * (hi - lo)
    lo, hi = lo - pad, hi + pad

    _draw_series(ax1, case, campaign, fits, sel, (lo, hi), label_models=False,
                 only_selected=True)
    ax1.set_title(f"Full time series with the selected model "
                  f"(P = {fits[sel]['P']:.3f} d)", fontsize=11)
    ax1.legend(fontsize=8, ncol=2, framealpha=0.95, loc="best")
    ax1.set_xlabel("time (days)")

    width = min(hi - lo, max(8.0, 1.3 * max(f["P"] for f in fits)))
    center = (float(np.mean(campaign.obs_t)) if campaign.obs_t
              else float(np.mean(case.init_t)))
    zlo = max(lo, center - width / 2.0)
    zhi = min(hi, zlo + width)
    zlo = max(lo, zhi - width)
    _draw_series(ax2, case, campaign, fits, sel, (zlo, zhi), label_models=True)
    ax2.set_title(f"Zoom, nights {zlo:.1f}-{zhi:.1f}: all candidate models",
                  fontsize=11)
    ax2.set_xlabel("time (days)")
    ax2.legend(fontsize=8, ncol=3, framealpha=0.95, loc="best")
    return _fig_b64(fig)


def plot_phase_fold(case, campaign, fit, sel_label):
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    _style(ax)
    P = fit["P"]
    t, y = campaign.data()
    n_init = len(case.init_t)
    ph = (t % P) / P
    ax.errorbar(ph[:n_init], y[:n_init], yerr=case.sigma, fmt="o", ms=6,
                color=C_INIT, ecolor="#7f9fbf", elinewidth=1.2, capsize=2.5,
                zorder=4, label="initial")
    if len(t) > n_init:
        ax.errorbar(ph[n_init:], y[n_init:], yerr=case.sigma, fmt="D", ms=7,
                    color=C_CAMP, ecolor="#e0a58c", elinewidth=1.2,
                    capsize=2.5, zorder=5, label="campaign")
    pg = np.linspace(0.0, 1.0, 500)
    ax.plot(pg, predict_circular(fit, pg * P), color="#333333", lw=1.6,
            zorder=3, label="model")
    ax.set_xlim(-0.02, 1.02)
    ax.set_xlabel(f"phase (period = {P:.4f} d)")
    ax.set_ylabel("radial velocity (m/s)")
    ax.set_title(f"Phase-folded RV — {sel_label}", fontsize=11)
    ax.legend(fontsize=8, framealpha=0.95, loc="best")
    return _fig_b64(fig)


def plot_residuals(case, campaign, fit):
    fig, ax = plt.subplots(figsize=(9.2, 3.3))
    _style(ax)
    t, y = campaign.data()
    n_init = len(case.init_t)
    r = y - predict_circular(fit, t)
    s = case.sigma
    ax.axhspan(-2 * s, 2 * s, color="#dfe8f2", zorder=1, label="+/- 2 sigma")
    ax.axhspan(-s, s, color="#c3d6ea", zorder=1, label="+/- 1 sigma")
    ax.axhline(0.0, color="#666666", lw=1.0, zorder=2)
    ax.errorbar(t[:n_init], r[:n_init], yerr=s, fmt="o", ms=6, color=C_INIT,
                ecolor="#7f9fbf", elinewidth=1.2, capsize=2.5, zorder=4,
                label="initial")
    if len(t) > n_init:
        ax.errorbar(t[n_init:], r[n_init:], yerr=s, fmt="D", ms=7,
                    color=C_CAMP, ecolor="#e0a58c", elinewidth=1.2,
                    capsize=2.5, zorder=5, label="campaign")
    ax.set_xlabel("time (days)")
    ax.set_ylabel("residual (m/s)")
    ax.set_title("Residuals to the selected model", fontsize=11)
    ax.legend(fontsize=8, ncol=4, framealpha=0.95, loc="best")
    return _fig_b64(fig)


# ------------------------------------------------------------------- HTML

CSS = """
:root { color-scheme: light; }
body { margin: 0; background: #f4f4f2; color: #1b1b1b;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif; font-size: 14px; line-height: 1.5; }
.page { max-width: 980px; margin: 0 auto; padding: 24px 26px 56px;
  background: #ffffff; border-left: 1px solid #e0e0dc;
  border-right: 1px solid #e0e0dc; }
h1 { font-size: 22px; margin: 18px 0 2px; }
h2 { font-size: 15px; text-transform: uppercase; letter-spacing: .06em;
  margin: 30px 0 8px; padding-bottom: 5px; border-bottom: 2px solid #1b1b1b; }
h3 { font-size: 13px; margin: 16px 0 6px; }
.sub { color: #5a5a5a; margin: 0 0 4px; }
.banner { background: #fff3cd; border: 2px solid #b8860b; border-radius: 4px;
  padding: 12px 14px; font-weight: 700; color: #6b4e00; letter-spacing: .01em; }
.approval { margin-top: 10px; border: 1px solid #c9c9c4; border-radius: 4px;
  background: #fafaf8; padding: 12px 14px; }
.approval .line { display: inline-block; border-bottom: 1px solid #8a8a8a;
  min-width: 230px; height: 1.25em; margin: 0 18px 0 6px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0 4px;
  font-size: 13px; }
th, td { border: 1px solid #cfcfca; padding: 6px 9px; text-align: left;
  vertical-align: top; }
th { background: #eceae5; font-weight: 600; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
tr.sel td { background: #fdf1e7; font-weight: 600; }
.why { color: #333; font-style: italic; }
.kv { width: auto; }
.kv td:first-child { background: #f6f5f2; font-weight: 600; white-space: nowrap; }
.verdict { border: 2px solid #1b1b1b; border-radius: 4px; padding: 4px 14px 12px;
  background: #fbfbf9; }
.tag { display: inline-block; padding: 2px 10px; border-radius: 3px;
  font-weight: 700; font-size: 12px; letter-spacing: .04em; }
.tag.res { background: #d9ecd9; color: #1e5b1e; border: 1px solid #1e5b1e; }
.tag.abs { background: #e7e7e7; color: #444; border: 1px solid #777; }
.tag.prog { background: #e6eefa; color: #1f4e79; border: 1px solid #1f4e79; }
img { max-width: 100%; display: block; margin: 6px 0 2px; }
figure { margin: 14px 0 20px; }
figcaption { color: #5a5a5a; font-size: 12px; }
ul.lim { margin: 6px 0; padding-left: 20px; }
ul.lim li { margin-bottom: 5px; }
.appendix { border: 2px dashed #8b1a1a; border-radius: 4px; padding: 4px 14px 14px;
  background: #fdf4f4; margin-top: 26px; }
.appendix h2 { border-bottom-color: #8b1a1a; color: #8b1a1a; }
footer { margin-top: 34px; padding-top: 10px; border-top: 1px solid #ddd;
  color: #6a6a6a; font-size: 12px; }
code { background: #f0efec; padding: 1px 4px; border-radius: 3px;
  font-family: ui-monospace, Consolas, "Courier New", monospace; font-size: 12px; }
"""


def _e(x):
    return html.escape("" if x is None else str(x))


def _f(x, n=3):
    try:
        return f"{float(x):.{n}f}"
    except (TypeError, ValueError):
        return "n/a"


def _img(b64, caption):
    return (f'<figure><img alt="{_e(caption)}" '
            f'src="data:image/png;base64,{b64}">'
            f'<figcaption>{_e(caption)}</figcaption></figure>')


def render_report(case_path, run_dir, out_path, reveal=False):
    """Render the campaign report for `run_dir` to `out_path`. Returns the path."""
    case, campaign, meta, state, log, vd = load_run(case_path, run_dir)

    t_all, y_all = campaign.data()
    fits = [fit_basin(t_all, y_all, case.sigma, P, case.freq_df)
            for P in case.candidates]
    support = support_from_chi2([f["chi2"] for f in fits])
    top = int(np.argmax(support))
    resolved = bool(vd["resolved"]) if vd else False
    sel = int(vd["pred"]) if (vd and resolved) else top
    sel_fit = fits[sel]
    sel_label = (f"candidate {sel} (selected)" if resolved
                 else f"candidate {sel} (top support; not resolved)")
    theta = meta.get("theta")
    if theta is None:
        theta = vd.get("theta") if vd else None

    rows = _campaign_rows(campaign, log)
    fin = _finalize_entry(log)
    stop_reason = (vd or {}).get("stop_reason") or (fin or {}).get("why") or ""

    p1 = plot_timeseries(case, campaign, fits, sel)
    p2 = plot_phase_fold(case, campaign, sel_fit, sel_label)
    p3 = plot_residuals(case, campaign, sel_fit)

    h = []
    a = h.append
    a("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">")
    a('<meta name="viewport" content="width=device-width, initial-scale=1">')
    a(f"<title>AliasBreaker campaign report — {_e(case.case_id)}</title>")
    a(f"<style>{CSS}</style></head><body><div class=\"page\">")

    # banner + approval
    a(f'<div class="banner">{_e(BANNER)}</div>')
    a('<div class="approval"><strong>Human approval required before any '
      'scheduling action.</strong><br>Reviewed by <span class="line"></span>'
      'Date <span class="line" style="min-width:150px"></span><br>'
      '<span style="color:#5a5a5a">Signature above certifies that an '
      'astronomer has reviewed the assumptions, the campaign log and the '
      'limitations section below.</span></div>')

    a(f"<h1>Campaign report — {_e(case.case_id)}</h1>")
    a(f'<p class="sub">Alias-breaking follow-up campaign, synthetic '
      f'radial-velocity benchmark. Generated '
      f'{_e(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))}.</p>')

    # case summary
    a("<h2>Case summary</h2><table class=\"kv\">")
    a(f"<tr><td>Case id</td><td>{_e(case.case_id)}</td></tr>")
    a(f"<tr><td>Measurement precision (sigma)</td>"
      f"<td>{_f(case.sigma, 2)} m/s</td></tr>")
    a(f"<tr><td>Observation budget</td><td>{case.budget}</td></tr>")
    a(f"<tr><td>Initial observations</td><td>{len(case.init_t)}</td></tr>")
    a(f"<tr><td>Campaign observations used</td>"
      f"<td>{len(campaign.obs_idx)} of {case.budget}</td></tr>")
    a(f"<tr><td>Legal follow-up slots</td><td>{len(case.slot_t)}</td></tr>")
    a(f"<tr><td>Candidate periods</td><td>{len(case.candidates)}</td></tr>")
    a(f"<tr><td>Resolution threshold theta</td>"
      f"<td>{_f(theta, 4) if theta is not None else 'not recorded'}</td></tr>")
    a(f"<tr><td>Campaign status</td><td>"
      f"{'finalized' if state.get('finalized') else 'in progress'}</td></tr>")
    a(f"<tr><td>Run directory</td><td><code>{_e(run_dir)}</code></td></tr>")
    a("</table>")

    # campaign log
    a("<h2>Campaign log</h2>")
    a('<p class="sub">Night-by-night follow-up decisions. The rationale '
      'column is recorded for auditability only.</p>')
    a('<table><tr><th class="num">#</th><th class="num">night (t, days)</th>'
      '<th class="num">slot</th><th class="num">measured RV (m/s)</th>'
      '<th>agent rationale (qualitative, not scored)</th></tr>')
    if rows:
        for r in rows:
            a(f'<tr><td class="num">{r["n"]}</td>'
              f'<td class="num">{_f(r["t"], 3)}</td>'
              f'<td class="num">{r["slot"]}</td>'
              f'<td class="num">{_f(r["rv"], 2)}</td>'
              f'<td class="why">{_e(r["why"]) or "&mdash;"}</td></tr>')
    else:
        a('<tr><td colspan="5">No follow-up observations recorded.</td></tr>')
    a("</table>")
    a('<h3>Next action / stop statement</h3>')
    if state.get("finalized"):
        a(f'<p>Campaign stopped after {len(campaign.obs_idx)} of '
          f'{case.budget} budgeted observations. Stated reason: '
          f'<span class="why">{_e(stop_reason) or "&mdash;"}</span></p>')
    else:
        rem = campaign.remaining_slots()
        nxt = (f"next legal slot {rem[0][0]} at t = {_f(rem[0][1], 3)} d"
               if rem else "no legal slots remain")
        a(f'<p>Campaign not finalized: {campaign.budget_left()} observation(s) '
          f'of budget remain; {_e(nxt)}.</p>')

    # support table
    a("<h2>Candidate support</h2>")
    a('<p class="sub">All candidates refit on every measurement (initial + '
      'campaign) with the period refined inside the candidate\'s own '
      'frequency basin. Support is candidate-set-relative, NOT a calibrated '
      'probability.</p>')
    a('<table><tr><th class="num">candidate</th>'
      '<th class="num">initial period (d)</th>'
      '<th class="num">refined period (d)</th><th class="num">K (m/s)</th>'
      '<th class="num">chi2</th><th class="num">support</th>'
      '<th>status</th></tr>')
    for i, (P0, f, s) in enumerate(zip(case.candidates, fits, support)):
        if resolved and i == sel:
            status = "SELECTED (resolved)"
        elif i == top:
            status = "top support" + ("" if resolved else " (no resolution)")
        else:
            status = ""
        cls = ' class="sel"' if i == sel else ""
        a(f'<tr{cls}><td class="num">{i}</td><td class="num">{_f(P0, 4)}</td>'
          f'<td class="num">{_f(f["P"], 4)}</td>'
          f'<td class="num">{_f(f["K"], 2)}</td>'
          f'<td class="num">{_f(f["chi2"], 2)}</td>'
          f'<td class="num">{_f(s, 4)}</td><td>{_e(status)}</td></tr>')
    a("</table>")

    # verdict
    a("<h2>Verdict</h2><div class=\"verdict\">")
    if vd is None:
        a('<p><span class="tag prog">IN PROGRESS</span> &nbsp;the campaign has '
          'not been finalized; the figures below use the current top-support '
          'candidate.</p>')
    elif resolved:
        a(f'<p><span class="tag res">RESOLVED</span> &nbsp;on candidate '
          f'{sel} at refined period <strong>{_f(sel_fit["P"], 4)} d</strong>'
          f'</p>')
    else:
        a('<p><span class="tag abs">ABSTAINED (unresolved)</span> &nbsp;no '
          'candidate reached the resolution threshold.</p>')
    a('<table class="kv">')
    a(f'<tr><td>Max support</td><td>{_f((vd or {}).get("max_support", support[top]), 4)}'
      f'</td></tr>')
    a(f'<tr><td>Threshold theta</td>'
      f'<td>{_f(theta, 4) if theta is not None else "not recorded"}</td></tr>')
    a(f'<tr><td>Support vs threshold</td><td>'
      f'{"support &ge; theta" if resolved else "support &lt; theta"}</td></tr>')
    a(f'<tr><td>Observations used</td>'
      f'<td>{len(campaign.obs_idx)} follow-up + {len(case.init_t)} initial '
      f'= {len(t_all)} total</td></tr>')
    a(f'<tr><td>Stop reason (stated)</td>'
      f'<td class="why">{_e(stop_reason) or "&mdash;"}</td></tr>')
    a("</table></div>")

    # figures
    a("<h2>Figures</h2>")
    a(_img(p1, "Figure 1. Top: the full campaign span with the selected "
               "model. Bottom: a zoom window over which every candidate "
               "model (thin lines, legend gives the refined periods) is "
               "distinguishable. Circles: initial observations. Diamonds: "
               "campaign observations, numbered in the order they were "
               "taken. Error bars are +/- 1 sigma."))
    a(_img(p2, f"Figure 2. RV folded at the refined period of {sel_label}, "
               f"P = {_f(sel_fit['P'], 4)} d."))
    a(_img(p3, "Figure 3. Residuals to the selected model versus time, with "
               "+/- 1 and +/- 2 sigma bands."))

    # limitations
    a("<h2>Limitations</h2><ul class=\"lim\">")
    for item in LIMITATIONS:
        a(f"<li>{_e(item)}</li>")
    a("</ul>")
    a('<p class="sub">This document is generated from a synthetic benchmark '
      'world. It is decision support for a benchmark exercise, not an '
      'observing recommendation.</p>')

    # evaluator appendix
    if reveal:
        a('<div class="appendix"><h2>Evaluator appendix</h2>')
        a('<p><strong>Evaluator-side information — hidden from the agent '
          'during the campaign.</strong> It is shown here only for scoring '
          'and audit, and played no part in any decision above.</p>')
        tp = case.true_params or {}
        a('<table class="kv">')
        a(f'<tr><td>Correct resolution</td>'
          f'<td>{_e((vd or {}).get("correct"))}</td></tr>')
        a(f'<tr><td>False resolution</td>'
          f'<td>{_e((vd or {}).get("false_resolution"))}</td></tr>')
        a(f'<tr><td>Support on truth\'s basin</td>'
          f'<td>{_f((vd or {}).get("truth_support"), 4)}</td></tr>')
        a(f'<tr><td>True period</td><td>{_f(tp.get("P"), 4)} d</td></tr>')
        a(f'<tr><td>True K</td><td>{_f(tp.get("K"), 2)} m/s</td></tr>')
        a(f'<tr><td>True gamma</td><td>{_f(tp.get("gamma"), 2)} m/s</td></tr>')
        a(f'<tr><td>Truth basin candidate index</td>'
          f'<td>{case.true_basin_index if case.true_basin_index >= 0 else "absent from candidate set"}</td></tr>')
        a("</table></div>")

    a(f'<footer>{_e(BANNER)}<br>Case fixture: <code>{_e(case_path)}</code>'
      f'</footer>')
    a("</div></body></html>")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(h), encoding="utf-8")
    return str(out)


def main(argv=None):
    p = argparse.ArgumentParser(prog="aliasbreaker.report")
    p.add_argument("--case", required=True, help="case fixture JSON")
    p.add_argument("--run", required=True, help="run directory")
    p.add_argument("--out", required=True, help="output HTML path")
    p.add_argument("--reveal", action="store_true",
                   help="append evaluator-side truth (never for agent-facing use)")
    args = p.parse_args(argv)
    out = render_report(args.case, args.run, args.out, reveal=args.reveal)
    print(json.dumps({"report": out}))


if __name__ == "__main__":
    main()
