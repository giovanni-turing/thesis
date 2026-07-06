"""EDA J — workload-class decomposition on the k² tile structure (GPU/cuDF).

Classes by tile-grid side k = sqrt(NumImages):
  text  (k=0) · single (k=1) · tiled-small (k∈[2,5], 4–25 imgs)
  tiled-large (k∈[6,10], 36–100) · frames (k>10, >100 imgs — video-like)

Per class: request/image volume shares, token profiles, rate signals and
burstiness — and the attribution question: WHICH class drives each burst
episode? (If bursts are single-class, per-class forecasting is the move.)
"""
import cupy as cp
import numpy as np
import pandas as pd

from _common import C_AQUA, C_BLUE, C_YELLOW, MUTED, load_trace, plt, save_fig, save_stats

df = load_trace()
k = df["NumImages"].pow(0.5).round().astype("int32")
df = df.assign(k=k)
conds = [
    ("text", df["NumImages"] == 0),
    ("single", (df["k"] == 1) & (df["NumImages"] > 0)),  # k=1 incl. NumImages=2 rounding down
    ("tiled_small", (df["k"] >= 2) & (df["k"] <= 5) & (df["NumImages"] > 1)),
    ("tiled_large", (df["k"] >= 6) & (df["k"] <= 10)),
    ("frames", df["k"] > 10),
]
df["cls"] = "text"
for name, cond in conds[1:]:
    df["cls"] = df["cls"].where(~cond, name)

CLASSES = ["text", "single", "tiled_small", "tiled_large", "frames"]
stats = {"classes": {}}
tot_img = float(df["NumImages"].sum())
for c in CLASSES:
    sub = df[df["cls"] == c]
    stats["classes"][c] = {
        "requests": int(len(sub)),
        "request_share": float(len(sub) / len(df)),
        "image_share": float(sub["NumImages"].sum() / tot_img),
        "ctx_p50": float(sub["ContextTokens"].quantile(0.5)),
        "gen_p50": float(sub["GeneratedTokens"].quantile(0.5)),
    }

# per-class 1-min image-rate signals
w = df.assign(win=df["ts"].dt.floor("min")).groupby(["win", "cls"])["NumImages"].sum()
w = w.sort_index().to_pandas().unstack(fill_value=0)
full = pd.date_range(w.index.min(), w.index.max(), freq="min")
w = w.reindex(full, fill_value=0) / 60.0  # img/s per class
for c in CLASSES:
    if c == "text":
        continue
    s = w[c] if c in w.columns else pd.Series(0, index=w.index)
    stats["classes"][c]["img_rate_cv2"] = float((s.std() / s.mean()) ** 2) if s.mean() > 0 else None
    stats["classes"][c]["img_rate_mean"] = float(s.mean())

# --- burst attribution: image-volume share per class inside each episode ---
import json

epi = json.load(open("i_burst_anatomy_stats.json"))["top6_by_peak"]
attribution = []
img_cols = [c for c in CLASSES if c != "text" and c in w.columns]
for e in epi:
    lo, hi = pd.Timestamp(e["start_baseline"]), pd.Timestamp(e["end_baseline"])
    seg = w.loc[lo:hi, img_cols]
    tot = seg.values.sum()
    shares = {c: float(seg[c].sum() / tot) for c in img_cols}
    dom = max(shares, key=shares.get)
    attribution.append({"peak": e["peak"], "peak_img_per_s": e["peak_img_per_s"],
                        "dominant_class": dom, "dominant_share": shares[dom],
                        "shares": shares})
stats["burst_attribution_top6"] = attribution
save_stats("j_classes_stats.json", stats)

# --- figures ---
# 1. per-class image-rate signals, small multiples (shared x)
plot_classes = [c for c in ["single", "tiled_small", "tiled_large", "frames"] if c in w.columns]
fig, axes = plt.subplots(len(plot_classes), 1, figsize=(9, 1.6 * len(plot_classes)),
                         sharex=True, constrained_layout=True)
for ax, c in zip(axes, plot_classes):
    ax.plot(w.index, w[c], color=C_BLUE, linewidth=0.6)
    ish = stats["classes"][c]["image_share"]
    ax.set_ylabel("img/s")
    ax.set_title(f"{c} — {ish:.0%} of image volume, CV²={stats['classes'][c]['img_rate_cv2']:.1f}",
                 fontsize=9, loc="left")
fig.autofmt_xdate()
save_fig(fig, "j_class_signals.png")

# 2. burst attribution heatmap (episodes × classes, sequential single hue)
from matplotlib.colors import LinearSegmentedColormap

seq = LinearSegmentedColormap.from_list("seqb", ["#f7f9fc", "#2a78d6", "#123c74"])
mat = np.array([[a["shares"].get(c, 0.0) for c in img_cols] for a in attribution])
fig, ax = plt.subplots(figsize=(6, 3.2))
im = ax.imshow(mat, cmap=seq, vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(img_cols)), img_cols)
ax.set_yticks(range(len(attribution)),
              [pd.Timestamp(a["peak"]).strftime("%m-%d %H:%M") for a in attribution])
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        if mat[i, j] >= 0.005:
            ax.text(j, i, f"{mat[i, j]:.0%}", ha="center", va="center", fontsize=8,
                    color="white" if mat[i, j] > 0.55 else "#1f2430")
ax.set_title("Top-6 burst episodes: image-volume share by class")
fig.colorbar(im, shrink=0.8, label="share")
save_fig(fig, "j_burst_attribution.png")

print("\nKey readout:")
for c in CLASSES:
    s = stats["classes"][c]
    extra = (f" img_share={s['image_share']:.1%} CV²={s.get('img_rate_cv2'):.1f}"
             if c != "text" else "")
    print(f"{c:12s} req_share={s['request_share']:.1%} ctx_p50={s['ctx_p50']:.0f} "
          f"gen_p50={s['gen_p50']:.0f}{extra}")
print("\nburst attribution (dominant class per episode):")
for a in attribution:
    print(f"  {a['peak'][:16]}  peak={a['peak_img_per_s']:.0f} img/s -> "
          f"{a['dominant_class']} ({a['dominant_share']:.0%})")
