#!/usr/bin/env python3
"""A12 request-linked E2E join. Run under EDA_PY.

Per (window, arm): joins each request's ENCODER delay (recovered from the
arm's composed trace vs the raw CSV slice, FIFO key-matching) with its
LANGUAGE TTFT (per-request records, matched by the replay's request_<N>
session ids = composed-trace line order, alignment asserted via arrival
deltas). Emits per-bin series + running stats of the true
ingress->first-token latency, per pool and end-to-end.
"""
import collections
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/gio/tese")
A12 = ROOT / "defense/anim/data/a12_runs"
OUT = ROOT / "defense/anim/data/a12_data.json"
WINS = json.load(open(ROOT / "defense/anim/data/windows_ext.json"))
verif = json.load(open(A12 / "verification.json"))
CONV = lambda n: min(n - 1, int(n * 99 / 100))
META = {
    "burst3": {"label": "1-min onset", "t0": "2024-10-18 10:18:00", "win": "burst3"},
    "burst5": {"label": "35-min onset", "t0": "2024-10-18 14:32:00", "win": "burst5"},
    "burst4": {"label": "60-min onset", "t0": "2024-10-18 15:37:00", "win": "burst4"},
    "burst1": {"label": "220-min onset", "t0": "2024-10-21 12:59:00", "win": "burst1"},
    "week": {"label": "full 5.60-day span", "t0": "2024-10-16 21:39:00", "win": "aggregate"},
}

raw = pd.read_csv(ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz")
ts = raw["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
raw["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
raw = raw.sort_values("ts").reset_index(drop=True)

payload = {"meta": {
    "sla_ttft": 1000.0, "union_budget_ms": 2000.0,
    "win_order": list(META),
    "note": "request-linked ingress->first-token = encoder delay (seam) + TTFT "
            "(per-request replay records); upgrades the thesis Ch.6 modelled "
            "reconstruction to a measured join",
}, "windows": {}}

for wk, m in META.items():
    win = WINS[m["win"]]
    span = int(math.floor(win["span_s"]))
    B = max(1, math.ceil(span / 1620))
    nb = math.ceil(span / B)
    w = raw.iloc[win["offset"]:win["offset"] + win["max_requests"]].reset_index(drop=True)
    t0r = w.ts.iloc[0]
    rel_ms = ((w.ts - t0r).dt.total_seconds() * 1000.0).to_numpy()
    hh = m["t0"].split(" ")[1].split(":")
    wmeta = {"key": wk, "label": m["label"], "span_s": span, "bin_s": B,
             "requests": int(win["max_requests"]), "date": m["t0"].split(" ")[0],
             "t0_day_s": int(hh[0]) * 3600 + int(hh[1]) * 60 + int(hh[2])}
    wout = {"meta": wmeta, "offered": None, "runs": {}}
    for arm in ("fc_toto", "fc_chronos", "fc_timesfm", "reactive"):
        tag = f"{wk}_{arm}"
        st = verif[tag]
        trace_path = ROOT / st["composed_trace"]
        # ---- encoder delays: composed-trace timestamps vs raw arrivals ----
        emitted = []
        for line in open(trace_path):
            r = json.loads(line)
            emitted.append((r["timestamp"], r["input_length"], r["output_length"]))
        key2idx = collections.defaultdict(collections.deque)
        for i, (ci, gi) in enumerate(zip(w["ContextTokens"], w["GeneratedTokens"])):
            key2idx[(max(1, int(ci)), max(1, int(gi)))].append(i)
        enc = np.full(len(rel_ms), np.nan)
        # trace line order -> raw index, remembered for the language join
        line2raw = np.empty(len(emitted), dtype=int)
        for li, (tms, il, ol) in enumerate(emitted):
            i = key2idx[(il, ol)].popleft()
            enc[i] = tms - rel_ms[i]
            line2raw[li] = i
        assert not np.isnan(enc).any(), f"{tag}: unmatched encoder rows"
        # ---- language TTFT: request_<N> session ids = trace line order ----
        n = len(emitted)
        ttft = np.full(n, np.nan)
        arr_l = np.full(n, np.nan)
        for line in open(A12 / f"{tag}.requests.jsonl"):
            r = json.loads(line)
            li = int(re.match(r"request_(\d+)", r["session_id"]).group(1)) - 1
            ttft[li] = r["ttft_ms"]
            arr_l[li] = r["arrival_time_ms"]
        assert not np.isnan(ttft).any(), f"{tag}: unmatched language rows"
        # alignment guard: replay re-zeroes to the first arrival; deltas must match
        t_trace = np.array([e[0] for e in emitted])
        d = (arr_l - (t_trace - t_trace.min()))
        assert np.abs(d - d[0]).max() < 1.0, f"{tag}: arrival alignment drift {np.abs(d-d[0]).max()}"
        # ---- the join, indexed by raw request ----
        enc_of_line = enc[line2raw]
        e2e = enc_of_line + ttft                      # ingress -> first token
        ing = rel_ms[line2raw] / 1000.0               # ingress time (s from window start)
        st2 = {**st,
               "enc_p99": round(float(np.partition(enc_of_line, CONV(n))[CONV(n)]), 1),
               "e2e_p99": round(float(np.partition(e2e, CONV(n))[CONV(n)]), 1),
               "e2e_max": round(float(e2e.max()), 1)}
        order = np.argsort(ing, kind="stable")
        ing_s, e2e_s, enc_s, ttft_s = ing[order], e2e[order], enc_of_line[order], ttft[order]
        bins = np.minimum((ing_s / B).astype(int), nb - 1)
        if wout["offered"] is None:
            cnt = np.zeros(nb); np.add.at(cnt, bins, 1)
            wout["offered"] = (cnt / B).round(2).tolist()
        dmax = np.zeros(nb); np.maximum.at(dmax, bins, e2e_s)
        cnt = np.zeros(nb); np.add.at(cnt, bins, 1)
        ccnt = np.cumsum(cnt).astype(int)
        p99run = np.zeros(nb); ep99run = np.zeros(nb); tp99run = np.zeros(nb)
        for b in range(nb):
            k = ccnt[b]
            if k:
                idx = CONV(k)
                p99run[b] = np.partition(e2e_s[:k], idx)[idx]
                ep99run[b] = np.partition(enc_s[:k], idx)[idx]
                tp99run[b] = np.partition(ttft_s[:k], idx)[idx]
        wout["runs"][arm] = {
            "dmax": [round(float(v), 1) for v in dmax],
            "p99run": [round(float(v), 1) for v in p99run],
            "enc_p99run": [round(float(v), 1) for v in ep99run],
            "ttft_p99run": [round(float(v), 1) for v in tp99run],
            "stats": st2,
        }
        print(f"{tag}: enc_p99 {st2['enc_p99']} + ttft_p99 {st['ttft_p99']} -> "
              f"E2E p99 {st2['e2e_p99']} (max {st2['e2e_max']})")
    payload["windows"][wk] = wout

OUT.write_text(json.dumps(payload, separators=(",", ":")))
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")
