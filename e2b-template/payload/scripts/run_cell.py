#!/usr/bin/env python3
"""One evaluation cell inside an E2B sandbox: schedule -> converter -> JSON.

Input: CELL env var (JSON) or argv[1]:
  {"window": "burst3", "policy": "forecast", "quantile": "p90", "rho": 15,
   "cold_start_s": 60, "hysteresis_min": 3, "resolution": "15s",
   "model": "chronos"}
"model" selects /opt/tese/forecasts/<model>_images.parquet (default chronos,
pilot-compatible); ignored for policy=reactive (trailing observation).
window offsets/counts come from the shipped windows.json. Prints exactly one
JSON line (the cell result) to stdout as the LAST line — sbx_batch captures it.
Paths are the template's: /opt/tese/* and PYTHONPATH=/opt/aic/src.
"""
import json
import os
import subprocess
import sys

CELL = json.loads(os.environ.get("CELL") or sys.argv[1])
W = json.load(open(os.environ.get("TESE_WINDOWS", "/opt/tese/windows.json")))
win = W[CELL["window"]]
sched = "/tmp/cell.sched.json"
out = "/tmp/cell.jsonl"

parquet = "/opt/tese/forecasts/%s_images.parquet" % CELL.get("model", "chronos")
ctl = [sys.executable, "/opt/tese/scripts/forecast_schedule.py",
       "--window", CELL["window"], "--policy", CELL.get("policy", "forecast"),
       "--resolution", CELL.get("resolution", "1min"),
       "--quantile", CELL.get("quantile", "p90"),
       "--rho", str(CELL.get("rho", 15)),
       "--cold-start-s", str(CELL.get("cold_start_s", 60)),
       "--hysteresis-min", str(CELL.get("hysteresis_min", 3)),
       "--parquet", parquet,
       "--out", sched]
r = subprocess.run(ctl, capture_output=True, text=True)
if r.returncode != 0:
    print(json.dumps({"cell": CELL, "error": "controller", "detail": r.stderr[-400:]}))
    sys.exit(0)

sim = [sys.executable, "/opt/tese/scripts/trace_to_two_pool.py",
       "--out", out, "--offset", str(win["offset"]),
       "--max-requests", str(win["max_requests"]),
       "--encoder-workers", "2", "--worker-schedule", sched]
r = subprocess.run(sim, capture_output=True, text=True)
if r.returncode != 0:
    print(json.dumps({"cell": CELL, "error": "converter", "detail": r.stderr[-400:]}))
    sys.exit(0)

st = json.load(open(out + ".stats.json"))
print(json.dumps({
    "cell": CELL,
    "p99_ms": st["encoder_delay_ms"]["p99"],
    "max_ms": st["encoder_delay_ms"]["max"],
    "feasible": st["encoder_delay_ms"]["p99"] < 1000 and not st["queue_divergent"],
    "provisioned_ws": st["provisioned_worker_seconds"],
    "busy_ws": st["busy_worker_seconds"],
    "schedule": st["worker_schedule"],
}))
