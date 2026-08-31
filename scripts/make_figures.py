"""Generate the README reference figures (docs/figures/*.png) with the
project's own code — reproducible, no external assets.

  python scripts/make_figures.py      (repo root; PYTHONPATH=src)

1. rv-method.png   — what a radial-velocity signal is: a star's line-of-sight
                     velocity oscillating with the orbital period P and
                     semi-amplitude K, sampled once per night with noise.
2. aliasing.png    — the trap: a P=10 d orbit and its 1-cycle/day alias
                     (P≈0.91 d) pass through identical nightly samples; one
                     off-cadence observation separates them.
3. periodogram.png — how astronomers find candidates: chi2 of a sinusoid fit
                     at each trial frequency for a real dev fixture's six
                     initial points, showing the near-equal alias peaks.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from aliasbreaker.fitting import periodogram, chi2_constant

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
BLUE, PURPLE, GOLD, GREY = "#2f6fed", "#9b51e0", "#e0a020", "#666666"


def fig_rv_method():
    P, K, gamma, sigma = 10.0, 18.0, 3.0, 2.5
    t = np.linspace(0, 30, 600)
    v = gamma + K * np.sin(2 * np.pi * t / P)
    rng = np.random.default_rng(7)
    nights = np.arange(0, 30) + 0.15
    obs = gamma + K * np.sin(2 * np.pi * nights / P) + rng.normal(0, sigma, 30)

    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot(t, v, color=BLUE, lw=2, label="stellar radial velocity")
    ax.errorbar(nights, obs, yerr=sigma, fmt="o", color="black", ms=4,
                capsize=2, label="one measurement per night (±σ)")
    ax.axhline(gamma, color=GREY, lw=0.8, ls="--")
    ax.annotate("", xy=(2.5, gamma + K), xytext=(2.5, gamma),
                arrowprops=dict(arrowstyle="<->", color=GOLD, lw=1.5))
    ax.text(3.0, gamma + K / 2, "K (semi-amplitude)", color=GOLD, va="center")
    ax.annotate("", xy=(P + 2.5, gamma - K - 4), xytext=(2.5, gamma - K - 4),
                arrowprops=dict(arrowstyle="<->", color=GOLD, lw=1.5))
    ax.text(2.5 + P / 2, gamma - K - 7.5, "P (orbital period)", color=GOLD,
            ha="center")
    ax.set_xlabel("time (days)")
    ax.set_ylabel("radial velocity (m/s)")
    ax.set_title("The radial-velocity method: a planet makes its star wobble "
                 "along our line of sight")
    ax.legend(loc="upper right", frameon=False)
    ax.set_ylim(gamma - K - 11, gamma + K + 6)
    fig.tight_layout()
    fig.savefig(OUT / "rv-method.png")
    plt.close(fig)


def fig_aliasing():
    f_true, f_alias = 0.10, 1.10          # cycles/day: f_alias = f_true + 1
    t = np.linspace(0, 11, 3000)
    nights = np.arange(0, 11)
    off = 6.5

    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.plot(t, np.sin(2 * np.pi * f_true * t), color=BLUE, lw=2.2,
            label="true orbit, P = 10 d")
    ax.plot(t, np.sin(2 * np.pi * f_alias * t), color=PURPLE, lw=1.1,
            alpha=0.85, label="daily alias, P ≈ 0.91 d (f + 1 cycle/day)")
    ax.plot(nights, np.sin(2 * np.pi * f_true * nights), "o", color="black",
            ms=6, zorder=5, label="nightly samples — both orbits agree")
    y1, y2 = np.sin(2 * np.pi * f_true * off), np.sin(2 * np.pi * f_alias * off)
    ax.plot([off, off], [y1, y2], color=GOLD, lw=2, ls="--")
    ax.plot(off, y1, "o", color=GOLD, ms=8, zorder=6)
    ax.plot(off, y2, "o", mfc="none", mec=GOLD, mew=2, ms=8, zorder=6)
    ax.annotate("observe off-cadence and they separate",
                xy=(off, (y1 + y2) / 2), xytext=(7.2, 1.35), color=GOLD,
                arrowprops=dict(arrowstyle="->", color=GOLD))
    ax.set_xlabel("time (days)")
    ax.set_ylabel("normalized RV")
    ax.set_ylim(-1.6, 1.7)
    ax.set_title("The trap: two different orbits thread the same nightly points")
    ax.legend(loc="lower left", frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "aliasing.png")
    plt.close(fig)


def fig_periodogram():
    d = json.loads((ROOT / "data/cases/dev/case-101.json").read_text())
    t, y, sigma = np.array(d["init_t"]), np.array(d["init_y"]), d["sigma"]
    freqs, chi2s, df = periodogram(t, y, sigma)
    dchi2 = chi2_constant(y, sigma) - chi2s
    cands = d["candidates"]
    f_true = 1.0 / d["hidden"]["true_params"]["P"]

    fig, ax = plt.subplots(figsize=(9, 4.0))
    ax.plot(freqs, dchi2, color=BLUE, lw=1)
    top = float(dchi2.max())
    for P in cands:
        f = 1.0 / P
        i = int(np.argmin(np.abs(freqs - f)))
        ax.plot(f, dchi2[i], "o", color=PURPLE, ms=7, zorder=5)
        ax.annotate(f"P = {P:.2f} d", xy=(f, dchi2[i]),
                    xytext=(0, 12), textcoords="offset points", ha="center",
                    fontsize=9, color=PURPLE, fontweight="bold")
    ax.axvline(f_true, color=GOLD, lw=1, ls="--", label="true frequency")
    ax.set_ylim(-5, top * 1.22)
    ax.set_xlabel("trial frequency (cycles/day)")
    ax.set_ylabel("Δχ² improvement over a flat fit")
    ax.set_title("Periodogram of six nightly points (dev case-101): "
                 "three alias peaks fit almost equally well", fontsize=11)
    ax.legend(frameon=False, loc="center left")
    fig.tight_layout()
    fig.savefig(OUT / "periodogram.png")
    plt.close(fig)


if __name__ == "__main__":
    fig_rv_method()
    fig_aliasing()
    fig_periodogram()
    for name in ("rv-method", "aliasing", "periodogram"):
        p = OUT / f"{name}.png"
        print(f"{p.relative_to(ROOT)}  {p.stat().st_size // 1024} KB")
