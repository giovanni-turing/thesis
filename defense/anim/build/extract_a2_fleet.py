#!/usr/bin/env python3
"""A2 fleet payload assembly (v2: multi-episode + live tickers).

Run under EDA_PY. Reads defense/anim/data/a2_runs/* (gen_a2_fleet.py,
endpoints ledger-verified) and emits defense/anim/data/a2_data.json.

Per (window, policy, lead), at adaptive bin width B = ceil(span/1620):
  qmax[b]   max queued images in bin          qpeak[b]  running peak queue
  busy[b]   max busy workers in bin           dmax[b]   worst delay among
                                                        image-bearing arrivals in bin
  cost[b]   provisioned worker-seconds so far (from the schedule integral)
  avgi[b]   running mean delay, image-bearing requests
  p99[b]    running p99 delay, ALL requests (converter index convention;
            converges to the ledgered verdict)
Delays recovered from seam timestamps via FIFO (input,output)-key matching and
cross-checked against each run's stats.
"""
import collections
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/gio/tese")
RUNS = ROOT / "defense/anim/data/a2_runs"
OUT = ROOT / "defense/anim/data/a2_data.json"
WINS = json.load(open(ROOT / "simulation/windows.json"))
WINDOWS = ["burst3", "burst5", "burst4", "burst1", "steady24h"]  # UI order
LEADS = [15, 30, 45, 165]
ONSET_LABEL = {"burst1": "220-min onset", "burst3": "1-min onset",
               "burst4": "60-min onset", "burst5": "35-min onset",
               "steady24h": "calm day"}

verif = json.load(open(RUNS / "verification.json"))

