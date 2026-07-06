"""EDA B — marginal distributions per pool (GPU/cuDF).

Vision pool: NumImages (text-only share, perfect-square structure, tail).
Language pool: ContextTokens (prefill load), GeneratedTokens (decode load).
"""
import numpy as np

from _common import C_AQUA, C_BLUE, load_trace, plt, save_fig, save_stats

df = load_trace()
n = len(df)
stats = {}

# --- NumImages ---
vc = df["NumImages"].value_counts().sort_index().to_pandas()
img = df[df["NumImages"] > 0]["NumImages"]
qs = [0.5, 0.9, 0.99, 0.999]
stats["numimages"] = {
    "share_text_only": float((df["NumImages"] == 0).sum() / n),
    "distinct_values": int(len(vc)),
    "all_perfect_squares": bool(all(int(v**0.5) ** 2 == v for v in vc.index if v > 0)),
    "quantiles_imagebearing": {str(q): float(img.quantile(q)) for q in qs},
    "max": int(img.max()),
    "mean_images_per_request_overall": float(df["NumImages"].mean()),
}

# --- token marginals ---
for col in ["ContextTokens", "GeneratedTokens"]:
    s = df[col]
    stats[col] = {
        "mean": float(s.mean()),
        "quantiles": {str(q): float(s.quantile(q)) for q in [0.5, 0.9, 0.99, 0.999]},
        "max": int(s.max()),
    }

# tail heaviness: share of total tokens carried by top 1% of requests
for col in ["ContextTokens", "GeneratedTokens"]:
    s = df[col]
    thr = s.quantile(0.99)
    stats[col]["top1pct_share_of_total"] = float(s[s >= thr].sum() / s.sum())

save_stats("b_marginals_stats.json", stats)

# --- figures ---
# 1. NumImages spectrum (image-bearing only, log-log) — bars at the square values
fig, ax = plt.subplots(figsize=(6, 3.2))
pos = vc[vc.index > 0]
sq_mask = [int(v**0.5) ** 2 == v for v in pos.index]
ax.plot(pos.index[sq_mask], pos.values[sq_mask], "o", color=C_BLUE,
        markersize=5, linestyle="none", label="perfect-square counts (99.99%)")
if (~np.array(sq_mask)).any():
    ax.plot(pos.index[~np.array(sq_mask)], pos.values[~np.array(sq_mask)], "x",
            color="#9ca3af", markersize=4, linestyle="none", label="non-square (53 reqs)")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("NumImages per request (log)")
ax.set_ylabel("requests (log)")
ax.set_title(f"Image-count spectrum — k×k tile/frame structure; "
             f"{stats['numimages']['share_text_only']:.0%} of requests are text-only")
ax.legend(frameon=False, fontsize=8)
save_fig(fig, "b_numimages_spectrum.png")

# 2. Token CCDFs (survival curves), one hue per pool series
fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
for ax, col, color in [
    (axes[0], "ContextTokens", C_AQUA),
    (axes[1], "GeneratedTokens", C_AQUA),
]:
    v = np.sort(df[col].to_numpy())
    ccdf = 1.0 - np.arange(1, len(v) + 1) / len(v)
    ax.plot(v, ccdf, color=color)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(col)
    ax.set_ylabel("P(X > x)")
    ax.set_title(f"{col} survival (CCDF)")
save_fig(fig, "b_token_ccdfs.png")

print("\nKey readout:")
print(f"text-only share: {stats['numimages']['share_text_only']:.1%}; "
      f"perfect squares: {stats['numimages']['all_perfect_squares']}")
print(f"images/request p50={stats['numimages']['quantiles_imagebearing']['0.5']:.0f} "
      f"p99={stats['numimages']['quantiles_imagebearing']['0.99']:.0f} max={stats['numimages']['max']}")
for col in ["ContextTokens", "GeneratedTokens"]:
    q = stats[col]["quantiles"]
    print(f"{col}: p50={q['0.5']:.0f} p99={q['0.99']:.0f} max={stats[col]['max']} "
          f"(top-1% carries {stats[col]['top1pct_share_of_total']:.1%} of volume)")
