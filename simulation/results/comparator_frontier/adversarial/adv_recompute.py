#!/usr/bin/env python
"""ADVERSARIAL independent recomputation of the §8.2 frontier.

Deliberately does NOT import anything from simulation/ or workload/.
Reads: raw trace CSV, emitted mooncake JSONL(.zst/.gz), schedule JSON.
Computes: encoder-delay p99 (converter's own percentile rule) and provisioned
worker-seconds (schedule integral to a re-derived t_end).
"""
import glob, gzip, io, json, os, re, sys
import numpy as np
import pandas as pd

ROOT = "/home/gio/tese"
TRACE = os.path.join(ROOT, "data/AzureLMMInferenceTrace_multimodal.csv.gz")
WIN = json.load(open(os.path.join(ROOT, "simulation/windows.json")))

# handoff model, re-derived from the converter's documented constants
TOK_PER_IMG = 196          # post-merge tokens per 448px image
LLM_HIDDEN = 4096
BYTES_PER_ELEM = 2
RTT_MS = 0.2
GBPS = 25.0
PER_IMG_MS = TOK_PER_IMG * LLM_HIDDEN * BYTES_PER_ELEM / (GBPS * 1e9 / 8) * 1e3

_df = None
def full_trace():
    global _df
    if _df is None:
        df = pd.read_csv(TRACE)
        ts = df["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
        df["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
        _df = df.drop(columns=["TIMESTAMP"]).sort_values("ts").reset_index(drop=True)
    return _df

_wcache = {}
def window_arrivals(w):
    """(arrivals_ms zero-based, num_images) for window w."""
    if w in _wcache:
        return _wcache[w]
    cfg = WIN[w]
    off = cfg["offset"]; n = cfg.get("max_requests") or cfg.get("requests")
    d = full_trace().iloc[off:off + n]
    t0 = d["ts"].iloc[0]
    arr = (d["ts"] - t0).dt.total_seconds().to_numpy() * 1000.0
    ni = d["NumImages"].to_numpy().astype(np.int64)
    _wcache[w] = (arr, ni)
    return _wcache[w]

def open_jsonl(path):
    if path.endswith(".zst"):
        import subprocess
        p = subprocess.Popen(["zstdcat", path], stdout=subprocess.PIPE)
        return io.TextIOWrapper(p.stdout)
    if path.endswith(".gz"):
        return gzip.open(path, "rt")
    return open(path)

def pctl(values, p):
    """The converter's exact percentile rule."""
    s = np.sort(np.asarray(values))
    return round(float(s[min(len(s) - 1, int(len(s) * p / 100))]), 3)

def recompute(jsonl, sched_path, window):
    arr, ni = window_arrivals(window)
    N = len(arr)
    ts = np.full(N, np.nan)
    seen = 0
    with open_jsonl(jsonl) as f:
        for line in f:
            r = json.loads(line)
            i = r["hash_ids"][0] // 100_000
            if not np.isnan(ts[i]):
                raise SystemExit(f"duplicate index {i} in {jsonl}")
            ts[i] = r["timestamp"]
            seen += 1
    if seen != N or np.isnan(ts).any():
        raise SystemExit(f"row count mismatch {jsonl}: {seen} vs window {N}")
    delay_ms = ts - arr   # mooncake timestamps are in MILLISECONDS
    delay_ms = np.where(ni > 0, delay_ms, 0.0)   # text-only contribute exactly 0
    # sanity: text-only rows must already be exactly 0 in the emitted file
    resid = np.abs(ts[ni == 0] - arr[ni == 0])
    max_text_resid = float(resid.max()) if resid.size else 0.0

    # t_end = max(last arrival, last batch finish); finish_i = ts_i*1000 - handoff_i
    h = RTT_MS + PER_IMG_MS * ni
    fin = ts - h
    last_finish = float(fin[ni > 0].max()) if (ni > 0).any() else 0.0
    t_end_ms = max(float(arr[-1]), last_finish)

    sched = sorted((float(t) * 1000.0, int(c)) for t, c in json.load(open(sched_path)))
    prov = 0.0
    for (t0, c0), (t1, _c) in zip(sched, sched[1:]):
        prov += c0 * max(0.0, min(t1, t_end_ms) - min(t0, t_end_ms))
    prov += sched[-1][1] * max(0.0, t_end_ms - sched[-1][0])

    return dict(
        n=N, n_img=int((ni > 0).sum()),
        p50=pctl(delay_ms, 50), p90=pctl(delay_ms, 90), p99=pctl(delay_ms, 99),
        max_delay=round(float(delay_ms.max()), 3),
        over1000=int((delay_ms > 1000).sum()),
        worker_s=round(prov / 1000.0, 1),
        t_end_s=round(t_end_ms / 1000.0, 3),
        steps=len(sched), sched_min=min(c for _, c in sched), sched_max=max(c for _, c in sched),
        max_text_resid_ms=round(max_text_resid, 6),
    )