raw = pd.read_csv(ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz")
ts = raw["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
raw["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
raw = raw.sort_values("ts").reset_index(drop=True)


def recover_delays(w: pd.DataFrame, rel_ms: np.ndarray, jsonl: Path) -> np.ndarray:
    key2idx = collections.defaultdict(collections.deque)
    for i, (ci, gi) in enumerate(zip(w["ContextTokens"], w["GeneratedTokens"])):
        key2idx[(max(1, int(ci)), max(1, int(gi)))].append(i)  # converter clamps both to >=1
    d = np.full(len(rel_ms), np.nan)
    for line in open(jsonl):
        r = json.loads(line)
        i = key2idx[(r["input_length"], r["output_length"])].popleft()
        d[i] = r["timestamp"] - rel_ms[i]
    assert not np.isnan(d).any()
    return d


payload = {"meta": {
    "rho": 15, "sla_ms": 1000.0, "leads": LEADS, "win_order": WINDOWS,
    "law": "identical for both policies: C = ceil(demand/15), 3-min hysteresis, lead L",
    "sources": ["defense/anim/data/a2_runs/ (gen_a2_fleet.py; endpoints ledger-verified)",
                "simulation/results/results_44.jsonl",
                "simulation/results/factorial_issuetime/factorial_issuetime_p90_rho15_results.json"],
}, "windows": {}}

for wk in WINDOWS:
    win = WINS[wk]
    w = raw.iloc[win["offset"]:win["offset"] + win["max_requests"]].reset_index(drop=True)
    t0 = w.ts.iloc[0]
    rel_ms = ((w.ts - t0).dt.total_seconds() * 1000.0).to_numpy()
    n_img = w["NumImages"].to_numpy()
    span = int(math.floor(win["span_s"]))
    B = max(1, math.ceil(span / 1620))
    nb = math.ceil(span / B)
    arr_bin = np.minimum((rel_ms / 1000.0 / B).astype(int), nb - 1)
    is_img = n_img > 0

    wmeta = {"key": wk, "label": ONSET_LABEL[wk], "span_s": span, "bin_s": B,
             "requests": int(win["max_requests"]),
             "peak_1min_img_per_s": win.get("peak_1min_img_per_s"),
             "date": str(t0.date()),
             "t0_day_s": int(t0.hour * 3600 + t0.minute * 60 + t0.second)}
    wout = {"meta": wmeta, "offered": None, "runs": {}}

    for policy in ("forecast", "reactive"):
        for lead in LEADS:
            tag = f"{wk}_{policy}_L{lead}"
            st = verif[tag]
            series = json.load(open(RUNS / f"{tag}.series.json"))["series"]
            q = np.array([r["queue_imgs_end"] for r in series[:span]])
            bz = np.array([r["busy_workers_end"] for r in series[:span]])
            a = np.array([r["img_arrived"] for r in series[:span]])
            pad = nb * B - len(q)
            if pad:
                q = np.pad(q, (0, pad)); bz = np.pad(bz, (0, pad)); a = np.pad(a, (0, pad))
            qmax = q.reshape(nb, B).max(1)
            busy = bz.reshape(nb, B).max(1)
            if wout["offered"] is None:
                wout["offered"] = a.reshape(nb, B).max(1).tolist()
            sched = json.load(open(RUNS / f"{tag}.sched.json"))
            # provisioned worker-seconds cumulative at bin ends
            edges = np.arange(1, nb + 1) * B
            cost = np.zeros(nb)
            pts = sched + [[span, sched[-1][1]]]
            for (ta, ca), (tb, _cb) in zip(pts, pts[1:]):
                lo = np.clip(edges, None, tb); hi = min(tb, span)
                cost += ca * np.clip(np.minimum(edges, hi) - ta, 0, None) \
                      - ca * np.clip(np.minimum(edges, hi) - hi, 0, None) * 0
                # simpler: overlap of [ta, min(tb,span)] with [0, edge]
            # (recompute cleanly to avoid cleverness)
            cost = np.zeros(nb)
            for (ta, ca), (tb, _cb) in zip(pts, pts[1:]):
                tb = min(tb, span)
                if tb <= ta:
                    continue
                cost += ca * np.clip(np.minimum(edges, tb) - ta, 0, tb - ta)
            # bill-from-order accounting: each upward worker-increment at step
            # time t warmed (billed but not usable) during [t-L, t). Exact for
            # reactive (every re-up is a fresh order); an UPPER BOUND for the
            # forecast lane (warm-pool re-ups charged as if re-ordered).
            warm = np.zeros(nb)
            prevc = sched[0][1]
            for t_step, c in sched[1:]:
                if c > prevc:
                    a0 = max(t_step - lead, 0.0)
                    warm += (c - prevc) * np.clip(np.minimum(edges, t_step) - a0,
                                                  0, t_step - a0)
                prevc = c
            delays = recover_delays(w, rel_ms, RUNS / f"{tag}.jsonl")
            s = np.sort(delays)
            p99_all = s[min(len(s) - 1, int(len(s) * 99 / 100))]
            assert abs(p99_all - st["p99_ms"]) / st["p99_ms"] < 0.01, \
                f"{tag}: recovered {p99_all} vs stats {st['p99_ms']}"
            # per-bin worst image-bearing delay
            dmax = np.zeros(nb)
            np.maximum.at(dmax, arr_bin[is_img], delays[is_img])
            # running mean (image-bearing) + running p99 (all)
            cnt_i = np.zeros(nb); np.add.at(cnt_i, arr_bin[is_img], 1)
            sum_i = np.zeros(nb); np.add.at(sum_i, arr_bin[is_img], delays[is_img])
            ccnt_i = np.maximum(np.cumsum(cnt_i), 1)
            avgi = np.cumsum(sum_i) / ccnt_i
            cnt_a = np.zeros(nb); np.add.at(cnt_a, arr_bin, 1)
            ccnt_a = np.cumsum(cnt_a).astype(int)
            order = np.argsort(rel_ms, kind="stable")
            d_by_arrival = delays[order]
            p99run = np.zeros(nb)
            for b in range(nb):
                k = ccnt_a[b]
                if k == 0:
                    continue
                idx = min(k - 1, int(k * 99 / 100))
                p99run[b] = np.partition(d_by_arrival[:k], idx)[idx]
            wout["runs"][f"{policy}_L{lead}"] = {
                "sched": sched,
                "qmax": qmax.astype(int).tolist(),
                "qpeak": np.maximum.accumulate(qmax).astype(int).tolist(),
                "busy": busy.astype(int).tolist(),
                "dmax": [round(float(v), 1) for v in dmax],
                "cost": cost.round(0).astype(int).tolist(),
                "cost2": (cost + warm).round(0).astype(int).tolist(),
                "avgi": [round(float(v), 1) for v in avgi],
                "p99run": [round(float(v), 1) for v in p99run],
                "stats": st,
                "warm_ws": round(float(warm[-1])),
            }
            print(f"{tag}: ok (p99 {p99_all:.1f} ~ {st['p99_ms']}, bins {nb} x {B}s)")
    payload["windows"][wk] = wout

OUT.write_text(json.dumps(payload, separators=(",", ":")))
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")
