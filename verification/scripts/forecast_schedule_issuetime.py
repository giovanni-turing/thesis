#!/usr/bin/env python3
"""B2 FIX: forecast -> encoder worker schedule actuated on FORECAST ISSUE time.

The shipped simulation/forecast_schedule.py indexes the desired capacity by
each bin's TARGET time and then delays every increase by the full cold-start
lead L (min over the trailing L window). Codex B2: that is a *delayed
target-time* path, not a scale-ahead controller. It also silently uses target
bins whose forecast was issued at horizon h; for h=1 the forecast is issued at
the target bin itself (zero usable lead), yet the shipped code still treats it
as provisionable L seconds ahead.

This variant honours the archive's tiled issue times. The 15-s archive is a
NON-OVERLAPPING stride-12 tiling: each 180-s tile (origin O) forecasts its 12
bins O..O+165 at horizons h=1..12, so a bin's forecast is ISSUED at
    O_i = ts_i - (h_i - 1) * 15 s   (the thesis's own issue-time formula),
and its maximum usable lead is (h_i - 1)*15 s in [0, 165] s. The archive can
therefore NEVER supply a 300-s issued lead; only L <= 165 s is honest.

Honest cold-start (replaces the shipped min-trailing-L):
    desired_i   = clamp(ceil((q_i / bin_s) / rho))           # same as shipped
    hdesired_i  = rolling max of desired over trailing hyst   # same as shipped
    ready_i     = max{ hdesired_j : O_j + L <= ts_i }         # matured orders
    avail_i     = min(hdesired_i, ready_i)                    # up-lead + down-now
`ready_i` is the highest capacity level whose order -- placed at its forecast
tile origin O_j (== its issue time, so issue == decision, the earliest honest
order) -- has had the full startup lead L to come up by ts_i. `avail_i` never
exceeds what is currently wanted (down-now) nor what is physically ready
(up-lead). A sustained plateau stays covered (the prior tile already forecast
it); only the genuine onset leading edge within L of first forecast detection
is short -- exactly the anticipation the experiment measures.

Emits the same [[t_s, workers], ...] change-point schedule the converter's
--worker-schedule hook consumes, and asserts the issue<=decision invariant.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "/home/gio/tese/simulation")
from forecast_schedule import window_start_ts  # reuse trace-anchored window start

BIN_S = 15.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", required=True)
    ap.add_argument("--parquet", default="/home/gio/tese/predictors/results/chronos_images.parquet")
    ap.add_argument("--resolution", default="15s")
    ap.add_argument("--quantile", default="p90")
    ap.add_argument("--rho", type=float, default=15.0)
    ap.add_argument("--cold-start-s", type=float, default=30.0)
    ap.add_argument("--hysteresis-min", type=int, default=3)
    ap.add_argument("--min-workers", type=int, default=1)
    ap.add_argument("--max-workers", type=int, default=32)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ledger-out", default=None, help="optional issue/decision ledger JSON")
    args = ap.parse_args()

    if args.resolution != "15s":
        sys.exit("issue-time actuation requires the 15s archive (h horizon carries the issue)")
    L = float(args.cold_start_s)
    if L > 165.0 + 1e-9:
        sys.exit(f"cold-start-s={L}: the H=12 15-s archive supplies at most "
                 f"(12-1)*15 = 165 s of issued lead. Refusing to fabricate lead.")

    win = json.loads((Path("/home/gio/tese/simulation/windows.json")).read_text())[args.window]
    t0 = window_start_ts(win["offset"])
    span_s = win["span_s"]

    df = pd.read_parquet(args.parquet)
    df = df[df.resolution == args.resolution]
    if "variate" in df.columns and df.variate.nunique() > 1:
        df = df[df.variate == "images"]
    df = df[(df.ts >= t0 - pd.Timedelta(minutes=1)) &
            (df.ts <= t0 + pd.Timedelta(seconds=span_s))]
    if df.empty:
        sys.exit(f"no forecast rows cover window {args.window}")
    df = df.sort_values("ts").drop_duplicates("ts").reset_index(drop=True)

    ts = df.ts.to_numpy()
    h = df.h.astype(int).to_numpy()
    # per-bin total -> img/s -> desired workers (identical rule to shipped code)
    q = (df[args.quantile].clip(lower=0.0) / BIN_S).to_numpy()
    desired = [max(args.min_workers, min(args.max_workers, int(math.ceil(v / args.rho))))
               for v in q]

    n = len(desired)
    # hysteresis: rolling max over trailing hyst_bins (scale-down hold) -- as _emit
    hyst_bins = max(0, int(round(args.hysteresis_min * 60.0 / BIN_S)))
    if hyst_bins > 0:
        hdesired = [max(desired[max(0, i - hyst_bins):i + 1]) for i in range(n)]
    else:
        hdesired = list(desired)

    # issue time per bin = tile origin O_i = ts_i - (h_i-1)*15 s
    ts_s = df.ts.astype("int64").to_numpy() / 1e9          # seconds since epoch
    issue_s = ts_s - (h - 1) * BIN_S
    ready_time = issue_s + L                                # order matures here

    # ready_i = max hdesired_j over j with ready_time_j <= ts_s_i  (matured orders).
    # Sweep in time order; maintain running max keyed by maturity <= current ts.
    # Because ready_time is not monotone in i (h varies within a tile), sort the
    # maturities and merge.
    order = sorted(range(n), key=lambda j: ready_time[j])
    avail = [args.min_workers] * n
    ledger = []
    ptr = 0
    running_max = args.min_workers
    # process target bins in ts order (already sorted by ts)
    matured = []  # (ready_time, level) already merged into running_max
    for i in range(n):
        ti = ts_s[i]
        while ptr < n and ready_time[order[ptr]] <= ti + 1e-9:
            j = order[ptr]
            if hdesired[j] > running_max:
                running_max = hdesired[j]
            matured.append(order[ptr])
            ptr += 1
        # running_max is a monotone-nondecreasing envelope of matured levels;
        # that is fine for an *up-lead* readiness gate: an increase is available
        # once matured. Down-now is enforced by the min with hdesired below.
        ready_i = running_max
        avail[i] = min(hdesired[i], ready_i)
        # record the binding issue for increases (for the ledger / invariant check)
        if i == 0 or avail[i] > avail[i - 1]:
            # find a matured j that justifies this level with the smallest issue
            just = [j for j in matured if hdesired[j] >= avail[i]]
            jbest = min(just, key=lambda j: issue_s[j]) if just else i
            ledger.append({
                "target_ts": str(pd.Timestamp(ts[i])),
                "level": int(avail[i]),
                "justifying_issue_ts": str(pd.Timestamp(int(issue_s[jbest] * 1e9))),
                "justifying_h": int(h[jbest]),
                "ready_ts": str(pd.Timestamp(int(ready_time[jbest] * 1e9))),
                "lead_s": L,
            })

    # ---- issue<=decision invariant: every unit of available capacity at ts_i
    # must be justified by a forecast issued at or before ts_i - L. ----
    for i in range(n):
        lvl = avail[i]
        if lvl <= args.min_workers:
            continue
        ok = any(hdesired[j] >= lvl and issue_s[j] + L <= ts_s[i] + 1e-9 for j in range(n))
        assert ok, (f"INVARIANT VIOLATION at bin {i} ts={pd.Timestamp(ts[i])}: "
                    f"avail={lvl} not justified by any issue<=ts-L")

    # ---- step-collapse + provisioned worker-seconds (mirrors _emit) ----
    minutes = ((df.ts - t0).dt.total_seconds()).to_numpy()
    steps: list[list[float]] = [[0.0, int(avail[0])]]
    for t, c in zip(minutes, avail):
        if int(c) != steps[-1][1]:
            steps.append([max(0.0, float(t)), int(c)])
    if steps[0][0] != 0.0:
        steps.insert(0, [0.0, int(avail[0])])

    Path(args.out).write_text(json.dumps(steps))
    if args.ledger_out:
        Path(args.ledger_out).write_text(json.dumps(ledger, indent=1))

    prov = 0.0
    for (a, ca), (b, _cb) in zip(steps, steps[1:]):
        prov += ca * (min(b, span_s) - min(a, span_s))
    prov += steps[-1][1] * max(0.0, span_s - steps[-1][0])
    print(f"{args.window} [issue-time L={L:.0f}s q={args.quantile} rho={args.rho:.0f}]: "
          f"{len(steps)} steps, workers {min(s[1] for s in steps)}..{max(s[1] for s in steps)}, "
          f"provisioned {prov:.0f} worker-s over {span_s:.0f}s "
          f"(invariant issue<=decision OK)")


if __name__ == "__main__":
    main()
