#!/usr/bin/env python
"""Phase 5.2 anchor, deliverable (iii): end-to-end FIFO replay of the burst3
image-arrival schedule through ONE encoder worker, under two cost models:

  (A) AIC-predicted f(N)  — what the simulator uses (aic_f_n_postinfill.csv)
  (B) MEASURED f(N)       — this silicon's sdpa sweep (anchor_sdpa_5x50.json)

The FIFO batching logic is a faithful port of
workload/trace_to_two_pool.simulate_vision_pool (greedy whole-request batching
up to the 64-image cap, parallel-chunk dispatch for oversized requests), and
encoder_delay = (finish - arrival) + handoff, exactly as the converter computes
it. Cost model (A) reproduces the simulator's own burst3-C1 result as a
self-consistency check; (B) shows what the SAME schedule does at measured
silicon service times. The comparison of encoder-delay p99 between (A) and (B)
is the end-to-end consequence of the measured/predicted f(N) ratio.

burst3 window: offset 531966, 3093 requests, 1241 image-bearing, 143240 images
(regenerated from the trace by pure pandas; matches the sim stats exactly).
Cost for a batch of T images is f(T), interpolated from the sampled curve
(images in a batch <= cap = 64; oversized requests chunked into <=64 forwards).

Usage: replay_burst3_fifo.py
"""
import bisect
import json
import math
import os
from collections import deque

_HERE = os.path.dirname(os.path.abspath(__file__))
CAP = 64
HANDOFF_RTT_MS = 0.2
HANDOFF_GBPS = 25.0
LLM_HIDDEN = 4096
BYTES_PER_ELEM = 2
TOKENS_PER_IMAGE = 196  # post-merge, 448px

REQS_JSON = os.path.join(_HERE, "burst3_img_reqs.json")
N_ALL_REQS = 3093  # burst3 window total (image + text-only); sim takes percentiles over all
AIC_CSV = os.path.join(_HERE, os.pardir, "phaseB_batch_validation",
                       "aic_f_n_postinfill.csv")
MEAS_JSON = os.path.join(_HERE, "anchor_sdpa_5x50.json")
SIM_REF = "/home/gio/tese/simulation/results/grid/vision_burst3_C1.json"


class PiecewiseCost:
    """f(N) from sampled (N, ms) points; linear interpolation, linear
    extrapolation on the last segment. Anchored at f(0)=0."""

    def __init__(self, points):
        pts = sorted(points)
        if pts[0][0] != 0:
            pts = [(0, 0.0)] + pts
        self.xs = [p[0] for p in pts]
        self.ys = [p[1] for p in pts]

    def latency_ms(self, n):
        n = int(n)
        if n <= 0:
            return 0.0
        if n <= self.xs[-1]:
            j = bisect.bisect_left(self.xs, n)
            if self.xs[j] == n:
                return self.ys[j]
            x0, x1 = self.xs[j - 1], self.xs[j]
            y0, y1 = self.ys[j - 1], self.ys[j]
        else:  # extrapolate on the last segment slope
            x0, x1 = self.xs[-2], self.xs[-1]
            y0, y1 = self.ys[-2], self.ys[-1]
        return y0 + (y1 - y0) * (n - x0) / (x1 - x0)

    def chunked_service_ms(self, n, cap):
        full, rem = divmod(int(n), cap)
        total = full * self.latency_ms(cap) if full else 0.0
        if rem:
            total += self.latency_ms(rem)
        return total


def load_aic():
    pts = []
    with open(AIC_CSV) as f:
        next(f)
        for line in f:
            n, ms, _ = line.split(",")
            pts.append((int(n), float(ms)))
    return PiecewiseCost(pts)


def load_measured():
    r = json.load(open(MEAS_JSON))
    pts = [(row["n_images"], row["mean_ms"]) for row in r["rows"]]
    return PiecewiseCost(pts), r["attn_used"]


def handoff_ms(n_img):
    if HANDOFF_GBPS <= 0 or n_img <= 0:
        return 0.0
    n_bytes = TOKENS_PER_IMAGE * n_img * LLM_HIDDEN * BYTES_PER_ELEM
    return HANDOFF_RTT_MS + n_bytes / (HANDOFF_GBPS * 1e9 / 8) * 1000.0


