"""Shared loader + figure style for the Azure multimodal trace EDA.

GPU-first: the trace is loaded and aggregated with cuDF on the RTX 5090;
only final (small) aggregates cross to host for matplotlib.

Palette: validated reference instance from the dataviz skill
(categorical slots in fixed order; sequential = single blue hue).
"""
import json
import os

import cudf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

TRACE = "/home/gio/tese/data/AzureLMMInferenceTrace_multimodal.csv.gz"
OUTDIR = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(OUTDIR, "figures")
os.makedirs(FIGDIR, exist_ok=True)

# dataviz reference palette (light mode), fixed slot order — never cycled
C_BLUE = "#2a78d6"    # slot 1: primary / vision-pool series
C_AQUA = "#1baf7a"    # slot 2: language-pool series
C_YELLOW = "#eda100"  # slot 3: third series only
INK = "#1f2430"
MUTED = "#6b7280"

plt.rcParams.update({
    "figure.dpi": 120,
    "font.size": 9,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "axes.titlesize": 10,
    "axes.grid": True,
    "grid.color": "#e5e7eb",
    "grid.linewidth": 0.6,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "lines.linewidth": 1.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def load_trace() -> cudf.DataFrame:
    df = cudf.read_csv(TRACE)
    # All rows carry millis but some have 2-digit fractions (len 23 vs 24);
    # normalize to exactly 3 fractional digits so one strptime format fits.
    clean = df["TIMESTAMP"].str.replace("Z", "").str.pad(width=23, side="right", fillchar="0")
    df["ts"] = cudf.to_datetime(clean, format="%Y-%m-%dT%H:%M:%S.%f")
    df = df.drop(columns=["TIMESTAMP"]).sort_values("ts").reset_index(drop=True)
    return df


def save_fig(fig, name: str):
    path = os.path.join(FIGDIR, name)
    fig.savefig(path, bbox_inches="tight")
    fig.savefig(os.path.splitext(path)[0] + ".pdf", bbox_inches="tight")  # vector
    plt.close(fig)
    print(f"figure: {path}")


def save_stats(name: str, stats: dict):
    path = os.path.join(OUTDIR, name)
    with open(path, "w") as f:
        json.dump(stats, f, indent=1, default=str)
    print(f"stats: {path}")
