"""EDA D — per-pool demand signals + predictability (GPU/cuDF + numpy).

The thesis's central quantitative claim, computed fresh on this trace:
how well does the request rate explain vision-pool work (constant-fraction
fit), and how predictable is each signal at horizons that matter for
autoscaling (autocorrelation vs replica cold-start times)?
"""
import numpy as np
import pandas as pd

from _common import C_AQUA, C_BLUE, C_YELLOW, load_trace, plt, save_fig, save_stats

df = load_trace()

w = df.assign(win=df["ts"].dt.floor("min")).groupby("win").agg(
    requests=("NumImages", "count"), images=("NumImages", "sum"),
    ctx=("ContextTokens", "sum"), gen=("GeneratedTokens", "sum"),
).sort_index().to_pandas()
full = pd.date_range(w.index.min(), w.index.max(), freq="min")
w = w.reindex(full, fill_value=0)

req = (w["requests"] / 60).to_numpy(dtype=float)
img = (w["images"] / 60).to_numpy(dtype=float)
ctx = (w["ctx"] / 60).to_numpy(dtype=float)
gen = (w["gen"] / 60).to_numpy(dtype=float)
stats = {}

# --- constant-fraction fit: images/s ~ alpha * requests/s (the strawman) ---
alpha = float((img @ req) / (req @ req))
resid = img - alpha * req
r2 = 1.0 - float((resid @ resid) / ((img - img.mean()) @ (img - img.mean())))
stats["constant_fraction_fit"] = {"alpha_img_per_req": alpha, "r2": r2}

# pearson correlations between pool signals
def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])

stats["pearson_1min"] = {
    "img_vs_req": corr(img, req),
    "ctx_vs_req": corr(ctx, req),
    "gen_vs_req": corr(gen, req),
    "img_vs_ctx": corr(img, ctx),
}

# --- autocorrelation (predictability horizon proxy) ---
def acf(x, max_lag):
    x = x - x.mean()
    var = x @ x
    return np.array([1.0] + [float((x[:-k] @ x[k:]) / var) for k in range(1, max_lag + 1)])

LAGS = 240  # minutes
acf_img, acf_req = acf(img, LAGS), acf(req, LAGS)
def horizon(a, level=0.5):
    below = np.nonzero(a < level)[0]
    return int(below[0]) if len(below) else LAGS

stats["acf_1min"] = {
    "img_halflife_minutes": horizon(acf_img),
    "req_halflife_minutes": horizon(acf_req),
    "img_acf_at": {m: float(acf_img[m]) for m in [1, 5, 15, 60, 120]},
    "req_acf_at": {m: float(acf_req[m]) for m in [1, 5, 15, 60, 120]},
}

save_stats("d_signals_stats.json", stats)

# --- figures ---
# 1. images/s vs requests/s scatter with the constant-fraction line
fig, ax = plt.subplots(figsize=(5, 3.6))
ax.plot(req, img, ".", color=C_BLUE, markersize=2, alpha=0.25, rasterized=True)
xs = np.linspace(0, req.max(), 50)
ax.plot(xs, alpha * xs, color=C_YELLOW, linewidth=1.8,
        label=f"constant fraction: {alpha:.1f} img/req (R²={r2:.2f})")
ax.set_xlabel("requests/s (1-min windows)")
ax.set_ylabel("images/s")
ax.set_title("Vision work is poorly explained by request rate")
ax.legend(frameon=False)
save_fig(fig, "d_img_vs_req_scatter.png")

# 2. ACF comparison (identity by fixed slots; one axis, indexed correlation)
fig, ax = plt.subplots(figsize=(6, 3.2))
lags = np.arange(LAGS + 1)
ax.plot(lags, acf_img, color=C_BLUE, label="images/s")
ax.plot(lags, acf_req, color=C_AQUA, label="requests/s")
ax.axhline(0.5, color="#9ca3af", linewidth=0.8, linestyle="--")
ax.annotate("0.5", xy=(LAGS, 0.5), xytext=(2, 2), textcoords="offset points",
            fontsize=8, color="#6b7280")
ax.set_xlabel("lag (minutes)")
ax.set_ylabel("autocorrelation")
ax.set_title("Demand-signal memory — forecast horizon material for both pools")
ax.legend(frameon=False)
save_fig(fig, "d_acf.png")

print("\nKey readout:")
print(f"constant-fraction fit: alpha={alpha:.1f} img/req, R²={r2:.3f}")
print(f"pearson img~req={stats['pearson_1min']['img_vs_req']:.3f}, "
      f"ctx~req={stats['pearson_1min']['ctx_vs_req']:.3f}, gen~req={stats['pearson_1min']['gen_vs_req']:.3f}")
print(f"ACF half-life: images {stats['acf_1min']['img_halflife_minutes']} min, "
      f"requests {stats['acf_1min']['req_halflife_minutes']} min")
print(f"ACF@5min: img={stats['acf_1min']['img_acf_at'][5]:.2f} req={stats['acf_1min']['req_acf_at'][5]:.2f}")
