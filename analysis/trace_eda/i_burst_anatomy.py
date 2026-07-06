"""EDA I — burst anatomy / onset dynamics (GPU: cuDF for aggregation).

For every burst episode of the image-rate signal: how fast does load ramp?
The onset time (baseline -> peak) minus replica cold-start time is the
forecast-horizon budget — the design constraint for the autoscaler.

Episode definition (consistent with §C): contiguous 1-min windows with
images/s above the p99 threshold; episode boundaries extended to the
surrounding baseline crossings (p50) to capture the full ramp.
"""
import numpy as np
import pandas as pd

from _common import C_BLUE, C_YELLOW, MUTED, load_trace, plt, save_fig, save_stats

df = load_trace()
w = df.assign(win=df["ts"].dt.floor("min")).groupby("win").agg(
    images=("NumImages", "sum")).sort_index().to_pandas()
w = w.reindex(pd.date_range(w.index.min(), w.index.max(), freq="min"), fill_value=0)
img = (w["images"] / 60.0).to_numpy(dtype=float)
idx = w.index

p50 = float(np.quantile(img, 0.50))
p99 = float(np.quantile(img, 0.99))

# --- episodes: runs above p99, then walk out to p50 crossings ---
above = img > p99
runs, start = [], None
for i, flag in enumerate(above):
    if flag and start is None:
        start = i
    elif not flag and start is not None:
        runs.append((start, i - 1))
        start = None
if start is not None:
    runs.append((start, len(above) - 1))

episodes = []
for a, b in runs:
    lo = a
    while lo > 0 and img[lo] > p50:
        lo -= 1
    hi = b
    while hi < len(img) - 1 and img[hi] > p50:
        hi += 1
    peak_i = a + int(np.argmax(img[a:b + 1]))
    onset_min = peak_i - lo                    # baseline -> peak
    decay_min = hi - peak_i                    # peak -> baseline
    ramp_rate = (img[peak_i] - img[lo]) / max(onset_min, 1)  # img/s per minute
    # steepest single-minute jump during onset (worst case for reaction)
    seg = img[lo:peak_i + 1]
    steepest = float(np.max(np.diff(seg))) if len(seg) > 1 else 0.0
    episodes.append({
        "start_baseline": str(idx[lo]), "peak": str(idx[peak_i]), "end_baseline": str(idx[hi]),
        "peak_img_per_s": float(img[peak_i]),
        "onset_minutes": int(onset_min), "decay_minutes": int(decay_min),
        "ramp_img_per_s_per_min": float(ramp_rate),
        "steepest_1min_jump_img_per_s": steepest,
    })

# merge episodes sharing the same extended window (overlapping p50 spans)
merged = []
for e in sorted(episodes, key=lambda x: x["start_baseline"]):
    if merged and e["start_baseline"] <= merged[-1]["end_baseline"]:
        if e["peak_img_per_s"] > merged[-1]["peak_img_per_s"]:
            merged[-1].update({k: e[k] for k in
                               ["peak", "peak_img_per_s", "onset_minutes",
                                "ramp_img_per_s_per_min", "steepest_1min_jump_img_per_s"]})
        merged[-1]["end_baseline"] = max(merged[-1]["end_baseline"], e["end_baseline"])
        merged[-1]["decay_minutes"] = None  # recomputed below if needed
    else:
        merged.append(dict(e))

onsets = np.array([e["onset_minutes"] for e in merged], dtype=float)
ramps = np.array([e["ramp_img_per_s_per_min"] for e in merged])
jumps = np.array([e["steepest_1min_jump_img_per_s"] for e in merged])
peaks = np.array([e["peak_img_per_s"] for e in merged])

stats = {
    "thresholds": {"p50_img_per_s": p50, "p99_img_per_s": p99},
    "n_raw_episodes": len(episodes), "n_merged_episodes": len(merged),
    "onset_minutes": {"p10": float(np.quantile(onsets, 0.1)), "p50": float(np.quantile(onsets, 0.5)),
                      "p90": float(np.quantile(onsets, 0.9)), "min": float(onsets.min())},
    "ramp_img_per_s_per_min": {"p50": float(np.quantile(ramps, 0.5)), "p90": float(np.quantile(ramps, 0.9)),
                               "max": float(ramps.max())},
    "steepest_1min_jump_img_per_s": {"p50": float(np.quantile(jumps, 0.5)),
                                     "p90": float(np.quantile(jumps, 0.9)), "max": float(jumps.max())},
    "top6_by_peak": sorted(merged, key=lambda e: -e["peak_img_per_s"])[:6],
}
save_stats("i_burst_anatomy_stats.json", stats)

# --- figures ---
fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4), constrained_layout=True)
axes[0].hist(onsets, bins=np.logspace(0, np.log10(max(onsets.max(), 2)), 25),
             color=C_BLUE, edgecolor="white", linewidth=0.5)
axes[0].set_xscale("log")
axes[0].set_xlabel("onset time, baseline→peak (minutes)")
axes[0].set_ylabel("episodes")
axes[0].set_title(f"Burst onset — p50 {np.quantile(onsets,0.5):.0f} min, "
                  f"p10 {np.quantile(onsets,0.1):.0f} min")
axes[1].plot(onsets, peaks, "o", color=C_BLUE, markersize=5, alpha=0.75)
axes[1].set_xscale("log")
axes[1].set_xlabel("onset time (minutes)")
axes[1].set_ylabel("peak images/s")
axes[1].set_title("Fast-onset bursts are not small")
save_fig(fig, "i_burst_onsets.png")

# aligned-ramp overlay of the top-6 episodes (minutes relative to peak)
fig, ax = plt.subplots(figsize=(6.5, 3.4))
for rank, e in enumerate(stats["top6_by_peak"]):
    pi = idx.get_loc(pd.Timestamp(e["peak"]))
    lo, hi = max(0, pi - 120), min(len(img), pi + 121)
    ax.plot(np.arange(lo - pi, hi - pi), img[lo:hi],
            color=C_BLUE, alpha=0.35 + 0.1 * (5 - rank) / 5, linewidth=1.0)
ax.axvline(0, color=MUTED, linewidth=0.8)
ax.axhline(p99, color=C_YELLOW, linewidth=0.9, linestyle="--")
ax.annotate("p99", xy=(-118, p99), xytext=(0, 3), textcoords="offset points",
            fontsize=8, color=MUTED)
ax.set_xlabel("minutes relative to episode peak")
ax.set_ylabel("images/s")
ax.set_title("Top-6 burst episodes, peak-aligned (±2 h)")
save_fig(fig, "i_burst_aligned.png")

print("\nKey readout:")
print(f"{len(merged)} merged episodes (from {len(episodes)} raw)")
print(f"onset minutes: p10={np.quantile(onsets,0.1):.0f} p50={np.quantile(onsets,0.5):.0f} "
      f"p90={np.quantile(onsets,0.9):.0f} min={onsets.min():.0f}")
print(f"ramp img/s/min: p50={np.quantile(ramps,0.5):.1f} max={ramps.max():.1f}")
print(f"steepest 1-min jump: p50={np.quantile(jumps,0.5):.0f} max={jumps.max():.0f} img/s")
