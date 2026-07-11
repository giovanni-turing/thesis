#!/usr/bin/env python3
"""P2-1 / M1 ablation controller: REACTIVE + trailing-window high-quantile.

The missing cell in the closed-loop matrix. The thesis runs, on the encoder
pool:
  - forecast  = p90 FORECAST band + rho=15 conversion + cold-start lead L
  - reactive  = trailing-observed POINT rate + rho=15 conversion + lead L
    (the reactive branch of simulation/forecast_schedule.py IGNORES --quantile
     and reads the last complete bin's observed image rate)

The forecast-vs-reactive head-to-head therefore bundles TWO dials: anticipation
(forecast sees the next bin) AND headroom (the p90 band vs a point). This script
adds the SINGLE missing cell that separates them: a purely reactive controller
(no forecast) that reads the trailing-window p90 of the OBSERVED image rate --
i.e. it is given the same tail-aware headroom the forecast gets, but sourced
from PAST observation instead of a forecast -- converted with the identical
rho=15 rule and actuated with the identical cold-start lead L and hysteresis.

Signal (mode=react_quantile):
  at bin m the controller knows complete bins 0..m-1 (reactive info set); its
  demand estimate is q(m) = quantile_p( observed_rate[m-W .. m-1] ), the p-th
  percentile of the trailing window of W observed per-bin image rates. W is
  --react-window-s / bin_s bins.
  q(m) = observed_rate[m-1] recovers the thesis reactive baseline exactly
  (mode=react_point, W ignored).

Everything downstream -- capacity rule C = clamp(ceil(q/rho)), hysteresis
(rolling max over H min), cold-start lead (min desired over trailing L),
step-collapse and worker-seconds accounting -- is the SHARED _emit() imported
verbatim from simulation/forecast_schedule.py, so the ONLY difference from the
thesis reactive baseline is point -> trailing-window quantile, and the ONLY
difference from the forecast policy is forecast-band -> trailing observation.

Output: the same [[t_seconds, workers], ...] schedule JSON the converter's
--worker-schedule hook consumes. Feed it to workload/trace_to_two_pool.py.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from argparse import Namespace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/gio/tese/simulation")
import forecast_schedule as fs  # reuse window_start_ts + _emit verbatim

TRACE = os.environ.get(
    "TESE_TRACE", "/home/gio/tese/data/AzureLMMInferenceTrace_multimodal.csv.gz"
)
WINDOWS = Path(os.environ.get("TESE_WINDOWS", "/home/gio/tese/simulation/windows.json"))


def _quantile_frac(q: str) -> float:
    q = q.strip().lower()
    if q in ("point", "mean"):
        return 1.0  # unused for point mode
    if q.startswith("p"):
        return float(q[1:]) / 100.0
    return float(q)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", required=True)
    ap.add_argument("--mode", choices=["react_quantile", "react_point"],
                    default="react_quantile")
    ap.add_argument("--resolution", default="15s")
    ap.add_argument("--quantile", default="p90",
                    help="trailing-window percentile used as the demand estimate")
    ap.add_argument("--react-window-s", type=float, default=240.0,
                    help="trailing window (seconds) over which the observed-rate "
                         "quantile is taken; converted to W=round(window/bin_s) bins")
    ap.add_argument("--rho", type=float, default=15.0,
                    help="assumed sustainable img/s per encoder worker (tail-aware=15)")
    ap.add_argument("--cold-start-s", type=float, default=60.0)
    ap.add_argument("--hysteresis-min", type=int, default=3)
    ap.add_argument("--min-workers", type=int, default=1)
    ap.add_argument("--max-workers", type=int, default=32)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    win = json.loads(WINDOWS.read_text())[args.window]
    t0 = fs.window_start_ts(win["offset"])
    span_s = win["span_s"]
    bin_s = pd.Timedelta(args.resolution.replace("min", "m")).total_seconds()

    # ---- observed per-bin image rate over the window (the reactive signal) ----
    raw = pd.read_csv(TRACE)
    ts = raw["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
    raw["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
    raw = raw.sort_values("ts").reset_index(drop=True)
    w = raw.iloc[win["offset"]:win["offset"] + win["max_requests"]]
    rate = (w.set_index("ts")["NumImages"].resample(f"{int(bin_s)}s").sum() / bin_s)

    if args.mode == "react_point":
        q = rate.shift(1).fillna(0.0).to_numpy()  # thesis reactive baseline
        W = 1
    else:
        W = max(1, int(round(args.react_window_s / bin_s)))
        frac = _quantile_frac(args.quantile)
        # rolling quantile over the trailing W bins INCLUDING the current bin,
        # then shift(1): at bin m the estimate uses complete bins [m-W .. m-1]
        # only (strictly past -> the reactive information set, no peeking).
        q = (rate.rolling(window=W, min_periods=1).quantile(frac)
                 .shift(1).fillna(0.0).to_numpy())

    minutes = ((rate.index - t0).total_seconds()).to_numpy()
    desired = [max(args.min_workers, min(args.max_workers, int(-(-v // args.rho))))
               for v in q]

    # shared policy tail (hysteresis + cold-start lead + step emission), verbatim
    emit_args = Namespace(hysteresis_min=args.hysteresis_min,
                          cold_start_s=args.cold_start_s,
                          out=args.out, window=args.window,
                          policy=f"{args.mode}[{args.quantile},W={W}b/{args.react_window_s:g}s]")
    fs._emit(emit_args, minutes, desired, span_s, bin_s)


if __name__ == "__main__":
    main()
