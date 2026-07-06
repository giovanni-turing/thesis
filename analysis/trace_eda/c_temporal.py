"""EDA C — arrival process, bursts, temporal structure (GPU/cuDF).

Request-rate vs image-rate series at multiple windows; burstiness (CV²,
peak/mean); diurnal profile; burst-episode extraction on the image-rate
signal (the vision pool's demand).
"""
import numpy as np

from _common import C_AQUA, C_BLUE, load_trace, plt, save_fig, save_stats

df = load_trace()
stats = {}

# --- windowed rates on GPU ---
def windowed(freq: str):
    w = df.assign(win=df["ts"].dt.floor(freq)).groupby("win").agg(
        requests=("NumImages", "count"), images=("NumImages", "sum"),
        ctx=("ContextTokens", "sum"), gen=("GeneratedTokens", "sum"),
    )
    w = w.sort_index().to_pandas()
    # groupby drops empty windows — reindex to the full clock and fill 0,
    # otherwise rate means/CV² are conditioned on "window had traffic".
    import pandas as pd

    full = pd.date_range(w.index.min(), w.index.max(), freq=freq)
    return w.reindex(full, fill_value=0)

w1m = windowed("min")
w1s = windowed("s")
sec = {"1min": 60.0, "1s": 1.0}

for name, w in [("1min", w1m), ("1s", w1s)]:
    d = sec[name]
    req_rate = w["requests"] / d
    img_rate = w["images"] / d
    stats[f"window_{name}"] = {
        "req_per_s": {"mean": float(req_rate.mean()), "p99": float(req_rate.quantile(0.99)),
                      "max": float(req_rate.max()), "cv2": float((req_rate.std() / req_rate.mean()) ** 2)},
        "img_per_s": {"mean": float(img_rate.mean()), "p99": float(img_rate.quantile(0.99)),
                      "max": float(img_rate.max()), "cv2": float((img_rate.std() / img_rate.mean()) ** 2)},
        "peak_to_mean_req": float(req_rate.max() / req_rate.mean()),
        "peak_to_mean_img": float(img_rate.max() / img_rate.mean()),
    }

# --- burst episodes on the 1-min image-rate signal ---
img_1m = w1m["images"] / 60.0
thr = img_1m.quantile(0.99)
above = img_1m > thr
# contiguous runs above threshold
runs, start = [], None
idx = img_1m.index
for i, flag in enumerate(above.values):
    if flag and start is None:
        start = i
    elif not flag and start is not None:
        runs.append((start, i - 1))
        start = None
if start is not None:
    runs.append((start, len(above) - 1))
episodes = sorted(
    ({"start": str(idx[a]), "end": str(idx[b]), "minutes": b - a + 1,
      "peak_img_per_s": float(img_1m.iloc[a:b + 1].max()),
      "peak_req_per_s": float((w1m["requests"].iloc[a:b + 1] / 60).max())}
     for a, b in runs),
    key=lambda e: -e["peak_img_per_s"],
)
stats["burst_episodes_img_gt_p99"] = {"threshold_img_per_s": float(thr),
                                      "count": len(episodes), "top6": episodes[:6]}

save_stats("c_temporal_stats.json", stats)

# --- figures ---
# 1. Seven-day series, small multiples (NO dual axis): req/s and img/s @1min
fig, axes = plt.subplots(2, 1, figsize=(9, 4.4), sharex=True)
axes[0].plot(w1m.index, w1m["requests"] / 60, color=C_AQUA, linewidth=0.7)
axes[0].set_ylabel("requests/s")
axes[0].set_title("Language-pool arrival signal (1-min windows, 7 days)")
axes[1].plot(w1m.index, img_1m, color=C_BLUE, linewidth=0.7)
axes[1].axhline(float(thr), color="#9ca3af", linewidth=0.8, linestyle="--")
axes[1].annotate(f"p99 = {thr:.1f} img/s", xy=(w1m.index[100], float(thr)),
                 xytext=(0, 4), textcoords="offset points", fontsize=8, color="#6b7280")
axes[1].set_ylabel("images/s")
axes[1].set_title("Vision-pool arrival signal — same clock, its own bursts")
fig.autofmt_xdate()
save_fig(fig, "c_seven_day_signals.png")

# 2. Diurnal profile: mean rate by hour-of-day, both signals normalized to their mean
prof = w1m.assign(hour=w1m.index.hour).groupby("hour")[["requests", "images"]].mean()
prof_n = prof / prof.mean()
fig, ax = plt.subplots(figsize=(6, 3.2))
ax.plot(prof_n.index, prof_n["requests"], color=C_AQUA, marker="o", markersize=3, label="requests (indexed)")
ax.plot(prof_n.index, prof_n["images"], color=C_BLUE, marker="o", markersize=3, label="images (indexed)")
ax.axhline(1.0, color="#9ca3af", linewidth=0.8)
ax.set_xlabel("hour of day (UTC)")
ax.set_ylabel("rate / own mean")
ax.set_title("Diurnal profile — each signal indexed to its own mean (one axis)")
ax.legend(frameon=False)
save_fig(fig, "c_diurnal_profile.png")

print("\nKey readout:")
for name in ["1min", "1s"]:
    s = stats[f"window_{name}"]
    print(f"[{name}] req/s mean={s['req_per_s']['mean']:.2f} max={s['req_per_s']['max']:.1f} "
          f"CV²={s['req_per_s']['cv2']:.2f} | img/s mean={s['img_per_s']['mean']:.1f} "
          f"max={s['img_per_s']['max']:.0f} CV²={s['img_per_s']['cv2']:.2f}")
print(f"burst episodes above p99({thr:.1f} img/s): {len(episodes)}; top episode "
      f"peak {episodes[0]['peak_img_per_s']:.0f} img/s vs {episodes[0]['peak_req_per_s']:.2f} req/s"
      if episodes else "no episodes")
