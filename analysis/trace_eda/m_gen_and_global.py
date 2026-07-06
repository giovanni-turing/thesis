"""EDA M — decode-signal symmetry + consolidated global percentile tables (GPU).

Completes the per-pool symmetry: gives gen-tokens/s (decode demand) the same
rate-signal treatment as images/s and ctx/s (CV², constant-fraction fit, ACF
half-life, spectral slope, burst-vs-calm), and emits ONE consolidated global
stats table: request-level marginals and 1-min rate signals, with percentiles
p1/p10/p50/p90/p95/p99/p99.9/max, for all four signals.
"""
import cupy as cp
import numpy as np
import pandas as pd

from _common import C_AQUA, load_trace, plt, save_fig, save_stats

df = load_trace()
QS = [0.01, 0.10, 0.50, 0.90, 0.95, 0.99, 0.999]
QNAMES = ["p1", "p10", "p50", "p90", "p95", "p99", "p99.9"]

# ---------- 1-min rate signals (zero-filled) ----------
df = df.assign(win=df["ts"].dt.floor("min"))
w = df.groupby("win").agg(
    requests=("NumImages", "count"), images=("NumImages", "sum"),
    ctx=("ContextTokens", "sum"), gen=("GeneratedTokens", "sum"),
).sort_index().to_pandas()
w = w.reindex(pd.date_range(w.index.min(), w.index.max(), freq="min"), fill_value=0)
rates = {
    "requests_per_s": w["requests"] / 60.0,
    "images_per_s": w["images"] / 60.0,
    "ctx_tokens_per_s": w["ctx"] / 60.0,
    "gen_tokens_per_s": w["gen"] / 60.0,
}

# ---------- decode-signal treatment (symmetry with D/F/G) ----------
gen = rates["gen_tokens_per_s"].to_numpy(dtype=float)
req = rates["requests_per_s"].to_numpy(dtype=float)
alpha = float((gen @ req) / (req @ req))
resid = gen - alpha * req
r2 = 1.0 - float((resid @ resid) / ((gen - gen.mean()) @ (gen - gen.mean())))

def acf_halflife(x, max_lag=240, level=0.5):
    x = x - x.mean()
    var = x @ x
    for k in range(1, max_lag + 1):
        if (x[:-k] @ x[k:]) / var < level:
            return k
    return max_lag

# spectral slope on per-second gen series (CuPy FFT)
gs = df.assign(win_s=df["ts"].dt.floor("s")).groupby("win_s")["GeneratedTokens"].sum() \
       .sort_index().to_pandas()
gs = gs.reindex(pd.date_range(gs.index.min(), gs.index.max(), freq="s"), fill_value=0)
x = cp.asarray(gs.to_numpy(), dtype=cp.float64); x -= x.mean()
p = cp.asnumpy(cp.abs(cp.fft.rfft(x)) ** 2 / len(x))[1:]
f = cp.asnumpy(cp.fft.rfftfreq(len(x), d=1.0))[1:]
edges = np.logspace(np.log10(f[0]), np.log10(f[-1]), 400)
idx = np.digitize(f, edges)
fb = np.array([f[idx == i].mean() for i in range(1, 400) if (idx == i).any()])
pb = np.array([p[idx == i].mean() for i in range(1, 400) if (idx == i).any()])
band = (fb > 1 / (12 * 3600)) & (fb < 1 / 600)
beta = -np.polyfit(np.log10(fb[band]), np.log10(pb[band]), 1)[0]

# burst-vs-calm decode behavior (bursts defined on the image signal, §C/I)
img_rate = rates["images_per_s"]
thr = img_rate.quantile(0.99)
burst_mask = img_rate > thr
gen_burst = rates["gen_tokens_per_s"][burst_mask]
gen_calm = rates["gen_tokens_per_s"][~burst_mask]
req_gen = df["GeneratedTokens"]
b_wins = set(w.index[burst_mask])
in_burst = df["win"].isin(list(b_wins))
gen_req_burst = df[in_burst]["GeneratedTokens"]
gen_req_calm = df[~in_burst]["GeneratedTokens"]

