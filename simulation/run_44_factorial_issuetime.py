#!/usr/bin/env python3
"""Rebuild the 60-cell p90/rho=15 encoder factorial under ISSUE-TIME actuation.

The archived 560-cell grid (gen_cells_44.py / run_cell.py) used the TARGET-time
controller (forecast_schedule.py) at leads {15,30,45,300}. The manuscript now
frames the encoder result as issue-time, so the "p90/rho=15 passes all 60 cells,
every lead 15-165 s" claim must be backed by an issue-time factorial. This driver
rebuilds exactly those 60 cells (5 in-span windows x 3 TSFMs x 4 realizable leads
{15,30,45,165}) under BOTH readiness models (warm-pool default + strict re-warm),
using the SAME per-window converter invocation as run_cell.py
(--offset win.offset --max-requests win.max_requests --encoder-workers 2).

Portable: paths resolve from TESE_ROOT (default = repo root inferred from this
file); interpreter venvs from EDA_PY / AIC_PY env (pandas generator + AIC
converter respectively). Per-request .jsonl intermediates go to a scratch dir
(TESE_SCRATCH, default /tmp) and are not kept; the committed evidence is
results/factorial_issuetime/factorial_issuetime_results.json.
"""
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(os.environ.get("TESE_ROOT", Path(__file__).resolve().parents[1]))
EDA_PY = os.environ.get("EDA_PY", str(ROOT / "eda/.venv/bin/python"))
AIC_PY = os.environ.get("AIC_PY", str(ROOT / "ai-dynamo/aiconfigurator/.venv/bin/python"))
GEN = ROOT / "verification/scripts/forecast_schedule_issuetime.py"
CONV = ROOT / "workload/trace_to_two_pool.py"
WINJSON = ROOT / "simulation/windows.json"
OUTDIR = ROOT / "simulation/results/factorial_issuetime"
SCRATCH = Path(os.environ.get("TESE_SCRATCH", tempfile.gettempdir())) / "factorial_issuetime"
OUTDIR.mkdir(parents=True, exist_ok=True)
SCRATCH.mkdir(parents=True, exist_ok=True)
WINS = json.load(open(WINJSON))
ENV = {**os.environ, "TESE_WINDOWS": str(WINJSON)}

WINDOWS = ["burst1", "burst3", "burst4", "burst5", "steady24h"]
MODELS = ["chronos", "toto", "timesfm"]
LEADS = [15, 30, 45, 165]
QUANTILE = os.environ.get("QUANTILE", "p90")  # p90 = headline; p50 = ablation


def run(window, model, lead, strict):
    tag = f"{window}_{model}_L{lead}_{'strict' if strict else 'warm'}"
    sched = SCRATCH / f"{tag}.sched.json"
    outjsonl = SCRATCH / f"{tag}.jsonl"
    parquet = ROOT / f"predictors/results/{model}_images.parquet"
    g = [EDA_PY, str(GEN), "--window", window, "--quantile", QUANTILE, "--rho", "15",
         "--cold-start-s", str(lead), "--parquet", str(parquet), "--out", str(sched)]
    if strict:
        g.append("--strict-rewarm")
    r = subprocess.run(g, capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        return {"window": window, "model": model, "lead": lead,
                "readiness": "strict" if strict else "warm",
                "error": "gen", "detail": r.stderr[-300:]}
    w = WINS[window]
    c = [AIC_PY, str(CONV), "--out", str(outjsonl), "--offset", str(w["offset"]),
         "--max-requests", str(w["max_requests"]), "--encoder-workers", "2",
         "--worker-schedule", str(sched)]
    r = subprocess.run(c, capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        return {"window": window, "model": model, "lead": lead,
                "readiness": "strict" if strict else "warm",
                "error": "conv", "detail": r.stderr[-300:]}
    st = json.load(open(str(outjsonl) + ".stats.json"))
    p99 = st["encoder_delay_ms"]["p99"]
    res = {"window": window, "model": model, "lead": lead,
           "readiness": "strict" if strict else "warm",
           "p99_ms": p99, "max_ms": st["encoder_delay_ms"]["max"],
           "queue_divergent": st["queue_divergent"],
           "feasible": (p99 < 1000) and (not st["queue_divergent"]),
           "provisioned_ws": st["provisioned_worker_seconds"]}
    # drop the big per-request jsonl; keep only stats+sched footprint tiny
    for p in (outjsonl, Path(str(outjsonl) + ".stats.json")):
        try:
            p.unlink()
        except OSError:
            pass
    return res


def main():
    cells = [(w, m, l, s) for w in WINDOWS for m in MODELS for l in LEADS
             for s in (False, True)]
    results = []
    with ThreadPoolExecutor(max_workers=int(os.environ.get("FACTORIAL_CONC", "8"))) as ex:
        for res in ex.map(lambda a: run(*a), cells):
            tag = f"{res['window']}_{res['model']}_L{res['lead']}_{res['readiness']}"
            print(tag, res.get("error") or f"p99={res.get('p99_ms')} feasible={res.get('feasible')}",
                  flush=True)
            results.append(res)
    results.sort(key=lambda r: (r["readiness"], r["window"], r["model"], r["lead"]))
    json.dump({"grid": QUANTILE + "/rho15 x {burst1,burst3,burst4,burst5,steady24h} x "
                       "{chronos,toto,timesfm} x leads{15,30,45,165} x "
                       "{warm-pool,strict-rewarm}; issue-time actuation; "
                       "denominator static C8; feasible = p99<1000ms & not divergent",
               "results": results},
              open(OUTDIR / f"factorial_issuetime_{QUANTILE}_results.json", "w"), indent=1)
    print("=" * 60)
    for rd in ("warm", "strict"):
        sub = [r for r in results if r["readiness"] == rd and "error" not in r]
        npass = sum(1 for r in sub if r["feasible"])
        p99s = [r["p99_ms"] for r in sub]
        errs = [r for r in results if r["readiness"] == rd and "error" in r]
        print(f"{rd:6s}: {npass}/{len(sub)} feasible | p99 range "
              f"{min(p99s):.1f}-{max(p99s):.1f} ms | {len(errs)} errors")
    print(f"-> {OUTDIR}/factorial_issuetime_{QUANTILE}_results.json")


if __name__ == "__main__":
    main()
