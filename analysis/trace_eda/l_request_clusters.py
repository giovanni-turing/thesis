"""EDA L — request-level clustering: semantic groups (GPU: cuDF + cuML).

Cluster all 1M requests on log1p(NumImages, ContextTokens, GeneratedTokens)
with cuML KMeans; k chosen by silhouette on a 50k GPU subsample over k=3..9.
Clusters are then read back as semantic request archetypes (named by their
median profiles and modality composition).
"""
import cudf
import cupy as cp
import numpy as np
from cuml.cluster import KMeans
from cuml.metrics.cluster import silhouette_score
from cuml.preprocessing import StandardScaler

from _common import load_trace, plt, save_fig, save_stats

df = load_trace()
n = len(df)

feats = cudf.DataFrame({
    "limg": cp.log1p(df["NumImages"].astype("float64").values),
    "lctx": cp.log1p(df["ContextTokens"].astype("float64").values),
    "lgen": cp.log1p(df["GeneratedTokens"].astype("float64").values),
})
Xs = StandardScaler().fit_transform(feats)

cp.random.seed(0)
sub_idx = cp.random.choice(n, 50_000, replace=False)
Xsub = Xs.iloc[cp.asnumpy(sub_idx)]

sil, models = {}, {}
for k in range(3, 10):
    km = KMeans(n_clusters=k, random_state=0, n_init=10).fit(Xs)
    sil[k] = float(silhouette_score(Xsub, km.predict(Xsub)))
    models[k] = km
best_k = max(sil, key=sil.get)
km = models[best_k]
labels = km.predict(Xs)
df = df.assign(cluster=labels.values)

# profile clusters on GPU
prof = df.groupby("cluster").agg(
    n=("NumImages", "count"),
    img_p50=("NumImages", "median"),
    ctx_p50=("ContextTokens", "median"),
    gen_p50=("GeneratedTokens", "median"),
    img_sum=("NumImages", "sum"),
    ctx_sum=("ContextTokens", "sum"),
).sort_index().to_pandas()
prof["req_share"] = prof["n"] / n
prof["img_share"] = prof["img_sum"] / prof["img_sum"].sum()
prof["ctx_share"] = prof["ctx_sum"] / prof["ctx_sum"].sum()


def name_cluster(r):
    if r.img_p50 == 0:
        # the text groups separate on generation length, not context
        return ("text: conversational generation" if r.gen_p50 >= 100
                else "text: short-answer / extraction")
    if r.img_p50 <= 30:
        return "vision: doc/tiled understanding"
    return "vision: video/frame analysis"


prof["semantic_name"] = [name_cluster(r) for r in prof.itertuples()]

stats = {
    "silhouette_by_k": sil, "chosen_k": int(best_k),
    "clusters": prof.round(3).to_dict(orient="index"),
}
save_stats("l_request_clusters_stats.json", stats)

# figure: ctx×gen and img×ctx scatters colored by cluster (40k subsample)
pdf = df[["NumImages", "ContextTokens", "GeneratedTokens", "cluster"]].to_pandas()
s = pdf.sample(40_000, random_state=0)
PALETTE = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948",
           "#e87ba4", "#eb6834"]
fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), constrained_layout=True)
for cl in sorted(s["cluster"].unique()):
    sub = s[s["cluster"] == cl]
    nm = prof.loc[cl, "semantic_name"]
    axes[0].scatter(sub["ContextTokens"], sub["GeneratedTokens"], s=3,
                    color=PALETTE[cl % 8], alpha=0.35, rasterized=True,
                    label=f"{cl}: {nm}")
    axes[1].scatter(sub["NumImages"] + 1, sub["ContextTokens"], s=3,
                    color=PALETTE[cl % 8], alpha=0.35, rasterized=True)
axes[0].set_xscale("log"); axes[0].set_yscale("log")
axes[0].set_xlabel("ContextTokens"); axes[0].set_ylabel("GeneratedTokens")
axes[0].set_title(f"Semantic request groups (k={best_k}, silhouette={sil[best_k]:.2f})")
leg = axes[0].legend(frameon=True, framealpha=0.9, facecolor="white",
                     edgecolor="none", fontsize=7, markerscale=4,
                     loc="lower right")
for lh in leg.legend_handles:
    lh.set_alpha(1.0)
axes[1].set_xscale("log"); axes[1].set_yscale("log")
axes[1].set_xlabel("NumImages + 1"); axes[1].set_ylabel("ContextTokens")
axes[1].set_title("Same groups in image-count space")
save_fig(fig, "l_request_clusters.png")

print("\nKey readout:")
print("silhouette:", {k: round(v, 3) for k, v in sil.items()}, "-> k =", best_k)
cols = ["semantic_name", "req_share", "img_share", "ctx_share",
        "img_p50", "ctx_p50", "gen_p50"]
print(prof[cols].sort_values("req_share", ascending=False).to_string())
