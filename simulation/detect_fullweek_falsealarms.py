#!/usr/bin/env python3
"""Full-week false-alarm rate for the p90 burst detector.

detect_onsets_44.py counts false alarms only on the calm reference day.
This extends that to the WHOLE 5.60-day evaluation span: over every
15-s bin in [2024-10-16 21:39, trace end], count bins where each
forecast path crosses the burst threshold (224 img/s x 15 s) while the
OBSERVED per-bin image total does NOT --- i.e. a scale-up the controller
would have ordered with no real onset behind it. Reports the count and
rate per model x path, EXCLUDING the true in-span episode windows (those
crossings are correct, not false).

Artifact: simulation/results/riders44/fullweek_false_alarms.json
"""
import json
import pandas as pd

BIN_S = 15
THR = 224 * BIN_S
SPAN = ("2024-10-16 21:39:00", "2024-10-22 12:00:00")
# true episodes to EXCLUDE from false-alarm counting (crossings there are correct)
EPISODES = [
    ("2024-10-21 12:30:00", "2024-10-21 21:30:00"),  # burst1 +pad
    ("2024-10-18 09:50:00", "2024-10-18 11:00:00"),  # burst3 +pad
    ("2024-10-18 15:30:00", "2024-10-18 19:00:00"),  # burst4 +pad
    ("2024-10-18 14:20:00", "2024-10-18 15:30:00"),  # burst5 +pad
]
MODELS = ["chronos", "toto", "timesfm"]
PATHS = ["point", "p50", "p90"]

lo, hi = pd.Timestamp(SPAN[0]), pd.Timestamp(SPAN[1])
out = {"threshold_img_per_bin": THR, "bin_s": BIN_S, "span": SPAN,
       "note": "false alarm = path crosses threshold while observed does NOT, "
               "outside true episode windows, over the full 5.60-day span",
       "false_alarms": {}}

for m in MODELS:
    df = pd.read_parquet(f"/home/gio/tese/predictors/results/{m}_images.parquet",
                         columns=["resolution", "ts", "h", "y_true", "point", "p50", "p90"])
    df = df[df.resolution == "15s"].copy()
    df["ts"] = pd.to_datetime(df["ts"])
    # one row per bin: use the shortest-horizon forecast for each ts (h==1)
    df = df[(df.ts >= lo) & (df.ts < hi)]
    df = df.sort_values(["ts", "h"]).drop_duplicates("ts", keep="first")
    # mask out true episodes
    in_ep = pd.Series(False, index=df.index)
    for a, b in EPISODES:
        in_ep |= (df.ts >= pd.Timestamp(a)) & (df.ts < pd.Timestamp(b))
    cand = df[~in_ep]
    total_bins = len(cand)
    obs_cross = cand["y_true"] >= THR
    for p in PATHS:
        path_cross = cand[p] >= THR
        # false alarm: path crosses, observed does not
        fa = int((path_cross & ~obs_cross).sum())
        out["false_alarms"].setdefault(m, {})[p] = {
            "count": fa, "bins": total_bins,
            "rate_per_day": round(fa / (total_bins * BIN_S / 86400), 3) if total_bins else None,
        }

art = "/home/gio/tese/simulation/results/riders44/fullweek_false_alarms.json"
json.dump(out, open(art, "w"), indent=1)
print(f"full-week false alarms (outside episodes), threshold {THR} img/bin:")
for m in MODELS:
    for p in PATHS:
        r = out["false_alarms"][m][p]
        print(f"  {m:9} {p:6}: {r['count']:>4} FA / {r['bins']} bins  ({r['rate_per_day']}/day)")
print(f"-> {art}")
