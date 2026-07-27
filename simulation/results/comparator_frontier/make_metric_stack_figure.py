#!/usr/bin/env python3
"""Vector figure for the convention-free metric stack (tab/fig cl-metric):
cost vs violation intensity on the aggregate span, every frontier arm on one
canvas. Reads metric_stack.json (the tracked compute artifact); writes
figuras/sim/sim_metric_frontier.pdf. Deterministic (SOURCE_DATE_EPOCH=0)."""
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["pdf.compression"] = 9
os.environ.setdefault("SOURCE_DATE_EPOCH", "0")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
TESE = HERE.parents[2]
ms = json.load(open(HERE / "metric_stack.json"))
arms = {r["arm"]: r for r in ms["arms"]}
INK, MUT = "#1a1a19", "#6f6e66"
COL = {"forecast_p90": "#eb6834", "reactive": "#1baf7a", "static_C8": "#2a78d6",
       "oracle_H0": "#008300"}

fig, ax = plt.subplots(figsize=(6.4, 4.3), facecolor="white")

fam = sorted(((a, r) for a, r in arms.items() if a.startswith("warm_floor_")),
             key=lambda kv: kv[1]["worker_h"])
fx = [r["worker_h"] for _, r in fam]
fy = [r["violations"]["1000"]["excess_mass_request_s"] for _, r in fam]
ax.plot(fx, fy, "-", color="#9ec5f4", lw=1.4, zorder=1)
ax.scatter(fx, fy, s=18, color="#6da7ec", zorder=2)
for a, r in fam:
    m = a.replace("warm_floor_", "")
    if m in ("M2", "M4", "M6", "M12", "M32"):
        ax.annotate(m, (r["worker_h"] * 1.03, r["violations"]["1000"]["excess_mass_request_s"] * 1.08),
                    color="#256abf", fontsize=7)

for arm, size in (("forecast_p90", 90), ("reactive", 60), ("static_C8", 60), ("oracle_H0", 60)):
    r = arms[arm]
    ax.scatter([r["worker_h"]], [r["violations"]["1000"]["excess_mass_request_s"]],
               s=size, color=COL[arm], zorder=3, edgecolors="white", linewidths=1.1)
for arm, t, xy, ha in (
        ("forecast_p90", "forecast p90", (655, 4600), "right"),
        ("reactive", "reactive (= floor $M{=}1$)", (760, 7500), "left"),
        ("static_C8", "static $C{=}8$", (1120, 350), "left"),
        ("oracle_H0", "oracle", (322, 700), "left")):
    ax.annotate(t, xy, color=COL[arm], fontsize=8.5, fontweight="bold", ha=ha)
ax.annotate("warm-floor family\n(standing capacity)", (1500, 135),
            color="#256abf", fontsize=7.5, style="italic", linespacing=1.3)

ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(280, 4800); ax.set_ylim(15, 13000)
ax.grid(True, which="major", color="#e8e7e0", lw=0.5)
ax.set_axisbelow(True)
for sp in ("top", "right"): ax.spines[sp].set_visible(False)
for sp in ("left", "bottom"): ax.spines[sp].set_color(MUT)
ax.tick_params(colors=MUT, labelsize=8)
ax.set_xlabel("provisioned worker-hours, aggregate span (log)", color=INK, fontsize=9)
ax.set_ylabel(r"excess mass over 1 s (request$\cdot$s, log)", color=INK, fontsize=9)
fig.tight_layout()
out = TESE / "figuras/sim/sim_metric_frontier.pdf"
fig.savefig(out, facecolor="white")
print("wrote", out)
