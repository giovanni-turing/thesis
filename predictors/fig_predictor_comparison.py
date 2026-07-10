#!/usr/bin/env python
"""Three-panel predictor-comparison figure — the 'why the framework differs' visual.

(a) Accuracy: image-signal WAPE, all predictors, coloured by class
    (foundation / classical / Dynamo-shipped) --- near-parity, deliberately.
(b) Closed-loop verdict: burst3 TTFT p99 by policy against the SLA line ---
    every shipped-predictor / mean-conversion policy FAILS; only p90 +
    tail-aware conversion PASSES. Accuracy does not explain this panel.
(c) Online fidelity: burst3 live-runtime vs offline-twin, both policies ---
    the closed-loop verdict reproduces on the real stack.

Data provenance (all ledgered):
  (a) predictors/results_dynamo/consolidated.json + results/metrics/metrics_h1.parquet
  (b) simulation/results/live51/twin_{re,fc}*.report.json + closedloop triad
  (c) simulation/results/live51/live_runs/{live_fc,live_re}/profile_export_aiperf.json
      vs twin_fc_p90 / twin_re
Style matches predictors/figures_tex.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIGOUT = ROOT / "figuras" / "pred" / "pred_framework_diff.png"

# --- thesis palette (from figures_tex.py) -------------------------------
C_BLUE, C_AQUA, C_YELLOW = "#2a78d6", "#1baf7a", "#eda100"
INK, MUTED = "#1f2430", "#6b7280"
GRAY_LIGHT, GRAY_MID, GRAY_DARK = "#b0b5bd", "#8a919c", "#4b5563"
C_PASS, C_FAIL = "#1baf7a", "#d1495b"   # status (green good / red critical)

plt.rcParams.update({
    "figure.dpi": 120, "savefig.dpi": 200, "font.size": 9,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "axes.titlesize": 10,
    "axes.grid": True, "grid.color": "#e5e7eb", "grid.linewidth": 0.6,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
})

# ======================================================================
# Panel (a) data — image-signal WAPE, 1min, h=1, point
# ======================================================================
shipped = json.load(open(HERE / "results_dynamo/consolidated.json"))["dynamo_predictors"]
m = pd.read_parquet(HERE / "results/metrics/metrics_h1.parquet")
img = m[(m.variate == "images") & (m.resolution == "1min")
        & (m.candidate == "point") & (m.span == "common")]
arch = {r.model + ("+cov" if r["mode"] == "cov" else ""): r.wape for _, r in img.iterrows()}

# class: foundation (blue), classical (grey), Dynamo-shipped (yellow)
# entity-fixed colour by CLASS, never by rank
FM = {"toto": arch.get("toto"), "timesfm": arch.get("timesfm"),
      "chronos": arch.get("chronos")}
CLASSICAL = {"ewma": arch.get("ewma"), "holt-winters": arch.get("holt_winters"),
             "naive": arch.get("naive")}
SHIPPED = {"arima": shipped["arima_1min"]["wape"], "prophet": shipped["prophet_1min"]["wape"],
           "kalman": shipped["kalman_1min"]["wape"]}
# constant == naive numerically; show once as naive/constant baseline
bars_a = []
for name, w in sorted(FM.items(), key=lambda kv: kv[1]):
    bars_a.append((name, w, C_BLUE, "foundation"))
for name, w in sorted(SHIPPED.items(), key=lambda kv: kv[1]):
    bars_a.append((name + "*", w, C_YELLOW, "Dynamo-shipped"))
for name, w in sorted(CLASSICAL.items(), key=lambda kv: kv[1]):
    bars_a.append((name, w, GRAY_MID, "classical"))

# ======================================================================
# Panel (b) data — burst3 closed-loop TTFT p99 by policy
# ======================================================================
def ttft(path):
    s = open(path).read()
    import re
    return float(re.search(r'"p99_ttft_ms":\s*([\d.]+)', s).group(1))

L = ROOT / "simulation/results/live51"
bars_b = [
    ("Dynamo\n(arima/kalman/\nprophet)", ttft(L / "twin_re.report.json"), C_FAIL),   # 3494.7
    ("forecast p50\n(mean conv.)", ttft(L / "twin_fc.report.json"), C_FAIL),          # 2164
    ("forecast p90\n(tail conv.)", ttft(L / "twin_fc_p90.report.json"), C_PASS),      # 651
]
SLA_MS = 1000.0

# ======================================================================
# Panel (c) data — burst3 online (live) vs offline (twin)
# ======================================================================
def ttft_aiperf(path):
    return json.load(open(path))["time_to_first_token"]["p99"]

LR = L / "live_runs"
online = {
    "forecast p90": (ttft_aiperf(LR / "live_fc/profile_export_aiperf.json"),
                     ttft(L / "twin_fc_p90_cap4.report.json")),
    "reactive": (ttft_aiperf(LR / "live_re/profile_export_aiperf.json"),
                 ttft(L / "twin_re_cap4.report.json")),
}

# ======================================================================
# Render
# ======================================================================
fig, (axa, axb, axc) = plt.subplots(1, 3, figsize=(9.6, 3.5))
fig.subplots_adjust(wspace=0.34, top=0.80, bottom=0.24, left=0.07, right=0.985)

# --- (a) accuracy ---
xa = range(len(bars_a))
labels_a = [b[0] for b in bars_a]
vals_a = [b[1] for b in bars_a]
cols_a = [b[2] for b in bars_a]
axa.bar(xa, vals_a, color=cols_a, width=0.72, zorder=3)
for x, v in zip(xa, vals_a):
    axa.text(x, v + 0.004, f"{v:.3f}", ha="center", va="bottom",
             fontsize=6.5, color=INK)
axa.set_xticks(list(xa))
axa.set_xticklabels(labels_a, rotation=45, ha="right", fontsize=7.5)
axa.set_ylim(0.50, 0.64)
axa.set_ylabel("WAPE (image signal, 1-min)")
axa.set_title("(a) forecast accuracy", loc="left", color=INK)
axa.margins(x=0.02)
# legend by class
from matplotlib.patches import Patch
axa.legend(handles=[Patch(color=C_BLUE, label="foundation"),
                    Patch(color=C_YELLOW, label="Dynamo-shipped$^*$"),
                    Patch(color=GRAY_MID, label="classical")],
           frameon=False, fontsize=7, loc="upper left", handlelength=1.1)

# --- (b) closed-loop verdict ---
xb = range(len(bars_b))
axb.bar(xb, [b[1] for b in bars_b], color=[b[2] for b in bars_b], width=0.6, zorder=3)
for x, (lab, v, c) in zip(xb, bars_b):
    axb.text(x, v + 60, f"{v:.0f}", ha="center", va="bottom", fontsize=7.5, color=INK)
axb.axhline(SLA_MS, color=INK, lw=1.1, ls="--", zorder=4)
axb.text(len(bars_b) - 0.5, SLA_MS + 60, "SLA 1000 ms", ha="right", va="bottom",
         fontsize=7, color=INK)
axb.set_xticks(list(xb))
axb.set_xticklabels([b[0] for b in bars_b], fontsize=7.5)
axb.set_ylabel("burst3 TTFT p99 (ms)")
axb.set_title("(b) closed-loop verdict", loc="left", color=INK)
axb.set_ylim(0, 3900)

# --- (c) online vs offline ---
import numpy as np
labels_c = list(online)
xc = np.arange(len(labels_c))
w = 0.34
live_v = [online[k][0] for k in labels_c]
off_v = [online[k][1] for k in labels_c]
axc.bar(xc - w / 2, live_v, w, color=C_BLUE, label="live runtime", zorder=3)
axc.bar(xc + w / 2, off_v, w, color=GRAY_MID, label="offline twin", zorder=3)
for x, v in zip(xc - w / 2, live_v):
    axc.text(x, v + 60, f"{v:.0f}", ha="center", va="bottom", fontsize=7, color=INK)
for x, v in zip(xc + w / 2, off_v):
    axc.text(x, v + 60, f"{v:.0f}", ha="center", va="bottom", fontsize=7, color=INK)
axc.axhline(SLA_MS, color=INK, lw=1.1, ls="--", zorder=4)
axc.set_xticks(xc)
axc.set_xticklabels(labels_c, fontsize=8)
axc.set_ylabel("burst3 TTFT p99 (ms)")
axc.set_title("(c) online fidelity", loc="left", color=INK)
axc.set_ylim(0, 3900)
axc.legend(frameon=False, fontsize=7.5, loc="upper left")

fig.suptitle("Accuracy does not explain the verdict: the framework differs in "
             "signal and conversion, and the verdict holds live",
             x=0.02, ha="left", color=INK, fontsize=10.5, y=0.965)

FIGOUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(FIGOUT, bbox_inches="tight")
print("wrote", FIGOUT)
# report the numbers used for a sanity read
print("(a) bars:", [(b[0], round(b[1], 3)) for b in bars_a])
print("(b) bars:", [(b[0].replace(chr(10), ' '), round(b[1])) for b in bars_b])
print("(c):", {k: (round(v[0]), round(v[1])) for k, v in online.items()})
