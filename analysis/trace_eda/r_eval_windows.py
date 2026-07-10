"""Evaluation-window stratification figure (fig:eda-windows).

One panel: the 1-minute image rate over the full week, with the
experiment windows shaded — the six largest burst episodes (each already
padded +/-10 min to its median-crossing envelope), the calmest full day
(steady reference), and the leading 1.4 days consumed as zero-shot
forecast context (never graded). Window bounds are the grid's
(simulation/results/grid/grid_summary.json); the context boundary is the
closed loop's FORECAST_T0.
"""
import pandas as pd

from _common import C_AQUA, C_BLUE, C_YELLOW, MUTED, load_trace, plt, save_fig

# [start, end) UTC, grid_summary notes (spans include the +/-10 min pad)
BURSTS = {
    "b1": ("2024-10-21 12:59", "2024-10-21 21:18"),
    "b2": ("2024-10-15 21:16", "2024-10-15 23:10"),
    "b3": ("2024-10-18 10:18", "2024-10-18 10:45"),
    "b4": ("2024-10-18 15:37", "2024-10-18 18:46"),
    "b5": ("2024-10-18 14:32", "2024-10-18 15:53"),
    "b6": ("2024-10-15 23:26", "2024-10-16 00:48"),
}
CALM = ("2024-10-19 00:00", "2024-10-20 00:00")
T0 = pd.Timestamp("2024-10-16 21:39")  # covered-span start (FORECAST_T0)

df = load_trace()
rate = (df.set_index("ts")["NumImages"].resample("1min").sum() / 60.0).to_pandas()
t_start = rate.index[0]

fig, ax = plt.subplots(figsize=(9.0, 2.7))

# bands first (recessive, behind the line)
ax.axvspan(t_start, T0, color=MUTED, alpha=0.10, hatch="//",
           edgecolor=MUTED, linewidth=0.0, zorder=0)
ax.axvspan(pd.Timestamp(CALM[0]), pd.Timestamp(CALM[1]),
           color=C_AQUA, alpha=0.14, linewidth=0.0, zorder=0)
for name, (a, b) in BURSTS.items():
    ax.axvspan(pd.Timestamp(a), pd.Timestamp(b),
               color=C_YELLOW, alpha=0.25, linewidth=0.0, zorder=0)

ax.plot(rate.index, rate.values, color=C_BLUE, linewidth=0.9, zorder=2)

# direct labels (identity never color-alone); staggered rows avoid collisions
ax.set_ylim(0, 460)
ROW1, ROW2 = 420, 372
rows = {"b1": ROW1, "b2": ROW1, "b3": ROW1, "b4": ROW1, "b5": ROW2, "b6": ROW2}
for name, (a, b) in BURSTS.items():
    mid = pd.Timestamp(a) + (pd.Timestamp(b) - pd.Timestamp(a)) / 2
    ax.text(mid, rows[name], name, ha="center", va="bottom", fontsize=8,
            color="#8a6d00")
ax.text(pd.Timestamp("2024-10-19 12:00"), ROW1, "calm day",
        ha="center", va="bottom", fontsize=8, color="#0e7a55")
ax.text(pd.Timestamp("2024-10-16 11:00"), ROW1, "forecast context",
        ha="center", va="bottom", fontsize=8, color=MUTED)

ax.set_ylabel("images/s (1-min mean)")
ax.set_xlim(t_start, rate.index[-1])
fig.autofmt_xdate(rotation=0, ha="center")

save_fig(fig, "r_eval_windows.png")
