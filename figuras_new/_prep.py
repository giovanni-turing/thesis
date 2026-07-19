"""One-time CPU prep: materialize the per-request derived arrays that the
matplotlib originals recomputed on the GPU, so the plotly figure scripts stay
fast and GPU-free. Reads the raw trace once with pandas.

Outputs into figuras_new/_data/:
  ctx_by_numimages.parquet   NumImages, count, p10, p25, p50, p75, p90  (count>=1000)
  interarrival.parquet       x (sorted inter-arrival s, ~20k subsample), surv (CCDF)
  clusters_40k.parquet       NumImages, ContextTokens, GeneratedTokens, cluster (0..3)
  cluster_meta.json          per-cluster shares + semantic names + silhouette
"""
import json, os
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "_data")
os.makedirs(DATA, exist_ok=True)
TRACE = "/home/gio/tese/data/AzureLMMInferenceTrace_multimodal.csv.gz"

print("loading trace ...")
df = pd.read_csv(TRACE)
ts = pd.to_datetime(df["TIMESTAMP"].str.replace("Z", "", regex=False),
                    format="ISO8601")
df = df.assign(ts=ts).sort_values("ts").reset_index(drop=True)
print(f"  {len(df):,} rows, {df.ts.min()} -> {df.ts.max()}")

# --- 1. ContextTokens conditional on NumImages (p10/p25/p50/p75/p90) ---------
g = df.groupby("NumImages")["ContextTokens"]
q = g.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).unstack()
q.columns = ["p10", "p25", "p50", "p75", "p90"]
q["count"] = g.size()
q = q[q["count"] >= 1000].reset_index()
q.to_parquet(os.path.join(DATA, "ctx_by_numimages.parquet"))
print("  ctx_by_numimages:", len(q), "image-count bins")

# --- 2. inter-arrival survival (subsample for plotting) ----------------------
d = df["ts"].diff().dt.total_seconds().dropna().to_numpy()
d.sort()
N = len(d)
surv = 1.0 - np.arange(N) / N
idx = np.unique(np.linspace(0, N - 1, 200000).astype(int))
pd.DataFrame({"x": d[idx], "surv": surv[idx]}).to_parquet(
    os.path.join(DATA, "interarrival.parquet"))
lam = 1.0 / d.mean()
print(f"  interarrival: N={N:,} lambda={lam:.4f}/s CV={d.std()/d.mean():.3f}")

# --- 3. semantic request clusters (sklearn, deterministic) -------------------
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

feat = np.log1p(df[["NumImages", "ContextTokens", "GeneratedTokens"]].to_numpy(float))
Xs = StandardScaler().fit_transform(feat)
# pick k by silhouette on a 50k subsample (matches original protocol)
rng = np.random.RandomState(0)
sub = rng.choice(len(Xs), 200_000, replace=False)
sils = {}
for k in range(3, 8):
    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(Xs[sub])
    sils[k] = float(silhouette_score(Xs[sub], km.labels_, sample_size=50000,
                                     random_state=0))
best_k = max(sils, key=sils.get)
print("  silhouette:", {k: round(v, 3) for k, v in sils.items()}, "-> k", best_k)
km = KMeans(n_clusters=best_k, n_init=10, random_state=0).fit(Xs)
lab = km.labels_

# order clusters so labels are stable/semantic: sort by (img_share, ctx median)
share_img = np.array([df.loc[lab == c, "NumImages"].sum() for c in range(best_k)])
tot_img = share_img.sum()
meta = {}
for c in range(best_k):
    m = lab == c
    meta[str(c)] = dict(
        n=int(m.sum()),
        req_share=float(m.mean()),
        img_share=float(df.loc[m, "NumImages"].sum() / tot_img),
        ctx_share=float(df.loc[m, "ContextTokens"].sum() / df["ContextTokens"].sum()),
        img_p50=float(df.loc[m, "NumImages"].median()),
        ctx_p50=float(df.loc[m, "ContextTokens"].median()),
        gen_p50=float(df.loc[m, "GeneratedTokens"].median()),
    )
# semantic naming by heuristic (image-heavy vs text; high vs low gen)
def name(c):
    d = meta[str(c)]
    if d["img_p50"] >= 1:
        return "vision: video/frame analysis" if d["req_share"] < 0.1 else "vision: doc/tiled understanding"
    return "text: conversational generation" if d["gen_p50"] >= 60 else "text: short-answer / extraction"
for c in range(best_k):
    meta[str(c)]["semantic_name"] = name(c)
meta["silhouette"] = sils
meta["best_k"] = best_k
json.dump(meta, open(os.path.join(DATA, "cluster_meta.json"), "w"), indent=1)

samp = rng.choice(len(df), 150_000, replace=False)
out = df.iloc[samp][["NumImages", "ContextTokens", "GeneratedTokens"]].copy()
out["cluster"] = lab[samp]
out.to_parquet(os.path.join(DATA, "clusters_40k.parquet"))
print("  clusters_40k written; shares:",
      {c: round(meta[str(c)]["img_share"], 3) for c in range(best_k)})
print("DONE")
