#!/usr/bin/env python3
"""A2 'The race' — payload assembly from the verified simulator runs.

Run under EDA_PY (needs pandas). Reads defense/anim/data/a2_runs/* (produced
by gen_a2_runs.py, endpoints ledger-verified) plus the raw trace slice, and
emits defense/anim/data/a2_data.json for the template.

Per-request encoder delay is recovered as emitted_ts_ms - raw_relative_ms
(the converter folds delay into the emitted arrival timestamp; that IS the
seam). Recovered p99 over all requests is asserted against the run stats.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path("/home/gio/tese")
RUNS = ROOT / "defense/anim/data/a2_runs"
OUT = ROOT / "defense/anim/data/a2_data.json"
WIN = json.load(open(ROOT / "simulation/windows.json"))["burst3"]
LEADS = [15, 30, 45, 165]

# raw window slice: arrival times + image counts, in file order (the converter
# preserves request order)
raw = pd.read_csv(ROOT / "data/AzureLMMInferenceTrace_multimodal.csv.gz")
ts = raw["TIMESTAMP"].str.replace("Z", "", regex=False).str.pad(23, "right", "0")
raw["ts"] = pd.to_datetime(ts, format="%Y-%m-%dT%H:%M:%S.%f")
raw = raw.sort_values("ts").reset_index(drop=True)
w = raw.iloc[WIN["offset"]:WIN["offset"] + WIN["max_requests"]].reset_index(drop=True)
t0 = w.ts.iloc[0]
raw_rel_ms = ((w.ts - t0).dt.total_seconds() * 1000.0).to_numpy()
n_img = w["NumImages"].to_numpy()

# offered image load per second (must equal every run's series img_arrived)
span = int(WIN["span_s"]) + 1

payload = {"meta": {
    "window": "burst3 — fastest-onset episode (±10 min pad)",
    "utc_start": str(t0), "utc_note": "2024-10-18 10:18:00 .. 10:45:00 UTC",
    "span_s": WIN["span_s"], "requests": WIN["max_requests"],
    "onset_min": 1, "peak_1min_img_per_s": WIN["peak_1min_img_per_s"],
    "rho": 15, "sla_ms": 1000.0, "leads": LEADS,
    "law": "identical for both policies: C = ceil(demand/15), 3-min hysteresis, lead L; "
           "forecast reads the archived Chronos p90 issue-time path, reactive the trailing "
           "observed 15-s image rate",
    "sources": ["defense/anim/data/a2_runs/ (gen_a2_runs.py; endpoints ledger-verified)",
                "simulation/results/results_44.jsonl (reactive rho15 cells)",
                "simulation/results/factorial_issuetime/factorial_issuetime_p90_rho15_results.json"],
}, "offered": None, "runs": {}}

verif = json.load(open(RUNS / "verification.json"))

for policy in ("forecast", "reactive"):
    for lead in LEADS:
        tag = f"{policy}_L{lead}"
        series = json.load(open(RUNS / f"{tag}.series.json"))["series"]
        assert len(series) >= span - 1
        q = [r["queue_imgs_end"] for r in series]
        b = [r["busy_workers_end"] for r in series]
        a = [r["img_arrived"] for r in series]
        if payload["offered"] is None:
            payload["offered"] = a
        else:
            assert a == payload["offered"], f"{tag}: offered arrivals differ between runs"
        sched = json.load(open(RUNS / f"{tag}.sched.json"))
        # The converter re-sorts emitted rows by their SHIFTED timestamp, so
        # line order != request order. Recover the pairing by matching each
        # emitted (input_length, output_length) to the earliest unclaimed raw
        # request with that key (FIFO — shifting preserves relative order among
        # identical keys). input_length is ContextTokens clamped to >= 1.
        import collections
        key2idx = collections.defaultdict(collections.deque)
        for i, (ci, gi) in enumerate(zip(w["ContextTokens"], w["GeneratedTokens"])):
            key2idx[(max(1, int(ci)), int(gi))].append(i)
        delays = [None] * len(raw_rel_ms)
        for line in open(RUNS / f"{tag}.jsonl"):
            r = json.loads(line)
            k = (r["input_length"], r["output_length"])
            i = key2idx[k].popleft()          # KeyError/IndexError = mismatch: fail loudly
            delays[i] = r["timestamp"] - raw_rel_ms[i]
        assert all(d is not None for d in delays), f"{tag}: unmatched requests"
        # cross-check the recovered delays against the run's official stats
        s = sorted(delays)
        p99 = s[min(len(s) - 1, int(len(s) * 99 / 100))]  # converter's convention
        exp = verif[tag]["p99_ms"]
        assert abs(p99 - exp) / exp < 0.01, f"{tag}: recovered p99 {p99} vs stats {exp}"
        # image-bearing request dots: [arrival_s, delay_ms]; delay>=0.1ms floor
        dots = [[round(rr / 1000.0, 1), round(max(d, 0.1), 1)]
                for rr, d, ni in zip(raw_rel_ms, delays, n_img) if ni > 0]
        payload["runs"][tag] = {
            "sched": sched, "q": q, "busy": b, "dots": dots,
            "stats": verif[tag],
        }
        print(f"{tag}: recovered p99 {p99:.1f} ~ stats {exp} OK; "
              f"{len(dots)} image-bearing dots; peak queue {max(q)}")

OUT.write_text(json.dumps(payload, separators=(",", ":")))
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.2f} MB)")