stats = {"gen_signal": {
    "tokens_per_s": {"mean": float(gen.mean()), "cv2": float((gen.std() / gen.mean()) ** 2),
                     "max": float(gen.max())},
    "constant_fraction_vs_req": {"alpha_tokens_per_req": alpha, "r2": r2},
    "acf_halflife_minutes": acf_halflife(gen),
    "spectral_slope_beta": float(beta),
    "hurst_from_beta": float((beta + 1) / 2),
    "burst_vs_calm": {
        "rate_mean_ratio": float(gen_burst.mean() / gen_calm.mean()),
        "per_request_p50_burst": float(gen_req_burst.quantile(0.5)),
        "per_request_p50_calm": float(gen_req_calm.quantile(0.5)),
    },
}}

# ---------- consolidated global percentile tables ----------
def qtable(s, is_gpu=False):
    out = {}
    for q, name in zip(QS, QNAMES):
        out[name] = float(s.quantile(q))
    out["max"] = float(s.max())
    out["mean"] = float(s.mean())
    return out

stats["global_request_level"] = {
    "NumImages": qtable(df["NumImages"]),
    "NumImages_imagebearing": qtable(df[df["NumImages"] > 0]["NumImages"]),
    "ContextTokens": qtable(df["ContextTokens"]),
    "GeneratedTokens": qtable(df["GeneratedTokens"]),
}
stats["global_rates_1min"] = {name: qtable(s) for name, s in rates.items()}
save_stats("m_gen_and_global_stats.json", stats)

# markdown table for the report
lines = ["| signal | mean | " + " | ".join(QNAMES) + " | max |",
         "| --- " * (len(QNAMES) + 3) + "|"]
for scope, tables in [("request-level", stats["global_request_level"]),
                      ("rate (1-min)", stats["global_rates_1min"])]:
    for name, t in tables.items():
        vals = " | ".join(f"{t[n]:,.0f}" if t[n] >= 10 else f"{t[n]:.2f}" for n in QNAMES)
        lines.append(f"| {scope}: {name} | {t['mean']:,.1f} | {vals} | {t['max']:,.0f} |")
open("m_global_percentiles.md", "w").write("\n".join(lines) + "\n")

# figure: the decode signal over 7 days (completing the small-multiples set)
fig, ax = plt.subplots(figsize=(9, 2.4))
ax.plot(w.index, rates["gen_tokens_per_s"], color=C_AQUA, linewidth=0.7)
ax.set_ylabel("gen tokens/s")
ax.set_title(f"Decode demand signal (1-min) — CV²={stats['gen_signal']['tokens_per_s']['cv2']:.2f}, "
             f"ACF half-life {stats['gen_signal']['acf_halflife_minutes']} min, "
             f"H≈{stats['gen_signal']['hurst_from_beta']:.2f}")
fig.autofmt_xdate()
save_fig(fig, "m_gen_signal.png")

print("\nKey readout (decode signal):")
g = stats["gen_signal"]
print(f"gen tok/s: mean={g['tokens_per_s']['mean']:.0f} CV²={g['tokens_per_s']['cv2']:.2f}")
print(f"constant-fraction vs req: R²={r2:.3f} (alpha={alpha:.0f} tok/req)")
print(f"ACF half-life={g['acf_halflife_minutes']} min; H≈{g['hurst_from_beta']:.2f}")
print(f"burst-vs-calm: rate ratio {g['burst_vs_calm']['rate_mean_ratio']:.2f}x; "
      f"per-request gen p50 {g['burst_vs_calm']['per_request_p50_burst']:.0f} vs "
      f"{g['burst_vs_calm']['per_request_p50_calm']:.0f}")
print("\nglobal percentile table -> m_global_percentiles.md")
