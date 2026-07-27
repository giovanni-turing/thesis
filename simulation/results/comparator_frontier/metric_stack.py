#!/usr/bin/env python3
"""SLO-convention-free metric stack over the frontier arms (author directive,
2026-07-27: "bursts and SLOs are conventions -- prefer aggregated metrics
(violations, intensity, worker-hours) and full distributions"). COMPUTE-ONLY:
writes metric_stack.json next to this script and prints a table; touches no
manuscript file.

Per arm, on the AGGREGATE evaluation span, from the tracked raw emitted
traces (the same inputs build_frontier_summary.py recomputes from):

  * the full encoder-delay quantile grid (all requests, and image-bearing
    only): p50/p90/p95/p99/p99.9/max;
  * violation COUNTS and fractions at a swept threshold grid
    {250, 500, 750, 1000, 1500, 2000} ms -- the 1000 ms evaluation SLA is
    one column of a curve, not the organizing convention;
  * violation INTENSITY: excess mass over each threshold,
    sum((delay - T)+) in request-seconds;
  * provisioned worker-seconds and worker-hours (absolute resource-time).

Arms: the five core arms + the full warm-floor family (aggregate window).
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_frontier_summary as B

THRESHOLDS_MS = [250, 500, 750, 1000, 1500, 2000]
QS = [50, 90, 95, 99, 99.9]


def dist_row(cell):
    jsonl = None
    for suffix in (".jsonl.zst", ".jsonl"):
        cand = cell["dir"] / f"{cell['tag']}{suffix}"
        if cand.exists():
            jsonl = cand
            break
    sched = cell["dir"] / f"{cell['tag']}.sched.json"
    if jsonl is None or not sched.exists():
        raise SystemExit(f"missing inputs for {cell['tag']} in {cell['dir']}")
    arr, ni = B.window_arrivals(cell["window"])
    n = len(arr)
    ts = np.full(n, np.nan)
    with B.open_jsonl(jsonl) as f:
        for line in f:
            r = json.loads(line)
            ts[r["hash_ids"][0] // 100_000] = r["timestamp"]
    if np.isnan(ts).any():
        raise SystemExit(f"row mismatch {jsonl}")
    delay = np.where(ni > 0, ts - arr, 0.0)
    img = delay[ni > 0]

    steps = sorted((float(t) * 1000.0, int(c)) for t, c in json.loads(sched.read_text()))
    h = B.RTT_MS + B.PER_IMG_MS * ni
    fin = ts - h
    t_end_ms = max(float(arr[-1]), float(fin[ni > 0].max()) if (ni > 0).any() else 0.0)
    prov = 0.0
    for (t0, c0), (t1, _) in zip(steps, steps[1:]):
        prov += c0 * max(0.0, min(t1, t_end_ms) - min(t0, t_end_ms))
    prov += steps[-1][1] * max(0.0, t_end_ms - steps[-1][0])
    worker_s = prov / 1000.0

    row = {
        "arm": cell["arm"], "group": cell["group"], "window": cell["window"],
        "n_requests": int(n), "n_image_bearing": int((ni > 0).sum()),
        "worker_s": round(worker_s, 1),
        "worker_h": round(worker_s / 3600.0, 2),
        "delay_quantiles_all_ms": {str(q): B.pctl(delay, q) for q in QS} | {
            "max": round(float(delay.max()), 3)},
        "delay_quantiles_image_bearing_ms": {str(q): B.pctl(img, q) for q in QS} | {
            "max": round(float(img.max()), 3)},
        "violations": {
            str(t): {
                "count": int((delay > t).sum()),
                "fraction_of_all": round(float((delay > t).mean()), 6),
                "fraction_of_image_bearing": round(float((img > t).mean()), 6),
                "excess_mass_request_s": round(float(np.clip(delay - t, 0, None).sum()) / 1000.0, 1),
            } for t in THRESHOLDS_MS},
    }
    return row


def main():
    want = [c for c in B.cells()
            if c["window"] == B.COST_WINDOW and c["group"] in ("core", "family")]
    rows = [dist_row(c) for c in want]
    static = next(r["worker_s"] for r in rows if r["arm"] == "static_C8")
    for r in rows:
        r["worker_s_vs_static"] = round(r["worker_s"] / static, 4)
    out = {
        "note": ("compute-only metric stack; the 1000 ms column reproduces the "
                 "evaluation SLA as ONE threshold of a swept curve"),
        "window": B.COST_WINDOW,
        "thresholds_ms": THRESHOLDS_MS,
        "arms": rows,
    }
    (HERE / "metric_stack.json").write_text(json.dumps(out, indent=1))
    print(f"{'arm':<28}{'worker_h':>9}{'vs_stat':>8}{'p99':>9}"
          + "".join(f"{'v>' + str(t):>9}" for t in THRESHOLDS_MS)
          + f"{'excess1000 (req.s)':>20}")
    for r in sorted(rows, key=lambda x: x["worker_s"]):
        print(f"{r['arm']:<28}{r['worker_h']:>9.1f}{r['worker_s_vs_static']:>8.3f}"
              f"{r['delay_quantiles_all_ms']['99']:>9.1f}"
              + "".join(f"{r['violations'][str(t)]['count']:>9}" for t in THRESHOLDS_MS)
              + f"{r['violations']['1000']['excess_mass_request_s']:>20.1f}")
    print(f"\nwrote {HERE / 'metric_stack.json'} ({len(rows)} arms)")


if __name__ == "__main__":
    main()
