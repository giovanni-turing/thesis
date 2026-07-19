#!/usr/bin/env python3
"""A12 'the composed system' — TRUE end-to-end two-pool runs, per policy.

For each (window, arm): the language planner replay runs on the ARM'S OWN
encoder-composed trace (the ledger-verified converter outputs of the A2/A6
fleets — forecast p90 schedules or the reactive schedule, encoder delays
folded into arrivals), with per-request records. Combined with the encoder
per-request delays already recovered from those same traces, this yields a
REQUEST-LINKED ingress->first-token measurement — the thesis's Ch.6
reconstruction, upgraded from modelled to measured.

Arms (headline leads: encoder L=30 issue-time, language replica L=60):
  fc_toto     encoder toto-p90/rho15/L30  -> planner forecast_file toto p90 + SCALE=8
  fc_chronos  encoder chronos-p90/rho15/L30 -> ditto chronos
  reactive    encoder reactive/rho15/L30  -> planner ARIMA ladder (200/20)
All simulated end to end (converter FIFO + dynamo.replay mocker, virtual clock).
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/home/gio/tese")
OUT = ROOT / "defense/anim/data/a12_runs"
OUT.mkdir(parents=True, exist_ok=True)
RR = ROOT / "simulation/run_replay.sh"
SRC_PY = ROOT / "ai-dynamo/dynamo/.venv/bin/python"
ENTRY = ROOT / "simulation/replay_with_forecast.py"
SMOKE = ROOT / "simulation/planner_forecast_smoke.json"
LADDER = ROOT / "simulation/results/riders44/planner_ladder_t200_20.json"
A2 = ROOT / "defense/anim/data/a2_runs"
A2T = ROOT / "defense/anim/data/a2t_runs"
A6 = ROOT / "defense/anim/data/a6_runs"
AGG = ROOT / "simulation/results/aggregate44"

# encoder-composed trace per (window, arm) — all ledger-verified converter runs
TRACES = {
    ("burst3", "fc_chronos"): A2 / "burst3_forecast_L30.jsonl",
    ("burst3", "fc_toto"): A2T / "burst3_forecast_toto_L30.jsonl",
    ("burst3", "reactive"): A2 / "burst3_reactive_L30.jsonl",
    ("burst5", "fc_chronos"): A2 / "burst5_forecast_L30.jsonl",
    ("burst5", "fc_toto"): A2T / "burst5_forecast_toto_L30.jsonl",
    ("burst5", "reactive"): A2 / "burst5_reactive_L30.jsonl",
    ("burst4", "fc_chronos"): A2 / "burst4_forecast_L30.jsonl",
    ("burst4", "fc_toto"): A2T / "burst4_forecast_toto_L30.jsonl",
    ("burst4", "reactive"): A2 / "burst4_reactive_L30.jsonl",
    ("burst1", "fc_chronos"): A2 / "burst1_forecast_L30.jsonl",
    ("burst1", "fc_toto"): A2T / "burst1_forecast_toto_L30.jsonl",
    ("burst1", "reactive"): A2 / "burst1_reactive_L30.jsonl",
    ("week", "fc_chronos"): AGG / "fc_p90_L30_issuetime.jsonl",
    ("week", "fc_toto"): A6 / "toto_p90_L30.jsonl",
    ("week", "reactive"): A6 / "react_L30.jsonl",
}
T0 = {"burst3": "2024-10-18 10:18:00", "burst5": "2024-10-18 14:32:00",
      "burst4": "2024-10-18 15:37:00", "burst1": "2024-10-21 12:59:00",
      "week": "2024-10-16 21:39:00"}


def run_cell(window: str, arm: str) -> tuple[str, dict]:
    tag = f"{window}_{arm}"
    trace = TRACES[(window, arm)]
    if not trace.exists():
        return tag, {"error": f"missing composed trace {trace}"}
    rep = OUT / f"{tag}.report.json"
    env = {**os.environ, "RUST_LOG": "warn", "AIC_TP": "2", "AIC_VER": "0.19.0",
           "REPLAY_PY": str(SRC_PY), "STARTUP_TIME": "60"}
    cfg = LADDER
    if arm.startswith("fc_"):
        cfg = SMOKE
        env.update(REPLAY_ENTRY=str(ENTRY), FORECAST_T0=T0[window],
                   FORECAST_MODEL=arm.split("_")[1], FORECAST_QUANTILE="p90",
                   FORECAST_RESOLUTION="15s", FORECAST_REQ_SCALE="8.0")
    cmd = ["bash", str(RR), str(trace), "aic", str(rep), "2",
           "--planner-config", str(cfg),
           "--report-jsonl", str(OUT / f"{tag}.requests.jsonl")]
    with open(OUT / f"{tag}.log", "w") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
    if r.returncode != 0:
        return tag, {"error": f"replay rc={r.returncode} (see {tag}.log)"}
    d = json.load(open(rep))
    return tag, {"ttft_p99": round(d["p99_ttft_ms"], 1),
                 "itl_p99": round(d["p99_itl_ms"], 1),
                 "gpu_h": round(d["gpu_hours"], 2),
                 "requests": sum(1 for _ in open(OUT / f"{tag}.requests.jsonl")),
                 "composed_trace": str(trace.relative_to(ROOT))}


def main() -> None:
    only = sys.argv[1:] or None
    cells = [(w, a) for w in T0 for a in ("fc_toto", "fc_chronos", "reactive")
             if only is None or f"{w}_{a}" in only]
    results = {}
    if (OUT / "verification.json").exists():
        results = json.load(open(OUT / "verification.json"))
    with ThreadPoolExecutor(max_workers=int(os.environ.get("A12_CONC", "5"))) as ex:
        for tag, res in ex.map(lambda a: run_cell(*a), cells):
            print(tag, res.get("error") or
                  f"ttft_p99={res['ttft_p99']} itl_p99={res['itl_p99']} n={res['requests']}",
                  flush=True)
            results[tag] = res
    (OUT / "verification.json").write_text(json.dumps(results, indent=1))
    bad = [t for t, r in results.items() if "error" in r]
    if bad:
        sys.exit(f"FAILED: {bad}")
    print(f"all {len(results)} e2e language arms done")


if __name__ == "__main__":
    main()
