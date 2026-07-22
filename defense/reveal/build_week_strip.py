#!/usr/bin/env python3
"""Week-strip data for the reveal deck's 'signal' slide.

1-min image rate + request rate over the full 7-day trace, downsampled to
per-bucket max (7-min buckets ~= 1 px per bucket at slide width) so burst
spikes survive; 18 episode spans + onsets from windows_ext.json (the A8
source). Output: defense/reveal/assets/week_data.js (offline <script src>).
"""
import gzip
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path("/home/gio/tese")
TRACE = ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz"
WINS = json.load(open(ROOT / "defense/anim/data/windows_ext.json"))
ONSET_B = {"burst1": 220, "burst2": 48, "burst3": 1, "burst4": 60, "burst5": 35, "burst6": 1}

raw = pd.read_csv(TRACE)
ts = raw["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
raw["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
w = raw.assign(win=raw["ts"].dt.floor("min")).groupby("win").agg(
    images=("NumImages", "sum"), reqs=("NumImages", "size")).sort_index()
w = w.reindex(pd.date_range(w.index.min(), w.index.max(), freq="min"), fill_value=0)
img = (w["images"] / 60.0).to_numpy()
req = (w["reqs"] / 60.0).to_numpy()
t0 = w.index[0]

BUCKET = 7  # minutes per bucket
n = len(img) // BUCKET
img_b = [round(float(img[i * BUCKET:(i + 1) * BUCKET].max()), 2) for i in range(n)]
req_b = [round(float(req[i * BUCKET:(i + 1) * BUCKET].max()), 3) for i in range(n)]

eps = []
for key in [f"burst{i}" for i in range(1, 7)] + [f"e{i}" for i in range(7, 19)]:
    win = WINS[key]
    m = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}):?\d* \.\. (\d{4}-\d{2}-\d{2} \d{2}:\d{2})", win["note"])
    s_min = (pd.Timestamp(m.group(1)) - t0).total_seconds() / 60.0
    e_min = (pd.Timestamp(m.group(2)) - t0).total_seconds() / 60.0
    eps.append({
        "key": key, "label": key.replace("burst", "b"),
        "onset": ONSET_B.get(key, win.get("onset_min")),
        "peak": round(win["peak_1min_img_per_s"], 1),
        "s": round(s_min, 1), "e": round(e_min, 1),
    })

data = {
    "t0": str(t0), "bucket_min": BUCKET, "total_min": n * BUCKET,
    "p99": 224, "req_p99": 4.35,
    "img": img_b, "req": req_b, "episodes": eps,
    "provenance": "1-min rates from AzureLMMInferenceTrace_multimodal.csv.gz, "
                  "per-7-min-bucket max; episodes from windows_ext.json (A8 source)",
}
out = ROOT / "defense/reveal/assets/week_data.js"
out.write_text("const WEEK = " + json.dumps(data) + ";\n")
print(f"wrote {out}: {n} buckets, {len(eps)} episodes, "
      f"img max {max(img_b)}, req max {max(req_b)}")
