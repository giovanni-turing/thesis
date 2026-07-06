"""EDA H — pairwise density colormaps: NumImages × ContextTokens × GeneratedTokens.

Three 2D density heatmaps in a row, one sequential single-hue colormap per
panel (dataviz rule: magnitude = one hue, light→dark; hue = panel identity).
Log-spaced bins and log color scale (heavy tails everywhere).
"""
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, LogNorm

from _common import INK, load_trace, plt, save_fig

df = load_trace().to_pandas()
mm = df[df["NumImages"] > 0]

def seq_cmap(name, hue, dark):
    return LinearSegmentedColormap.from_list(name, ["#f7f9fc", hue, dark])

CMAPS = {
    "blue": seq_cmap("seq_blue", "#2a78d6", "#123c74"),
    "aqua": seq_cmap("seq_aqua", "#1baf7a", "#0b5a3e"),
    "yellow": seq_cmap("seq_yellow", "#eda100", "#7a5200"),
}

def logbins(series, n=70):
    v = series[series > 0]
    return np.logspace(np.log10(v.min()), np.log10(v.max()), n)

pairs = [
    # (x, y, data, cmap, note)
    ("NumImages", "ContextTokens", mm, CMAPS["blue"], "ρ=0.83 (mm)"),
    ("NumImages", "GeneratedTokens", mm, CMAPS["aqua"], "ρ=0.08 (mm)"),
    ("ContextTokens", "GeneratedTokens", df, CMAPS["yellow"], "ρ=0.17 (all)"),
]

fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.6), constrained_layout=True)
for ax, (xc, yc, d, cmap, note) in zip(axes, pairs):
    x = d[xc].to_numpy(dtype=float)
    y = d[yc].to_numpy(dtype=float)
    keep = (x > 0) & (y > 0)
    h, xe, ye = np.histogram2d(x[keep], y[keep],
                               bins=[logbins(d[xc]), logbins(d[yc])])
    pc = ax.pcolormesh(xe, ye, h.T, cmap=cmap, norm=LogNorm(vmin=1), rasterized=True)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel(xc)
    ax.set_ylabel(yc)
    ax.set_title(f"{xc} × {yc}", fontsize=9)
    ax.text(0.03, 0.95, note, transform=ax.transAxes, fontsize=8,
            color=INK, va="top")
    fig.colorbar(pc, ax=ax, shrink=0.85, label="requests")
save_fig(fig, "h_pairwise_density.png")
print("done")
