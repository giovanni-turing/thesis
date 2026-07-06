"""EDA K — clustering burst episodes into types (GPU: cuDF + cuML KMeans).

Features per merged episode (from §I definition): log peak rate, log onset,
log duration, image-volume share per class (§J classes), median ctx/request.
KMeans on GPU (cuML), k chosen by silhouette over k=2..5. 18 episodes is a
small sample — treated as descriptive typing, not population inference.
"""
import json

import cudf
import cupy as cp
import numpy as np
import pandas as pd
from cuml.cluster import KMeans
from cuml.metrics.cluster import silhouette_score
from cuml.preprocessing import StandardScaler

from _common import C_AQUA, C_BLUE, C_YELLOW, MUTED, load_trace, plt, save_fig, save_stats

df = load_trace()
k_side = df["NumImages"].pow(0.5).round().astype("int32")
df = df.assign(k=k_side, cls="text")
for name, cond in [("single", (df["k"] == 1) & (df["NumImages"] > 0)),  # k=1 incl. NumImages=2 rounding down
                   ("tiled_small", (df["k"] >= 2) & (df["k"] <= 5) & (df["NumImages"] > 1)),
                   ("tiled_large", (df["k"] >= 6) & (df["k"] <= 10)),
                   ("frames", df["k"] > 10)]:
    df["cls"] = df["cls"].where(~cond, name)

# rebuild merged episodes exactly as in §I
w = df.assign(win=df["ts"].dt.floor("min")).groupby("win").agg(
    images=("NumImages", "sum")).sort_index().to_pandas()
w = w.reindex(pd.date_range(w.index.min(), w.index.max(), freq="min"), fill_value=0)
img = (w["images"] / 60.0).to_numpy(dtype=float)
idx = w.index
p50, p99 = np.quantile(img, 0.5), np.quantile(img, 0.99)

above = img > p99
runs, start = [], None
for i, flag in enumerate(above):
    if flag and start is None:
        start = i
    elif not flag and start is not None:
        runs.append((start, i - 1)); start = None
if start is not None:
    runs.append((start, len(above) - 1))

spans = []
for a, b in runs:
    lo = a
    while lo > 0 and img[lo] > p50:
        lo -= 1
    hi = b
    while hi < len(img) - 1 and img[hi] > p50:
        hi += 1
    if spans and lo <= spans[-1][1]:
        spans[-1] = (spans[-1][0], max(hi, spans[-1][1]))
    else:
        spans.append((lo, hi))

# per-class per-minute image rates for composition features
wc = df.assign(win=df["ts"].dt.floor("min")).groupby(["win", "cls"])["NumImages"].sum()
wc = wc.sort_index().to_pandas().unstack(fill_value=0).reindex(idx, fill_value=0)
IMG_CLASSES = [c for c in ["single", "tiled_small", "tiled_large", "frames"] if c in wc.columns]

rows = []
for lo, hi in spans:
    seg = wc.iloc[lo:hi + 1][IMG_CLASSES]
    tot = seg.values.sum()
    peak_i = lo + int(np.argmax(img[lo:hi + 1]))
    t0, t1 = idx[lo], idx[hi]
    req = df[(df["ts"] >= t0) & (df["ts"] <= t1)]
    rows.append({
        "start": str(t0), "peak": str(idx[peak_i]),
        "peak_img_per_s": img[peak_i],
        "onset_min": max(peak_i - lo, 1),
        "duration_min": hi - lo + 1,
        **{f"share_{c}": float(seg[c].sum() / tot) for c in IMG_CLASSES},
        "ctx_p50": float(req["ContextTokens"].quantile(0.5)),
    })
ep = pd.DataFrame(rows)

feat_cols = ["peak_img_per_s", "onset_min", "duration_min", "ctx_p50"] + \
            [f"share_{c}" for c in IMG_CLASSES]
X = ep[feat_cols].copy()
for c in ["peak_img_per_s", "onset_min", "duration_min", "ctx_p50"]:
    X[c] = np.log10(X[c] + 1)

Xg = cudf.DataFrame(X.astype("float64"))
Xs = StandardScaler().fit_transform(Xg)

sil = {}
models = {}
for kk in range(2, 6):
    km = KMeans(n_clusters=kk, random_state=0, n_init=10).fit(Xs)
    sil[kk] = float(silhouette_score(Xs, km.labels_))
    models[kk] = km
best_k = max(sil, key=sil.get)
labels = cp.asnumpy(models[best_k].labels_.values)
ep["cluster"] = labels

profile = ep.groupby("cluster")[feat_cols].median().round(2)
counts = ep["cluster"].value_counts().sort_index()

stats = {
    "n_episodes": len(ep),
    "silhouette_by_k": sil, "chosen_k": int(best_k),
    "cluster_sizes": {int(k): int(v) for k, v in counts.items()},
    "cluster_profiles_median": profile.to_dict(orient="index"),
    "episodes": ep.round(3).to_dict(orient="records"),
}
save_stats("k_episode_clusters_stats.json", stats)

# figure: onset vs peak, colored by cluster (categorical slots, fixed order)
COLORS = [C_BLUE, C_AQUA, C_YELLOW, "#4a3aa7"]
fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), constrained_layout=True)
for cl in sorted(ep["cluster"].unique()):
    sub = ep[ep["cluster"] == cl]
    axes[0].scatter(sub["onset_min"], sub["peak_img_per_s"], s=42,
                    color=COLORS[cl % len(COLORS)], label=f"type {cl} (n={len(sub)})")
axes[0].set_xscale("log")
axes[0].set_xlabel("onset (min)")
axes[0].set_ylabel("peak images/s")
axes[0].set_title(f"Episode types (k={best_k}, silhouette={sil[best_k]:.2f})")
axes[0].legend(frameon=False, fontsize=8)
for cl in sorted(ep["cluster"].unique()):
    sub = ep[ep["cluster"] == cl]
    axes[1].scatter(sub["duration_min"], sub["share_frames"], s=42,
                    color=COLORS[cl % len(COLORS)])
axes[1].set_xscale("log")
axes[1].set_xlabel("duration (min)")
axes[1].set_ylabel("frames-class image share")
axes[1].set_title("Composition vs duration")
save_fig(fig, "k_episode_clusters.png")

print("\nKey readout:")
print("silhouette:", {k: round(v, 3) for k, v in sil.items()}, "-> k =", best_k)
print(profile.to_string())
print("\nsizes:", dict(counts))
