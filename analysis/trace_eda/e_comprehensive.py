"""EDA E — comprehensive: arrival process, distributions, correlations (GPU/cuDF).

1. Arrival process: inter-arrival CCDF vs exponential; per-second count pmf vs
   Poisson; Fano factor (index of dispersion) across window scales.
2. Distributions: ContextTokens / GeneratedTokens split by modality; tail
   indices (Hill); NumImages within multimodal.
3. Correlations: request-level Pearson+Spearman (overall & multimodal-only);
   ContextTokens×GeneratedTokens density; GeneratedTokens|NumImages;
   window-level matrix; lagged cross-correlation (does image load lead
   decode load?).
"""
import numpy as np
import pandas as pd

from _common import C_AQUA, C_BLUE, C_YELLOW, INK, MUTED, load_trace, plt, save_fig, save_stats

df = load_trace()
n = len(df)
stats = {}

mm = df[df["NumImages"] > 0]   # multimodal
to = df[df["NumImages"] == 0]  # text-only

# ============================== 1. ARRIVAL PROCESS ==============================
delta_s = (df["ts"].diff().dropna().astype("int64") / 1e9).to_numpy()  # seconds
lam = 1.0 / delta_s.mean()
stats["arrivals"] = {
    "mean_rate_req_per_s": float(lam),
    "interarrival_cv": float(delta_s.std() / delta_s.mean()),
    # memorylessness check: P(X > x) exponential ⇒ straight line on semilog
}

# Fano factor across scales: var/mean of counts per window
# cudf floor only accepts base units; build per-second counts once, then
# aggregate to coarser windows by integer-block sums.
c_sec = df.assign(win=df["ts"].dt.floor("s")).groupby("win").size().sort_index().to_pandas()
c_sec = c_sec.reindex(pd.date_range(c_sec.index.min(), c_sec.index.max(), freq="s"), fill_value=0)

