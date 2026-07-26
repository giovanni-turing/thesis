#!/usr/bin/env python3
"""Ingest the lang_qsweep artifacts NOT covered by the langcalib loader (review
Finding 4). load_langcalib.py owns 162 report files (eval_*, calib burst[26]_*,
folds_*, baseline_calib/eval/week, extra_week) under experiment='langcalib' -- those
stay file-gated in ingest_log and are NEVER re-ingested here (no second run_id for the
same underlying run). What langcalib does NOT carry, and this loader does, under
experiment='lang_qsweep' with runid.py-scoped ids:

  perreq/  -- the 2026-07-26 per-request rerun (run_lang_perreq_rerun.sh): 9 full-week
              (749,601-req) replays WITH --report-jsonl per-request records, backing the
              exact cost<->violation curves (violation_curves_2026-07-26.txt). These are
              NEW replays of frontier operating points, not copies of langcalib runs:
              each has its own report + per-request archive (*.perreq.jsonl.zst).
              lang_qsweep:perreq:fc_chronos_p50_s8 already existed (migrated by
              schema/32) -- it gains canonical window/tp/config here, no duplicate.
  smoke_b2_p90_s8.report.json -- the burst2 smoke validation of the --report-jsonl flow
              (2026-07-24 23:04, before the calib sweep), kept for completeness with
              config.arm='smoke'.

Quantile p70 is outside the closed vocabulary {p50,p90,obs} -> quantile NULL +
config.forecast_quantile='p70' (same convention as load_langcalib). Idempotent
(ON CONFLICT upserts + ingest_log sha gate); run-row upserts always execute so
canonical dims heal on gated files. Run: python3 provenance/loader/load_lang_qsweep.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db, ingest_common as ic

ROOT = "/home/gio/tese/simulation/results/lang_qsweep"
EXP = "lang_qsweep"

LLM_COLS = ["completed_requests", "num_requests", "mean_ttft_ms", "median_ttft_ms",
            "p90_ttft_ms", "p95_ttft_ms", "p99_ttft_ms", "max_ttft_ms", "mean_itl_ms",
            "p99_itl_ms", "mean_tpot_ms", "p99_tpot_ms", "mean_e2e_latency_ms",
            "p90_e2e_latency_ms", "p99_e2e_latency_ms", "max_e2e_latency_ms",
            "p99_ttst_ms", "request_throughput_rps", "output_throughput_tok_s",
            "total_throughput_tok_s", "gpu_hours", "decode_worker_seconds",
            "prefill_worker_seconds", "prefix_cache_reused_ratio"]

_NOTE = ("per-request rerun 2026-07-26 (run_lang_perreq_rerun.sh, sequential, "
         "--report-jsonl): exact week-wide SLO violation counts at any threshold; "
         "backs violation_curves_2026-07-26.txt")
_SLA = "planner goodput SLA: ttft<=200 ms, itl<=20 ms (--sla-ttft-ms 200 --sla-itl-ms 20)"


def _fc(stem, model, q, s):
    return dict(stem=stem, policy="forecast", model=model,
                quantile=(q if q in ("p50", "p90") else None), lead=60,
                cfg={"forecast_quantile": q, "forecast_req_scale": s,
                     "point": f"{q}/s{s}", "arm": "perreq",
                     "conversion": "mean(native)" if s == 1 else "tail-aware",
                     "sla": _SLA, "note": _NOTE})


def discover():
    P = [
        _fc("fc_chronos_p50_s8", "chronos", "p50", 8),
        _fc("fc_chronos_p70_s6", "chronos", "p70", 6),
        _fc("fc_chronos_p90_s1", "chronos", "p90", 1),   # mean-conversion (scale=1)
        _fc("fc_chronos_p90_s4", "chronos", "p90", 4),
        _fc("fc_chronos_p90_s6", "chronos", "p90", 6),   # the robust/deployable point
        _fc("fc_timesfm_p90_s6", "timesfm", "p90", 6),
        _fc("fc_toto_p90_s6", "toto", "p90", 6),
        dict(stem="reactive_200_20", policy="reactive", model="arima", quantile=None,
             lead=60, cfg={"targets": "200/20", "predictor": "arima",
                           "variant": "Dynamo SLA planner (B), ARIMA slot",
                           "conversion": "mean(native)", "arm": "perreq",
                           "sla": _SLA, "note": _NOTE}),
        dict(stem="static_tp2x2", policy="static", model=None, quantile=None, lead=0,
             cfg={"tp": 2, "n_replicas": 2, "arm": "perreq",
                  "sla": "per-request thresholds only (no planner goodput SLA)",
                  "note": _NOTE}),
    ]
    R = []
    for r in P:
        d = f"{ROOT}/perreq"
        R.append(dict(rid=f"{EXP}:perreq:{r['stem']}", window="aggregate", tp=2,
                      n_replicas=(2 if r["stem"] == "static_tp2x2" else None),
                      res=("15s" if r["policy"] == "forecast" else None),
                      path=f"{d}/{r['stem']}.report.json",
                      arts=[f"{d}/{r['stem']}.report.json",
                            f"{d}/{r['stem']}.perreq.jsonl.zst",
                            f"{d}/{r['stem']}.log.zst"],
                      expect_requests=749601, **r))
    # burst2 smoke of the --report-jsonl flow. Filename tokens b2/p90/s8; the log
    # confirms a forecast_file planner replay over burst2 (13,870 requests) but does
    # not archive the forecaster name, so model stays NULL and the label provenance
    # is recorded in config.
    R.append(dict(rid=f"{EXP}:smoke_b2_p90_s8", window="burst2", tp=2, n_replicas=None,
                  res="15s", stem="smoke_b2_p90_s8", policy="forecast", model=None,
                  quantile="p90", lead=60,
                  path=f"{ROOT}/smoke_b2_p90_s8.report.json",
                  arts=[f"{ROOT}/smoke_b2_p90_s8.report.json",
                        f"{ROOT}/smoke_b2_p90_s8.log"],
                  expect_requests=13870,
                  cfg={"forecast_quantile": "p90", "forecast_req_scale": 8,
                       "arm": "smoke",
                       "label_source": "filename tokens b2/p90/s8; log shows "
                       "forecast_file planner replay on burst2; forecaster not "
                       "archived in the artifact",
                       "note": "--report-jsonl smoke validation (2026-07-24 23:04) "
                       "before the week-scale perreq reruns"}))
    return R


def _iso_mtime(path):
    import datetime
    return datetime.datetime.fromtimestamp(os.path.getmtime(path),
                                           datetime.timezone.utc).isoformat()


def main():
    idx = ic.load_ingest_index()
    n_runs = n_files = 0
    for r in discover():
        rep = json.load(open(r["path"]))
        assert rep.get("completed_requests") == r["expect_requests"], (
            r["rid"], rep.get("completed_requests"), r["expect_requests"])
        run = {"run_id": r["rid"], "experiment": EXP, "pool": "language",
               "window_name": r["window"], "policy": r["policy"], "model": r["model"],
               "quantile": r["quantile"], "resolution": r["res"], "lead_s": r["lead"],
               "tp": r["tp"], "n_replicas": r["n_replicas"], "converter": "aic",
               "kind": "K1", "source_path": r["path"],
               "artifact_paths": [a for a in r["arts"] if os.path.exists(a)],
               "command": ("simulation/run_lang_perreq_rerun.sh (run_replay.sh aic tp2, "
                           "trace aggregate44/fc_p90_L30.jsonl, --report-jsonl)"
                           if "/perreq/" in r["path"] else
                           "one-off --report-jsonl smoke replay (burst2)"),
               "run_utc": _iso_mtime(r["path"]), "is_current": True, "config": r["cfg"]}
        stmts = [ic.run_upsert_sql(run)]  # ALWAYS: heals canonical dims on gated files
        n_runs += 1
        sha, nb = ic.file_meta(r["path"])
        if idx.get(r["path"]) != sha:
            ic.guard_run_collision(r["rid"], r["path"], idx, "llm_run_summary", "K1")
            llm = {"run_id": r["rid"]}
            for c in LLM_COLS:
                if rep.get(c) is not None:
                    llm[c] = rep[c]
            llm["metrics"] = rep
            llm["has_raw_records"] = False  # per-request archive is *.perreq.jsonl.zst,
            # not llm_request rows -- summary-only in-DB, exact curves in the artifact
            stmts.append(ic.upsert_sql("llm_run_summary", llm, "run_id",
                                       jsonb_cols=("metrics",)))
            stmts.append(ic.ingest_sql(r["path"], sha, "K1", 1, r["rid"], nb))
            n_files += 1
        db.run_sql(";\n".join(stmts))
    print(f"lang_qsweep: {n_runs} runs upserted; {n_files} report files (re)loaded")
    print("total lang_qsweep runs:", db.scalar(
        f"select count(*) from provenance.runs where experiment='{EXP}'"))
    print("llm_run_summary rows:", db.scalar(
        f"select count(*) from provenance.llm_run_summary where run_id like '{EXP}:%'"))
    print("langcalib runs (must be untouched, 162):", db.scalar(
        "select count(*) from provenance.runs where experiment='langcalib'"))


if __name__ == "__main__":
    main()
