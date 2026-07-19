#!/usr/bin/env python3
"""A11 payload assembly: language-pool race from planner replays.

Per (window, policy, lead): replica staircase (parsed from the run's
"Scaling events" stdout block, initial 2 replicas), per-bin worst TTFT,
running mean/p99 TTFT + running p99 ITL (recovered from the per-request
records; final values asserted against each run's report), and cumulative
GPU-hours (replicas x 2 GPUs for TP2, verified against the report).
"""
import json
import math
import re
from pathlib import Path

import numpy as np

ROOT = Path("/home/gio/tese")
RUNS = ROOT / "defense/anim/data/a11_runs"
OUT = ROOT / "defense/anim/data/a11_data.json"
WINS = json.load(open(ROOT / "simulation/windows.json"))
LEADS = [60, 120, 300]
GPUS_PER_REPLICA = 2  # TP2
META = {
    "burst3": {"label": "1-min onset · live-validated", "t0": "2024-10-18 10:18:00", "budget": 4},
    "burst5": {"label": "35-min onset", "t0": "2024-10-18 14:32:00", "budget": 8},
    "burst4": {"label": "60-min onset", "t0": "2024-10-18 15:37:00", "budget": 8},
    "burst1": {"label": "220-min onset", "t0": "2024-10-21 12:59:00", "budget": 8},
    "week": {"label": "full 5.60-day span", "t0": "2024-10-16 21:39:00", "budget": 8,
             "win": "aggregate", "leads": [60]},
}
verif = json.load(open(RUNS / "verification.json"))
CONV = lambda n: min(n - 1, int(n * 99 / 100))

payload = {"meta": {
    "sla_ttft": 1000.0, "sla_itl": 100.0, "leads": LEADS,
    "win_order": list(META), "gpus_per_replica": GPUS_PER_REPLICA,
    "law": "both policies through Dynamo's planner on the same composed grid trace; "
           "fc = archived p90 path (15 s) + tail-aware conversion (SCALE=8), "
           "reactive = SLA planner (ARIMA, 200/20 ms targets); TP2 replicas",
    "sources": ["defense/anim/data/a11_runs/ (gen_a11_runs.py; L60 anchors match "
                "episode twins / live51 cap4 twins / riders ladder)"],
}, "windows": {}}

for wk, m in META.items():
    win = WINS[m.get("win", wk)]
    span = int(math.floor(win["span_s"]))
    B = max(1, math.ceil(span / 1620))
    nb = math.ceil(span / B)
    t0 = m["t0"].split(" ")[1].split(":")
    wmeta = {"key": wk, "label": m["label"], "span_s": span, "bin_s": B,
             "requests": int(win["max_requests"]), "budget": m["budget"],
             "date": m["t0"].split(" ")[0],
             "t0_day_s": int(t0[0]) * 3600 + int(t0[1]) * 60 + int(t0[2])}
    wout = {"meta": wmeta, "offered": None, "runs": {}}
    for policy in ("fc_chronos", "fc_toto", "fc_timesfm", "reactive"):
        for lead in m.get("leads", LEADS):
            tag = f"{wk}_{policy}_L{lead}"
            st = verif[tag]
            recs = [json.loads(l) for l in open(RUNS / f"{tag}.requests.jsonl")]
            arr = np.array([r["arrival_time_ms"] for r in recs]) / 1000.0
            ttft = np.array([r["ttft_ms"] if r["ttft_ms"] is not None else np.nan
                             for r in recs])
            itl = np.array([r["itl_ms"] if r["itl_ms"] is not None else np.nan
                            for r in recs])
            assert not np.isnan(ttft).any(), f"{tag}: incomplete requests"
            order = np.argsort(arr, kind="stable")
            arr, ttft, itl = arr[order], ttft[order], itl[order]
            s = np.sort(ttft)
            p99 = s[CONV(len(s))]
            # nearest-rank (mine) vs the report's percentile method differ on
            # heavy tails; both measure the same run. Verdict is unaffected.
            drift = abs(p99 - st["ttft_p99"]) / st["ttft_p99"]
            assert drift < 0.05, f"{tag}: recovered {p99} vs report {st['ttft_p99']}"
            if drift > 0.01:
                print(f"  note {tag}: recovered p99 {p99:.1f} vs report "
                      f"{st['ttft_p99']} ({drift*100:.1f}% percentile-convention)")
            bins = np.minimum((arr / B).astype(int), nb - 1)
            if wout["offered"] is None:
                cnt = np.zeros(nb); np.add.at(cnt, bins, 1)
                wout["offered"] = (cnt / B).round(2).tolist()   # req/s per bin
            dmax = np.zeros(nb)
            np.maximum.at(dmax, bins, ttft)
            cnt = np.zeros(nb); np.add.at(cnt, bins, 1)
            ccnt = np.cumsum(cnt).astype(int)
            p99run = np.zeros(nb); ip99run = np.zeros(nb)
            avgr = np.zeros(nb)
            csum = np.cumsum(np.concatenate([[0.0], ttft]))
            itl_clean = np.nan_to_num(itl, nan=0.0)
            for b in range(nb):
                k = ccnt[b]
                if k:
                    idx = CONV(k)
                    p99run[b] = np.partition(ttft[:k], idx)[idx]
                    ip99run[b] = np.partition(itl_clean[:k], idx)[idx]
                    avgr[b] = csum[k] / k
            # replica staircase from the log's Scaling events block
            sched = [[0.0, 2]]
            for line in open(RUNS / f"{tag}.log"):
                mm = re.match(r"\s*t=([\d.]+)s \[\w+\]: (\d+) -> (\d+) workers", line)
                if mm:
                    sched.append([float(mm.group(1)), int(mm.group(3))])
            edges = np.arange(1, nb + 1) * B
            pts = sched + [[span, sched[-1][1]]]
            cost = np.zeros(nb)
            for (ta, ca), (tb, _cb) in zip(pts, pts[1:]):
                tb = min(tb, span)
                if tb > ta:
                    cost += ca * np.clip(np.minimum(edges, tb) - ta, 0, tb - ta)
            gpu_h = cost[-1] * GPUS_PER_REPLICA / 3600.0
            if abs(gpu_h - st["gpu_h"]) / st["gpu_h"] > 0.06:
                print(f"  WARN {tag}: staircase GPU-h {gpu_h:.2f} vs report "
                      f"{st['gpu_h']} (display only; report value authoritative)")
            wout["runs"][f"{policy}_L{lead}"] = {
                "sched": sched,
                "dmax": [round(float(v), 1) for v in dmax],
                "avg": [round(float(v), 1) for v in avgr],
                "p99run": [round(float(v), 1) for v in p99run],
                "ip99run": [round(float(v), 2) for v in ip99run],
                "cost": (cost * GPUS_PER_REPLICA).round(0).astype(int).tolist(),  # GPU-seconds
                "stats": st,
            }
            print(f"{tag}: ok (p99 {p99:.1f} ~ {st['ttft_p99']}; "
                  f"gpu_h {gpu_h:.2f} ~ {st['gpu_h']}; {len(sched)} sched steps)")
    payload["windows"][wk] = wout

OUT.write_text(json.dumps(payload, separators=(",", ":")))
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")