def simulate(reqs, n_workers, cap, cost):
    """Faithful port of simulate_vision_pool (parallel-chunk, static workers)."""
    units = []
    for arr, idx, n in reqs:
        if n > cap:
            full, rem = divmod(n, cap)
            units.extend((arr, idx, cap, True) for _ in range(full))
            if rem:
                units.append((arr, idx, rem, True))
        else:
            units.append((arr, idx, n, False))
    units.sort()  # FIFO by arrival
    finish = {}
    worker_free = [0.0] * n_workers
    queue = deque()
    i = 0
    while i < len(units) or queue:
        if not queue:
            queue.append(units[i])
            i += 1
        head_arrival = queue[0][0]
        w = min(range(n_workers), key=lambda k: (max(worker_free[k], head_arrival), k))
        start = max(worker_free[w], head_arrival)
        while i < len(units) and units[i][0] <= start:
            queue.append(units[i])
            i += 1
        head = queue.popleft()
        members = [head]
        total = head[2]
        if head[3]:
            service = cost.latency_ms(total)
        else:
            while queue and not queue[0][3] and total + queue[0][2] <= cap:
                u = queue.popleft()
                members.append(u)
                total += u[2]
            service = cost.latency_ms(total)
        fin = start + service
        worker_free[w] = fin
        for arr, idx, _n, _c in members:
            finish[idx] = max(finish.get(idx, 0.0), fin)
    return finish


def pct(values, ps=(50, 90, 99)):
    s = sorted(values)
    return {f"p{p}": round(s[min(len(s) - 1, int(len(s) * p / 100))], 3) for p in ps}


def run(reqs, cost, label):
    finish = simulate(reqs, 1, CAP, cost)
    delays = []
    for arr, idx, n in reqs:
        delays.append((finish[idx] - arr) + handoff_ms(n))
    # Match the sim's convention: percentiles over ALL window requests, with
    # text-only requests contributing 0.0 encoder delay.
    delays_all = delays + [0.0] * (N_ALL_REQS - len(reqs))
    d = pct(delays_all)
    d["max"] = round(max(delays), 3)
    busy_ms = sum(cost.chunked_service_ms(n, CAP) for _, _, n in reqs)
    return {"label": label, "encoder_delay_ms": d,
            "busy_s": round(busy_ms / 1000, 1)}


def main():
    reqs = [tuple(r) for r in json.load(open(REQS_JSON))]
    horizon_s = (max(r[0] for r in reqs) - min(r[0] for r in reqs)) / 1000.0
    total_img = sum(r[2] for r in reqs)
    aic = load_aic()
    meas, attn = load_measured()
    sim = json.load(open(SIM_REF))

    res_aic = run(reqs, aic, "AIC f(N) [sim cost model]")
    res_meas = run(reqs, meas, f"MEASURED f(N) [{attn}, this silicon]")

    print(f"# burst3 window: {len(reqs)} image-bearing reqs, {total_img} images, "
          f"horizon {horizon_s:.1f} s, 1 worker, cap {CAP}")
    print(f"# f(64): AIC {aic.latency_ms(64):.1f} ms  vs  measured "
          f"{meas.latency_ms(64):.1f} ms  (ratio {meas.latency_ms(64)/aic.latency_ms(64):.3f})")
    print()
    print(f"{'cost model':<38} {'p50':>10} {'p90':>10} {'p99':>10} "
          f"{'max':>10} {'busy_s':>8}")
    for res in (res_aic, res_meas):
        d = res["encoder_delay_ms"]
        print(f"{res['label']:<38} {d['p50']:>10.1f} {d['p90']:>10.1f} "
              f"{d['p99']:>10.1f} {d['max']:>10.1f} {res['busy_s']:>8.1f}")
    print()
    sd = sim["encoder_delay_ms"]
    print(f"# SIM reference (vision_burst3_C1.json) encoder_delay_ms: "
          f"p50 {sd['p50']} p90 {sd['p90']} p99 {sd['p99']} max {sd['max']}")
    print(f"# self-consistency: replay-under-AIC p99 {res_aic['encoder_delay_ms']['p99']} "
          f"vs sim p99 {sd['p99']} "
          f"(match => FIFO port is faithful)")
    p99a = res_aic["encoder_delay_ms"]["p99"]
    p99m = res_meas["encoder_delay_ms"]["p99"]
    print(f"# end-to-end consequence: measured f(N) raises encoder-delay p99 "
          f"{p99a:.0f} -> {p99m:.0f} ms  (x{p99m/p99a:.2f})")

    out = {"window": "burst3", "n_image_reqs": len(reqs), "total_images": total_img,
           "horizon_s": round(horizon_s, 1), "workers": 1, "cap": CAP,
           "f64_aic_ms": round(aic.latency_ms(64), 3),
           "f64_measured_ms": round(meas.latency_ms(64), 3),
           "replay_aic": res_aic, "replay_measured": res_meas,
           "sim_reference_encoder_delay_ms": sd,
           "attn_used": attn}
    op = os.path.join(_HERE, "burst3_fifo_replay.json")
    json.dump(out, open(op, "w"), indent=2)
    print(f"# wrote {op}")


if __name__ == "__main__":
    main()
