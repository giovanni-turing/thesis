#!/usr/bin/env python3
"""Convention-minimized metric stack over the frontier arms (author directive,
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
  * TOTAL delay mass sum(delay) in request-seconds -- the leading
    threshold-integrated synthesis (the area under the full empirical
    exceedance-count curve: sum_i d_i = integral_0^inf N(d>t) dt), per
    reviewer msgs 203/208; the frozen endpoint remains every-window p99;
  * provisioned worker-seconds and worker-hours (absolute resource-time).

Plus an fc_vs_re block: the exact survival-curve comparison between
forecast_p90 and reactive (strict-exceedance counts at every observed cut;
the exception intervals where forecast has MORE exceedances), and the exact
request-paired outcome counts (same request index in both traces).

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
QS = [50, 90, 95, 99, 99.5, 99.9, 99.99]


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
        "total_delay_request_s": round(float(delay.sum()) / 1000.0, 3),
        "violations": {
            str(t): {
                "count": int((delay > t).sum()),
                "fraction_of_all": round(float((delay > t).mean()), 6),
                "fraction_of_image_bearing": round(float((img > t).mean()), 6),
                "excess_mass_request_s": round(float(np.clip(delay - t, 0, None).sum()) / 1000.0, 1),
            } for t in THRESHOLDS_MS},
    }
    return row, delay


def fc_vs_re(d_fc, d_re):
    """Exact survival comparison + request-paired outcomes (msg 203)."""
    cuts = np.unique(np.concatenate([d_fc, d_re]))
    sf, sr = np.sort(d_fc), np.sort(d_re)
    cf = len(d_fc) - np.searchsorted(sf, cuts, side="right")
    cr = len(d_re) - np.searchsorted(sr, cuts, side="right")
    worse = cf > cr          # forecast strictly MORE exceedances at cut t
    intervals = []
    i = 0
    while i < len(cuts):
        if worse[i]:
            j = i
            while j + 1 < len(cuts) and worse[j + 1]:
                j += 1
            end = float(cuts[j + 1]) if j + 1 < len(cuts) else float("inf")
            intervals.append({
                "interval_s": [round(float(cuts[i]) / 1000.0, 6),
                               round(end / 1000.0, 6)],
                "counts_fc_re": [int(cf[i]), int(cr[i])]})
            i = j + 1
        else:
            i += 1
    delta = d_fc - d_re
    return {
        "note": ("exceedance counts use strict >t at every observed cut; "
                 "'paired' compares the SAME request index across the two "
                 "traces (not order-statistic ranks)"),
        "exception_intervals": intervals,
        "max_delay_s": [round(float(d_fc.max()) / 1000.0, 6),
                        round(float(d_re.max()) / 1000.0, 6)],
        "paired": {
            "forecast_better": int((delta < 0).sum()),
            "ties": int((delta == 0).sum()),
            "forecast_worse": int((delta > 0).sum()),
        },
    }


def main():
    check = "--check" in sys.argv
    want = [c for c in B.cells()
            if c["window"] == B.COST_WINDOW and c["group"] in ("core", "family")]
    pairs = [dist_row(c) for c in want]
    rows = [r for r, _ in pairs]
    delays = {r["arm"]: d for (r, d) in pairs}

    # readiness diagnostics (msg 204): the shipped forecast/oracle arms use
    # warm-pool issue-time maturity while the shipped reactive family uses
    # strict re-warm (frontier_summary.symmetry_repair_diagnostics). The
    # three tracked repair traces let the full-span comparison be stated
    # under each readiness interpretation. NOT frontier arms.
    diag_cells = [
        {"arm": "forecast_p90_strict_rewarm", "group": "readiness_diagnostic",
         "window": B.COST_WINDOW, "dir": HERE / "adversarial",
         "tag": "aggregate_fcSTRICT"},
        {"arm": "reactive_warmpool_M1", "group": "readiness_diagnostic",
         "window": B.COST_WINDOW, "dir": HERE / "adversarial",
         "tag": "aggregate_reWPm1"},
        {"arm": "reactive_warmpool_M2", "group": "readiness_diagnostic",
         "window": B.COST_WINDOW, "dir": HERE / "adversarial",
         "tag": "aggregate_reWPm2"},
    ]
    diag_rows = [r for r, _ in (dist_row(c) for c in diag_cells)]
    static = next(r["worker_s"] for r in rows if r["arm"] == "static_C8")
    for r in rows:
        r["worker_s_vs_static"] = round(r["worker_s"] / static, 4)
    out = {
        "note": ("compute-only metric stack; the 1000 ms column reproduces the "
                 "evaluation SLA as ONE threshold of a swept curve; "
                 "total_delay_request_s is the leading threshold-integrated synthesis; the frozen endpoint remains every-window p99 compliance"),
        "window": B.COST_WINDOW,
        "thresholds_ms": THRESHOLDS_MS,
        "arms": rows,
        "fc_vs_re": fc_vs_re(delays["forecast_p90"], delays["reactive"]),
        "comparisons_by_readiness": {
            "note": ("shipped forecast/oracle arms use warm-pool issue-time "
                     "maturity; the shipped reactive family uses strict "
                     "re-warm (frontier_summary.symmetry_repair_diagnostics). "
                     "These tracked repair traces are diagnostics, NOT "
                     "frontier arms; every-window compliance stays the "
                     "predeclared endpoint (reactive_warmpool_M1 fails "
                     "burst3)."),
            "arms": diag_rows,
        },
    }
    if check:
        tracked = json.loads((HERE / "metric_stack.json").read_text())
        if tracked == out:
            print("metric_stack --check: OK (recomputed == tracked)")
            return
        raise SystemExit("metric_stack --check: MISMATCH against tracked artifact")
    (HERE / "metric_stack.json").write_text(json.dumps(out, indent=1))
    print(f"{'arm':<28}{'worker_h':>9}{'vs_stat':>8}{'p99':>9}{'total_delay':>13}"
          + "".join(f"{'v>' + str(t):>9}" for t in THRESHOLDS_MS)
          + f"{'excess1000 (req.s)':>20}")
    for r in sorted(rows, key=lambda x: x["worker_s"]):
        print(f"{r['arm']:<28}{r['worker_h']:>9.1f}{r['worker_s_vs_static']:>8.3f}"
              f"{r['delay_quantiles_all_ms']['99']:>9.1f}"
              f"{r['total_delay_request_s']:>13.1f}"
              + "".join(f"{r['violations'][str(t)]['count']:>9}" for t in THRESHOLDS_MS)
              + f"{r['violations']['1000']['excess_mass_request_s']:>20.1f}")
    print("fc_vs_re:", json.dumps(out["fc_vs_re"], indent=1))
    print(f"\nwrote {HERE / 'metric_stack.json'} ({len(rows)} arms)")


if __name__ == "__main__":
    main()
