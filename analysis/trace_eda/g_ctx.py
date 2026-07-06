"""EDA G — ContextTokens as a demand signal (GPU: cuDF + CuPy FFT).

ContextTokens/s IS the prefill-side load of the language pool (and, via the
r≈0.89 coupling with images/s, the co-signal of the vision pool). Dedicated
treatment:
  1. ctx-rate signal: burstiness, constant-fraction fit vs request rate,
     ACF half-life, spectral slope (predictability).
  2. Decomposition by modality: how much prefill volume is vision-borne,
     and how the mix moves over time.
  3. Distributional structure: modality mixture; burst vs calm shifts.
"""
import cupy as cp
import numpy as np
import pandas as pd

from _common import C_AQUA, C_BLUE, C_YELLOW, MUTED, load_trace, plt, save_fig, save_stats

df = load_trace()
stats = {}

df = df.assign(win=df["ts"].dt.floor("min"), is_mm=(df["NumImages"] > 0))
w = df.groupby("win").agg(
    requests=("ContextTokens", "count"),
    ctx=("ContextTokens", "sum"),
    images=("NumImages", "sum"),
).sort_index().to_pandas()
mm_ctx = df[df["is_mm"]].groupby("win")["ContextTokens"].sum().sort_index().to_pandas()
full = pd.date_range(w.index.min(), w.index.max(), freq="min")
w = w.reindex(full, fill_value=0)
w["ctx_mm"] = mm_ctx.reindex(full, fill_value=0)
w["ctx_to"] = w["ctx"] - w["ctx_mm"]

ctx = (w["ctx"] / 60).to_numpy(dtype=float)   # tokens/s
req = (w["requests"] / 60).to_numpy(dtype=float)

# --- 1. signal properties ---
alpha = float((ctx @ req) / (req @ req))
resid = ctx - alpha * req
r2 = 1.0 - float((resid @ resid) / ((ctx - ctx.mean()) @ (ctx - ctx.mean())))

def acf_halflife(x, max_lag=240, level=0.5):
    x = x - x.mean()
    var = x @ x
    for k in range(1, max_lag + 1):
        if (x[:-k] @ x[k:]) / var < level:
            return k
    return max_lag

# spectral slope on per-second ctx series
cs = df.assign(win_s=df["ts"].dt.floor("s")).groupby("win_s")["ContextTokens"].sum().sort_index().to_pandas()
cs = cs.reindex(pd.date_range(cs.index.min(), cs.index.max(), freq="s"), fill_value=0)
x = cp.asarray(cs.to_numpy(), dtype=cp.float64)
x = x - x.mean()
p = cp.asnumpy(cp.abs(cp.fft.rfft(x)) ** 2 / len(x))[1:]
f = cp.asnumpy(cp.fft.rfftfreq(len(x), d=1.0))[1:]
edges = np.logspace(np.log10(f[0]), np.log10(f[-1]), 400)
idx = np.digitize(f, edges)
fb = np.array([f[idx == i].mean() for i in range(1, 400) if (idx == i).any()])
pb = np.array([p[idx == i].mean() for i in range(1, 400) if (idx == i).any()])
band = (fb > 1 / (12 * 3600)) & (fb < 1 / 600)
beta = -np.polyfit(np.log10(fb[band]), np.log10(pb[band]), 1)[0]

stats["ctx_signal"] = {
    "tokens_per_s": {"mean": float(ctx.mean()), "p99": float(np.quantile(ctx, 0.99)),
                     "max": float(ctx.max()),
                     "cv2": float((ctx.std() / ctx.mean()) ** 2)},
    "constant_fraction_vs_req": {"alpha_tokens_per_req": alpha, "r2": r2},
    "acf_halflife_minutes": acf_halflife(ctx),
    "spectral_slope_beta": float(beta),
    "hurst_from_beta": float((beta + 1) / 2),
}

# --- 2. modality decomposition of prefill volume ---
share_mm = float(w["ctx_mm"].sum() / w["ctx"].sum())
share_series = (w["ctx_mm"] / w["ctx"].replace(0, np.nan)).fillna(0)
stats["prefill_volume"] = {
    "share_from_multimodal": share_mm,
    "share_of_requests_multimodal": float(df["is_mm"].sum() / len(df)),
    "minute_share_mm_p10_p90": [float(share_series.quantile(0.1)), float(share_series.quantile(0.9))],
}

