#!/usr/bin/env python
"""Phase 2.3 figure — per-pool load-vs-latency curves with saturation knees.

Reads results/sweeps/summary.json (built by sweep_load.py) and renders
results/sweeps/knees.png: two side-by-side panels (never dual y-axes) —
  left : language pool, TTFT p99 vs offered req/s
  right: vision pool,   encoder delay p99 vs offered img/s
log-log, placeholder-SLA threshold lines, ringed knee markers, hollow markers
where the vision queue is divergent (pool never drains).

Style follows predictors/figures_tex.py (thesis palette; entity-fixed colors:
window head2k=blue, burst1=aqua; linestyle poly=solid, aic=dashed).

Run with the eda venv (matplotlib):
    /home/gio/tese/eda/.venv/bin/python simulation/sweep_fig.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
SWEEPS = HERE / "results" / "sweeps"

# --- constants from predictors/figures_tex.py ---
C_BLUE, C_AQUA, C_YELLOW = "#2a78d6", "#1baf7a", "#eda100"
INK, MUTED = "#1f2430", "#6b7280"

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 200,
    "font.size": 9,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "axes.titlesize": 10,
    "axes.grid": True,
    "grid.color": "#e5e7eb",
    "grid.linewidth": 0.6,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "lines.linewidth": 1.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

WINDOW_COLOR = {"head2k": C_BLUE, "burst1": C_AQUA}  # entity-fixed, never re-assigned
TIMING_STYLE = {"poly": "-", "aic": "--"}


def curve_points(summary: dict, pool: str, window: str, timing: str) -> list[dict]:
    pts = [p for p in summary["points"]
           if p["pool"] == pool and p["window"] == window and p["timing"] == timing]
    return sorted(pts, key=lambda p: p["speedup"])


def draw_curve(ax, pts: list[dict], curve: dict, *, color: str, ls: str, label: str,
               xkey: str, metric,
               knee_label: tuple = (0, -15, "center", "top")) -> None:
    xs = [p["offered"][xkey] for p in pts]
    ys = [metric(p) for p in pts]
    ax.plot(xs, ys, ls, color=color, label=label, zorder=3)
    for p, x, y in zip(pts, xs, ys):
        divergent = bool(p.get("queue_divergent"))
        ax.plot([x], [y], "o", ms=4.5, zorder=4, color=color,
                markerfacecolor="white" if divergent else color,
                markeredgecolor=color if divergent else "white",
                markeredgewidth=1.2)
    # knee marker: ringed dot + annotation
    knee = curve.get("knee_speedup")
    if knee is not None:
        kp = next(p for p in pts if p["speedup"] == knee)
        kx, ky = kp["offered"][xkey], metric(kp)
        ax.plot([kx], [ky], "o", ms=9, color=color, markerfacecolor=color,
                markeredgecolor="white", markeredgewidth=2, zorder=5)
        censored = not curve.get("saturated_in_range", True)
        txt = f"knee s={knee:g}" + (" (censored)" if censored else "")
        dx, dy, ha, va = knee_label
        ax.annotate(txt, (kx, ky), textcoords="offset points", xytext=(dx, dy),
                    ha=ha, va=va, fontsize=8, color=INK, zorder=6)
    else:  # already over threshold at the smallest swept speedup
        x0, y0 = xs[0], ys[0]
        ax.annotate(f"saturated at s={pts[0]['speedup']:g}", (x0, y0),
                    textcoords="offset points", xytext=(6, 8), ha="left",
                    fontsize=8, color=INK, zorder=6)


def main() -> None:
    summary = json.loads((SWEEPS / "summary.json").read_text())
    thr = summary["thresholds"]

    fig, (ax_l, ax_v) = plt.subplots(1, 2, figsize=(9.6, 3.9), layout="constrained")

    # ---- left: language pool ----
    knee_labels = {("head2k", "poly"): (0, -15, "center", "top"),
                   ("head2k", "aic"): (0, 9, "center", "bottom"),
                   ("burst1", "poly"): (7, -3, "left", "top"),
                   ("burst1", "aic"): (7, -3, "left", "top")}
    for window, timing in (("head2k", "poly"), ("head2k", "aic"), ("burst1", "poly"),
                           ("burst1", "aic")):
        pts = curve_points(summary, "llm", window, timing)
        c = summary["curves"].get(f"llm|{window}|{timing}")
        if not pts or not c:
            continue
        draw_curve(ax_l, pts, c, color=WINDOW_COLOR[window], ls=TIMING_STYLE[timing],
                   label=f"{window} · {timing}", xkey="req_per_s",
                   metric=lambda p: p["ttft_ms"]["p99"],
                   knee_label=knee_labels[(window, timing)])
    t = thr["llm_ttft_p99_ms"]
    ax_l.axhline(t, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=2)
    ax_l.text(0.985, t * 1.12, f"threshold {t:g} ms (placeholder SLA)", ha="right",
              va="bottom", fontsize=7.5, color=MUTED, transform=ax_l.get_yaxis_transform())
    ax_l.set_xscale("log")
    ax_l.set_yscale("log")
    ax_l.set_xlabel("offered load (req/s, log)")
    ax_l.set_ylabel("TTFT p99 (ms, log)")
    ax_l.set_title("Language pool (dynamo.replay, 2 workers)", color=INK)
    ax_l.legend(frameon=False, fontsize=8, loc="upper left")

    # ---- right: vision pool ----
    for window in ("head2k", "burst1"):
        pts = curve_points(summary, "vision", window, "aic")
        c = summary["curves"].get(f"vision|{window}|aic")
        if not pts or not c:
            continue
        draw_curve(ax_v, pts, c, color=WINDOW_COLOR[window], ls="-",
                   label=f"{window}", xkey="img_per_s",
                   metric=lambda p: p["encoder_delay_ms"]["p99"],
                   knee_label=(7, -11, "left", "top"))
    t = thr["vision_encoder_delay_p99_ms"]
    ax_v.axhline(t, color=MUTED, lw=1, ls=(0, (4, 3)), zorder=2)
    ax_v.text(0.02, t * 1.12, f"threshold {t:g} ms (placeholder SLA)", ha="left",
              va="bottom", fontsize=7.5, color=MUTED, transform=ax_v.get_yaxis_transform())
    ax_v.set_xscale("log")
    ax_v.set_yscale("log")
    ax_v.set_xlabel("offered load (img/s, log)")
    ax_v.set_ylabel("encoder delay p99 (ms, log)")
    ax_v.set_title("Vision pool (converter FIFO, 2 encoder workers)", color=INK)
    handles, labels = ax_v.get_legend_handles_labels()
    any_divergent = any(bool(p.get("queue_divergent")) for p in summary["points"]
                        if p["pool"] == "vision")
    if any_divergent:
        handles.append(Line2D([], [], marker="o", ls="none", ms=4.5,
                              markerfacecolor="white", markeredgecolor=MUTED,
                              markeredgewidth=1.2))
        labels.append("queue divergent")
    ax_v.legend(handles, labels, frameon=False, fontsize=8, loc="upper left")

    fig.suptitle("Saturation knees per pool — arrival-speedup sweep on the Azure LMM trace "
                 "(2 encoder × 2 LLM workers)", fontsize=10.5, color=INK)
    out = SWEEPS / "knees.png"
    fig.savefig(out, bbox_inches="tight")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
