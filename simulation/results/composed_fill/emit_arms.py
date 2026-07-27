#!/usr/bin/env python3
"""Project composed_fill_joined.json into the provenance.composed_e2e column
shape, so the 9 new request-linked arms line up with the 20 already loaded.

Window naming follows provenance/audit/WINDOW_ALIAS.md; `fulltrace` is the
full 1,000,000-request trace and is distinct from `aggregate` (749,601, the
forecast-covered span).
"""
import json
from pathlib import Path

OUT = Path("/home/gio/tese/simulation/results/composed_fill")
J = json.load(open(OUT / "composed_fill_joined.json"))

ARM_META = {
    "static_C8": ("-", "static"),
    "fc_chronos": ("chronos", "forecast_p90"),
    "reactive": ("-", "reactive"),
}

rows = []
for cell, r in sorted(J.items()):
    if "error" in r:
        continue
    model, policy = ARM_META[r["arm"]]
    rows.append({
        "window_name": r["window"],
        "arm": r["arm"],
        "model": model,
        "policy": policy,
        "requests": r["requests"],
        "enc_p99_ms": r["enc_p99"],
        "ttft_p99_ms": r["ttft_p99"],
        "e2e_p99_ms": r["e2e_p99"],
        "e2e_max_ms": r["e2e_max"],
        "itl_p99_ms": r["itl_p99"],
        "gpu_hours": r["gpu_h"],
        "composed_trace": r["composed_trace"],
        "source_path": "simulation/results/composed_fill/composed_fill_joined.json",
        "window_name_as_ingested": r["window"],
    })

(OUT / "composed_fill_arms.json").write_text(json.dumps(rows, indent=1))
hdr = f"{'window':11s} {'arm':11s} {'n':>8s} {'enc_p99':>9s} {'ttft_p99':>9s} {'e2e_p99':>9s} {'e2e_max':>9s} {'naive':>9s} {'err':>7s} {'gpu_h':>8s}"
print(hdr); print("-" * len(hdr))
for c, r in sorted(J.items(), key=lambda kv: (kv[1].get("window", ""), kv[1].get("arm", ""))):
    if "error" in r:
        print(f"{c}  ERROR: {r['error']}"); continue
    print(f"{r['window']:11s} {r['arm']:11s} {r['requests']:8d} {r['enc_p99']:9.1f} "
          f"{r['ttft_p99']:9.1f} {r['e2e_p99']:9.1f} {r['e2e_max']:9.1f} "
          f"{r['naive_sum']:9.1f} {r['error_ratio']:7.4f} {r['gpu_h']:8.2f}")
print(f"\n{len(rows)} arms -> {OUT/'composed_fill_arms.json'}")
