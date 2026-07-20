#!/usr/bin/env python3
"""K23 -- family "vllm": measured vLLM ETL detail (the only silicon ground truth).

Source: /mnt/.../vllm_trace_analysis/out/ -- ONE real H100-SXM vLLM run
(gemma4-E4B-it, multimodal), 7,817 requests, 5,252.114 s wall clock.
Everything loads under a single run_id, RUN_ID below.

  python3 load_vllm_etl.py            # load (skips files whose sha256 is unchanged)
  python3 load_vllm_etl.py --reload   # ignore ingest_log, reload everything

Also exposes load_vllm_etl(idx, reload) -> (files_loaded, rows_loaded), matching the
signature the other loaders in loaders.py use, so it can be wired into main.py.

NOT ingested, on purpose (see the notes in schema/08_vllm.sql):
  prometheus_wide.parquet    -- pure pivot of prometheus_tidy + mechanical _delta/_rate/_mean
                                (use view v_vllm_prom_wide)
  vision_cost_by_n.parquet   -- 8-row GROUP BY over vision.parquet (use v_vllm_vision_cost_by_n)
  per_request.parquet        -- already loaded by K11 into provenance.measured_request
  global_buckets' 11 hardware columns -- an as-of join against sys.parquet; only the join key
                                is kept (vllm_bucket_1s.sys_join_ts)
  model_bundle.json "fits"   -- rounded duplicates of the full-precision numbers in
                                stats/{model_mlp,model_knn,xgb_ensemble,physical_mechanistic}.json;
                                only best_models (-> is_best) and simulator (-> vllm_sim_validation)
                                are taken from it
"""
import argparse, json, math, os, re, sys
import db
import ingest_common as ic

VLLM = "/mnt/9d1dd233-5327-4660-a734-36a12ae92abd/vllm_trace_analysis"
OUT = f"{VLLM}/out"
KIND = "K23"
RUN_ID = "measured:vllm_h100_trace"

RUN = {
    "run_id": RUN_ID, "experiment": "eda", "pool": "language", "window_name": "fulltrace",
    "kind": KIND, "source_path": OUT, "gpu": "h100_sxm", "engine": "vLLM",
    "feeds": "measured/silicon chapter: vLLM execution dynamics, latency models, simulator validation",
    "config": {
        "model_name": "gemma4-E4B-it", "n_requests": 7817, "wall_clock_s": 5252.11420083046,
        "generated_tokens": 1354025, "images_encoded": 35219,
        "concurrency_cap": 16, "closed_loop": True,
        "note": ("Single real H100-SXM vLLM run. Per-request rows for the SAME physical run are "
                 "in provenance.measured_request under run_id measured:vllm_per_request (K11). "
                 "All fitted models are valid ONLY for concurrency 0..16."),
    },
}


# --------------------------------------------------------------- small helpers

def _prep(path, idx, reload):
    """None if the file should be skipped (worktree, missing, or sha unchanged)."""
    if ic.is_worktree(path) or not os.path.exists(path):
        return None
    sha, nbytes = ic.file_meta(path)
    if not reload and idx.get(path) == sha:
        return None
    return sha, nbytes


def _f(v):
    """float or None -- NaN/Inf become NULL rather than Postgres 'NaN'."""
    if v is None:
        return None
    try:
        if isinstance(v, float) and not math.isfinite(v):
            return None
    except TypeError:
        return None
    return v


def _finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _batches(path, cols, batch_size=50000):
    """Yield per-row tuples of `cols` from a parquet file, NaN-cleaned."""
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=batch_size, columns=cols):
        d = batch.to_pydict()
        m = len(d[cols[0]])
        for i in range(m):
            yield tuple(_f(d[c][i]) for c in cols)


def _copy_parquet(path, table, parquet_cols, table_cols, sha, nbytes, batch_size=50000):
    """DELETE this run's rows, stream the parquet in, log the ingest. Returns rows."""
    db.run_sql(ic.delete_for_run_sql(table, RUN_ID))
    n = db.copy_rows(table, ["run_id"] + table_cols,
                     ((RUN_ID,) + row for row in _batches(path, parquet_cols, batch_size)))
    db.run_sql(ic.ingest_sql(path, sha, KIND, n, RUN_ID, nbytes))
    return n


