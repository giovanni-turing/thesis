#!/usr/bin/env python3
"""Run the forward-EWMA calibrated-p90 baseline through the IDENTICAL encoder
issue-time pipeline as the TSFM policy (GEN=forecast_schedule_issuetime.py ->
CONV=trace_to_two_pool.py), so the only thing that changes is the forecaster.

Answers the "did you ever price a cheap forward forecaster at a calibrated
quantile?" question: chronos (control) vs EWMA {add,mult,wsc} calibrated p90.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(os.environ.get("TESE_ROOT", Path(__file__).resolve().parents[2]))
EDA_PY = str(ROOT / "eda/.venv/bin/python")
AIC_PY = str(ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python")
GEN = str(ROOT / "verification/scripts/forecast_schedule_issuetime.py")
CONV = str(ROOT / "workload/trace_to_two_pool.py")
WINS = json.load(open(ROOT / "simulation/windows.json"))
ENV = {**os.environ, "TESE_WINDOWS": str(ROOT / "simulation/windows.json"), "TESE_ROOT": str(ROOT)}
SCRATCH = Path(tempfile.gettempdir()) / "ewma_baseline"; SCRATCH.mkdir(parents=True, exist_ok=True)

PARQUETS = {
    "chronos":  ROOT / "predictors/results/chronos_images.parquet",
    "ewma-add": ROOT / "predictors/results/ewma_cal_add_images.parquet",
    "ewma-mult":ROOT / "predictors/results/ewma_cal_mult_images.parquet",
    "ewma-wsc": ROOT / "predictors/results/ewma_cal_wsc_images.parquet",
}
DENOM = 8 * 483659.8  # static C=8 over the aggregate span

def run(model, window, lead, rho=15, q="p90", strict=False):
    w = WINS[window]
    tag = f"{model}_{window}_L{lead}_{q}_rho{rho}_{'strict' if strict else 'warm'}"
    sched = SCRATCH / f"{tag}.sched.json"; out = SCRATCH / f"{tag}.jsonl"
    g = [EDA_PY, GEN, "--window", window, "--quantile", q, "--rho", str(rho),
         "--cold-start-s", str(lead), "--parquet", str(PARQUETS[model]), "--out", str(sched)]
    if strict: g.append("--strict-rewarm")
    r = subprocess.run(g, capture_output=True, text=True, env=ENV)
    if r.returncode: return {"model": model, "window": window, "lead": lead, "err": "gen:" + r.stderr[-200:]}
    c = [AIC_PY, CONV, "--out", str(out), "--offset", str(w["offset"]),
         "--max-requests", str(w["max_requests"]), "--encoder-workers", "2", "--worker-schedule", str(sched)]
    r = subprocess.run(c, capture_output=True, text=True, env=ENV)
    if r.returncode: return {"model": model, "window": window, "lead": lead, "err": "conv:" + r.stderr[-200:]}
    st = json.load(open(str(out) + ".stats.json"))
    p99 = st["encoder_delay_ms"]["p99"]; ws = st["provisioned_worker_seconds"]
    for p in (out, Path(str(out) + ".stats.json")):
        try: p.unlink()
        except OSError: pass
    return {"model": model, "window": window, "lead": lead, "rho": rho, "q": q,
            "readiness": "strict" if strict else "warm",
            "p99_ms": p99, "max_ms": st["encoder_delay_ms"]["max"],
            "divergent": st["queue_divergent"], "ws": ws,
            "ratio_vs_static": round(ws / DENOM, 4) if window == "aggregate" else None,
            "feasible": (p99 < 1000) and (not st["queue_divergent"])}

if __name__ == "__main__":
    # args: window lead[,lead...]  (models = all)
    window = sys.argv[1] if len(sys.argv) > 1 else "burst3"
    leads = [int(x) for x in (sys.argv[2].split(",") if len(sys.argv) > 2 else ["30"])]
    strict = "--strict" in sys.argv
    rows = []
    for model in PARQUETS:
        for lead in leads:
            res = run(model, window, lead, strict=strict)
            rows.append(res)
            if "err" in res:
                print(f"{model:10s} {window} L{lead}: ERROR {res['err']}", flush=True)
            else:
                print(f"{model:10s} {window} L{lead:<3d} {res['readiness']}: "
                      f"p99={res['p99_ms']:8.1f}ms  ws={res['ws']:>12.1f}  "
                      f"ratio={res['ratio_vs_static']}  "
                      f"{'PASS' if res['feasible'] else 'FAIL'}"
                      f"{' DIVERGENT' if res['divergent'] else ''}", flush=True)
    outp = ROOT / f"verification/results/ewma_baseline_{window}{'_strict' if strict else ''}.json"
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(rows, indent=1))
    print(f"-> {outp}")
