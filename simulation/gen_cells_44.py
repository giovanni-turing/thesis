#!/usr/bin/env python3
"""Generate the 4.4 fleet-matrix cells file (cells_44.jsonl).

Grid (user-reviewed 2026-07-08):
  windows     in-span only: burst1, burst3, burst4, burst5, steady24h
              (burst2/6 are pre-context-window: structurally unforecastable)
  resolution  15s everywhere — burst1 included (15-s forecasts cover from
              Oct 16; running all windows at one resolution also makes the
              encoder leads land on exact bins: {15,30,45,300}s = {1,2,3,20})
  policy      forecast (quantile in {p50,p90} x model in {chronos,toto,
              timesfm}) and reactive (trailing observation; no model dim)
  lead        cold_start_s in {15,30,45,300}: warm-pool band (15/30/45, on a
              measured 3-5 s model-side floor — Phase D) + the 300 s
              node-provision anchor
  rho         {10,15,20,25} img/s per worker (shared by both policies)
  hysteresis  3 min (fixed; scale-down trailing-max)

480 forecast + 80 reactive = 560 cells, shuffled with a fixed seed so any
prefix is a representative sample (the launch ramps: first 60 cells as a
canary wave at concurrency 60, then the remaining 500 at concurrency 500).
"""
import itertools
import json
import random

WINDOWS = ["burst1", "burst3", "burst4", "burst5", "steady24h"]
LEADS = [15, 30, 45, 300]
RHOS = [10, 15, 20, 25]
MODELS = ["chronos", "toto", "timesfm"]
QUANTILES = ["p50", "p90"]

cells = []
for w, lead, rho in itertools.product(WINDOWS, LEADS, RHOS):
    base = {"window": w, "resolution": "15s", "rho": rho,
            "cold_start_s": lead, "hysteresis_min": 3}
    for q, m in itertools.product(QUANTILES, MODELS):
        cells.append({**base, "policy": "forecast", "quantile": q, "model": m})
    cells.append({**base, "policy": "reactive"})

random.Random(0).shuffle(cells)

out = "/home/gio/tese/simulation/results/cells_44.jsonl"
with open(out, "w") as f:
    for c in cells:
        f.write(json.dumps(c) + "\n")
print(f"{len(cells)} cells (seed-0 shuffle) -> {out}")
