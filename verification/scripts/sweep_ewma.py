#!/usr/bin/env python3
"""FULL sweep: forward-EWMA calibrated-p90 vs Chronos control through the
identical encoder issue-time loop.

Per-window factorial (rho15, p90): {burst1,burst3,burst4,burst5,steady24h}
  x {chronos, ewma-add, ewma-mult, ewma-wsc} x leads{15,30,45,165}
  x readiness{warm, strict-rewarm}.
Aggregate: same 4 variants x leads{15,30,45,165} x {warm,strict} at rho15/p90;
  plus rho-frontier {10,20,25} (L30 warm); plus a p50 arm (L30 warm rho15).
GEN=forecast_schedule_issuetime.py -> CONV=trace_to_two_pool.py. Denominator
static C8 = 3,869,278 ws. feasible = p99<1000ms AND not queue_divergent.
Per-cell failures are recorded, never abort the sweep.
"""
import json, os, subprocess, tempfile, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(os.environ.get("TESE_ROOT", Path(__file__).resolve().parents[2]))
EDA_PY = str(ROOT / "eda/.venv/bin/python")
AIC_PY = str(ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python")
GEN = str(ROOT / "verification/scripts/forecast_schedule_issuetime.py")
CONV = str(ROOT / "workload/trace_to_two_pool.py")
WINS = json.load(open(ROOT / "simulation/windows.json"))
ENV = {**os.environ, "TESE_WINDOWS": str(ROOT / "simulation/windows.json"), "TESE_ROOT": str(ROOT)}
SCRATCH = Path(tempfile.gettempdir()) / "ewma_sweep"; SCRATCH.mkdir(parents=True, exist_ok=True)
DENOM = 8 * 483659.8
PARQUETS = {
    "chronos":   ROOT / "predictors/results/chronos_images.parquet",
    "ewma-add":  ROOT / "predictors/results/ewma_cal_add_images.parquet",
    "ewma-mult": ROOT / "predictors/results/ewma_cal_mult_images.parquet",
    "ewma-wsc":  ROOT / "predictors/results/ewma_cal_wsc_images.parquet",
}

def run(cell):
    model, window, lead, rho, q, strict = cell
    w = WINS[window]
    tag = f"{model}_{window}_L{lead}_rho{rho}_{q}_{'strict' if strict else 'warm'}"
    sched = SCRATCH / f"{tag}.sched.json"; out = SCRATCH / f"{tag}.jsonl"
    base = {"model": model, "window": window, "lead": lead, "rho": rho, "q": q,
            "readiness": "strict" if strict else "warm"}
    g = [EDA_PY, GEN, "--window", window, "--quantile", q, "--rho", str(rho),
         "--cold-start-s", str(lead), "--parquet", str(PARQUETS[model]), "--out", str(sched)]
    if strict: g.append("--strict-rewarm")
    r = subprocess.run(g, capture_output=True, text=True, env=ENV)
    if r.returncode: return {**base, "err": "gen:" + r.stderr[-160:]}
    c = [AIC_PY, CONV, "--out", str(out), "--offset", str(w["offset"]),
         "--max-requests", str(w["max_requests"]), "--encoder-workers", "2", "--worker-schedule", str(sched)]
    r = subprocess.run(c, capture_output=True, text=True, env=ENV)
    if r.returncode: return {**base, "err": "conv:" + r.stderr[-160:]}
    try:
        st = json.load(open(str(out) + ".stats.json"))
    except Exception as e:
        return {**base, "err": f"stats:{e}"}
    p99 = st["encoder_delay_ms"]["p99"]; ws = st["provisioned_worker_seconds"]
    for p in (sched, out, Path(str(out) + ".stats.json")):
        try: p.unlink()
        except OSError: pass
    return {**base, "p99_ms": p99, "max_ms": st["encoder_delay_ms"]["max"],
            "divergent": st["queue_divergent"], "ws": ws,
            "ratio": round(ws / DENOM, 4) if window == "aggregate" else None,
            "feasible": (p99 < 1000) and (not st["queue_divergent"])}

def phase(name, cells, conc):
    print(f"\n### {name}: {len(cells)} cells, conc={conc}", flush=True)
    res = []
    with ThreadPoolExecutor(max_workers=conc) as ex:
        for r in ex.map(run, cells):
            tag = f"{r['model']:10s} {r['window']:9s} L{r['lead']:<3d} rho{r['rho']} {r['q']} {r['readiness']:6s}"
            if "err" in r: print(f"{tag}: ERR {r['err']}", flush=True)
            else: print(f"{tag}: p99={r['p99_ms']:8.1f} ws={r['ws']:>12.1f} "
                        f"ratio={r['ratio']} {'PASS' if r['feasible'] else 'FAIL'}"
                        f"{' DIV' if r['divergent'] else ''}", flush=True)
            res.append(r)
    return res

if __name__ == "__main__":
    t0 = time.time()
    MODELS = list(PARQUETS); LEADS = [15, 30, 45, 165]
    WINDOWS = ["burst1", "burst3", "burst4", "burst5", "steady24h"]
    per_window = [(m, w, L, 15, "p90", s) for w in WINDOWS for m in MODELS
                  for L in LEADS for s in (False, True)]
    agg_main = [(m, "aggregate", L, 15, "p90", s) for m in MODELS for L in LEADS for s in (False, True)]
    agg_rho  = [(m, "aggregate", 30, rho, "p90", False) for m in MODELS for rho in (10, 20, 25)]
    agg_p50  = [(m, "aggregate", 30, 15, "p50", False) for m in MODELS]
    results = []
    results += phase("PER-WINDOW factorial (rho15/p90)", per_window, 8)
    results += phase("AGGREGATE (p90 rho15 leads x readiness)", agg_main, 4)
    results += phase("AGGREGATE rho-frontier (L30 warm)", agg_rho, 4)
    results += phase("AGGREGATE p50 arm (L30 warm rho15)", agg_p50, 4)
    outp = ROOT / "verification/results/ewma_sweep.json"
    outp.write_text(json.dumps({"denom_static_c8_ws": DENOM, "cells": results}, indent=1))
    ok = sum(1 for r in results if "err" not in r); err = len(results) - ok
    print(f"\n=== sweep done: {ok} cells, {err} errors, {time.time()-t0:.0f}s -> {outp} ===", flush=True)
