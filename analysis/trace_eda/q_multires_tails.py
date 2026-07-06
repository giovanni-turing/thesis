"""EDA Q — multi-resolution analysis + tail-regime marginals (GPU).

Part 1 — multi-resolution: how the four demand signals look as the binning
window grows (1s -> 60s): burstiness (CV²), observed peaks, and peak
attenuation. Quantifies what a monitoring stack sampling at coarse windows
does and does not see.

Part 2 — tail regimes: conditional marginal distributions (1D Gaussian KDEs
in log space, GPU) of the other variables given
  (a) large context   (ctx    >= request-level p99),
  (b) large image count (img  >= image-bearing p99),
  (c) high request-rate minutes (req/s >= window p99),
each against the global marginal. Plus regime-overlap statistics.
"""
import json
import os

import cupy as cp
import numpy as np
import pandas as pd

from _common import C_AQUA, C_BLUE, C_YELLOW, MUTED, load_trace, plt, save_fig, save_stats

HERE = os.path.dirname(os.path.abspath(__file__))
SERIES = os.path.join(HERE, "series")
C_VIOLET = "#4a3aa7"  # categorical slot 5

# ============================ Part 1: multi-resolution ============================
RES = [("1s", 1, "1s"), ("15s", 15, "15s"), ("30s", 30, "30s"),
       ("45s", 45, "45s"), ("60s", 60, "1min")]
SIGNALS = [("requests", C_AQUA), ("images", C_BLUE), ("ctx", C_YELLOW), ("gen", C_VIOLET)]

mr = {}
for name, secs, fname in RES:
    w = pd.read_parquet(os.path.join(SERIES, f"rates_{fname}.parquet"))
    mr[name] = {}
    for col, _ in SIGNALS:
        r = w[col].to_numpy(float) / secs
        mr[name][col] = {
            "mean": float(r.mean()), "cv2": float((r.std() / r.mean()) ** 2),
            "p99": float(np.quantile(r, 0.99)), "max": float(r.max()),
        }

atten = {col: {name: mr[name][col]["max"] / mr["1s"][col]["max"] for name, _, _ in RES}
         for col, _ in SIGNALS}

fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4), constrained_layout=True)
xs = [secs for _, secs, _ in RES]
for col, color in SIGNALS:
    axes[0].plot(xs, [mr[n][col]["cv2"] for n, _, _ in RES], "o-", color=color, label=col)
    axes[1].plot(xs, [atten[col][n] for n, _, _ in RES], "o-", color=color, label=col)
axes[0].set_xscale("log"); axes[0].set_yscale("log")
axes[0].set_xlabel("window (s)"); axes[0].set_ylabel("CV² of rate")
axes[0].set_title("Burstiness vs binning window")
axes[0].legend(frameon=False, fontsize=8)
axes[1].set_xscale("log")
axes[1].set_xlabel("window (s)"); axes[1].set_ylabel("observed peak / 1s peak")
axes[1].set_title("Peak attenuation under aggregation")
save_fig(fig, "q_multires.png")

# ============================ Part 2: tail regimes ============================
df = load_trace()
df = df.assign(win=df["ts"].dt.floor("min"))

thr_ctx = float(df["ContextTokens"].quantile(0.99))          # 35,932
img_pos = df[df["NumImages"] > 0]["NumImages"]
thr_img = float(img_pos.quantile(0.99))                      # 529
wreq = df.groupby("win").size().sort_index().to_pandas()
wreq = wreq.reindex(pd.date_range(wreq.index.min(), wreq.index.max(), freq="min"), fill_value=0)
thr_req = float(wreq.quantile(0.99))
hot_wins = set(wreq.index[wreq >= thr_req])
in_hot = df["win"].isin(list(hot_wins))

regimes = {
    "large_ctx": df["ContextTokens"] >= thr_ctx,
    "large_img": df["NumImages"] >= thr_img,
    "high_req_rate": in_hot,
}

