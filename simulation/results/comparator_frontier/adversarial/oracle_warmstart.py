#!/usr/bin/env python3
"""§8.2 comparator arm (5): PERFECT-FUTURE ORACLE encoder schedule.

Upper bound on any forecast-driven policy under the thesis's own conversion and
actuation physics. The oracle is the forecast arm with the forecast replaced by
TRUTH:

  signal      the TRUE per-bin image rate of the trace itself, at the bin it is
              provisioning for (no shift, no forecast error). The reactive arm
              reads bin m-1; the forecast arm reads a p90 band issued at the
              tile origin; the oracle reads bin m exactly.
  headroom    NONE. Quantile headroom exists to cover forecast error; a perfect
              forecast has none, so the oracle consumes the point rate. (The
              conversion rating rho is NOT headroom -- it is the measured
              tail-aware per-worker capacity and is held identical to every
              other arm.)
  conversion  identical: desired = clamp(ceil(rate / rho), min_workers,
              max_workers), rho=15 img/s (verification/scripts/
              reactive_quantile_schedule.py:110-112,
              forecast_schedule_issuetime.py:105-107).
  hysteresis  identical: rolling max of desired over the trailing H minutes
              (H=3), so scale-down is damped exactly as in the other arms
              (simulation/forecast_schedule.py:139-144).
  startup     IDENTICAL PHYSICS, best-case placement. Capacity ordered at t is
              ready at t+L and not before. Knowing the future, the oracle places
              every order exactly L ahead of the bin that needs it:
                  order_i     = max(0, ts_i - L)      # never before t=0
                  ready_i     = order_i + L
                  readylvl(t) = max{ hdesired_j : ready_j <= t }
                  avail_i     = min(hdesired_i, max(readylvl(ts_i), min_workers))
              This is the forecast arm's maturity rule
              (forecast_schedule_issuetime.py:117-162) with the archive's issue
              time replaced by the earliest honest order time. Consequence: the
              lead binds ONLY in the first L seconds of the window (nothing can
              be ordered before the controller exists); everywhere else the
              oracle pays for capacity from readiness with no anticipation
              error. `avail` never exceeds what is currently wanted (down-now)
              nor what is physically ready (up-lead).

It is therefore NOT a zero-startup fantasy: it obeys the same lead as every
other arm, and it is not free -- it still bills every provisioned worker-second
from readiness. What it removes is exactly one thing: forecast error. Any
forecast policy that beat it under the same conversion would be beating the
truth.

Emits the same [[t_seconds, workers], ...] change-point schedule the converter's
--worker-schedule hook consumes (workload/trace_to_two_pool.py:467-475).

Usage:
  comparator_frontier_oracle.py --window aggregate --rho 15 --cold-start-s 30 \
      --hysteresis-min 3 --out oracle.sched.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import pandas as pd

_ROOT = os.environ.get("TESE_ROOT") or str(Path(__file__).resolve().parents[1])
sys.path.insert(0, os.path.join(_ROOT, "simulation"))
from forecast_schedule import window_start_ts  # trace-anchored window start, verbatim

TRACE = os.environ.get(
    "TESE_TRACE", os.path.join(_ROOT, "data/AzureLMMInferenceTrace_multimodal.csv.gz")
)
WINDOWS = Path(os.environ.get("TESE_WINDOWS", os.path.join(_ROOT, "simulation/windows.json")))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", required=True)
    ap.add_argument("--resolution", default="15s",
                    help="control bin; 15s = the archive/controller bin used by every arm")
    ap.add_argument("--rho", type=float, default=15.0,
                    help="assumed sustainable img/s per encoder worker (tail-aware=15)")
    ap.add_argument("--cold-start-s", type=float, default=30.0,
                    help="startup lead L: capacity ordered at t is ready at t+L")
    ap.add_argument("--hysteresis-min", type=int, default=3,
                    help="scale-down damping, identical to the other arms (0 = off, "
                         "the cost-minimal oracle variant)")
    ap.add_argument("--min-workers", type=int, default=1)
    ap.add_argument("--max-workers", type=int, default=32)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ledger-out", default=None,
                    help="optional order/readiness ledger JSON (audit trail)")
    args = ap.parse_args()

    win = json.loads(WINDOWS.read_text())[args.window]
    t0 = window_start_ts(win["offset"])
    span_s = float(win["span_s"])
    bin_s = pd.Timedelta(args.resolution.replace("min", "m")).total_seconds()
    L = float(args.cold_start_s)

    # ---- TRUE per-bin image rate over the window (same slice + resample as the
    # reactive arm, verification/scripts/reactive_quantile_schedule.py:104-108,
    # but WITHOUT the .shift(1): the oracle knows the bin it provisions for). ----
    raw = pd.read_csv(TRACE)
    ts_col = raw["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
    raw["ts"] = pd.to_datetime(ts_col, format="%Y-%m-%dT%H:%M:%S.%f")
    raw = raw.sort_values("ts").reset_index(drop=True)
    nreq = win.get("max_requests") or win.get("requests")
    w = raw.iloc[win["offset"]:win["offset"] + int(nreq)]
    rate = (w.set_index("ts")["NumImages"].resample(f"{int(bin_s)}s").sum() / bin_s)

    ts_rel = ((rate.index - t0).total_seconds()).to_numpy()  # seconds from window start
    q = rate.to_numpy()
    desired = [max(args.min_workers, min(args.max_workers, int(math.ceil(v / args.rho))))
               for v in q]
    n = len(desired)

    # hysteresis: rolling max over trailing hyst_bins -- forecast_schedule.py:139-144
    hyst_bins = max(0, int(round(args.hysteresis_min * 60.0 / bin_s)))
    if hyst_bins > 0:
        hdesired = [max(desired[max(0, i - hyst_bins):i + 1]) for i in range(n)]
    else:
        hdesired = list(desired)

    # ---- startup physics: order L ahead, never before the window starts ----
    order_t = [float(ts_rel[i]) - L for i in range(n)]  # ADVERSARIAL VARIANT: pre-window ordering allowed (the fc arm's convention)
    ready_t = [order_t[i] + L for i in range(n)]
    order = sorted(range(n), key=lambda j: ready_t[j])

    avail = [args.min_workers] * n
    ledger = []
    ptr = 0
    running_max = args.min_workers
    matured: list[int] = []
    for i in range(n):
        ti = float(ts_rel[i])
        while ptr < n and ready_t[order[ptr]] <= ti + 1e-9:
            j = order[ptr]
            if hdesired[j] > running_max:
                running_max = hdesired[j]
            matured.append(j)
            ptr += 1
        avail[i] = min(hdesired[i], max(running_max, args.min_workers))
        if i == 0 or avail[i] > avail[i - 1]:
            just = [j for j in matured if hdesired[j] >= avail[i]]
            jb = min(just, key=lambda j: order_t[j]) if just else i
            ledger.append({
                "target_ts": str(pd.Timestamp(rate.index[i])),
                "target_rel_s": round(ti, 3),
                "level": int(avail[i]),
                "order_rel_s": round(order_t[jb], 3),
                "ready_rel_s": round(ready_t[jb], 3),
                "lead_s": L,
                "signal": "true-future-point",
            })

    # ---- invariant: every unit of capacity above the floor at ts_i must be
    # justified by an order placed at or before ts_i - L, and never before t=0. ----
    for i in range(n):
        lvl = avail[i]
        if lvl <= args.min_workers:
            continue
        ok = any(hdesired[j] >= lvl
                 and order_t[j] + L <= float(ts_rel[i]) + 1e-9 for j in range(n))
        assert ok, (f"ORACLE INVARIANT VIOLATION at bin {i} t={ts_rel[i]:.1f}s: "
                    f"avail={lvl} not justified by any order placed <= t-L")

    # ---- step-collapse + provisioned worker-seconds (mirrors _emit verbatim,
    # simulation/forecast_schedule.py:152-167) ----
    steps: list[list[float]] = [[0.0, int(avail[0])]]
    for t, c in zip(ts_rel, avail):
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
    print(f"{args.window} [oracle L={L:.0f}s rho={args.rho:.0f} H={args.hysteresis_min}min]: "
          f"{len(steps)} steps, workers {min(s[1] for s in steps)}..{max(s[1] for s in steps)}, "
          f"provisioned {prov:.0f} worker-s over {span_s:.0f}s "
          f"(order<=t-L invariant OK)")


if __name__ == "__main__":
    main()