# ------------------------------------------------------- JSON -> tall vllm_stat

def flatten(obj, prefix=""):
    """Yield (metric_path, value) leaves. Homogeneous scalar lists stay whole."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(obj, list):
        if obj and all(not isinstance(x, (dict, list)) for x in obj):
            yield prefix, obj                       # scalar array -> value_json
        else:
            for i, v in enumerate(obj):
                yield from flatten(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def _stat_rows(source_file, facet, obj):
    out = []
    for path, v in flatten(obj):
        if not path:
            continue
        num = txt = js = None
        if isinstance(v, bool):
            num, txt = (1.0 if v else 0.0), ("true" if v else "false")
        elif isinstance(v, (int, float)):
            if math.isfinite(v):
                num = float(v)
            else:
                txt = repr(v)                        # nan / inf preserved as text
        elif isinstance(v, str):
            txt = v
        elif isinstance(v, list):
            js = v
        elif v is None:
            txt = None
        else:
            txt = str(v)
        out.append({"run_id": RUN_ID, "source_file": source_file, "facet": facet,
                    "metric_path": path, "value_num": num, "value_text": txt,
                    "value_json": js, "is_valid": True})
    return out


_STAT_COLS = ["run_id", "source_file", "facet", "metric_path", "value_num",
              "value_text", "value_json", "is_valid"]


def _write_stats(source_file, facet, obj):
    """Replace this file's stat rows. Chunked so no SQL string gets huge."""
    rows = _stat_rows(source_file, facet, obj)
    db.run_sql(f"delete from provenance.vllm_stat where run_id={ic.lit(RUN_ID)} "
               f"and source_file={ic.lit(source_file)}")
    for i in range(0, len(rows), 500):
        sql = ic.multi_upsert_sql("vllm_stat", _STAT_COLS, rows[i:i + 500],
                                  ["run_id", "source_file", "metric_path"],
                                  jsonb_cols=("value_json",))
        if sql:
            db.run_sql(sql)
    return len(rows)


# ------------------------------------------------------------ model-fit typing

# stats file -> (model label, results key, path to the results dict)
_MODEL_FILES = [
    ("model_mlp.json", "torch_mlp", "results"),
    ("model_knn.json", "cuml_knn", "results"),
    ("xgb_ensemble.json", "xgboost", "results"),
    ("physical_mechanistic.json", "physical", "targets"),
]
_FIT_COLS = ["run_id", "model", "target", "variant", "mape", "median_ape", "rmse", "r2",
             "p90_abs_err", "mean_abs_err", "n_test", "is_best", "top_features", "source_file"]


def _fit_rows(source_file, model, obj, results_key):
    """xgb stores metrics inline; mlp/knn/physical nest them under 'metrics'."""
    res = obj.get(results_key) or {}
    rows = []
    for key, r in res.items():
        if not isinstance(r, dict):
            continue
        m = r.get("metrics") if isinstance(r.get("metrics"), dict) else r
        target = r.get("target")
        variant = r.get("variant")
        if not target or not variant:                       # derive from the key
            k = key.replace("__", "_")
            for v in ("marginal", "contextual"):
                if k.endswith("_" + v):
                    variant, target = v, k[: -(len(v) + 1)]
                    break
        tf = r.get("top_features") or m.get("top_features")
        rows.append({
            "run_id": RUN_ID, "model": model, "target": target, "variant": variant,
            "mape": _f(m.get("mape")), "median_ape": _f(m.get("median_ape")),
            "rmse": _f(m.get("rmse")), "r2": _f(m.get("r2")),
            "p90_abs_err": _f(m.get("p90_abs_err")), "mean_abs_err": _f(m.get("mean_abs_err")),
            "n_test": m.get("n"), "is_best": False,
            "top_features": tf if isinstance(tf, list) else None,
            "source_file": source_file})
    return [r for r in rows if r["target"] and r["variant"]]


