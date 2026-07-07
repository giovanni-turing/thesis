"""Burst-episode vision-pool queue dynamics figure for the thesis chapter.

Reads the per-second series of the vision burst1 sweep point at s=1 (the
trace's own recorded rate) and renders offered image rate vs queue depth —
the FIFO head-of-line story: SLA-relevant backlog at low mean utilization.

Style matches predictors/figures_tex.py (dataviz reference palette).
Run with the eda venv:  ../eda/.venv/bin/python burst_queue_fig.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
SERIES = HERE / "results" / "sweeps" / "series" / "vision_burst1_s1.series.json"
OUT = HERE / "results" / "sweeps" / "burst_queue.png"

C_BLUE, C_AQUA = "#2a78d6", "#1baf7a"
INK, MUTED = "#1f2430", "#6b7280"
plt.rcParams.update({
    "figure.dpi": 120, "savefig.dpi": 200, "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "axes.titlesize": 10,
    "axes.grid": True, "grid.color": "#e5e7eb", "grid.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED, "lines.linewidth": 1.6,
    "axes.spines.top": False, "axes.spines.right": False,
})

series = json.load(open(SERIES))["series"]
point = json.load(open(HERE / "results" / "sweeps" / "vision_burst1_aic_s1.json"))
util_pct = round(point["encoder_utilization"] * 100)
n_workers = point["encoder_workers"]
t_h = np.array([s["t"] for s in series]) / 3600.0
arrived = np.array([s["img_arrived"] for s in series], dtype=float)
queue = np.array([s["queue_imgs_end"] for s in series], dtype=float)
busy = np.array([s["busy_workers_end"] for s in series], dtype=float)

kernel = np.ones(60) / 60.0  # 1-min mean of the per-second arrival rate
arr_1min = np.convolve(arrived, kernel, mode="same")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.4, 4.6), sharex=True,
                               gridspec_kw={"height_ratios": [1, 1.2]})
ax1.fill_between(t_h, arr_1min, color=C_AQUA, alpha=0.35, linewidth=0)
ax1.plot(t_h, arr_1min, color=C_AQUA, linewidth=1.0)
ax1.set_ylabel("offered images/s\n(1-min mean)")
ax1.set_ylim(bottom=0)
ax1.set_title("Vision pool over the largest burst episode at the trace's own rate "
              f"({n_workers} workers, mean utilization {util_pct}%)",
              loc="left", color=INK)

ax2.plot(t_h, queue, color=C_BLUE, linewidth=1.0)
ax2.set_ylabel("queued images")
ax2.set_xlabel("hours into the episode window")
ax2.set_ylim(bottom=0)
peak = int(queue.argmax())
ax2.annotate(f"peak {int(queue[peak]):,} images queued",
             xy=(t_h[peak], queue[peak]), xytext=(t_h[peak] - 3.4, queue[peak] * 0.86),
             color=INK, fontsize=8,
             arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.8))

fig.tight_layout()
fig.savefig(OUT, bbox_inches="tight")
print("figure:", OUT)
print(f"peak queue {int(queue.max())} at t={series[peak]['t']}s; "
      f"seconds queue>1000: {(queue > 1000).sum()}; busy max {int(busy.max())}")
