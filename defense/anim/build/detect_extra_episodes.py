#!/usr/bin/env python3
"""Derive ALL burst episodes of the image signal (thesis Ch.3 definition) and
emit converter-exact ±10-min windows for the ones NOT already evaluated
(top6) that fall inside the 15-s forecast coverage.

Replicates analysis/trace_eda/i_burst_anatomy.py exactly (1-min bins, runs
above p99, walk out to p50 crossings, merge overlapping envelopes) and
simulation/derive_windows.py's converter-exact row addressing (anchor
assertion on burst1). Output: defense/anim/data/windows_ext.json — the
standard windows.json schema, keys e<rank> by peak order (top6 = burst1..6
excluded), plus the original entries merged in so schedule generators can
consume it via TESE_WINDOWS.
"""
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/gio/tese")
PAD = timedelta(minutes=10)
BASE = json.load(open(ROOT / "simulation/windows.json"))

df = pd.read_csv(ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz")
ts = df["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
df["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
df = df.drop(columns=["TIMESTAMP"]).sort_values("ts").reset_index(drop=True)

w = df.assign(win=df["ts"].dt.floor("min")).groupby("win").agg(
    images=("NumImages", "sum")).sort_index()
w = w.reindex(pd.date_range(w.index.min(), w.index.max(), freq="min"), fill_value=0)
img = (w["images"] / 60.0).to_numpy(dtype=float)
idx = w.index

p50 = float(np.quantile(img, 0.50))
p99 = float(np.quantile(img, 0.99))

above = img > p99
runs, start = [], None
for i, flag in enumerate(above):
    if flag and start is None:
        start = i
    elif not flag and start is not None:
        runs.append((start, i - 1)); start = None
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
    episodes.append({"lo": lo, "hi": hi, "peak_i": peak_i,
                     "peak": float(img[peak_i]),
                     "onset_min": int(peak_i - lo)})

merged = []
for e in sorted(episodes, key=lambda x: x["lo"]):
    if merged and e["lo"] <= merged[-1]["hi"]:
        m = merged[-1]
        if e["peak"] > m["peak"]:
            m.update(peak=e["peak"], peak_i=e["peak_i"], onset_min=e["onset_min"])
        m["hi"] = max(m["hi"], e["hi"])
    else:
        merged.append(dict(e))
print(f"{len(merged)} merged episodes (from {len(episodes)} raw); "
      f"p99 threshold {p99:.0f} img/s")

# rank by peak; top6 are the evaluated burst1..6
ranked = sorted(merged, key=lambda e: -e["peak"])
cov_start = pd.Timestamp("2024-10-16 21:39:00")   # aggregate/forecast coverage

out = dict(BASE)
rows = []
for rank, e in enumerate(ranked, 1):
    if rank <= 6:
        continue
    t_lo = idx[e["lo"]] - PAD
    t_hi = idx[e["hi"]] + PAD
    lo = int(df["ts"].searchsorted(t_lo, side="left"))
    hi = int(df["ts"].searchsorted(t_hi, side="left"))
    ww = df.iloc[lo:hi]
    span = (ww["ts"].iloc[-1] - ww["ts"].iloc[0]).total_seconds()
    in_cov = idx[e["lo"]] >= cov_start
    key = f"e{rank}"
    entry = {"offset": lo, "max_requests": hi - lo,
             "note": f"episode rank {rank} by peak ±10min pad: "
                     f"[{idx[e['lo']]} .. {idx[e['hi']]}] peak "
                     f"{e['peak']:.1f} img/s @ {idx[e['peak_i']]}, "
                     f"onset {e['onset_min']} min"
                     + ("" if in_cov else " [OUTSIDE forecast coverage]"),
             "requests": hi - lo, "span_s": round(span, 1),
             "peak_1min_img_per_s": round(e["peak"], 2),
             "onset_min": e["onset_min"], "in_coverage": bool(in_cov)}
    out[key] = entry
    rows.append((key, str(idx[e["lo"]]), e["peak"], e["onset_min"],
                 hi - lo, round(span/60), in_cov))

# converter-exactness anchor (burst1 must reproduce)
b1 = ranked[0]
lo = int(df["ts"].searchsorted(idx[b1["lo"]] - PAD, side="left"))
hi = int(df["ts"].searchsorted(idx[b1["hi"]] + PAD, side="left"))
assert (lo, hi - lo) == (843072, 64804), f"anchor mismatch: {(lo, hi-lo)}"
print("burst1 anchor reproduced ✓")

Path(ROOT / "defense/anim/data/windows_ext.json").write_text(json.dumps(out, indent=1))
print(f"{'key':4s} {'start':20s} {'peak':>6s} {'onset':>5s} {'req':>6s} {'min':>4s} cov")
for r in rows:
    print(f"{r[0]:4s} {r[1]:20s} {r[2]:6.0f} {r[3]:5d} {r[4]:6d} {r[5]:4d} {r[6]}")
