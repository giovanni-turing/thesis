#!/usr/bin/env python3
"""K26 loader -- family "costmodel": polynomial vs calibrated (AIC) decode timing.

Backs thesis tab:sim-poly-aic.

Three families of PAIRED runs, each {poly, aic} over an identical window,
trace and topology, so the only independent variable is how decode time is
priced:

  head2k_src  simulation/results/srcbuild/llm_head2k_{poly,aic}_src.json
              -- source-built runtime; THE PAIR PRINTED IN tab:sim-poly-aic
  two_pool    simulation/results/two_pool_{poly,aic}.json
  llm_only    simulation/results/llm_only_{poly,aic}.json

Ingests (kind K26, sha256-gated):
  the 6 JSONs -> cost_model_variant (6) + cost_model_metric (~380, tall)

The artifacts are flat aiperf-style metric dicts whose key sets differ across
families (srcbuild adds gpu_hours / worker-seconds / prefix-cache keys), so the
COMPLETE payload goes tall into cost_model_metric and only the metrics the
thesis prints are promoted to columns on cost_model_variant.

Deliberately NOT ingested:
  srcbuild/run_{poly,aic}.log (~865 KB each) -- per-request driver stdout;
      every number they contain is already in the summary JSONs

Reproduce tab:sim-poly-aic:

  SELECT round(max(mean_ttft_ms) FILTER (WHERE converter='poly')::numeric,1) ...
    FROM provenance.cost_model_variant WHERE family='head2k_src';

Run:  cd /home/gio/tese/provenance/loader && python3 load_costmodel.py [--reload]
"""
import json
import os
import sys

import db
import ingest_common as ic

RESULTS = "/home/gio/tese/simulation/results"
KIND = "K26"

# family -> (path template, window, runtime, published?)
FAMILIES = {
    "head2k_src": (f"{RESULTS}/srcbuild/llm_head2k_{{c}}_src.json",
                   "head2k", "srcbuild", True),
    "two_pool":   (f"{RESULTS}/two_pool_{{c}}.json", "head2k", None, False),
    "llm_only":   (f"{RESULTS}/llm_only_{{c}}.json", "head2k", None, False),
}
CONVERTERS = ("poly", "aic")
TOPOLOGY = "2 language workers, offline KV router"

# JSON key -> promoted column on cost_model_variant
_PROMOTE = {
    "mean_ttft_ms": "mean_ttft_ms",
    "p99_ttft_ms": "p99_ttft_ms",
    "max_ttft_ms": "max_ttft_ms",
    "mean_e2e_latency_ms": "mean_e2e_latency_ms",
    "p99_e2e_latency_ms": "p99_e2e_latency_ms",
    "mean_itl_ms": "mean_itl_ms",
    "max_itl_ms": "max_itl_ms",
    "mean_output_token_throughput_per_user": "mean_output_tok_per_user",
    "completed_requests": "completed_requests",
    "duration_ms": "duration_ms",
    "request_throughput_rps": "request_throughput_rps",
    "total_input_tokens": "total_input_tokens",
    "total_output_tokens": "total_output_tokens",
    "gpu_hours": "gpu_hours",
    "decode_worker_seconds": "decode_worker_seconds",
    "prefill_worker_seconds": "prefill_worker_seconds",
}

_VAR_COLS = (["variant_id", "family", "converter", "window_name", "runtime",
              "topology", "is_published"]
             + sorted(set(_PROMOTE.values()))
             + ["n_metrics", "source_path"])


def _prep(path, idx, reload):
    if ic.is_worktree(path):
        return None
    sha, nbytes = ic.file_meta(path)
    if not reload and idx.get(path) == sha:
        return None
    return sha, nbytes


def _run(*stmts):
    sql = ";\n".join(s for s in stmts if s)
    if sql:
        db.run_sql(sql)


def load_costmodel(idx, reload):
    """K26 entrypoint. Returns (files_loaded, rows_loaded)."""
    nf = nr = 0
    for family, (tmpl, window, runtime, published) in FAMILIES.items():
        for conv in CONVERTERS:
            path = tmpl.format(c=conv)
            if not os.path.exists(path):
                print(f"[{KIND}] MISSING {path}", file=sys.stderr, flush=True)
                continue
            prep = _prep(path, idx, reload)
            if prep is None:
                continue
            sha, nbytes = prep
            with open(path) as f:
                d = json.load(f)

            variant_id = f"{family}:{conv}"
            # tall: every numeric scalar, nothing dropped
            metrics = [{"variant_id": variant_id, "metric": k, "value": float(v)}
                       for k, v in sorted(d.items())
                       if isinstance(v, (int, float)) and not isinstance(v, bool)]

            row = {"variant_id": variant_id, "family": family, "converter": conv,
                   "window_name": window, "runtime": runtime, "topology": TOPOLOGY,
                   "is_published": published, "n_metrics": len(metrics),
                   "source_path": path}
            for jk, col in _PROMOTE.items():
                row[col] = d.get(jk)

            _run(ic.upsert_sql("cost_model_variant", row, "variant_id"),
                 ic.delete_for_run_sql("cost_model_metric", variant_id, "variant_id"),
                 ic.multi_upsert_sql("cost_model_metric",
                                     ["variant_id", "metric", "value"],
                                     metrics, ["variant_id", "metric"]),
                 ic.ingest_sql(path, sha, KIND, 1 + len(metrics), variant_id, nbytes))
            nf += 1
            nr += 1 + len(metrics)
    return nf, nr


def main():
    reload = "--reload" in sys.argv
    idx = ic.load_ingest_index()
    nf, nr = load_costmodel(idx, reload)
    print(f"[K26   costmodel       ] files={nf:5d} rows={nr:13,d}", flush=True)


if __name__ == "__main__":
    main()
