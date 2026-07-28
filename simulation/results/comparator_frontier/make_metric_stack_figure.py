#!/usr/bin/env python3
"""Vector figure for the convention-minimized metric stack (fig cl-metric):
cost versus encoder-delay burden on the aggregate span, every frontier arm on
one canvas. Two panels: (a) LEADING SYNTHESIS -- threshold-integrated total delay mass
(sum of all per-request delays = the area under the full exceedance-count
curve; no SLA cut, no percentile); (b) sensitivity -- excess mass over the
1 s evaluation SLA (one threshold of the swept grid). Reads metric_stack.json
(the tracked compute artifact); writes figuras/sim/sim_metric_frontier.pdf.
Deterministic (SOURCE_DATE_EPOCH=0 forced)."""
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.compression"] = 9
os.environ["SOURCE_DATE_EPOCH"] = "0"   # FORCED: byte-determinism regardless of caller env
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
TESE = HERE.parents[2]
ms = json.load(open(HERE / "metric_stack.json"))
arms = {r["arm"]: r for r in ms["arms"]}
INK, MUT = "#1a1a19", "#6f6e66"
COL = {"forecast_p90": "#eb6834", "reactive": "#1baf7a", "static_C8": "#2a78d6",
       "oracle_H0": "#008300"}

fam = sorted(((a, r) for a, r in arms.items() if a.startswith("warm_floor_")),
             key=lambda kv: kv[1]["worker_h"])

fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.3), facecolor="white")


MARK = {"forecast_p90": "o", "reactive": "s", "static_C8": "D",
        "oracle_H0": "^"}   # distinct shapes: grayscale/print safety


def draw(ax, yof, ylabel, logy, fam_labels, ann):
    fx = [r["worker_h"] for _, r in fam]
    fy = [yof(r) for _, r in fam]
    ax.plot(fx, fy, "-", color="#9ec5f4", lw=1.8, zorder=1)
    ax.scatter(fx, fy, s=18, color="#6da7ec", zorder=2)
    for a, r in fam:
        m = a.replace("warm_floor_", "")
        if m in fam_labels:
            dx, dy = fam_labels[m]
            ax.annotate(m, (r["worker_h"] * dx, yof(r) * dy),
                        color="#256abf", fontsize=8)
    for arm, size in (("forecast_p90", 95), ("reactive", 65),
                      ("static_C8", 65), ("oracle_H0", 70)):
        r = arms[arm]
        ax.scatter([r["worker_h"]], [yof(r)], s=size, color=COL[arm],
                   marker=MARK[arm], zorder=3, edgecolors="white",
                   linewidths=1.1)
    for arm, t, xy, ha in ann:
        ax.annotate(t, xy, color=COL[arm], fontsize=8.5, fontweight="bold", ha=ha)
    ax.set_xscale("log")
    if logy:
        ax.set_yscale("log")
    ax.grid(True, which="major", color="#e8e7e0", lw=0.5)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(MUT)
    ax.tick_params(colors=MUT, labelsize=8)
    ax.set_xticks([300, 500, 1000, 2000, 4000])
    ax.xaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xlabel("provisioned worker-hours, aggregate span (log)", color=INK, fontsize=9)
    ax.set_ylabel(ylabel, color=INK, fontsize=9)


# (a) leading synthesis: threshold-integrated total delay mass (10^3 request-s)
draw(axes[0], lambda r: r["total_delay_request_s"] / 1000.0,
     r"total encoder delay ($10^3$ request$\cdot$s)", False,
     {"M2": (1.02, 1.01), "M4": (0.88, 0.985), "M8": (1.0, 1.015),
      "M16": (1.0, 1.015), "M32": (0.97, 1.015)},
     [("forecast_p90", "forecast p90", (640, 29.1), "right"),
      ("reactive", "reactive (= floor $M{=}1$)", (770, 34.0), "left"),
      ("static_C8", "static $C{=}8$", (1130, 25.7), "left"),
      ("oracle_H0", "oracle", (325, 26.3), "left")])
axes[0].set_title("(a) threshold-integrated synthesis", color=INK, fontsize=9)

# (b) sensitivity: excess mass over the 1 s evaluation SLA
draw(axes[1], lambda r: r["violations"]["1000"]["excess_mass_request_s"],
     r"excess mass over 1 s (request$\cdot$s, log)", True,
     {"M2": (1.03, 1.08), "M4": (1.03, 1.08), "M8": (1.0, 0.72),
      "M16": (1.0, 1.25), "M32": (0.97, 1.15)},
     [("forecast_p90", "forecast p90", (640, 4600), "right"),
      ("reactive", "reactive", (770, 7500), "left"),
      ("static_C8", "static $C{=}8$", (1180, 470), "left"),
      ("oracle_H0", "oracle", (322, 700), "left")])
axes[1].set_title("(b) excess over 1 s (sensitivity)", color=INK, fontsize=9)
axes[1].set_xlim(280, 4800)
axes[1].set_ylim(15, 13000)

fig.tight_layout()
out = TESE / "figuras/sim/sim_metric_frontier.pdf"
fig.savefig(out, facecolor="white")
print("wrote", out)
