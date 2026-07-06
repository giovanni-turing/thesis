"""EDA A — data quality + ContextTokens semantics (GPU/cuDF).

Answers, before the converter fixes any formula:
  1. Coverage: duration, monotonicity, inter-arrival gaps, dupes, zeros/negatives.
  2. THE semantics question: does ContextTokens already include vision tokens?
     Method: conditional distribution of ContextTokens given NumImages. If the
     trace embedded vision tokens, ContextTokens would shift up by ~k tokens per
     image (k = fixed per-image token count for the traced model); a flat
     conditional median vs NumImages ⇒ text-only accounting.
"""
from _common import C_BLUE, MUTED, load_trace, plt, save_fig, save_stats

df = load_trace()
n = len(df)

# --- coverage & hygiene ---
ts = df["ts"]
dur = (ts.iloc[-1] - ts.iloc[0])
deltas_ms = ts.diff().dropna().astype("int64") / 1e6
stats = {
    "rows": n,
    "t_start": str(ts.iloc[0]),
    "t_end": str(ts.iloc[-1]),
    "duration_hours": float(dur.total_seconds() / 3600) if hasattr(dur, "total_seconds") else str(dur),
    "monotonic_after_sort_violations": int((deltas_ms < 0).sum()),
    "duplicate_full_rows": int(n - len(df.drop_duplicates())),
    "interarrival_ms": {
        "p50": float(deltas_ms.quantile(0.5)),
        "p99": float(deltas_ms.quantile(0.99)),
        "max": float(deltas_ms.max()),
    },
    "largest_gap_minutes": float(deltas_ms.max() / 60000),
    "zeros": {
        "NumImages==0": int((df["NumImages"] == 0).sum()),
        "ContextTokens==0": int((df["ContextTokens"] == 0).sum()),
        "GeneratedTokens==0": int((df["GeneratedTokens"] == 0).sum()),
    },
    "negatives": {c: int((df[c] < 0).sum()) for c in ["NumImages", "ContextTokens", "GeneratedTokens"]},
    "ranges": {c: [int(df[c].min()), int(df[c].max())] for c in ["NumImages", "ContextTokens", "GeneratedTokens"]},
}

# --- ContextTokens | NumImages ---
cond = (
    df.groupby("NumImages")["ContextTokens"]
    .agg(["count", "median", "mean"])
    .sort_index()
    .to_pandas()
)
stats["context_tokens_by_numimages"] = {
    str(k): {"count": int(r["count"]), "median": float(r["median"]), "mean": float(r["mean"])}
    for k, r in cond.iterrows()
}
# linear fit median(ContextTokens) ~ NumImages over well-populated counts
well = cond[cond["count"] >= 1000]
if len(well) >= 3:
    import numpy as np

    slope, intercept = np.polyfit(well.index.to_numpy(), well["median"].to_numpy(), 1)
    stats["median_context_vs_images_slope_tokens_per_image"] = float(slope)
    stats["median_context_vs_images_intercept"] = float(intercept)

save_stats("a_quality_stats.json", stats)

# --- figure: conditional ContextTokens vs NumImages (box-style via quantiles) ---
# cudf 26.06 groupby.quantile with a list trips an indexing edge; query scalars
import pandas as pd

g = df.groupby("NumImages")["ContextTokens"]
q = pd.DataFrame({
    0.1: g.quantile(0.1).to_pandas(),
    0.5: g.quantile(0.5).to_pandas(),
    0.9: g.quantile(0.9).to_pandas(),
}).sort_index()
q = q[q.index.isin(well.index if len(well) >= 3 else q.index)]
fig, ax = plt.subplots(figsize=(6, 3.2))
ax.fill_between(q.index, q[0.1], q[0.9], color=C_BLUE, alpha=0.18, linewidth=0, label="p10–p90")
ax.plot(q.index, q[0.5], color=C_BLUE, marker="o", markersize=4, label="median")
ax.set_xlabel("NumImages")
ax.set_ylabel("ContextTokens")
ax.set_title("ContextTokens conditional on image count (counts ≥ 1000)")
ax.legend(frameon=False)
save_fig(fig, "a_context_vs_numimages.png")

print("\nKey readout:")
print(cond[cond["count"] >= 1000][["count", "median"]].to_string())
if "median_context_vs_images_slope_tokens_per_image" in stats:
    print(f"\nslope ≈ {stats['median_context_vs_images_slope_tokens_per_image']:.1f} tokens/image "
          f"(intercept {stats['median_context_vs_images_intercept']:.0f})")
    print("≈0 slope ⇒ text-only accounting; ≈constant>0 ⇒ vision tokens embedded")
