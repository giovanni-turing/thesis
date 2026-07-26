#!/usr/bin/env python3
"""ADVERSARIAL PROBE: the reactive arm actuated under the *warm-pool* readiness
model that the forecast (forecast_schedule_issuetime.py:127-137) and oracle
(comparator_frontier_oracle.py) arms already use.

ONE dial changed vs verification/scripts/reactive_quantile_schedule.py:
  shipped `_emit` (simulation/forecast_schedule.py:146-150):
      avail_i = min(hdesired[i-lead_bins .. i])           # strict re-warm
  warm-pool (forecast_schedule_issuetime.py:139-162, oracle:127-146):
      avail_i = min(hdesired_i, max{hdesired_j : ts_j + L <= ts_i})

Signal, conversion, rho, hysteresis, bin, floor, clamp: identical, taken from the
shipped reactive generator verbatim.
"""
import argparse, json, os, sys, math
from pathlib import Path
import pandas as pd
sys.path.insert(0, "/home/gio/tese/simulation")
from forecast_schedule import window_start_ts
TRACE = os.environ.get("TESE_TRACE", "/home/gio/tese/data/AzureLMMInferenceTrace_multimodal.csv.gz")
WINDOWS = Path(os.environ.get("TESE_WINDOWS", "/home/gio/tese/simulation/windows.json"))

ap = argparse.ArgumentParser()
ap.add_argument("--window", required=True); ap.add_argument("--resolution", default="15s")
ap.add_argument("--rho", type=float, default=15.0); ap.add_argument("--cold-start-s", type=float, default=30.0)
ap.add_argument("--hysteresis-min", type=int, default=3); ap.add_argument("--min-workers", type=int, default=1)
ap.add_argument("--max-workers", type=int, default=32); ap.add_argument("--out", required=True)
a = ap.parse_args()

win = json.loads(WINDOWS.read_text())[a.window]
t0 = window_start_ts(win["offset"]); span_s = float(win["span_s"])
bin_s = pd.Timedelta(a.resolution.replace("min","m")).total_seconds(); L = float(a.cold_start_s)
raw = pd.read_csv(TRACE)
ts = raw["TIMESTAMP"].str.replace("Z","",regex=False).str.pad(23,"right","0")
raw["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
raw = raw.sort_values("ts").reset_index(drop=True)
nreq = win.get("max_requests") or win.get("requests")
w = raw.iloc[win["offset"]:win["offset"]+int(nreq)]
rate = (w.set_index("ts")["NumImages"].resample(f"{int(bin_s)}s").sum()/bin_s)
q = rate.shift(1).fillna(0.0).to_numpy()                       # react_point, verbatim
ts_rel = ((rate.index - t0).total_seconds()).to_numpy()
desired = [max(a.min_workers, min(a.max_workers, int(-(-v // a.rho)))) for v in q]
n = len(desired)
hyst_bins = max(0, int(round(a.hysteresis_min*60.0/bin_s)))
hdes = [max(desired[max(0,i-hyst_bins):i+1]) for i in range(n)] if hyst_bins>0 else list(desired)

ready = [float(ts_rel[i]) + L for i in range(n)]               # order at the bin it is computed
order = sorted(range(n), key=lambda j: ready[j])
avail=[a.min_workers]*n; ptr=0; running=a.min_workers
for i in range(n):
    ti=float(ts_rel[i])
    while ptr<n and ready[order[ptr]]<=ti+1e-9:
        j=order[ptr]; running=max(running,hdes[j]); ptr+=1
    avail[i]=min(hdes[i], max(running, a.min_workers))
steps=[[0.0,int(avail[0])]]
for t,c in zip(ts_rel,avail):
    if int(c)!=steps[-1][1]: steps.append([max(0.0,float(t)),int(c)])
if steps[0][0]!=0.0: steps.insert(0,[0.0,int(avail[0])])
Path(a.out).write_text(json.dumps(steps))
print(f"{a.window} warm-pool reactive: {len(steps)} steps {min(s[1] for s in steps)}..{max(s[1] for s in steps)}")
