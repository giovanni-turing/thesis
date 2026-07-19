#!/usr/bin/env python3
"""A15 expanding-context E2E: each forecast model over the ~full trace
(span_expctx = 999,599 req, 99.96% of 1M) through BOTH pools, per-request
records. Uses the expanding-context forecast archives (*_expctx.parquet), so
forecasts exist from 3 min into the trace. Encoder: forecast schedule from the
expctx image parquet -> converter. Language: forecast_file with FORECAST_SUFFIX
=_expctx. Max parallel: encoders 3-wide, language 3-wide (idle CPU, ~13GB each).
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/home/gio/tese")
OUT = ROOT / "defense/anim/data/a15_runs"
OUT.mkdir(parents=True, exist_ok=True)
WINJSON = ROOT / "defense/anim/data/windows_ext.json"
WIN = json.load(open(WINJSON))["span_expctx"]
EDA_PY = ROOT / "eda/.venv/bin/python"
AIC_PY = ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"
SRC_PY = ROOT / "ai-dynamo/dynamo/.venv/bin/python"
RR = ROOT / "simulation/run_replay.sh"
GEN = ROOT / "verification/scripts/forecast_schedule_issuetime.py"
ENTRY = ROOT / "simulation/replay_with_forecast.py"
SMOKE = ROOT / "simulation/planner_forecast_smoke.json"
ENV = {**os.environ, "TESE_WINDOWS": str(WINJSON), "TESE_ROOT": str(ROOT)}
MODELS = ["timesfm", "toto", "chronos"]
N = WIN["max_requests"]


def encoder(model: str) -> dict:
    sched = OUT / f"{model}_enc.sched.json"
    trace = OUT / f"{model}_composed.jsonl"
    r = subprocess.run(
        [str(EDA_PY), str(GEN), "--window", "span_expctx", "--quantile", "p90",
         "--rho", "15", "--cold-start-s", "30",
         "--parquet", str(ROOT / f"predictors/results/{model}_images_expctx.parquet"),
         "--out", str(sched)], capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        return {"error": f"enc sched: {r.stderr[-400:]}"}
    r = subprocess.run(
        [str(AIC_PY), str(ROOT / "defense/anim/build/a2_conv_snapshot.py"),
         "--out", str(trace), "--offset", str(WIN["offset"]),
         "--max-requests", str(N), "--encoder-workers", "2",
         "--worker-schedule", str(sched),
         "--series-out", str(OUT / f"{model}_enc.series.json")],
        capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        return {"error": f"enc conv: {r.stderr[-400:]}"}
    st = json.load(open(f"{trace}.stats.json"))
    nl = sum(1 for _ in open(trace))
    res = {"enc_p99": round(st["encoder_delay_ms"]["p99"], 1), "enc_requests": nl}
    if nl != N:
        res["error"] = f"enc coverage {nl} != {N}"
    return res


def language(model: str) -> dict:
    trace = OUT / f"{model}_composed.jsonl"
    rep = OUT / f"{model}_e2e.report.json"
    env = {**ENV, "RUST_LOG": "warn", "AIC_TP": "2", "AIC_VER": "0.19.0",
           "REPLAY_PY": str(SRC_PY), "STARTUP_TIME": "60",
           "REPLAY_ENTRY": str(ENTRY), "FORECAST_T0": WIN["t0"],
           "FORECAST_MODEL": model, "FORECAST_QUANTILE": "p90",
           "FORECAST_RESOLUTION": "15s", "FORECAST_REQ_SCALE": "8.0",
           "FORECAST_SUFFIX": "_expctx"}
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
           "gpu_h": round(d["gpu_hours"], 2), "pct_of_1M": round(N / 1e6 * 100, 2)}
    if nl != N or d["completed_requests"] != N:
        res["error"] = f"lang coverage jsonl {nl} completed {d['completed_requests']} != {N}"
    return res


def main() -> None:
    results = {}
    if (OUT / "verification.json").exists():
        results = json.load(open(OUT / "verification.json"))
    with ThreadPoolExecutor(max_workers=3) as ex:
        for m, r in zip(MODELS, ex.map(encoder, MODELS)):
            results.setdefault(m, {}).update(r)
            print(f"[enc] {m}: " + (r.get("error") or f"enc_p99={r.get('enc_p99')} n={r.get('enc_requests')}"), flush=True)
    (OUT / "verification.json").write_text(json.dumps(results, indent=1))
    if any("error" in results[m] for m in MODELS):
        sys.exit("encoder stage failed")
    with ThreadPoolExecutor(max_workers=3) as ex:
        for m, r in zip(MODELS, ex.map(language, MODELS)):
            results[m].update(r)
            print(f"[lang] {m}: " + (r.get("error") or f"ttft_p99={r.get('ttft_p99')} n={r.get('lang_requests')} ({r.get('pct_of_1M')}% of 1M)"), flush=True)
    (OUT / "verification.json").write_text(json.dumps(results, indent=1))
    bad = [m for m in MODELS if "error" in results[m]]
    if bad:
        sys.exit(f"FAILED: {bad}")
    print(f"A15 EXPANDING-CONTEXT E2E COMPLETE: each model {N:,} req "
          f"(99.96% of 1M), both pools, per-request records")


if __name__ == "__main__":
    main()
