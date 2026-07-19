#!/usr/bin/env python3
"""A14 max-span per-model E2E: each forecast model over ITS OWN maximum
forecastable span (the largest slice of the 1,000,000-request trace it can
cover, from its first 15-s forecast to trace end), through BOTH pools with
per-request records.

  timesfm  931,628 req (93.2% of 1M)   toto  872,980 (87.3%)   chronos  749,601 (75.0%)

Per model: forecast p90/rho15/L30 encoder schedule -> snapshot-graph converter
(composed trace + series) -> forecast_file language replay (p90, SCALE=8, L60,
per-request records). Full trace coverage for the always-defined policies
(static/reactive) is A13's job; this is the maximal FORECAST-policy coverage.

Stages are RAM-gentle-parallel: the machine is CPU/RAM-bound (mocker uses no
GPU), 24 vCPU / 125 GB, ~13 GB per language replay.
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/home/gio/tese")
OUT = ROOT / "defense/anim/data/a14_runs"
OUT.mkdir(parents=True, exist_ok=True)
WINJSON = ROOT / "defense/anim/data/windows_ext.json"
WINS = json.load(open(WINJSON))
EDA_PY = ROOT / "eda/.venv/bin/python"
AIC_PY = ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"
SRC_PY = ROOT / "ai-dynamo/dynamo/.venv/bin/python"
RR = ROOT / "simulation/run_replay.sh"
GEN = ROOT / "verification/scripts/forecast_schedule_issuetime.py"
ENTRY = ROOT / "simulation/replay_with_forecast.py"
SMOKE = ROOT / "simulation/planner_forecast_smoke.json"
ENV = {**os.environ, "TESE_WINDOWS": str(WINJSON), "TESE_ROOT": str(ROOT)}
MODELS = ["timesfm", "toto", "chronos"]


def encoder(model: str) -> dict:
    win = WINS[f"span_{model}"]
    sched = OUT / f"{model}_enc.sched.json"
    trace = OUT / f"{model}_composed.jsonl"
    r = subprocess.run(
        [str(EDA_PY), str(GEN), "--window", f"span_{model}", "--quantile", "p90",
         "--rho", "15", "--cold-start-s", "30",
         "--parquet", str(ROOT / f"predictors/results/{model}_images.parquet"),
         "--out", str(sched)], capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        return {"error": f"enc sched: {r.stderr[-400:]}"}
    r = subprocess.run(
        [str(AIC_PY), str(ROOT / "defense/anim/build/a2_conv_snapshot.py"),
         "--out", str(trace), "--offset", str(win["offset"]),
         "--max-requests", str(win["max_requests"]), "--encoder-workers", "2",
         "--worker-schedule", str(sched),
         "--series-out", str(OUT / f"{model}_enc.series.json")],
        capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        return {"error": f"enc conv: {r.stderr[-400:]}"}
    st = json.load(open(f"{trace}.stats.json"))
    nl = sum(1 for _ in open(trace))
    res = {"enc_p99": round(st["encoder_delay_ms"]["p99"], 1),
           "enc_requests": nl, "provisioned_ws": st["provisioned_worker_seconds"]}
    if nl != win["max_requests"]:
        res["error"] = f"enc coverage {nl} != {win['max_requests']}"
    return res


def language(model: str) -> dict:
    win = WINS[f"span_{model}"]
    trace = OUT / f"{model}_composed.jsonl"
    rep = OUT / f"{model}_e2e.report.json"
    env = {**ENV, "RUST_LOG": "warn", "AIC_TP": "2", "AIC_VER": "0.19.0",
           "REPLAY_PY": str(SRC_PY), "STARTUP_TIME": "60",
           "REPLAY_ENTRY": str(ENTRY), "FORECAST_T0": win["t0"],
           "FORECAST_MODEL": model, "FORECAST_QUANTILE": "p90",
           "FORECAST_RESOLUTION": "15s", "FORECAST_REQ_SCALE": "8.0"}
    with open(OUT / f"{model}_e2e.log", "w") as log:
        r = subprocess.run(
            ["bash", str(RR), str(trace), "aic", str(rep), "2",
             "--planner-config", str(SMOKE),
             "--report-jsonl", str(OUT / f"{model}_e2e.requests.jsonl")],
            stdout=log, stderr=subprocess.STDOUT, env=env)
    if r.returncode != 0:
        return {"error": f"lang rc={r.returncode} (see {model}_e2e.log)"}
    d = json.load(open(rep))
    nl = sum(1 for _ in open(OUT / f"{model}_e2e.requests.jsonl"))
    res = {"lang_requests": nl, "completed": d["completed_requests"],
           "ttft_p99": round(d["p99_ttft_ms"], 1), "itl_p99": round(d["p99_itl_ms"], 1),
           "gpu_h": round(d["gpu_hours"], 2),
           "max_requests": win["max_requests"], "pct_of_1M": round(win["max_requests"] / 1e6 * 100, 1)}
    if nl != win["max_requests"] or d["completed_requests"] != win["max_requests"]:
        res["error"] = f"lang coverage jsonl {nl} completed {d['completed_requests']} != {win['max_requests']}"
    return res


def main() -> None:
    results = {}
    if (OUT / "verification.json").exists():
        results = json.load(open(OUT / "verification.json"))
    # stage 1: encoders (converter, 2-wide)
    with ThreadPoolExecutor(max_workers=2) as ex:
        for m, r in zip(MODELS, ex.map(encoder, MODELS)):
            results.setdefault(m, {}).update(r)
            print(f"[enc] {m}: " + (r.get("error") or f"enc_p99={r.get('enc_p99')} n={r.get('enc_requests')}"), flush=True)
    (OUT / "verification.json").write_text(json.dumps(results, indent=1))
    if any("error" in results[m] for m in MODELS):
        sys.exit("encoder stage failed")
    # stage 2: language (3-wide; ~13GB each, RAM fine)
    with ThreadPoolExecutor(max_workers=3) as ex:
        for m, r in zip(MODELS, ex.map(language, MODELS)):
            results[m].update(r)
            print(f"[lang] {m}: " + (r.get("error") or f"ttft_p99={r.get('ttft_p99')} n={r.get('lang_requests')} ({r.get('pct_of_1M')}% of 1M)"), flush=True)
    (OUT / "verification.json").write_text(json.dumps(results, indent=1))
    bad = [m for m in MODELS if "error" in results[m]]
    if bad:
        sys.exit(f"FAILED: {bad}")
    tot = sum(results[m]["lang_requests"] for m in MODELS)
    print(f"MAX-SPAN E2E COMPLETE: timesfm {results['timesfm']['lang_requests']:,} + "
          f"toto {results['toto']['lang_requests']:,} + chronos {results['chronos']['lang_requests']:,} "
          f"= {tot:,} forecast-covered request-runs, both pools, per-request records")


if __name__ == "__main__":
    main()