def _apply_best_models():
    """Set is_best from model_bundle.best_models. Runs unconditionally (cheap, idempotent)
    so a re-COPY of a fits file cannot silently drop the flag."""
    path = f"{OUT}/findings/model_bundle.json"
    if not os.path.exists(path):
        return
    best = (json.load(open(path)) or {}).get("best_models") or {}
    stmts = [f"update provenance.vllm_model_fit set is_best=false where run_id={ic.lit(RUN_ID)}"]
    for target, b in best.items():
        stmts.append(
            "update provenance.vllm_model_fit set is_best=true where "
            f"run_id={ic.lit(RUN_ID)} and target={ic.lit(target)} "
            f"and model={ic.lit(b.get('model'))} and variant='contextual'")
    db.run_sql(";\n".join(stmts))


# =============================================================== the loader

_PARQUETS = [
    # (basename, table, parquet cols, table cols)
    ("token_itl.parquet", "vllm_token_itl",
     ["request_id", "token_idx", "offset_ms", "itl_ms", "abs_ts"],
     ["request_id", "token_idx", "offset_ms", "itl_ms", "abs_ts"]),
    ("prometheus_tidy.parquet", "vllm_prom_sample",
     ["ts", "metric", "labels", "value"], ["ts", "metric", "labels", "value"]),
    ("vision.parquet", "vllm_vision_encode",
     ["ts", "num_images", "encode_ms", "ms_per_image"],
     ["ts", "num_images", "encode_ms", "ms_per_image"]),
    ("detok.parquet", "vllm_detok",
     ["ts", "calls", "tokens", "sec", "d_calls", "d_tokens", "d_sec", "us_per_token_interval"],
     ["ts", "calls", "tokens", "sec", "d_calls", "d_tokens", "d_sec", "us_per_token_interval"]),
    ("sys.parquet", "vllm_sys_sample",
     ["ts", "gpu_util_pct", "gpu_mem_util_pct", "gpu_mem_used_mib", "gpu_power_w", "gpu_temp_c",
      "gpu_sm_clock_mhz", "cpu_pct", "cpu_pct_max_core", "load1", "ram_used_mib", "ram_pct"],
     ["ts", "gpu_util_pct", "gpu_mem_util_pct", "gpu_mem_used_mib", "gpu_power_w", "gpu_temp_c",
      "gpu_sm_clock_mhz", "cpu_pct", "cpu_pct_max_core", "load1", "ram_used_mib", "ram_pct"]),
    # global_buckets: the 11 hardware cols are an as-of join against sys.parquet -> dropped;
    # only the join key `ts` survives, renamed sys_join_ts.
    ("global_buckets.parquet", "vllm_bucket_1s",
     ["t", "t_rel", "arrivals", "completions", "gen_tokens", "gen_tput_tok_s", "prompt_tokens",
      "prompt_tput_tok_s", "vision_encode_ms", "vision_images", "vision_busy_frac", "inflight", "ts"],
     ["t", "t_rel", "arrivals", "completions", "gen_tokens", "gen_tput_tok_s", "prompt_tokens",
      "prompt_tput_tok_s", "vision_encode_ms", "vision_images", "vision_busy_frac", "inflight",
      "sys_join_ts"]),
    ("stdout_engine.parquet", "vllm_engine_step",
     ["ts_local", "prompt_tput", "gen_tput", "running", "waiting", "kv_usage_pct", "prefix_hit_pct"],
     ["ts_local", "prompt_tput", "gen_tput", "running", "waiting", "kv_usage_pct", "prefix_hit_pct"]),
    ("otlp_startup.parquet", "vllm_otlp_startup",
     ["name", "start_ts", "end_ts", "duration_ms", "process_kind", "module"],
     ["span_name", "start_ts", "end_ts", "duration_ms", "process_kind", "module"]),
]

_CRITIC_CATS = [("gaps", "gap"), ("redo_needed", "redo_needed"),
                ("inconsistencies", "inconsistency"), ("headline_results", "headline_result")]
_CLAIM_REF = re.compile(r"^([a-z_]+)\s+CLAIMS?\s+(\d+)", re.I)


