#!/usr/bin/env python3
"""A9 dataset KDE — per-image-bucket 2D histograms of (ContextTokens,
GeneratedTokens) in log10 space, for the client-side binned Gaussian KDE.

Run under EDA_PY. Buckets follow the trace's k x k grid structure (image
counts are perfect squares for 99.99% of image-bearing requests; k =
round(sqrt(NumImages))); the frames class of the thesis is k > 10.
Output: defense/anim/data/a9_data.json (grids as flat int lists).
"""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/gio/tese")
OUT = ROOT / "defense/anim/data/a9_data.json"
NX = NY = 110
XLO, XHI = 0.0, 5.25   # log10(ctx+1): 1 .. ~178k
YLO, YHI = 0.0, 4.35   # log10(gen+1): 1 .. ~22k

df = pd.read_csv(ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz")
n = df["NumImages"].to_numpy()
k = np.round(np.sqrt(n)).astype(int)
lx = np.log10(df["ContextTokens"].to_numpy() + 1.0)
ly = np.log10(df["GeneratedTokens"].to_numpy() + 1.0)

BUCKETS = [
    ("text-only", "0 images", k == 0),
    ("k=1", "1 image", k == 1),
    ("k=2", "4 images", k == 2),
    ("k=3", "9 images", k == 3),
    ("k=4–6", "16–36 images", (k >= 4) & (k <= 6)),
    ("k=7–10", "49–100 images", (k >= 7) & (k <= 10)),
    ("k=11–17", "121–289 images", (k >= 11) & (k <= 17)),
    ("k=18–23", "324–529 images", (k >= 18) & (k <= 23)),
    ("k=24–33", "576–1,089 images", (k >= 24) & (k <= 33)),
    ("k≥34", "1,156–9,409 images", k >= 34),
]

buckets = []
for name, imgs, mask in BUCKETS:
    H, _, _ = np.histogram2d(lx[mask], ly[mask],
                             bins=[NX, NY], range=[[XLO, XHI], [YLO, YHI]])
    sub = df[mask]
    buckets.append({
        "name": name, "imgs": imgs, "count": int(mask.sum()),
        "med_ctx": int(sub["ContextTokens"].median()) if mask.any() else 0,
        "med_gen": int(sub["GeneratedTokens"].median()) if mask.any() else 0,
        "grid": H.astype(int).flatten().tolist(),   # row-major [ix*NY + iy]
    })
    print(f"{name:8s} {imgs:18s} n={mask.sum():7d} "
          f"med ctx {buckets[-1]['med_ctx']:6d} gen {buckets[-1]['med_gen']:5d}")

total = sum(b["count"] for b in buckets)
assert total == len(df), (total, len(df))

OUT.write_text(json.dumps({
    "nx": NX, "ny": NY, "xlo": XLO, "xhi": XHI, "ylo": YLO, "yhi": YHI,
    "total": total, "buckets": buckets,
    "note": "ContextTokens embeds the traced model's vision tokens "
            "(~277/img at 1 image declining to ~66/img at 529): "
            "ctx ≈ text + img·tok(img). Thesis frames class = k>10.",
}, separators=(",", ":")))
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")
