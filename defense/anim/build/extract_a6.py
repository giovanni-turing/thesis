#!/usr/bin/env python3
"""A6 'The week' payload assembly. Run under EDA_PY.

Bins the 5.60-day aggregate runs (defense/anim/data/a6_runs/, ledger-verified)
to 300-s bins and emits defense/anim/data/a6_data.json with, per policy:
worker schedule, qmax, busy, running cost (both accountings), running p99
(all requests, converter convention), per-bin worst delay, and per-episode
p99 verdicts for the in-span episodes (burst3/5/4, calm day, burst1).
"""
import collections
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/gio/tese")
RUNS = ROOT / "defense/anim/data/a6_runs"
OUT = ROOT / "defense/anim/data/a6_data.json"
WINS = json.load(open(ROOT / "simulation/windows.json"))
AGG = WINS["aggregate"]
LEAD = 30.0
B = 300
POLICIES = ["static_C8", "toto_p90_L30", "react_L30", "toto_p50_L30", "static_C2"]

verif = json.load(open(RUNS / "verification.json"))

raw = pd.read_csv(ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz")
ts = raw["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
raw["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
raw = raw.sort_values("ts").reset_index(drop=True)
w = raw.iloc[AGG["offset"]:AGG["offset"] + AGG["max_requests"]].reset_index(drop=True)
t0 = w.ts.iloc[0]
rel_ms = ((w.ts - t0).dt.total_seconds() * 1000.0).to_numpy()
n_img = w["NumImages"].to_numpy()
is_img = n_img > 0
span = int(math.floor(AGG["span_s"]))
nb = math.ceil(span / B)
arr_bin = np.minimum((rel_ms / 1000.0 / B).astype(int), nb - 1)
edges = np.arange(1, nb + 1) * B

# in-span episodes, chronological, with [start, end) seconds relative to t0
episodes = []
for ek, lbl in [("burst3", "b3 · 1-min"), ("burst5", "b5 · 35-min"),
                ("burst4", "b4 · 60-min"), ("steady24h", "calm day"),
                ("burst1", "b1 · 220-min")]:
    e = WINS[ek]
    es = (raw.ts.iloc[e["offset"]] - t0).total_seconds()
    episodes.append({"key": ek, "label": lbl, "start_s": round(es, 1),
                     "end_s": round(es + e["span_s"], 1)})
episodes.sort(key=lambda e: e["start_s"])


def recover_delays(jsonl: Path) -> np.ndarray:
    key2idx = collections.defaultdict(collections.deque)
    for i, (ci, gi) in enumerate(zip(w["ContextTokens"], w["GeneratedTokens"])):
        key2idx[(max(1, int(ci)), max(1, int(gi)))].append(i)
    d = np.full(len(rel_ms), np.nan)
    for line in open(jsonl):
        r = json.loads(line)
        i = key2idx[(r["input_length"], r["output_length"])].popleft()
        d[i] = r["timestamp"] - rel_ms[i]
    assert not np.isnan(d).any()
    return d


payload = {"meta": {
    "span_s": span, "bin_s": B, "requests": int(AGG["max_requests"]),
    "total_images": 11400000, "t0_iso": str(t0), "lead_s": LEAD, "rho": 15,
    "sla_ms": 1000.0, "episodes": episodes,
    "static_c8_ws": verif["static_C8"]["provisioned_ws"],
    "sources": ["defense/anim/data/a6_runs/ (gen_a6_runs.py; all 5 endpoints ledger-verified)",
                "simulation/results/week_surface_issuetime/ (toto cells)",
                "simulation/results/aggregate44/ + rerun_verify/ (reactive, statics)"],
}, "offered": None, "runs": {}}

CONV_IDX = lambda n: min(n - 1, int(n * 99 / 100))

for tag in POLICIES:
    series = json.load(open(RUNS / f"{tag}.series.json"))["series"]
    q = np.array([r["queue_imgs_end"] for r in series[:span]])
    bz = np.array([r["busy_workers_end"] for r in series[:span]])
    a = np.array([r["img_arrived"] for r in series[:span]])
    pad = nb * B - len(q)
    if pad:
        q = np.pad(q, (0, pad)); bz = np.pad(bz, (0, pad)); a = np.pad(a, (0, pad))
    if payload["offered"] is None:
        payload["offered"] = (a.reshape(nb, B).max(1)).astype(int).tolist()
    if tag.startswith("static"):
        c = int(tag.split("_C")[1])
        sched = [[0.0, c]]
    else:
        sched = json.load(open(RUNS / f"{tag}.sched.json"))
    pts = sched + [[span, sched[-1][1]]]
    cost = np.zeros(nb)
    for (ta, ca), (tb, _cb) in zip(pts, pts[1:]):
        tb = min(tb, span)
        if tb > ta:
            cost += ca * np.clip(np.minimum(edges, tb) - ta, 0, tb - ta)
    warm = np.zeros(nb)
    prevc = sched[0][1]
    for t_step, cc in sched[1:]:
        if cc > prevc:
            a0 = max(t_step - LEAD, 0.0)
            warm += (cc - prevc) * np.clip(np.minimum(edges, t_step) - a0, 0, t_step - a0)
        prevc = cc
    delays = recover_delays(RUNS / f"{tag}.jsonl")
    s = np.sort(delays)
    p99_all = s[CONV_IDX(len(s))]
    exp = verif[tag]["p99_ms"]
    assert abs(p99_all - exp) / exp < 0.01, f"{tag}: recovered {p99_all} vs {exp}"
    dmax = np.zeros(nb)
    np.maximum.at(dmax, arr_bin[is_img], delays[is_img])
    cnt = np.zeros(nb); np.add.at(cnt, arr_bin, 1)
    ccnt = np.cumsum(cnt).astype(int)
    order = np.argsort(rel_ms, kind="stable")
    d_by = delays[order]
    p99run = np.zeros(nb)
    for b in range(nb):
        k = ccnt[b]
        if k:
            idx = CONV_IDX(k)
            p99run[b] = np.partition(d_by[:k], idx)[idx]
    # per-episode p99 (all requests inside the episode span)
    ep = {}
    for e in episodes:
        m = (rel_ms >= e["start_s"] * 1000) & (rel_ms < e["end_s"] * 1000)
        de = np.sort(delays[m])
        ep[e["key"]] = round(float(de[CONV_IDX(len(de))]), 1)
    payload["runs"][tag] = {
        "sched": sched,
        "qmax": q.reshape(nb, B).max(1).astype(int).tolist(),
        "busy": bz.reshape(nb, B).max(1).astype(int).tolist(),
        "dmax": [round(float(v), 1) for v in dmax],
        "cost": cost.round(0).astype(int).tolist(),
        "cost2": (cost + warm).round(0).astype(int).tolist(),
        "p99run": [round(float(v), 1) for v in p99run],
        "ep_p99": ep,
        "stats": verif[tag],
    }
    print(f"{tag}: ok (p99 {p99_all:.1f} ~ {exp}); episodes " +
          " ".join(f"{k}:{v:.0f}" for k, v in ep.items()))

OUT.write_text(json.dumps(payload, separators=(",", ":")))
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")
