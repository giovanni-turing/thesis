#!/usr/bin/env python3
"""A1 'The invisible failure' — data extraction.

Reads the ledgered burst-window artifacts and emits a compact JSON payload
that build_a1.py inlines into the self-contained HTML animation.

Sources (all ledgered; see progress/results-ledger.md):
  simulation/results/sweeps/series/vision_burst1_s1.series.json  (per-second FIFO series)
  simulation/results/sweeps/traces/vision_burst1_s1.jsonl        (request arrivals, ms)
  simulation/results/sweeps/summary.json                         (official percentiles)
"""
import json
from pathlib import Path

ROOT = Path("/home/gio/tese")
OUT = ROOT / "defense/anim/data/a1_data.json"

# Encoder pool constants (thesis Ch.5/6): f(64)=316.369 ms per 64-image forward,
# 2 workers -> full-drain rate = 2 * 64 / 0.316369 s.
F64_MS = 316.369
WORKERS = 2
DRAIN_IMG_PER_S = WORKERS * 64 / (F64_MS / 1000.0)  # ~404.6 img/s
SLA_MS = 1000.0
# queue depth whose backlog-implied wait equals the 1 s SLA
Q_SLA = DRAIN_IMG_PER_S * (SLA_MS / 1000.0)

series = json.loads((ROOT / "simulation/results/sweeps/series/vision_burst1_s1.series.json").read_text())
assert series["freq_s"] == 1 and series["arrival_speedup"] == 1.0
rows = series["series"]

q = [r["queue_imgs_end"] for r in rows]
a = [r["img_arrived"] for r in rows]
b = [r["busy_workers_end"] for r in rows]
n = len(rows)

# per-minute request rate from the trace (timestamps in ms from window start)
horizon_min = (n + 59) // 60
req_per_min = [0] * horizon_min
with open(ROOT / "simulation/results/sweeps/traces/vision_burst1_s1.jsonl") as f:
    n_req = 0
    for line in f:
        ts_ms = json.loads(line)["timestamp"]
        m = int(ts_ms / 1000 / 60)
        if m < horizon_min:
            req_per_min[m] += 1
        n_req += 1

# per-minute dashboard series
util_per_min = []
img_per_min = []
for m in range(horizon_min):
    lo, hi = m * 60, min((m + 1) * 60, n)
    util_per_min.append(round(sum(b[lo:hi]) / (hi - lo) / WORKERS * 100, 1))
    img_per_min.append(round(sum(a[lo:hi]) / (hi - lo), 1))
req_rate_min = [round(c / 60.0, 3) for c in req_per_min]

# excursions and cross-checks
sla_secs = sum(1 for x in q if x > Q_SLA)
q1000_secs = sum(1 for x in q if x > 1000)
peak_q = max(q); peak_q_t = q.index(peak_q)
worst_arr = max(a); worst_arr_t = a.index(worst_arr)
peak_img_min = max(img_per_min); peak_img_min_idx = img_per_min.index(peak_img_min)

summary = json.loads((ROOT / "simulation/results/sweeps/summary.json").read_text())
vis = next(p for p in summary["points"]
           if p["pool"] == "vision" and p["window"] == "burst1" and p["speedup"] == 1.0)

payload = {
    "meta": {
        "window": "largest burst episode ±10 min (thesis 'burst window')",
        "utc_start": "2024-10-21T12:59:00Z",
        "horizon_s": n,
        "requests": vis["requests"],
        "total_images": vis["total_images"],
        "workers": WORKERS,
        "drain_img_per_s": round(DRAIN_IMG_PER_S, 2),
        "q_sla": round(Q_SLA, 2),  # exact threshold: JS counter must match sla_backlog_secs
        "sla_ms": SLA_MS,
        "official": {
            "enc_delay_p99_ms": vis["encoder_delay_ms"]["p99"],
            "enc_delay_max_ms": vis["encoder_delay_ms"]["max"],
            "enc_delay_p50_ms": vis["encoder_delay_ms"]["p50"],
            "utilization": vis["encoder_utilization"],
            "batches": vis["batches"],
            "mean_req_per_s": vis["base"]["req_per_s"],
            "mean_img_per_s": vis["base"]["img_per_s"],
        },
        "checks": {
            "sla_backlog_secs": sla_secs,        # secs with implied wait > 1 s
            "q_gt_1000_secs": q1000_secs,        # thesis quotes 805 s
            "peak_queue": peak_q, "peak_queue_t": peak_q_t,
            "worst_second_images": worst_arr, "worst_second_t": worst_arr_t,
            "peak_img_min": peak_img_min, "peak_img_min_t": peak_img_min_idx * 60,
        },
        "sources": [
            "simulation/results/sweeps/series/vision_burst1_s1.series.json",
            "simulation/results/sweeps/traces/vision_burst1_s1.jsonl",
            "simulation/results/sweeps/summary.json",
        ],
    },
    "sec": {"q": q, "a": a, "b": b},
    "min": {"req": req_rate_min, "util": util_per_min, "img": img_per_min},
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, separators=(",", ":")))
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")
print("requests in trace:", n_req)
print("checks:", json.dumps(payload["meta"]["checks"], indent=1))
