"""Publication figures + LaTeX table bodies for the predictor-benchmark chapter.

Reads the assembled forecasts (results/*.parquet) and the precision metrics
(results/metrics/*.parquet) and emits:
  results/figures/pred_horizon_wape.png   per-horizon WAPE degradation, 1min
  results/figures/pred_forecast_band.png  forecast path + p10-p90 band on the
                                          largest in-span image burst, 1min
  results/figures/pred_wape_heatmap.png   overall point WAPE, all cells
plus (stdout) the LaTeX rows for the chapter tables and the key prose numbers.

Style matches analysis/trace_eda/_common.py (dataviz reference palette, light
mode; _common itself imports cuDF so the constants are replicated here).
Entity-fixed colors: chronos=blue, toto=aqua, timesfm=yellow; the stdlib
baselines are neutral grays distinguished by line style.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
METRICS = RESULTS / "metrics"
FIGDIR = RESULTS / "figures"
FIGDIR.mkdir(exist_ok=True)

C_BLUE, C_AQUA, C_YELLOW = "#2a78d6", "#1baf7a", "#eda100"
INK, MUTED = "#1f2430", "#6b7280"
GRAY_LIGHT, GRAY_MID, GRAY_DARK = "#b0b5bd", "#8a919c", "#4b5563"

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

VARIATES = ["requests", "images", "ctx", "gen"]
VLABEL = {"requests": "requests", "images": "images", "ctx": "context tokens", "gen": "generated tokens"}
RES_ORDER = ["1min", "45s", "30s", "15s", "1s"]
STYLE = {  # (label, color, linestyle) — entity-fixed, never re-assigned
    ("naive", "uni"): ("naive", GRAY_LIGHT, "--"),
    ("ewma", "uni"): ("EWMA", GRAY_MID, "-."),
    ("holt_winters", "uni"): ("Holt-Winters", GRAY_DARK, ":"),
    ("timesfm", "uni"): ("TimesFM", C_YELLOW, "-"),
    ("chronos", "uni"): ("Chronos-2", C_BLUE, "-"),
    ("toto", "uni"): ("Toto-2", C_AQUA, "-"),
}
ROW_ORDER = [
    ("naive", "uni"), ("ewma", "uni"), ("holt_winters", "uni"), ("timesfm", "uni"),
    ("chronos", "uni"), ("chronos", "cov"), ("toto", "uni"), ("toto", "cov"),
]
ROW_LABEL = {
    ("naive", "uni"): "naive", ("ewma", "uni"): "EWMA", ("holt_winters", "uni"): "Holt--Winters",
    ("timesfm", "uni"): "TimesFM", ("chronos", "uni"): "Chronos-2", ("chronos", "cov"): "Chronos-2 (cov)",
    ("toto", "uni"): "Toto-2", ("toto", "cov"): "Toto-2 (cov)",
}

by_h = pq.read_table(METRICS / "metrics_by_h.parquet").to_pandas()
overall = pq.read_table(METRICS / "metrics_overall.parquet").to_pandas()
h1 = pq.read_table(METRICS / "metrics_h1.parquet").to_pandas()
for df in (by_h, overall, h1):
    df.query("span == 'common'", inplace=True)


def fig_horizon() -> None:
    d = by_h.query("resolution == '1min' and candidate == 'point'")
    fig, axes = plt.subplots(2, 2, figsize=(8.4, 5.6), sharex=True)
    for ax, v in zip(axes.ravel(), VARIATES):
        for (model, mode), (label, color, ls) in STYLE.items():
            s = d.query("model == @model and mode == @mode and variate == @v").sort_values("h")
            ax.plot(s.h, 100 * s.wape, ls, color=color, label=label,
                    zorder=3 if mode == "uni" and model in ("chronos", "toto", "timesfm") else 2)
        ax.set_title(VLABEL[v], loc="left", color=INK)
        ax.set_xticks([1, 3, 6, 9, 12])
        ax.set_ylim(bottom=0)
    for ax in axes[1]:
        ax.set_xlabel("horizon step $h$")
    for ax in axes[:, 0]:
        ax.set_ylabel("WAPE (%)")
    axes[0, 0].legend(ncol=2, frameon=False, fontsize=8, loc="lower right")
    fig.suptitle("Point-forecast error across the horizon — 1-minute bins, common span",
                 x=0.02, ha="left", color=INK, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(FIGDIR / "pred_horizon_wape.png", bbox_inches="tight")
    plt.close(fig)


def fig_band() -> tuple[str, str]:
    """Largest 1-min image burst inside a covariate model's span; returns (model, peak ts)."""
    toto = pq.read_table(RESULTS / "toto_covariates.parquet").to_pandas().query(
        "resolution == '1min' and variate == 'images'")
    chron = pq.read_table(RESULTS / "chronos_covariates.parquet").to_pandas().query(
        "resolution == '1min' and variate == 'images'")
    # Prefer chronos/cov (the 1min images winner) if the week's tallest in-toto-span
    # burst is inside its shorter span too; otherwise fall back to toto/cov.
    peak_step = int(toto.loc[toto.y_true.idxmax(), "step"])
    d, name = (chron, "chronos") if peak_step >= chron.step.min() else (toto, "toto")
    d = d.sort_values("step").reset_index(drop=True)
    peak = d.y_true.idxmax()
    w = d.iloc[max(0, peak - 150) : peak + 150]

    fig, ax = plt.subplots(figsize=(8.4, 3.4))
    ts, scale = pd.to_datetime(w.ts), 1 / 60.0  # per-minute counts -> images/s
    ax.fill_between(ts, w.p10 * scale, w.p90 * scale, color=C_BLUE, alpha=0.18, linewidth=0,
                    label="p10–p90 band")
    ax.plot(ts, w.y_true * scale, color=INK, linewidth=1.2, label="observed")
    ax.plot(ts, w.point * scale, color=C_BLUE, linewidth=1.6, label="point forecast")
    naive = pq.read_table(RESULTS / "naive_images.parquet").to_pandas().query(
        "resolution == '1min'").sort_values("step")
    nv = naive[naive.step.isin(w.step)]
    ax.plot(pd.to_datetime(nv.ts), nv.point * scale, "--", color=GRAY_MID, linewidth=1.2,
            label="naive")
    ax.set_ylabel("images/s")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper left")
    model_label = "Chronos-2 (cov)" if name == "chronos" else "Toto-2 (cov)"
    ax.set_title(f"{model_label}: stitched 12-step forecast path over the largest in-span image burst",
                 loc="left", color=INK)
    fig.tight_layout()
    fig.savefig(FIGDIR / "pred_forecast_band.png", bbox_inches="tight")
    plt.close(fig)
    return name, str(w.loc[w.y_true.idxmax(), "ts"])


