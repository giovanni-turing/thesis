#!/usr/bin/env python3
"""Rider (d) — burst-onset detection from the archived stitched forecasts.

For each in-span episode (15-s forecasts cover from 2024-10-16 09:36; that
excludes ep2/ep6, both pre-span) and each model x path in {point, p50, p90}:

  t_actual  first 15-s bin in [start_baseline - 30 min, end_baseline] where
            the OBSERVED per-bin image total crosses the episode threshold
            (224 img/s x 15 s = 3,360 images/bin — the Ch.3 p99 definition).
  t_pred    first bin in the same range where the forecast path crosses it.
  delay_s   t_pred - t_actual  (negative = the path crosses BEFORE the
            observed signal does — anticipation).
  t_issue   wall-clock time the crossing tile was issued (ts - (h-1)*15 s):
            the moment a controller could have ACTED on that value.
  usable_lead_s  t_actual - t_issue: the largest cold-start lead L under
            which capacity ordered at issue time is serving by the actual
            crossing. Compare against the 4.4 grid {15,30,45,300}.

False alarms: on the calm reference day (2024-10-19, the steady24h window),
count bins where each path crosses the threshold while the observed signal
never does (per-day rate).

Artifact: simulation/results/riders44/detection_delay.json
Run: eda/.venv/bin/python simulation/detect_onsets_44.py
"""
import json

import pandas as pd

BIN_S = 15
THR = 224 * BIN_S          # images per 15-s bin
EPISODES = {                # in-span at 15-s resolution (span starts Oct 16 09:36)
    "ep1/burst1": ("2024-10-21 13:09:00", "2024-10-21 21:08:00", 220),
    "ep3/burst3": ("2024-10-18 10:28:00", "2024-10-18 10:35:00", 1),
    "ep4/burst4": ("2024-10-18 15:47:00", "2024-10-18 18:36:00", 60),
    "ep5/burst5": ("2024-10-18 14:42:00", "2024-10-18 15:17:00", 35),
}
CALM = ("2024-10-19 00:00:00", "2024-10-20 00:00:00")
MODELS = ["chronos", "toto", "timesfm"]
PATHS = ["point", "p50", "p90"]

out = {"threshold_img_per_bin": THR, "bin_s": BIN_S, "episodes": {}, "false_alarms_calm_day": {}}
for m in MODELS:
    df = pd.read_parquet(f"/home/gio/tese/predictors/results/{m}_images.parquet",
                         columns=["resolution", "ts", "h", "y_true", "point", "p50", "p90"])
    df = df[df.resolution == "15s"].sort_values("ts").drop_duplicates("ts")

    for ep, (start, end, onset_min) in EPISODES.items():
        t0 = pd.Timestamp(start) - pd.Timedelta(minutes=30)
        w = df[(df.ts >= t0) & (df.ts <= pd.Timestamp(end))]
        rec = out["episodes"].setdefault(ep, {"onset_minutes": onset_min})
        act = w[w.y_true >= THR]
        if act.empty:
            rec[m] = "actual never crosses"
            continue
        t_actual = act.ts.iloc[0]
        rec.setdefault("t_actual", str(t_actual))
        rec[m] = {}
        for p in PATHS:
            hit = w[w[p] >= THR]
            if hit.empty:
                rec[m][p] = {"detected": False}
                continue
            row = hit.iloc[0]
            t_issue = row.ts - pd.Timedelta(seconds=(int(row.h) - 1) * BIN_S)
            rec[m][p] = {
                "detected": True,
                "delay_s": float((row.ts - t_actual).total_seconds()),
                "usable_lead_s": float((t_actual - t_issue).total_seconds()),
            }

    calm = df[(df.ts >= pd.Timestamp(CALM[0])) & (df.ts < pd.Timestamp(CALM[1]))]
    fa = {"actual_crossings": int((calm.y_true >= THR).sum())}
    for p in PATHS:
        fa[p] = int((calm[p] >= THR).sum())
    out["false_alarms_calm_day"][m] = fa

path = "/home/gio/tese/simulation/results/riders44/detection_delay.json"
json.dump(out, open(path, "w"), indent=1)
print(json.dumps(out, indent=1))
print("->", path)
