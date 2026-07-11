#!/usr/bin/env python3
"""Full issue-time WEEK-SCALE surface: every (model, quantile, rho, lead) cell as
a continuous aggregate replay of the covered span, under issue-time actuation.

Backs the "quantile is the decisive dial, rating is a cost knob" week-scale
conclusion with committed evidence (the archived run_week_matrix.sh was
target-time at L=300). 3 models x 2 quantiles x 4 ratings x 4 realizable leads
= 96 warm-pool cells; per-request jsonl -> scratch (dropped), consolidated
results committed as results/week_surface_issuetime/week_surface_issuetime_results.json.

Portable: TESE_ROOT / EDA_PY / AIC_PY env (defaults inferred). Denominator =
static C8 over the covered span = 3,869,278 worker-s.
"""
import json
import os
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("TESE_ROOT", Path(__file__).resolve().parents[1]))
EDA_PY = os.environ.get("EDA_PY", str(ROOT / "eda/.venv/bin/python"))
AIC_PY = os.environ.get("AIC_PY", str(ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"))
GEN = ROOT / "verification/scripts/forecast_schedule_issuetime.py"
CONV = ROOT / "workload/trace_to_two_pool.py"
WINJSON = ROOT / "simulation/windows.json"
OUTDIR = ROOT / "simulation/results/week_surface_issuetime"
SCRATCH = Path(os.environ.get("TESE_SCRATCH", tempfile.gettempdir())) / "week_surface_issuetime"
OUTDIR.mkdir(parents=True, exist_ok=True)
SCRATCH.mkdir(parents=True, exist_ok=True)
ENV = {**os.environ, "TESE_WINDOWS": str(WINJSON), "TESE_ROOT": str(ROOT)}
AGG = json.load(open(WINJSON))["aggregate"]
STATIC_C8 = 8 * AGG["span_s"]

MODELS = ["chronos", "toto", "timesfm"]
QUANTILES = ["p90", "p50"]
RHOS = [10, 15, 20, 25]
LEADS = [15, 30, 45, 165]


def run(model, quantile, rho, lead):
    tag = f"{model}_{quantile}_rho{rho}_L{lead}"
    sched = SCRATCH / f"{tag}.sched.json"
    outjsonl = SCRATCH / f"{tag}.jsonl"
    parquet = ROOT / f"predictors/results/{model}_images.parquet"
    g = [EDA_PY, str(GEN), "--window", "aggregate", "--quantile", quantile,
         "--rho", str(rho), "--cold-start-s", str(lead), "--parquet", str(parquet),
         "--out", str(sched)]
    r = subprocess.run(g, capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        return {"model": model, "quantile": quantile, "rho": rho, "lead": lead,
                "error": "gen", "detail": r.stderr[-300:]}
    c = [AIC_PY, str(CONV), "--out", str(outjsonl), "--offset", str(AGG["offset"]),
         "--max-requests", str(AGG["max_requests"]), "--encoder-workers", "2",
         "--worker-schedule", str(sched)]
    r = subprocess.run(c, capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        return {"model": model, "quantile": quantile, "rho": rho, "lead": lead,
                "error": "conv", "detail": r.stderr[-300:]}
    st = json.load(open(str(outjsonl) + ".stats.json"))
    p99 = st["encoder_delay_ms"]["p99"]
    ws = st["provisioned_worker_seconds"]
    res = {"model": model, "quantile": quantile, "rho": rho, "lead": lead,
           "p99_ms": round(p99, 2), "provisioned_ws": round(ws),
           "ratio_vs_static_c8": round(ws / STATIC_C8, 4),
           "queue_divergent": st["queue_divergent"],
           "aggregate_feasible": (p99 < 1000) and (not st["queue_divergent"])}
    for p in (outjsonl, Path(str(outjsonl) + ".stats.json")):
        try:
            p.unlink()
        except OSError:
            pass
    return res


def main():
    cells = [(m, q, r, l) for m in MODELS for q in QUANTILES for r in RHOS for l in LEADS]
    results = []
    with ThreadPoolExecutor(max_workers=int(os.environ.get("SURFACE_CONC", "6"))) as ex:
        for res in ex.map(lambda a: run(*a), cells):
            print(f"{res['model']}_{res['quantile']}_rho{res['rho']}_L{res['lead']}",
                  res.get("error") or f"p99={res['p99_ms']} {res['ratio_vs_static_c8']}x "
                  f"feasible={res['aggregate_feasible']}", flush=True)
            results.append(res)
    results.sort(key=lambda r: (r["quantile"], r["rho"], r["model"], r["lead"]))
    json.dump({"surface": "3 models x {p50,p90} x rho{10,15,20,25} x leads{15,30,45,165} "
                          "= 96 warm-pool aggregate cells; issue-time; static C8 denominator "
                          f"= {round(STATIC_C8)} ws; aggregate_feasible = p99<1000 & not divergent",
               "results": results},
              open(OUTDIR / "week_surface_issuetime_results.json", "w"), indent=1)
    print("=" * 60)
    for q in QUANTILES:
        sub = [r for r in results if r["quantile"] == q and "error" not in r]
        npass = sum(1 for r in sub if r["aggregate_feasible"])
        p99s = [r["p99_ms"] for r in sub]
        print(f"{q}: {npass}/{len(sub)} aggregate-feasible | p99 {min(p99s):.0f}-{max(p99s):.0f} ms")


if __name__ == "__main__":
    main()
