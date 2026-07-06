"""EDA N — materialize binned time series (GPU/cuDF).

Plain binning of the trace into zero-filled windows. One schema, five
resolutions: index window_start; columns requests, images, ctx, gen
(counts per window — divide by window seconds for rates).

  series/rates_1s.parquet    604,800 rows
  series/rates_15s.parquet    40,320 rows
  series/rates_30s.parquet    20,160 rows
  series/rates_45s.parquet    13,440 rows
  series/rates_1min.parquet   10,080 rows
"""
import os

import numpy as np
import pandas as pd

from _common import load_trace

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "series")
os.makedirs(OUT, exist_ok=True)

df = load_trace()

w1s = df.assign(win=df["ts"].dt.floor("s")).groupby("win").agg(
    requests=("NumImages", "count"), images=("NumImages", "sum"),
    ctx=("ContextTokens", "sum"), gen=("GeneratedTokens", "sum"),
).sort_index().to_pandas()
w1s = w1s.reindex(pd.date_range(w1s.index.min(), w1s.index.max(), freq="s"), fill_value=0)
w1s.index.name = "window_start"
w1s.to_parquet(os.path.join(OUT, "rates_1s.parquet"))
print(f"rates_1s.parquet:   {w1s.shape}")

for secs, name in [(15, "15s"), (30, "30s"), (45, "45s"), (60, "1min")]:
    blocks = np.arange(len(w1s)) // secs
    wb = w1s.groupby(blocks).sum()
    wb.index = w1s.index[::secs][: len(wb)]
    wb.index.name = "window_start"
    wb.to_parquet(os.path.join(OUT, f"rates_{name}.parquet"))
    print(f"rates_{name}.parquet: {wb.shape}")