# --- 3. burst vs calm composition ---
img_rate = w["images"] / 60
thr = img_rate.quantile(0.99)
burst_min = set(w.index[img_rate > thr])
df_burst_flag = df.assign(in_burst=df["win"].isin(list(burst_min)))
qs = [0.5, 0.9, 0.99]
b = df_burst_flag[df_burst_flag["in_burst"]]["ContextTokens"]
q_ = df_burst_flag[~df_burst_flag["in_burst"]]["ContextTokens"]
stats["ctx_burst_vs_calm"] = {
    "burst": {str(q): float(b.quantile(q)) for q in qs},
    "calm": {str(q): float(q_.quantile(q)) for q in qs},
    "mean_ratio_burst_over_calm": float(b.mean() / q_.mean()),
}

save_stats("g_ctx_stats.json", stats)

# --- figures ---
# 1. prefill volume decomposition over the 7 days (stacked, 2 series, 2px gap via edge)
fig, axes = plt.subplots(2, 1, figsize=(9, 4.4), sharex=True,
                         height_ratios=[2, 1])
axes[0].fill_between(w.index, 0, w["ctx_to"] / 60, color=C_AQUA, alpha=0.85,
                     linewidth=0, label="text-only prefill")
axes[0].fill_between(w.index, w["ctx_to"] / 60, w["ctx"] / 60, color=C_BLUE, alpha=0.85,
                     linewidth=0, label="multimodal prefill")
axes[0].set_ylabel("context tokens/s")
axes[0].set_title(f"Prefill volume by modality — multimodal carries {share_mm:.0%} of tokens "
                  f"({stats['prefill_volume']['share_of_requests_multimodal']:.0%} of requests)")
axes[0].legend(frameon=False, fontsize=8, loc="upper right")
axes[1].plot(w.index, share_series.rolling(30, min_periods=1).mean(), color=C_BLUE, linewidth=0.8)
axes[1].axhline(share_mm, color=MUTED, linewidth=0.8, linestyle="--")
axes[1].set_ylabel("mm share (30-min avg)")
axes[1].set_ylim(0, 1)
fig.autofmt_xdate()
save_fig(fig, "g_ctx_decomposition.png")

# 2. ctx distribution: modality mixture (log-x hist) + burst-vs-calm CCDF
fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
bins = np.logspace(0, np.log10(float(df["ContextTokens"].max()) + 1), 120)
for sub, color, label in [(df[~df["is_mm"]], C_AQUA, "text-only"),
                          (df[df["is_mm"]], C_BLUE, "multimodal")]:
    axes[0].hist(sub["ContextTokens"].to_numpy(), bins=bins, histtype="step",
                 color=color, linewidth=1.4, label=label)
axes[0].set_xscale("log")
axes[0].set_yscale("log")
axes[0].set_xlabel("ContextTokens per request")
axes[0].set_ylabel("requests")
axes[0].set_title("Prefill-length mixture by modality")
axes[0].legend(frameon=False, fontsize=8)
for series, color, label in [(q_, C_AQUA, "calm minutes"), (b, C_YELLOW, "burst minutes")]:
    vals = np.sort(series.to_numpy())
    cc = 1.0 - np.arange(1, len(vals) + 1) / len(vals)
    axes[1].loglog(vals, cc, color=color, label=label)
axes[1].set_xlabel("ContextTokens per request")
axes[1].set_ylabel("P(X > x)")
axes[1].set_title("Prefill length: burst vs calm")
axes[1].legend(frameon=False, fontsize=8)
save_fig(fig, "g_ctx_mixture_burst.png")

print("\nKey readout:")
s = stats["ctx_signal"]
print(f"ctx tokens/s: mean={s['tokens_per_s']['mean']:.0f} max={s['tokens_per_s']['max']:.0f} "
      f"CV²={s['tokens_per_s']['cv2']:.2f}")
print(f"constant-fraction vs req: alpha={alpha:.0f} tok/req, R²={r2:.3f}")
print(f"ACF half-life={s['acf_halflife_minutes']} min; beta={beta:.2f} (H≈{(beta+1)/2:.2f})")
print(f"prefill volume from multimodal: {share_mm:.1%} "
      f"(requests: {stats['prefill_volume']['share_of_requests_multimodal']:.1%})")
print(f"burst-vs-calm ctx p50: {stats['ctx_burst_vs_calm']['burst']['0.5']:.0f} vs "
      f"{stats['ctx_burst_vs_calm']['calm']['0.5']:.0f} "
      f"(mean ratio {stats['ctx_burst_vs_calm']['mean_ratio_burst_over_calm']:.2f}x)")
