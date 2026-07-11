#!/usr/bin/env python3
"""Phase 4.3 controller: TSFM forecast -> encoder worker schedule C(t).

Consumes the archived benchmark forecasts (predictors/results/*.parquet:
stitched 12-step tiles, point + p10..p90 per bin) exactly as a scaler
would — at wall-time t the controller knows the tile forecast issued at
that tile's origin — and emits the piecewise-constant schedule the
converter's --worker-schedule hook consumes.

Policy v1 (the ablation axes deliberately exposed as flags):
  desired(t)   = clamp(ceil(q(t) / rho), min_workers, max_workers)
  hysteresis   = rolling max of desired over the trailing H minutes
                 (scale down only after H quiet minutes; H=0 disables)
  cold start   = available(t) = min desired over the trailing L seconds
                 (an increase takes effect only once the desired level has
                 been held for the full lead L; decreases are immediate —
                 the standard up-lead/down-now semantics)
where q(t) is the chosen forecast column (point, p50, p90, ...) of the
image-rate signal and rho is the assumed per-worker sustainable img/s.

Output JSON [[t_seconds, workers], ...] relative to the window start
(t=0 first), collapsed to change-points. Also prints the schedule's
provisioned worker-seconds for quick comparison against static C*.

Example:
  python3 simulation/forecast_schedule.py --window burst1 \
      --parquet predictors/results/chronos_images.parquet \
      --quantile p90 --rho 20 --cold-start-s 60 --hysteresis-min 3 \
      --out /tmp/sched_burst1_p90.json
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
# Portable: TESE_TRACE overrides; else TESE_ROOT/data/...; else repo root
# (simulation/ -> parent).
TRACE = os.environ.get("TESE_TRACE",
    str(Path(os.environ.get("TESE_ROOT", HERE.parent))
        / "data/AzureLMMInferenceTrace_multimodal.csv.gz"))
WINDOWS = Path(os.environ.get("TESE_WINDOWS", HERE / "windows.json"))


def window_start_ts(offset: int) -> pd.Timestamp:
    df = pd.read_csv(TRACE, usecols=["TIMESTAMP"])
    ts = df["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
    ts = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f").sort_values().reset_index(drop=True)
    return ts.iloc[offset]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", required=True)
    ap.add_argument("--policy", choices=["forecast", "reactive"], default="forecast",
                    help="forecast: consume the archived TSFM path. reactive: the "
                         "twin baseline — identical capacity rule, hysteresis and "
                         "cold-start, but driven by the OBSERVED image rate of the "
                         "trailing bin (what a threshold autoscaler watches); the "
                         "only difference vs forecast is signal lead time")
    ap.add_argument("--parquet", default=os.environ.get("FORECAST_PARQUET",
                        str(HERE.parent / "predictors/results/chronos_images.parquet")))
    ap.add_argument("--resolution", default="1min")
    ap.add_argument("--quantile", default="p50",
                    help="forecast column consumed: point, p10..p90")
    ap.add_argument("--rho", type=float, default=20.0,
                    help="assumed sustainable img/s per encoder worker")
    ap.add_argument("--cold-start-s", type=float, default=60.0)
    ap.add_argument("--hysteresis-min", type=int, default=3,
                    help="scale down only after this many quiet minutes (0=off)")
    ap.add_argument("--min-workers", type=int, default=1)
    ap.add_argument("--max-workers", type=int, default=32)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    win = json.loads(WINDOWS.read_text())[args.window]
    t0 = window_start_ts(win["offset"])
    span_s = win["span_s"]

    if args.policy == "reactive":
        # Observed trailing-bin image rate from the trace itself (lagged one
        # bin: at minute m the scaler knows minute m-1's rate — the reactive
        # information set). Same units (img/s) as the forecast branch.
        raw = pd.read_csv(TRACE)
        ts = raw["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
        raw["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
        raw = raw.sort_values("ts").reset_index(drop=True)
        w = raw.iloc[win["offset"]:win["offset"] + win["max_requests"]]
        bin_s = pd.Timedelta(args.resolution.replace("min", "m")).total_seconds()
        rate = (w.set_index("ts")["NumImages"]
                 .resample(f"{int(bin_s)}s").sum() / bin_s)
        rate = rate.shift(1).fillna(0.0)          # trailing-bin observation
        minutes = ((rate.index - t0).total_seconds()).to_numpy()
        q = rate.to_numpy()
        desired = [max(args.min_workers,
                       min(args.max_workers, int(-(-v // args.rho))))
                   for v in q]
        _emit(args, minutes, desired, span_s, bin_s)
        return

    df = pd.read_parquet(args.parquet)
    df = df[df.resolution == args.resolution]
    if "variate" in df.columns and df.variate.nunique() > 1:
        df = df[df.variate == "images"]
    df = df[(df.ts >= t0 - pd.Timedelta(minutes=1)) &
            (df.ts <= t0 + pd.Timedelta(seconds=span_s))]
    if df.empty:
        raise SystemExit(f"no forecast rows cover window {args.window} "
                         f"({t0} .. +{span_s:.0f}s) — outside the common span?")
    df = df.sort_values("ts").drop_duplicates("ts")  # stitched tiles: 1 row/bin
    gap_s = (df.ts.iloc[0] - t0).total_seconds()
    bin_chk = pd.Timedelta(args.resolution.replace("min", "m")).total_seconds()
    if gap_s > 2 * bin_chk:
        raise SystemExit(
            f"window start {t0} is OUTSIDE the {args.resolution} forecast "
            f"span (first bin {df.ts.iloc[0]}, {gap_s/3600:.1f} h later) — "
            f"use a finer resolution or an in-span window")

    minutes = ((df.ts - t0).dt.total_seconds()).to_numpy()
    # Forecast series are PER-BIN TOTALS (predictors chapter: "per-bin
    # totals ... at resolutions of 1s..1min"); convert to img/s so rho
    # stays in img/s-per-worker.
    bin_s = pd.Timedelta(args.resolution.replace("min", "m")).total_seconds()
    q = (df[args.quantile].clip(lower=0.0) / bin_s).to_numpy()
    desired = [max(args.min_workers, min(args.max_workers, int(-(-v // args.rho))))
               for v in q]
    _emit(args, minutes, desired, span_s, bin_s)


def _emit(args, minutes, desired, span_s, bin_s) -> None:
    """Shared policy tail: hysteresis, cold-start, step emission.
    Both windows are TIME-based and converted to bins at the actual
    resolution (a 60 s lead is 1 bin at 1min but 4 bins at 15 s)."""
    hyst_bins = max(0, int(round(args.hysteresis_min * 60.0 / bin_s)))
    if hyst_bins > 0:  # rolling max over trailing H entries
        held = []
        for i in range(len(desired)):
            held.append(max(desired[max(0, i - hyst_bins):i + 1]))
        desired = held

    # cold start: available = min desired over the trailing lead window
    lead_bins = max(0, int(round(args.cold_start_s / bin_s)))
    avail = []
    for i in range(len(desired)):
        avail.append(min(desired[max(0, i - lead_bins):i + 1]))

    steps: list[list[float]] = [[0.0, avail[0]]]
    for t, c in zip(minutes, avail):
        if c != steps[-1][1]:
            steps.append([max(0.0, float(t)), int(c)])
    if steps[0][0] != 0.0:
        steps.insert(0, [0.0, int(avail[0])])

    Path(args.out).write_text(json.dumps(steps))
    prov = 0.0
    for (a, ca), (b, _cb) in zip(steps, steps[1:]):
        prov += ca * (min(b, span_s) - min(a, span_s))
    prov += steps[-1][1] * max(0.0, span_s - steps[-1][0])
    print(f"{args.window} [{args.policy}]: {len(steps)} steps, workers "
          f"{min(s[1] for s in steps)}..{max(s[1] for s in steps)}, "
          f"provisioned {prov:.0f} worker-s over the {span_s:.0f}s window "
          f"(static C*x span for comparison; drain tail extra)")


if __name__ == "__main__":
    main()