fano, counts_cache = {}, {}
for name, secs in [("s", 1), ("10s", 10), ("min", 60), ("10min", 600), ("h", 3600)]:
    c = c_sec if secs == 1 else c_sec.groupby(np.arange(len(c_sec)) // secs).sum()
    counts_cache[name] = c
    fano[name] = float(c.var() / c.mean())
stats["fano_factor_by_window"] = fano

# per-second count pmf vs Poisson(lam)
c1 = counts_cache["s"]
maxk = int(c1.quantile(0.9999))
emp = c1.value_counts(normalize=True).sort_index()
emp = emp[emp.index <= maxk]
from math import exp, factorial, lgamma

def pois_pmf(k, l):
    return exp(k * np.log(l) - l - lgamma(k + 1))

pois = {k: pois_pmf(k, c1.mean()) for k in emp.index}

fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))
# (a) interarrival CCDF, semilog-y, exponential reference
v = np.sort(delta_s)
ccdf = 1.0 - np.arange(1, len(v) + 1) / len(v)
sub = slice(0, len(v), max(1, len(v) // 20000))
axes[0].semilogy(v[sub], ccdf[sub], color=C_BLUE, label="empirical")
xs = np.linspace(0, v.max(), 200)
axes[0].semilogy(xs, np.exp(-lam * xs), color=C_YELLOW, linestyle="--",
                 label=f"exponential (λ={lam:.2f}/s)")
axes[0].set_xlabel("inter-arrival (s)")
axes[0].set_ylabel("P(X > x)")
axes[0].set_title("Inter-arrival survival")
axes[0].legend(frameon=False, fontsize=8)
# (b) per-second counts vs Poisson
axes[1].plot(emp.index, emp.values, "o", color=C_BLUE, markersize=4, label="empirical")
axes[1].plot(list(pois.keys()), list(pois.values()), "s", color=C_YELLOW,
             markersize=3, linestyle="none", label=f"Poisson({c1.mean():.2f})")
axes[1].set_yscale("log")
axes[1].set_xlabel("requests in 1 s")
axes[1].set_ylabel("probability")
axes[1].set_title("Counts vs Poisson")
axes[1].legend(frameon=False, fontsize=8)
# (c) Fano factor vs window
keys = ["s", "10s", "min", "10min", "h"]
axes[2].plot(range(len(keys)), [fano[k] for k in keys], "o-", color=C_BLUE)
axes[2].axhline(1.0, color=MUTED, linewidth=0.8, linestyle="--")
axes[2].annotate("Poisson = 1", xy=(0.05, 1.0), xytext=(0, 4),
                 textcoords="offset points", fontsize=8, color=MUTED)
axes[2].set_xticks(range(len(keys)), ["1s", "10s", "1min", "10min", "1h"])
axes[2].set_yscale("log")
axes[2].set_ylabel("Fano factor (var/mean)")
axes[2].set_title("Overdispersion grows with scale")
save_fig(fig, "e_arrival_process.png")

# ============================== 2. DISTRIBUTIONS ==============================
def hill(x, k_frac=0.01):
    """Hill tail-index estimator on the top k_frac order statistics."""
    x = np.sort(x[x > 0])
    k = max(10, int(len(x) * k_frac))
    tail = x[-k:]
    return float(1.0 / np.mean(np.log(tail / tail[0]))) if tail[0] > 0 else None

for col in ["ContextTokens", "GeneratedTokens"]:
    stats[col] = {
        "text_only": {"p50": float(to[col].quantile(0.5)), "p99": float(to[col].quantile(0.99)),
                      "mean": float(to[col].mean())},
        "multimodal": {"p50": float(mm[col].quantile(0.5)), "p99": float(mm[col].quantile(0.99)),
                       "mean": float(mm[col].mean())},
        "hill_tail_index_top1pct": hill(df[col].to_numpy()),
    }
stats["NumImages_multimodal"] = {
    "p50": float(mm["NumImages"].quantile(0.5)), "p90": float(mm["NumImages"].quantile(0.9)),
    "p99": float(mm["NumImages"].quantile(0.99)),
    "hill_tail_index_top1pct": hill(mm["NumImages"].to_numpy()),
}

fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
for ax, col in [(axes[0], "ContextTokens"), (axes[1], "GeneratedTokens")]:
    for sub_df, color, label in [(to, C_AQUA, "text-only"), (mm, C_BLUE, "multimodal")]:
        vals = np.sort(sub_df[col].to_numpy())
        cc = 1.0 - np.arange(1, len(vals) + 1) / len(vals)
        ax.loglog(vals, cc, color=color, label=label)
    ax.set_xlabel(col)
    ax.set_ylabel("P(X > x)")
    ax.set_title(f"{col} by modality")
    ax.legend(frameon=False, fontsize=8)
save_fig(fig, "e_tokens_by_modality.png")

# ============================== 3. CORRELATIONS ==============================
cols = ["NumImages", "ContextTokens", "GeneratedTokens"]
pear_all = df[cols].to_pandas().corr(method="pearson")
spear_all = df[cols].to_pandas().corr(method="spearman")
spear_mm = mm[cols].to_pandas().corr(method="spearman")
stats["request_level_corr"] = {
    "pearson_all": pear_all.round(3).to_dict(),
    "spearman_all": spear_all.round(3).to_dict(),
    "spearman_multimodal_only": spear_mm.round(3).to_dict(),
}

# GeneratedTokens conditional on NumImages (well-populated square counts)
vc = mm["NumImages"].value_counts()
big = sorted(int(v) for v in vc[vc >= 1000].index.to_pandas())
gcond = {v: float(mm[mm["NumImages"] == v]["GeneratedTokens"].quantile(0.5)) for v in big}
stats["gen_median_by_numimages"] = gcond

# window-level (1min) matrix + lagged cross-correlation img->gen
w = df.assign(win=df["ts"].dt.floor("min")).groupby("win").agg(
    requests=("NumImages", "count"), images=("NumImages", "sum"),
    ctx=("ContextTokens", "sum"), gen=("GeneratedTokens", "sum"),
).sort_index().to_pandas()
w = w.reindex(pd.date_range(w.index.min(), w.index.max(), freq="min"), fill_value=0)
win_corr = w.corr(method="pearson")
stats["window_level_pearson_1min"] = win_corr.round(3).to_dict()

img_z = (w["images"] - w["images"].mean()) / w["images"].std()
gen_z = (w["gen"] - w["gen"].mean()) / w["gen"].std()
lags = range(-30, 31)
xcorr = {int(l): float((img_z.shift(l) * gen_z).mean()) for l in lags}
best_lag = max(xcorr, key=xcorr.get)
stats["img_gen_xcorr_1min"] = {"best_lag_minutes": best_lag, "best_corr": xcorr[best_lag],
                               "at_lag_0": xcorr[0]}

save_stats("e_comprehensive_stats.json", stats)

# figure: correlation heatmap (diverging, gray midpoint) + gen|images + xcorr
from matplotlib.colors import LinearSegmentedColormap

div = LinearSegmentedColormap.from_list("div", ["#e34948", "#e5e7eb", "#2a78d6"])
fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.4), constrained_layout=True)
im = axes[0].imshow(spear_all.values, cmap=div, vmin=-1, vmax=1)
axes[0].set_xticks(range(3), ["imgs", "ctx", "gen"])
axes[0].set_yticks(range(3), ["imgs", "ctx", "gen"])
for i in range(3):
    for j in range(3):
        axes[0].text(j, i, f"{spear_all.values[i, j]:.2f}", ha="center", va="center",
                     fontsize=9, color=INK)
