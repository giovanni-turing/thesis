#!/usr/bin/env python3
"""A13 full-trace coverage batch: EVERY request of the 1,000,000-request trace
simulated through BOTH pools with per-request records.

Encoder pool (converter FIFO, snapshot graph, per-second series):
  ft_static_C8      deployable static (8 workers)
  ft_static_C2      calm-day optimum (2 workers)
  ft_reactive_L30   reactive rho15/L30 (15-s trailing observation; defined on
                    the whole trace — no forecast needed)
Language pool (dynamo.replay, per-request records), on the matching
encoder-composed trace:
  ft_llm_static     TP2x2 deployable shape (2 workers, no planner) on the
                    C8-composed trace
  ft_llm_reactive   SLA planner (ARIMA ladder, L=60) on the reactive-composed
                    trace — true E2E reactive
Forecast policies are structurally undefined on the first 1.4 days (no
archived forecast exists there — thesis coverage boundary); their full
covered-span runs already exist (a6_runs / a11_runs / a12_runs).
Verification: every stage must report exactly 1,000,000 requests.
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path("/home/gio/tese")
OUT = ROOT / "defense/anim/data/a13_runs"
OUT.mkdir(parents=True, exist_ok=True)
WINJSON = ROOT / "defense/anim/data/windows_ext.json"
W = json.load(open(WINJSON))["fulltrace"]
EDA_PY = ROOT / "eda/.venv/bin/python"
AIC_PY = ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"
SRC_PY = ROOT / "ai-dynamo/dynamo/.venv/bin/python"
RR = ROOT / "simulation/run_replay.sh"
LADDER = ROOT / "simulation/results/riders44/planner_ladder_t200_20.json"
N = 1_000_000


def conv(tag: str, workers: int, sched: Path | None) -> dict:
    out = OUT / f"{tag}.jsonl"
    cmd = [str(AIC_PY), str(ROOT / "defense/anim/build/a2_conv_snapshot.py"),
           "--out", str(out), "--offset", "0", "--max-requests", str(N),
           "--encoder-workers", str(workers),
           "--series-out", str(OUT / f"{tag}.series.json")]
    if sched is not None:
        cmd += ["--worker-schedule", str(sched)]
    env = {**os.environ, "TESE_WINDOWS": str(WINJSON), "TESE_ROOT": str(ROOT)}
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        return {"error": f"conv rc={r.returncode}: {r.stderr[-400:]}"}
    st = json.load(open(f"{out}.stats.json"))
    nl = sum(1 for _ in open(out))
    res = {"stage": "encoder", "requests": nl,
           "enc_p99": round(st["encoder_delay_ms"]["p99"], 1),
           "enc_max": round(st["encoder_delay_ms"]["max"], 1),
           "provisioned_ws": st["provisioned_worker_seconds"],
           "queue_divergent": st["queue_divergent"]}
    if nl != N:
        res["error"] = f"coverage hole: {nl} != {N}"
    return res


def llm(tag: str, trace: Path, planner: bool) -> dict:
    rep = OUT / f"{tag}.report.json"
    env = {**os.environ, "RUST_LOG": "warn", "AIC_TP": "2", "AIC_VER": "0.19.0",
           "REPLAY_PY": str(SRC_PY), "STARTUP_TIME": "60"}
    cmd = ["bash", str(RR), str(trace), "aic", str(rep), "2",
           "--report-jsonl", str(OUT / f"{tag}.requests.jsonl")]
    if planner:
        cmd += ["--planner-config", str(LADDER)]
    with open(OUT / f"{tag}.log", "w") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env)
    if r.returncode != 0:
        return {"error": f"llm rc={r.returncode} (see {tag}.log)"}
    d = json.load(open(rep))
    nl = sum(1 for _ in open(OUT / f"{tag}.requests.jsonl"))
    res = {"stage": "language", "requests": nl,
           "completed": d["completed_requests"],
           "ttft_p99": round(d["p99_ttft_ms"], 1),
           "itl_p99": round(d["p99_itl_ms"], 1),
           "gpu_h": round(d["gpu_hours"], 2)}
    if nl != N or d["completed_requests"] != N:
        res["error"] = f"coverage hole: jsonl {nl}, completed {d['completed_requests']} != {N}"
    return res


def main() -> None:
    results = {}
    if (OUT / "verification.json").exists():
        results = json.load(open(OUT / "verification.json"))

    def save():
        (OUT / "verification.json").write_text(json.dumps(results, indent=1))

    # reactive encoder schedule over the full trace
    sched = OUT / "ft_reactive_L30.sched.json"
    if not sched.exists():
        env = {**os.environ, "TESE_WINDOWS": str(WINJSON), "TESE_ROOT": str(ROOT)}
        r = subprocess.run([str(EDA_PY), str(ROOT / "simulation/forecast_schedule.py"),
                            "--window", "fulltrace", "--policy", "reactive",
                            "--resolution", "15s", "--rho", "15",
                            "--cold-start-s", "30", "--hysteresis-min", "3",
                            "--out", str(sched)],
                           capture_output=True, text=True, env=env)
        if r.returncode != 0:
            sys.exit(f"reactive schedule gen failed: {r.stderr[-500:]}")

    stage1 = [("ft_static_C8", 8, None), ("ft_static_C2", 2, None),
              ("ft_reactive_L30", 2, sched)]
    with ThreadPoolExecutor(max_workers=2) as ex:
        for (tag, _, _), res in zip(stage1, ex.map(lambda a: conv(*a), stage1)):
            if tag in results and "error" not in results[tag]:
                continue
            results[tag] = res
            print(tag, res, flush=True)
    save()
    if any("error" in results[t] for t, _, _ in stage1):
        sys.exit("stage 1 failed")

    stage2 = [("ft_llm_static", OUT / "ft_static_C8.jsonl", False),
              ("ft_llm_reactive", OUT / "ft_reactive_L30.jsonl", True)]
    with ThreadPoolExecutor(max_workers=1) as ex:  # RAM: 1M-req replays are ~13GB each, run one at a time
        for (tag, _, _), res in zip(stage2, ex.map(lambda a: llm(*a), stage2)):
            results[tag] = res
            print(tag, res, flush=True)
    save()
    bad = [t for t, r in results.items() if "error" in r]
    if bad:
        sys.exit(f"FAILED: {bad}")
    print("FULL-TRACE COVERAGE COMPLETE: all 1,000,000 requests simulated "
          "through both pools with per-request records")


if __name__ == "__main__":
    main()
