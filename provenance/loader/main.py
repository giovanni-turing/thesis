#!/usr/bin/env python3
"""Provenance loader entrypoint.

  python main.py --projections        # small typed layer (fast; NL queries usable after)
  python main.py --raw                # heavy raw fact tables (COPY)
  python main.py --only K2,K5         # specific kinds
  python main.py --reload             # ignore ingest_log sha, reload
  python main.py --list               # list kinds

Per-kind runs are independent and touch different tables, so several
`python main.py --only Kx` processes can run in parallel (background) for the raw load.
"""
import argparse, sys, time
import loaders as L
import load_grid, load_collector_silicon, load_trace_eda, load_vllm_etl, load_pred_ewma
import load_sweeps, load_costmodel, load_residual, load_a16
from ingest_common import load_ingest_index

PROJ = [("K9", "windows", L.load_windows), ("K1", "llm_reports", L.load_llm_reports),
        ("K3", "encoder_stats", L.load_encoder_stats), ("K7", "factorial", L.load_factorial),
        ("K8", "coverage", L.load_coverage), ("K8b", "verification", L.load_verification),
        ("K10m", "forecast_metrics", L.load_forecast_metrics),
        ("K12", "collector", L.load_collector), ("K14", "cost_accounting", L.load_cost_accounting),
        ("K15", "composed_e2e", L.load_composed_e2e),
        ("K13", "ledger", L.load_ledger),
        # projection-layer loaders that live in their own modules
        ("K20", "grid", load_grid.load_grid),
        ("K21", "collector_silicon", load_collector_silicon.load_collector_silicon),
        ("K22", "trace_eda", load_trace_eda.load_trace_eda),
        ("K23", "vllm_etl", load_vllm_etl.load_vllm_etl),
        ("K24", "pred_ewma", load_pred_ewma.load_pred_ewma),
        ("K25", "sweeps", load_sweeps.load_sweeps),
        ("K26", "costmodel", load_costmodel.load_costmodel),
        ("K27", "ewma_cal", load_residual.load_ewma_cal),
        ("K28", "rerun_b1", load_residual.load_rerun_b1)]
RAW = [("K4", "worker_schedule", L.load_worker_schedule),
       ("K2", "llm_requests", L.load_llm_requests),
       ("K5", "encoder_series", L.load_encoder_series),
       ("K6", "composed", L.load_composed), ("K10", "forecast", L.load_forecast),
       ("K11", "measured", L.load_measured),
       ("K29", "eda_rates", load_residual.load_eda_rates)]
PROJ.append(("K30", "a16_analysis", load_a16.load_a16))
ALL = PROJ + RAW
BYKIND = {k: (k, name, fn) for k, name, fn in ALL}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma list of kinds, e.g. K2,K5")
    ap.add_argument("--projections", action="store_true")
    ap.add_argument("--raw", action="store_true")
    ap.add_argument("--reload", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for k, name, _ in ALL:
            print(f"{k:5} {name}")
        return
    if a.only:
        sel = [BYKIND[k.strip()] for k in a.only.split(",")]
    elif a.projections:
        sel = PROJ
    elif a.raw:
        sel = RAW
    else:
        sel = ALL
    idx = load_ingest_index()
    tot_f = tot_r = 0
    for k, name, fn in sel:
        t0 = time.time()
        try:
            nf, nr = fn(idx, a.reload)
        except Exception as e:
            print(f"[{k:5} {name:16}] ERROR: {e}", file=sys.stderr, flush=True)
            continue
        print(f"[{k:5} {name:16}] files={nf:5d} rows={nr:13,d}  {time.time()-t0:7.1f}s", flush=True)
        tot_f += nf
        tot_r += nr
    print(f"TOTAL files={tot_f} rows={tot_r:,}", flush=True)


if __name__ == "__main__":
    main()