def kde1d_gpu(vals, grid=None, npts=240):
    """Gaussian KDE of log10(1+x) values on GPU; returns (grid, density)."""
    x = cp.asarray(np.log10(1.0 + vals), dtype=cp.float32)
    n = len(x)
    h = float(1.06 * float(x.std()) * n ** (-0.2)) + 1e-6
    if grid is None:
        grid = cp.linspace(float(x.min()), float(x.max()), npts)
    else:
        grid = cp.asarray(grid, dtype=cp.float32)
    d2 = (grid[:, None] - x[None, :]) ** 2
    dens = cp.exp(-d2 / (2 * h * h)).sum(1) / (n * h * np.sqrt(2 * np.pi))
    return cp.asnumpy(grid), cp.asnumpy(dens)

VARS = ["NumImages", "ContextTokens", "GeneratedTokens"]
stats = {"multi_resolution": mr, "peak_attenuation_vs_1s": atten,
         "regime_thresholds": {"ctx_p99": thr_ctx, "img_p99_imagebearing": thr_img,
                               "req_per_min_p99": thr_req},
         "regimes": {}}

fig, axes = plt.subplots(3, 3, figsize=(11.5, 8.2), constrained_layout=True)
for ri, (rname, mask) in enumerate(regimes.items()):
    sub = df[mask]
    n_sub = len(sub)
    row = {"requests": int(n_sub), "share": float(n_sub / len(df)),
           "multimodal_share": float((sub["NumImages"] > 0).sum() / n_sub)}
    for vi, var in enumerate(VARS):
        gvals = df[var].to_numpy(float)
        svals = sub[var].to_numpy(float)
        gmax = np.log10(1.0 + gvals.max())
        grid = np.linspace(0, gmax, 240)
        _, gd = kde1d_gpu(gvals, grid)
        _, sd = kde1d_gpu(svals, grid)
        ax = axes[ri][vi]
        ax.plot(grid, gd, color=MUTED, linewidth=1.2, label="global")
        ax.plot(grid, sd, color=C_BLUE, linewidth=1.6, label=rname)
        ticks = [0, 1, 2, 3, 4, 5]
        ax.set_xticks([t for t in ticks if t <= gmax],
                      [f"{10**t - 1:,.0f}" for t in ticks if t <= gmax])
        ax.set_xlabel(var)
        if vi == 0:
            ax.set_ylabel("KDE density")
        if ri == 0 and vi == 0:
            ax.legend(frameon=False, fontsize=8)
        if ri == 0:
            ax.set_title(var, fontsize=9)
        row[var] = {"p50": float(np.median(svals)), "p50_global": float(np.median(gvals))}
    axes[ri][0].annotate(rname, xy=(-0.32, 0.5), xycoords="axes fraction",
                         rotation=90, va="center", fontsize=10, color="#1f2430")
    stats["regimes"][rname] = row

# regime overlap: are high-request minutes also high-image minutes?
wimg = df.groupby("win")["NumImages"].sum().sort_index().to_pandas()
wimg = wimg.reindex(wreq.index, fill_value=0)
hot_img_wins = set(wimg.index[wimg >= wimg.quantile(0.99)])
inter = len(hot_wins & hot_img_wins)
stats["window_regime_overlap"] = {
    "hot_req_minutes": len(hot_wins), "hot_img_minutes": len(hot_img_wins),
    "intersection": inter,
    "jaccard": inter / len(hot_wins | hot_img_wins),
}
save_fig(fig, "q_tail_regime_kdes.png")
save_stats("q_multires_tails_stats.json", stats)

print("\nKey readout:")
print("peak attenuation 1s->60s:",
      {c: round(atten[c]["60s"], 3) for c, _ in SIGNALS})
for rname, row in stats["regimes"].items():
    print(f"{rname}: share={row['share']:.2%} mm_share={row['multimodal_share']:.0%} "
          + " ".join(f"{v} p50={row[v]['p50']:.0f} (global {row[v]['p50_global']:.0f})"
                     for v in VARS))
o = stats["window_regime_overlap"]
print(f"hot-req ∩ hot-img minutes: {o['intersection']}/{o['hot_req_minutes']} "
      f"(jaccard {o['jaccard']:.2f})")
