"""EDA N — materialize the binned time series as reusable artifacts (GPU/cuDF).

Persists what every script so far recomputed on the fly:
  series/rates_1min.parquet : per-minute requests, images, ctx, gen
                              (+ per-class image counts) — zero-filled clock
  series/rates_1s.parquet   : per-second requests, images, ctx, gen — zero-filled
Consumers: predictors/ (forecasting input), trace_to_two_pool.py (scenarios).
Convention: counts per window (NOT divided by window seconds); rate = value/60
or /1 as appropriate.
"""
import os

import pandas as pd

from _common import load_trace

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "series")
os.makedirs(OUT, exist_ok=True)

df = load_trace()
k = df["NumImages"].pow(0.5).round().astype("int32")
df = df.assign(k=k, cls="text")
for name, cond in [("single", df["NumImages"] == 1),
                   ("tiled_small", (df["k"] >= 2) & (df["k"] <= 5) & (df["NumImages"] > 1)),
                   ("tiled_large", (df["k"] >= 6) & (df["k"] <= 10)),
                   ("frames", df["k"] > 10)]:
    df["cls"] = df["cls"].where(~cond, name)

def base_agg(freq):
    w = df.assign(win=df["ts"].dt.floor(freq)).groupby("win").agg(
        requests=("NumImages", "count"), images=("NumImages", "sum"),
        ctx=("ContextTokens", "sum"), gen=("GeneratedTokens", "sum"),
    ).sort_index().to_pandas()
    full = pd.date_range(w.index.min(), w.index.max(), freq=freq)
    return w.reindex(full, fill_value=0)

# 1-min: base + per-class image counts
w1m = base_agg("min")
wc = df.assign(win=df["ts"].dt.floor("min")).groupby(["win", "cls"])["NumImages"].sum()
wc = wc.sort_index().to_pandas().unstack(fill_value=0).reindex(w1m.index, fill_value=0)
for c in ["single", "tiled_small", "tiled_large", "frames"]:
    w1m[f"images_{c}"] = wc[c] if c in wc.columns else 0
w1m.index.name = "window_start"
w1m.to_parquet(os.path.join(OUT, "rates_1min.parquet"))

w1s = base_agg("s")
w1s.index.name = "window_start"
w1s.to_parquet(os.path.join(OUT, "rates_1s.parquet"))

print(f"rates_1min.parquet: {w1m.shape} cols={list(w1m.columns)}")
print(f"rates_1s.parquet:   {w1s.shape}")