def fig_heatmap() -> None:
    d = overall.query("candidate == 'point'")
    cols = [(v, r) for v in VARIATES for r in RES_ORDER]
    M = np.full((len(ROW_ORDER), len(cols)), np.nan)
    for i, (model, mode) in enumerate(ROW_ORDER):
        s = d.query("model == @model and mode == @mode").set_index(["variate", "resolution"]).wape
        for j, key in enumerate(cols):
            M[i, j] = 100 * s.get(key, np.nan)
    rel = M / np.nanmin(M, axis=0, keepdims=True)  # ratio to column best

    fig, ax = plt.subplots(figsize=(10.4, 3.6))
    im = ax.imshow(np.clip(rel, 1, 2), cmap="Blues", vmin=1, vmax=2, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            best = rel[i, j] <= 1.0 + 1e-9
            ax.text(j, i, f"{M[i, j]:.0f}" if M[i, j] >= 9.95 else f"{M[i, j]:.1f}",
                    ha="center", va="center", fontsize=6.8,
                    color=INK, fontweight="bold" if best else "normal")
    ax.set_yticks(range(len(ROW_ORDER)), [ROW_LABEL[k].replace("--", "–") for k in ROW_ORDER], fontsize=8)
    ax.set_xticks(range(len(cols)), [r for _, r in cols], fontsize=7)
    for k, v in enumerate(VARIATES):
        ax.text(k * 5 + 2, -0.9, VLABEL[v], ha="center", fontsize=9, color=INK)
        if k:
            ax.axvline(k * 5 - 0.5, color="white", linewidth=2.5)
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01)
    cb.set_label("WAPE ÷ column best", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(FIGDIR / "pred_wape_heatmap.png", bbox_inches="tight")
    plt.close(fig)


def fmt_pct(x: float) -> str:
    return f"{100 * x:.1f}"


def tables() -> None:
    d = overall.query("candidate == 'point'")
    print("\n%% ---- T1: overall point WAPE (%), common span, 1min & 1s ----")
    for res in ("1min", "1s"):
        print(f"%% block {res}")
        sub = d.query("resolution == @res").set_index(["model", "mode", "variate"]).wape
        best = {v: min(sub.get((m, mo, v), np.inf) for m, mo in ROW_ORDER) for v in VARIATES}
        for m, mo in ROW_ORDER:
            cells = []
            for v in VARIATES:
                val = sub.get((m, mo, v), np.nan)
                s = fmt_pct(val)
                cells.append(rf"\textbf{{{s}}}" if val <= best[v] + 1e-12 else s)
            print(f"{ROW_LABEL[(m, mo)]} & " + " & ".join(cells) + r" \\")

    print("\n%% ---- T2: covariate effect, mean over variates of (cov-uni)/uni overall MAE, % ----")
    for model in ("chronos", "toto"):
        row = [ROW_LABEL[(model, "uni")].split(" ")[0]]
        for res in RES_ORDER:
            u = d.query("model == @model and mode == 'uni' and resolution == @res").set_index("variate").mae
            c = d.query("model == @model and mode == 'cov' and resolution == @res").set_index("variate").mae
            row.append(f"{100 * float(((c - u) / u).mean()):+.2f}")
        print(" & ".join(row) + r" \\")

    print("\n%% ---- T3: winner + best percentile per (variate, res in {1min,1s}) ----")
    oc = overall  # all candidates
    for res in ("1min", "1s"):
        for v in VARIATES:
            cell = oc.query("resolution == @res and variate == @v")
            pts = cell.query("candidate == 'point'").set_index(["model", "mode"]).mae
            (wm, wmode) = pts.idxmin()
            qs = cell.query("model == @wm and mode == @wmode and candidate != 'point'")
            bq = qs.loc[qs.mae.idxmin()]
            delta = 100 * (bq.mae / pts.min() - 1)
            print(f"{res} & {VLABEL[v]} & {ROW_LABEL[(wm, wmode)]} & {fmt_pct(pts.min() if v!='requests' else pts.min())}"
                  f" & {bq.candidate} & {delta:+.1f} \\\\  % winner point WAPE={fmt_pct(cell.query('candidate==\"point\"').wape.min())}")

    print("\n%% ---- prose numbers ----")
    hh = by_h.query("resolution == '1min' and candidate == 'point' and variate == 'images'")
    for m, mo in (("chronos", "cov"), ("toto", "cov"), ("naive", "uni"), ("ewma", "uni")):
        s = hh.query("model == @m and mode == @mo").sort_values("h")
        if len(s):
            print(f"images@1min {m}/{mo}: WAPE h1={fmt_pct(s.wape.iloc[0])} h12={fmt_pct(s.wape.iloc[-1])}")
    for res in ("1min", "1s"):
        cell = d.query("resolution == @res and variate == 'images'").set_index(["model", "mode"])
        print(f"images@{res} overall WAPE: " + ", ".join(
            f"{m}/{mo}={fmt_pct(cell.wape.get((m, mo), np.nan))}" for m, mo in ROW_ORDER))
    # h=1 winners table-let
    p1 = h1.query("candidate == 'point'")
    for res in ("1min", "1s"):
        line = []
        for v in VARIATES:
            c = p1.query("resolution == @res and variate == @v").set_index(["model", "mode"])
            (wm, wmode) = c.mae.idxmin()
            line.append(f"{v}:{wm}/{wmode}={fmt_pct(c.wape.min())}")
        print(f"h=1 winners @{res}: " + " | ".join(line))


if __name__ == "__main__":
    fig_horizon()
    band_model, band_peak = fig_band()
    fig_heatmap()
    print(f"band figure model: {band_model}, peak at {band_peak}")
    for f in ("pred_horizon_wape", "pred_forecast_band", "pred_wape_heatmap"):
        print("figure:", FIGDIR / f"{f}.png")
    tables()