axes[0].set_title("Request-level Spearman (all)")
fig.colorbar(im, ax=axes[0], shrink=0.8)

xs = list(gcond.keys())
axes[1].plot(xs, [gcond[v] for v in xs], "o-", color=C_BLUE, markersize=4)
axes[1].set_xscale("log")
axes[1].set_xlabel("NumImages")
axes[1].set_ylabel("median GeneratedTokens")
axes[1].set_title("median gen tokens | image count")

axes[2].plot(list(xcorr.keys()), list(xcorr.values()), color=C_BLUE)
axes[2].axvline(0, color=MUTED, linewidth=0.8)
axes[2].set_xlabel("lag (min) — img leads gen for lag>0")
axes[2].set_ylabel("cross-correlation")
axes[2].set_title(f"img/s × gen-tok/s xcorr (peak @ {best_lag} min)")
save_fig(fig, "e_correlations.png")

print("\nKey readout:")
print(f"arrival: rate={lam:.2f}/s, interarrival CV={stats['arrivals']['interarrival_cv']:.2f} "
      f"(1=Poisson); Fano 1s={fano['s']:.1f} -> 1h={fano['h']:.0f}")
print(f"tokens by modality: ctx p50 text-only={stats['ContextTokens']['text_only']['p50']:.0f} vs "
      f"multimodal={stats['ContextTokens']['multimodal']['p50']:.0f}; "
      f"gen p50 {stats['GeneratedTokens']['text_only']['p50']:.0f} vs "
      f"{stats['GeneratedTokens']['multimodal']['p50']:.0f}")
print(f"request-level Spearman: imgs~ctx={spear_all.loc['NumImages','ContextTokens']:.2f}, "
      f"imgs~gen={spear_all.loc['NumImages','GeneratedTokens']:.2f}, "
      f"ctx~gen={spear_all.loc['ContextTokens','GeneratedTokens']:.2f}")
print(f"window-level img~gen r={win_corr.loc['images','gen']:.2f}; "
      f"xcorr peak at lag {best_lag} min ({xcorr[best_lag]:.2f})")