def load_vllm_etl(idx, reload=False):
    nf = nr = 0
    db.run_sql(ic.run_upsert_sql(RUN))

    # ---- 1. raw parquet series -------------------------------------------
    for base, table, pcols, tcols in _PARQUETS:
        path = f"{OUT}/{base}"
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        n = _copy_parquet(path, table, pcols, tcols, sha, nbytes)
        nf += 1
        nr += n
        print(f"  {base:26} -> {table:20} {n:9,d}", flush=True)

    # ---- 2. reconcile.json: 13 checks + summary block into vllm_stat ------
    path = f"{OUT}/reconcile.json"
    prep = _prep(path, idx, reload)
    if prep:
        sha, nbytes = prep
        j = json.load(open(path))
        checks = [{"run_id": RUN_ID, "check_name": c.get("name"), "level": c.get("level"),
                   "passed": c.get("pass"), "detail": c.get("detail")}
                  for c in j.get("checks", [])]
        db.run_sql(ic.delete_for_run_sql("vllm_reconcile_check", RUN_ID))
        sql = ic.multi_upsert_sql(
            "vllm_reconcile_check", ["run_id", "check_name", "level", "passed", "detail"],
            checks, ["run_id", "check_name"])
        if sql:
            db.run_sql(sql)
        ns = _write_stats("reconcile.json", "reconcile",
                          {"hard_fail": j.get("hard_fail"), "summary": j.get("summary")})
        n = len(checks) + ns
        db.run_sql(ic.ingest_sql(path, sha, KIND, n, RUN_ID, nbytes))
        nf += 1
        nr += n
        print(f"  {'reconcile.json':26} -> vllm_reconcile_check {len(checks):4d} + stats {ns:5d}",
              flush=True)

    # ---- 3. out/stats/*.json -> vllm_stat (+ typed vllm_model_fit) -------
    model_by_file = {f: (m, k) for f, m, k in _MODEL_FILES}
    stats_dir = f"{OUT}/stats"
    for base in sorted(os.listdir(stats_dir)) if os.path.isdir(stats_dir) else []:
        if not base.endswith(".json"):
            continue
        path = f"{stats_dir}/{base}"
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        j = json.load(open(path))
        n = _write_stats(base, base[:-5], j)
        if base in model_by_file:
            model, rkey = model_by_file[base]
            fits = _fit_rows(base, model, j, rkey)
            db.run_sql(f"delete from provenance.vllm_model_fit where run_id={ic.lit(RUN_ID)} "
                       f"and model={ic.lit(model)}")
            sql = ic.multi_upsert_sql("vllm_model_fit", _FIT_COLS, fits,
                                      ["run_id", "model", "target", "variant"])
            if sql:
                db.run_sql(sql)
            n += len(fits)
        db.run_sql(ic.ingest_sql(path, sha, KIND, n, RUN_ID, nbytes))
        nf += 1
        nr += n
        print(f"  stats/{base:20} -> vllm_stat            {n:9,d}", flush=True)

    # ---- 4. findings/analysis_bundle.json: facets, claims, critic --------
    path = f"{OUT}/findings/analysis_bundle.json"
    prep = _prep(path, idx, reload)
    if prep:
        sha, nbytes = prep
        j = json.load(open(path))
        facets, claims = [], []
        for f in j.get("facets", []):
            a = f.get("analysis") or {}
            v = f.get("verification") or {}
            name = f.get("facet") or a.get("facet")
            verdicts = {vd.get("claim_index"): vd for vd in v.get("verdicts", [])}
            hf = a.get("headline_findings") or []
            for i, h in enumerate(hf, 1):
                vd = verdicts.get(i, {})
                claims.append({
                    "run_id": RUN_ID, "facet": name, "claim_index": i,
                    "claim": h.get("claim"), "evidence": h.get("evidence"),
                    "confidence": h.get("confidence"), "verdict": vd.get("verdict"),
                    "verdict_note": vd.get("note"), "recomputed": vd.get("recomputed"),
                    "is_valid": True})
            vs = [vd.get("verdict") for vd in v.get("verdicts", [])]
            facets.append({
                "run_id": RUN_ID, "facet": name, "script_path": a.get("script_path"),
                "stats_json": a.get("stats_json"), "figures": a.get("figures"),
                "n_claims": len(hf), "n_confirmed": sum(1 for x in vs if x == "confirmed"),
                "n_partly": sum(1 for x in vs if x == "partly"),
                "analysis": a, "verification": v})

        notes = []
        refuted = set()
        critic = j.get("critic") or {}
        for key, cat in _CRITIC_CATS:
            for i, text in enumerate(critic.get(key) or [], 1):
                m = _CLAIM_REF.match(text or "")
                fct = m.group(1) if m else None
                cidx = int(m.group(2)) if m else None
                if cat == "redo_needed" and fct and cidx:
                    refuted.add((fct, cidx))
                notes.append({"run_id": RUN_ID, "category": cat, "note_index": i,
                              "facet": fct, "claim_index": cidx, "note": text})
        for c in claims:
            if (c["facet"], c["claim_index"]) in refuted:
                c["is_valid"] = False

        db.run_sql(";\n".join([ic.delete_for_run_sql("vllm_facet_claim", RUN_ID),
                               ic.delete_for_run_sql("vllm_critic_note", RUN_ID),
                               ic.delete_for_run_sql("vllm_facet", RUN_ID)]))
        for f in facets:                                   # one at a time: big jsonb
            db.run_sql(ic.multi_upsert_sql(
                "vllm_facet",
                ["run_id", "facet", "script_path", "stats_json", "figures", "n_claims",
                 "n_confirmed", "n_partly", "analysis", "verification"],
                [f], ["run_id", "facet"], jsonb_cols=("analysis", "verification")))
        for chunk in (claims[i:i + 20] for i in range(0, len(claims), 20)):
            db.run_sql(ic.multi_upsert_sql(
                "vllm_facet_claim",
                ["run_id", "facet", "claim_index", "claim", "evidence", "confidence",
                 "verdict", "verdict_note", "recomputed", "is_valid"],
                chunk, ["run_id", "facet", "claim_index"]))
        for chunk in (notes[i:i + 20] for i in range(0, len(notes), 20)):
            db.run_sql(ic.multi_upsert_sql(
                "vllm_critic_note",
                ["run_id", "category", "note_index", "facet", "claim_index", "note"],
                chunk, ["run_id", "category", "note_index"]))
        n = len(facets) + len(claims) + len(notes)
        db.run_sql(ic.ingest_sql(path, sha, KIND, n, RUN_ID, nbytes))
        nf += 1
        nr += n
        print(f"  findings/analysis_bundle.json -> facets {len(facets)} claims {len(claims)} "
              f"(invalid {len(refuted)}) critic {len(notes)}", flush=True)

    # ---- 5. findings/model_bundle.json: simulator validation only --------
    path = f"{OUT}/findings/model_bundle.json"
    prep = _prep(path, idx, reload)
    if prep:
        sha, nbytes = prep
        j = json.load(open(path))
        vm = ((j.get("simulator") or {}).get("validation_metrics") or {})
        sim = [dict({"run_id": RUN_ID, "metric": k},
                    **{c: _f(v.get(c)) for c in
                       ("median_actual", "median_sim", "median_ape_pct", "p95_actual",
                        "p95_sim", "p95_ape_pct", "per_request_mape_pct", "ks_stat")})
               for k, v in vm.items()]
        db.run_sql(ic.delete_for_run_sql("vllm_sim_validation", RUN_ID))
        sql = ic.multi_upsert_sql(
            "vllm_sim_validation",
            ["run_id", "metric", "median_actual", "median_sim", "median_ape_pct", "p95_actual",
             "p95_sim", "p95_ape_pct", "per_request_mape_pct", "ks_stat"],
            sim, ["run_id", "metric"])
        if sql:
            db.run_sql(sql)
        # simulator scope/valid_ranges/api kept as stats; "fits" deliberately NOT ingested
        # (rounded duplicates of the full-precision stats/*.json numbers already loaded).
        ns = _write_stats("model_bundle.json", "model_bundle",
                          {"simulator": {k: v for k, v in (j.get("simulator") or {}).items()
                                         if k != "validation_metrics"},
                           "best_models": j.get("best_models")})
        n = len(sim) + ns
        db.run_sql(ic.ingest_sql(path, sha, KIND, n, RUN_ID, nbytes))
        nf += 1
        nr += n
        print(f"  findings/model_bundle.json -> sim_validation {len(sim)} + stats {ns}", flush=True)

    _apply_best_models()
    return nf, nr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reload", action="store_true")
    a = ap.parse_args()
    idx = ic.load_ingest_index()
    nf, nr = load_vllm_etl(idx, a.reload)
    print(f"[{KIND}  vllm_etl] files={nf} rows={nr:,}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
