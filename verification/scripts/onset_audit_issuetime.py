#!/usr/bin/env python3
"""B4 HONEST onset audit: restricted to each DECLARED episode span.

Fixes the two defects codex B4 identifies in simulation/detect_onsets_44.py:
  1. The old audit searches from episode_start - 30 min, so its "actual"
     crossing lands BEFORE (and sometimes entirely outside) the declared
     episode. Here the search is RESTRICTED to [episode_start, episode_end]
     exactly as declared in detect_onsets_44.py:32-37.
  2. The old audit applies a 60-second-cadence p99 rate (224 img/s * 15 s =
     3360 img/bin) at 15-second cadence. Here we report BOTH thresholds:
       - thr_60s : 223.985 img/s  -> * 15 s = 3359.8 img/bin  (the value the
                   old detector used, i.e. the Ch.3 1-min p99 rate)
       - thr_15s : 286.387 img/s  -> * 15 s = 4295.8 img/bin  (the honest
                   15-second-cadence p99 rate)
     from analysis/trace_eda/q_multires_tails_stats.json.

For each in-span episode (burst1,3,4,5) and each model (chronos/toto/timesfm):
  y_true crosses -> actual onset bin (t_actual)
  p90    crosses -> forecast crossing bin (t_pred, horizon h)
  t_issue     = t_pred - (h-1)*15 s           (thesis's own issue-time formula)
  delay       = t_pred - t_actual             (negative = crosses before signal)
  usable_lead = t_actual - t_issue            (positive => a controller acting
                at issue could have capacity ready by the actual onset for any
                startup lead L <= usable_lead; negative => LATE even at issue).

Emits verification/../rerun_verify/onset_audit_issuetime.json and prints a table.
"""
import json
import pandas as pd

BIN_S = 15
THRESHOLDS = {                       # img/s (from q_multires_tails_stats.json)
    "thr_60s_224": 223.985 * BIN_S,  # 3359.8 img/bin  (old detector's value)
    "thr_15s_286": 286.387 * BIN_S,  # 4295.8 img/bin  (honest 15s-cadence p99)
}
# Declared episode spans, verbatim from detect_onsets_44.py:32-37.
EPISODES = {
    "burst1": ("2024-10-21 13:09:00", "2024-10-21 21:08:00", 220),
    "burst3": ("2024-10-18 10:28:00", "2024-10-18 10:35:00", 1),
    "burst4": ("2024-10-18 15:47:00", "2024-10-18 18:36:00", 60),
    "burst5": ("2024-10-18 14:42:00", "2024-10-18 15:17:00", 35),
}
MODELS = ["chronos", "toto", "timesfm"]

out = {"bin_s": BIN_S, "thresholds_img_per_bin": THRESHOLDS, "episodes": {}}

frames = {m: (lambda d: d[d.resolution == "15s"].sort_values("ts").drop_duplicates("ts"))(
    pd.read_parquet(f"/home/gio/tese/predictors/results/{m}_images.parquet",
                    columns=["resolution", "ts", "h", "y_true", "point", "p50", "p90"]))
          for m in MODELS}


def first_cross(w, col, thr):
    hit = w[w[col] >= thr]
    if hit.empty:
        return None
    return hit.iloc[0]


for ep, (start, end, onset_min) in EPISODES.items():
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    rec = {"span": [start, end], "declared_onset_minutes": onset_min, "by_threshold": {}}
    for thr_name, thr in THRESHOLDS.items():
        trec = {}
        for m in MODELS:
            w = frames[m][(frames[m].ts >= s) & (frames[m].ts <= e)]
            arow = first_cross(w, "y_true", thr)
            entry = {}
            if arow is None:
                entry["actual"] = "y_true never crosses in-span"
            else:
                t_actual = arow.ts
                entry["t_actual"] = str(t_actual)
                for col in ("point", "p50", "p90"):
                    prow = first_cross(w, col, thr)
                    if prow is None:
                        entry[col] = {"detected": False}
                        continue
                    h = int(prow.h)
                    t_issue = prow.ts - pd.Timedelta(seconds=(h - 1) * BIN_S)
                    delay = (prow.ts - t_actual).total_seconds()
                    usable = (t_actual - t_issue).total_seconds()
                    entry[col] = {
                        "detected": True, "t_pred": str(prow.ts), "h": h,
                        "t_issue": str(t_issue),
                        "delay_s": delay, "usable_lead_s": usable,
                        "anticipated": usable > 0,
                    }
            trec[m] = entry
        rec["by_threshold"][thr_name] = trec
    out["episodes"][ep] = rec

path = "/home/gio/tese/simulation/results/rerun_verify/onset_audit_issuetime.json"
json.dump(out, open(path, "w"), indent=1)

# ---- pretty per-threshold p90 table ----
for thr_name in THRESHOLDS:
    print(f"\n===== p90 onset audit, threshold={thr_name} "
          f"({THRESHOLDS[thr_name]:.1f} img/bin) =====")
    print(f"{'episode':8s} {'model':8s} {'t_actual':21s} {'t_pred':21s} "
          f"{'h':>2s} {'delay_s':>8s} {'usable_lead_s':>13s}  verdict")
    for ep in EPISODES:
        for m in MODELS:
            en = out["episodes"][ep]["by_threshold"][thr_name][m]
            ta = en.get("t_actual", en.get("actual", "-"))
            p = en.get("p90", {})
            if not p.get("detected"):
                print(f"{ep:8s} {m:8s} {ta:21s} {'p90 never crosses':21s}")
                continue
            v = "ANTICIPATED" if p["usable_lead_s"] > 0 else "LATE"
            print(f"{ep:8s} {m:8s} {ta:21s} {p['t_pred']:21s} {p['h']:>2d} "
                  f"{p['delay_s']:>8.0f} {p['usable_lead_s']:>13.0f}  {v}")
print("\n->", path)
