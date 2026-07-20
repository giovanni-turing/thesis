#!/usr/bin/env python3
"""K21 -- collector / AIC silicon validation family.

Ingests /home/gio/tese/collector_artifacts/ (phase0..phase9, phaseA..phaseE): the
aiconfigurator cost model measured against a real RTX 5090 running the Qwen3-VL-8B
vision tower. Backs tex/aiconfigurator.tex (Ch.5).

Tables: see provenance/schema/06_collector.sql.

Run standalone:   cd /home/gio/tese/provenance/loader && python3 load_collector_silicon.py
Or from main.py:  load_collector_silicon(idx, reload) -> (files_loaded, rows_loaded)

Idempotency: every file is recorded in provenance.ingest_log with kind 'K21'; a file whose
sha256 is unchanged is skipped. Re-running loads 0 rows.

DELIBERATE EXCLUSIONS (see EXCLUDED_NOTES at the bottom of this file for the reasons).
"""
import csv as _csv
import glob
import json
import os

import db
import ingest_common as ic

COLL = "/home/gio/tese/collector_artifacts"
E = f"{COLL}/phaseE_physical_anchor"
KIND = "K21"

# 'compile' (anchor_master.json) and 'compiled' (burst_anchor_all.json) are the same
# engine -- torch.compile. Normalized to 'compiled' everywhere in the DB.
ENGINE_NORM = {"compile": "compiled", "compiled": "compiled", "aic": "aic",
               "vllm": "vllm", "eager": "eager"}


def norm_engine(e):
    return ENGINE_NORM.get(e, e)


def _prep(path, idx, reload):
    """None if the file should be skipped (missing / worktree / unchanged sha)."""
    if not os.path.exists(path) or ic.is_worktree(path):
        return None
    sha, nbytes = ic.file_meta(path)
    if not reload and idx.get(path) == sha:
        return None
    return sha, nbytes


def _phase_of(path):
    rel = os.path.relpath(path, COLL)
    return rel.split(os.sep)[0] if os.sep in rel else "root"


def _f(v):
    return None if v is None else float(v)


def _i(v):
    return None if v is None else int(v)


# --------------------------------------------------------------- SQL emitters
BENCH_COLS = ["source_path", "family", "phase", "experiment", "attn_requested", "attn_used",
              "engine", "model_dir", "n_params", "load_s", "nruns", "iters", "warmup",
              "image_px", "grid_n", "aic_reference_csv", "clocks_locked", "clock_lock_note",
              "gpu_name", "sm_clock_mhz", "sm_clock_before", "sm_clock_after",
              "max_sm_clock_mhz", "power_w_before", "power_w_after", "temp_c_before",
              "temp_c_after", "throttle_hex_after", "mem_used_mib_after", "torch_version",
              "cuda_version", "python_version", "ratio_min", "ratio_max", "ratio_mean",
              "ratio_spread_pct", "ts", "is_valid", "invalid_reason", "raw"]

FN_COLS = ["source_path", "engine", "attn", "image_px", "n_images", "patches",
           "post_merge_tokens", "mean_ms", "ci95_ms", "p50_ms", "p99_ms", "min_ms",
           "ms_per_img", "peak_mem_gb", "sm_clock_mhz", "aic_pred_ms",
           "ratio_meas_over_aic", "speedup_over_eager", "is_valid", "note", "raw"]


def bench_sql(row):
    return ic.multi_upsert_sql("collector_bench_run", BENCH_COLS, [row], "source_path",
                               jsonb_cols=("raw",))


def fn_sql(rows):
    return ic.multi_upsert_sql("collector_encoder_fn", FN_COLS, rows,
                               ["source_path", "engine", "image_px", "n_images"],
                               jsonb_cols=("raw",))


def scalar_sql(rows):
    return ic.multi_upsert_sql("collector_scalar",
                               ["source_path", "scope", "metric", "value_num", "value_text"],
                               rows, ["source_path", "scope", "metric"])


def sc(path, scope, metric, v):
    """Build one collector_scalar row from an arbitrary JSON leaf."""
    if isinstance(v, bool):
        return {"source_path": path, "scope": scope, "metric": metric,
                "value_num": 1.0 if v else 0.0, "value_text": str(v).lower()}
    if isinstance(v, (int, float)):
        return {"source_path": path, "scope": scope, "metric": metric,
                "value_num": float(v), "value_text": repr(v)}
    return {"source_path": path, "scope": scope, "metric": metric,
            "value_num": None, "value_text": json.dumps(v) if isinstance(v, (list, dict)) else str(v)}


def _emit(path, sha, nbytes, stmts, nrows):
    stmts = [s for s in stmts if s]
    stmts.append(ic.ingest_sql(path, sha, KIND, nrows, None, nbytes))
    db.run_sql(";\n".join(stmts))
    return nrows


# =========================================================== anchor_*.json bench
def _gpu_bench_row(path, j, family, engine=None, is_valid=True, invalid_reason=None):
    gb, ga = j.get("gpu_state_before") or {}, j.get("gpu_state_after") or {}
    pr = j.get("protocol") or {}
    rs = j.get("ratio_summary") or {}
    header = {k: v for k, v in j.items() if k not in ("rows", "results")}
    return {
        "source_path": path, "family": family, "phase": _phase_of(path),
        "experiment": j.get("experiment"), "attn_requested": j.get("attn_requested"),
        "attn_used": j.get("attn_used") or j.get("attn"), "engine": engine,
        "model_dir": j.get("model_dir"), "n_params": _i(j.get("n_params")),
        "load_s": _f(j.get("load_s")), "nruns": _i(pr.get("nruns")),
        "iters": _i(pr.get("iters")), "warmup": _i(pr.get("warmup")),
        "image_px": _i(pr.get("image_px") or j.get("px")), "grid_n": _i(pr.get("grid")),
        "aic_reference_csv": j.get("aic_reference_csv"),
        "clocks_locked": j.get("clocks_locked"), "clock_lock_note": j.get("clock_lock_note"),
        "gpu_name": gb.get("name") or ga.get("name"),
        "sm_clock_mhz": _i(j.get("sm_clock_mhz") or j.get("sm_mhz") or j.get("clock_mhz")
                           or j.get("sm_clock")),
        "sm_clock_before": _i(gb.get("sm_clock_mhz")), "sm_clock_after": _i(ga.get("sm_clock_mhz")),
        "max_sm_clock_mhz": _i(gb.get("max_sm_clock_mhz")),
        "power_w_before": _f(gb.get("power_w")), "power_w_after": _f(ga.get("power_w")),
        "temp_c_before": _i(gb.get("temp_c")), "temp_c_after": _i(ga.get("temp_c")),
        "throttle_hex_after": ga.get("throttle_hex"),
        "mem_used_mib_after": _i(ga.get("mem_used_mib")),
        "torch_version": j.get("torch"), "cuda_version": j.get("cuda"),
        "python_version": j.get("python"),
        "ratio_min": _f(rs.get("min")), "ratio_max": _f(rs.get("max")),
        "ratio_mean": _f(rs.get("mean")), "ratio_spread_pct": _f(rs.get("spread_pct")),
        "ts": j.get("timestamp_utc"), "is_valid": is_valid,
        "invalid_reason": invalid_reason, "raw": header}


def load_anchor_bench(path, sha, nbytes):
    """anchor_{sdpa_5x50,flash_attention_2_5x50,sdpa_locked2400,dense_sdpa_2400}.json"""
    j = json.load(open(path))
    engine = j.get("attn_used")
    px = (j.get("protocol") or {}).get("image_px")
    fn = []
    for r in j["rows"]:
        fn.append({
            "source_path": path, "engine": engine, "attn": engine, "image_px": _i(px),
            "n_images": _i(r["n_images"]), "patches": _i(r.get("patches")),
            "post_merge_tokens": _i(r.get("post_merge_tokens")),
            "mean_ms": _f(r.get("mean_ms")), "ci95_ms": _f(r.get("ci95_ms")),
            "p50_ms": _f(r.get("p50_ms")), "p99_ms": _f(r.get("p99_ms")),
            "min_ms": _f(r.get("min_ms")), "ms_per_img": _f(r.get("ms_per_img")),
            "peak_mem_gb": _f(r.get("peak_mem_gb")), "sm_clock_mhz": _i(r.get("sm_clock_mhz")),
            "aic_pred_ms": _f(r.get("aic_pred_ms")),
            "ratio_meas_over_aic": _f(r.get("ratio_meas_over_pred")),
            "speedup_over_eager": None, "is_valid": True, "note": None, "raw": r})
    return _emit(path, sha, nbytes,
                 [bench_sql(_gpu_bench_row(path, j, "anchor", engine)), fn_sql(fn)],
                 1 + len(fn))


# ============================================================== anchor_master
def load_anchor_master(path, sha, nbytes):
    j = json.load(open(path))
    clock, sla = _i(j.get("clock_mhz")), _f(j.get("sla_ms"))
    f64, over = j.get("f64_ms") or {}, j.get("f64_over_aic") or {}
    geo = j.get("geomean") or {}
    eng_rows = []
    for raw_e, ms in f64.items():
        e = norm_engine(raw_e)
        eng_rows.append({
            "source_path": path, "engine": e, "clock_mhz": clock, "sla_ms": sla,
            "f64_ms": _f(ms),
            "f64_over_aic": 1.0 if raw_e == "aic" else _f(over.get(raw_e)),
            "geo_w1_ratio": _f(geo.get(f"w1_ratio_{raw_e}")),
            "geo_inflation": _f(geo.get(f"inflation_{raw_e}"))})
    win_rows = []
    for wname, w in (j.get("windows") or {}).items():
        for raw_e in ("aic", "vllm", "eager", "compile"):
            d = w.get(raw_e)
            if not d:
                continue
            e = norm_engine(raw_e)
            win_rows.append({
                "source_path": path, "window_name": wname, "engine": e,
                "images": _i(w.get("images")), "n_image_reqs": _i(w.get("n_image_reqs")),
                "w1_p99_ms": _f(d.get("w1_p99_ms")), "cstar": _i(d.get("cstar")),
                "gate": d.get("gate"), "p99_at_aic_cstar": _f(d.get("p99_at_aic_cstar")),
                "w1_ratio_over_aic": 1.0 if raw_e == "aic" else _f(w.get(f"w1_ratio_{raw_e}")),
                "inflation_over_aic": 1.0 if raw_e == "aic" else _f(w.get(f"inflation_{raw_e}"))})
    scal = [sc(path, "file", "sweep_n_grid", j.get("sweep")),
            sc(path, "file", "sla_ms", sla), sc(path, "file", "clock_mhz", clock)]
    stmts = [bench_sql(_gpu_bench_row(path, {"sm_clock_mhz": clock, "experiment": "anchor_master"},
                                      "anchor_master")),
             ic.multi_upsert_sql("collector_anchor_engine",
                                 ["source_path", "engine", "clock_mhz", "sla_ms", "f64_ms",
                                  "f64_over_aic", "geo_w1_ratio", "geo_inflation"],
                                 eng_rows, ["source_path", "engine"]),
             ic.multi_upsert_sql("collector_anchor_window_engine",
                                 ["source_path", "window_name", "engine", "images",
                                  "n_image_reqs", "w1_p99_ms", "cstar", "gate",
                                  "p99_at_aic_cstar", "w1_ratio_over_aic", "inflation_over_aic"],
                                 win_rows, ["source_path", "window_name", "engine"]),
            scalar_sql(scal)]
    return _emit(path, sha, nbytes, stmts, 1 + len(eng_rows) + len(win_rows) + len(scal))


# =========================================================== burst_anchor_all
def load_burst_anchor_all(path, sha, nbytes):
    j = json.load(open(path))
    smhz = _i(j.get("sm_clock_mhz"))
    lat = []
    for wname, w in (j.get("windows") or {}).items():
        for raw_e in ("aic", "eager", "compiled", "compile", "vllm"):
            d = w.get(raw_e)
            if not isinstance(d, dict):
                continue
            lat.append({
                "source_path": path, "window_name": wname, "engine": norm_engine(raw_e),
                "n_reqs": _i(w.get("n_reqs")), "images": _i(w.get("images")),
                "p50_ms": _f(d.get("p50")), "p90_ms": _f(d.get("p90")),
                "p99_ms": _f(d.get("p99")), "max_ms": _f(d.get("max")),
                "busy_s": _f(d.get("busy_s")), "p99_over_aic": _f(d.get("p99_over_aic")),
                "sm_clock_mhz": smhz})
    fn = []
    for key, eng in (("fn_eager", "eager"), ("fn_compiled", "compiled")):
        for n, ms in (j.get(key) or {}).items():
            fn.append({"source_path": path, "engine": eng, "attn": None, "image_px": 448,
                       "n_images": int(n), "mean_ms": _f(ms), "sm_clock_mhz": smhz,
                       "ms_per_img": _f(ms) / int(n), "is_valid": True,
                       "note": f"encoder cost curve driving the {eng} replay arm",
                       "raw": {"n": int(n), "ms": ms}})
    stmts = [bench_sql(_gpu_bench_row(path, {"sm_clock_mhz": smhz,
                                             "experiment": "burst_anchor_all"}, "burst_anchor")),
             ic.multi_upsert_sql("collector_burst_anchor_latency",
                                 ["source_path", "window_name", "engine", "n_reqs", "images",
                                  "p50_ms", "p90_ms", "p99_ms", "max_ms", "busy_s",
                                  "p99_over_aic", "sm_clock_mhz"], lat,
                                 ["source_path", "window_name", "engine"]),
             fn_sql(fn)]
    return _emit(path, sha, nbytes, stmts, 1 + len(lat) + len(fn))


# ================================================================== multires
def load_fn_multires(path, sha, nbytes):
    """fn_multires.json: measured eager/compiled f(N) at 3 resolutions."""
    j = json.load(open(path))
    smhz = _i(j.get("sm_mhz"))
    fn = []
    for raw_e in ("eager", "compiled"):
        for res, curve in (j.get(raw_e) or {}).items():
            for n, ms in curve.items():
                fn.append({"source_path": path, "engine": norm_engine(raw_e), "attn": None,
                           "image_px": int(res), "n_images": int(n), "mean_ms": _f(ms),
                           "ms_per_img": _f(ms) / int(n), "sm_clock_mhz": smhz,
                           "is_valid": True, "raw": {"n": int(n), "ms": ms, "res": int(res)}})
    stmts = [bench_sql(_gpu_bench_row(path, {"sm_clock_mhz": smhz, "experiment": "fn_multires"},
                                      "fn")),
             fn_sql(fn),
             scalar_sql([sc(path, "file", "grid_n", j.get("grid_n")),
                         sc(path, "file", "res_grid", j.get("res"))])]
    return _emit(path, sha, nbytes, stmts, 1 + len(fn) + 2)


def load_aic_multires(path, sha, nbytes):
    """aic_multires.json: the AIC-predicted counterpart of fn_multires (same shape, unwrapped)."""
    j = json.load(open(path))
    fn = []
    for res, curve in j.items():
        for n, ms in curve.items():
            fn.append({"source_path": path, "engine": "aic", "attn": None,
                       "image_px": int(res), "n_images": int(n), "mean_ms": _f(ms),
                       "ms_per_img": _f(ms) / int(n), "is_valid": True,
                       "note": "aiconfigurator analytic prediction, not a measurement",
                       "raw": {"n": int(n), "ms": ms, "res": int(res)}})
    stmts = [bench_sql(_gpu_bench_row(path, {"experiment": "aic_multires"}, "fn", "aic")),
             fn_sql(fn)]
    return _emit(path, sha, nbytes, stmts, 1 + len(fn))


def load_fn_repro(path, sha, nbytes):
    """fn_repro.json: independent re-measurement of the eager/compiled curves with CIs."""
    j = json.load(open(path))
    fn = []
    for raw_e in ("eager", "compiled"):
        for n, d in (j.get(raw_e) or {}).items():
            fn.append({"source_path": path, "engine": norm_engine(raw_e), "attn": None,
                       "image_px": 448, "n_images": int(n), "mean_ms": _f(d.get("ms")),
                       "ci95_ms": _f(d.get("ci95")), "ms_per_img": _f(d.get("ms")) / int(n),
                       "sm_clock_mhz": _i(d.get("sm_mhz")), "is_valid": True,
                       "note": "reproduction run", "raw": d})
    stmts = [bench_sql(_gpu_bench_row(path, {"experiment": "fn_repro"}, "fn")), fn_sql(fn)]
    return _emit(path, sha, nbytes, stmts, 1 + len(fn))


def load_fn_contended_invalid(path, sha, nbytes):
    """fn_silicon_CONTENDED_INVALID.json -- SUPERSEDED/INVALID: GPU was shared during the run.

    Ingested only with is_valid=false so it can be audited but never quoted as an anchor.
    """
    j = json.load(open(path))
    reason = j.get("invalid_note") or "contended run"
    eng = j.get("attn")
    fn = []
    for r in j.get("rows") or []:
        fn.append({"source_path": path, "engine": eng, "attn": eng,
                   "image_px": _i(j.get("px")), "n_images": _i(r.get("N")),
                   "mean_ms": _f(r.get("meas_ms")), "ci95_ms": _f(r.get("ci95_ms")),
                   "ms_per_img": _f(r.get("meas_ms")) / int(r["N"]),
                   "aic_pred_ms": _f(r.get("aic_ms")),
                   "ratio_meas_over_aic": _f(r.get("ratio_meas_over_aic")),
                   "is_valid": False, "note": reason, "raw": r})
    scal = [sc(path, "file", k, j.get(k)) for k in
            ("ratio_mean", "ratio_min", "ratio_max", "clocks_locked", "clocks_mhz_observed",
             "note", "invalid_note")]
    stmts = [bench_sql(_gpu_bench_row(path, j, "fn", eng, is_valid=False, invalid_reason=reason)),
             fn_sql(fn), scalar_sql(scal)]
    return _emit(path, sha, nbytes, stmts, 1 + len(fn) + len(scal))


# ================================================================ vLLM engine
def load_vllm_dense(path, sha, nbytes):
    """vllm_eager_dense.json / vllm_multires.json: vLLM ViT path, rows keyed by N or '<px>x<N>'."""
    j = json.load(open(path))
    px_default = (j.get("protocol") or {}).get("image_px")
    fn = []
    for key, r in (j.get("rows") or {}).items():
        px = _i(r.get("image_px") or px_default)
        n = _i(r.get("N")) if r.get("N") is not None else int(key)
        fn.append({"source_path": path, "engine": "vllm", "attn": j.get("attn_backend"),
                   "image_px": px, "n_images": n, "mean_ms": _f(r.get("mean_ms")),
                   "ci95_ms": _f(r.get("ci95_ms")), "p50_ms": _f(r.get("p50_ms")),
                   "min_ms": _f(r.get("min_ms")), "ms_per_img": _f(r.get("ms_per_img")),
                   "sm_clock_mhz": _i(r.get("sm_clock_mhz")), "is_valid": True, "raw": r})
    hdr = dict(j)
    hdr.pop("rows", None)
    hdr["attn_used"] = j.get("attn_backend")
    stmts = [bench_sql(_gpu_bench_row(path, hdr, "vllm", "vllm")), fn_sql(fn),
             scalar_sql([sc(path, "file", "ci_method", j.get("ci_method"))])]
    return _emit(path, sha, nbytes, stmts, 1 + len(fn) + 1)


def load_vllm_eager_vit(path, sha, nbytes):
    """vllm_eager_vit.json: results{N: {vllm_eager_ms, p50}}."""
    j = json.load(open(path))
    smhz = _i(j.get("sm_clock"))
    fn = [{"source_path": path, "engine": "vllm", "attn": j.get("attn_backend"),
           "image_px": 448, "n_images": int(n), "mean_ms": _f(d.get("vllm_eager_ms")),
           "p50_ms": _f(d.get("p50")), "ms_per_img": _f(d.get("vllm_eager_ms")) / int(n),
           "sm_clock_mhz": smhz, "is_valid": True, "raw": d}
          for n, d in (j.get("results") or {}).items()]
    hdr = {"sm_clock": smhz, "attn_used": j.get("attn_backend"), "experiment": "vllm_eager_vit"}
    stmts = [bench_sql(_gpu_bench_row(path, hdr, "vllm", "vllm")), fn_sql(fn)]
    return _emit(path, sha, nbytes, stmts, 1 + len(fn))


# ========================================================== torch.compile runs
def load_vit_compile(path, sha, nbytes):
    """vit_compile.json: {N: {eager_ms, compiled_ms, speedup}}."""
    j = json.load(open(path))
    fn = []
    for n, d in j.items():
        ni = int(n)
        fn.append({"source_path": path, "engine": "eager", "image_px": 448, "n_images": ni,
                   "mean_ms": _f(d.get("eager_ms")), "ms_per_img": _f(d.get("eager_ms")) / ni,
                   "is_valid": True, "raw": d})
        fn.append({"source_path": path, "engine": "compiled", "image_px": 448, "n_images": ni,
                   "mean_ms": _f(d.get("compiled_ms")),
                   "ms_per_img": _f(d.get("compiled_ms")) / ni,
                   "speedup_over_eager": _f(d.get("speedup")), "is_valid": True, "raw": d})
    stmts = [bench_sql(_gpu_bench_row(path, {"experiment": "vit_compile"}, "compile")), fn_sql(fn)]
    return _emit(path, sha, nbytes, stmts, 1 + len(fn))


def load_vit_compile_curve(path, sha, nbytes):
    """vit_compile_dense.json {N:{compiled_ms,ci95}} and vit_compile_sweep.json {N: ms}."""
    j = json.load(open(path))
    fn = []
    for n, d in j.items():
        ni = int(n)
        ms = _f(d.get("compiled_ms")) if isinstance(d, dict) else _f(d)
        ci = _f(d.get("ci95")) if isinstance(d, dict) else None
        fn.append({"source_path": path, "engine": "compiled", "image_px": 448, "n_images": ni,
                   "mean_ms": ms, "ci95_ms": ci, "ms_per_img": ms / ni, "is_valid": True,
                   "raw": d if isinstance(d, dict) else {"compiled_ms": d}})
    exp = os.path.basename(path).replace(".json", "")
    stmts = [bench_sql(_gpu_bench_row(path, {"experiment": exp}, "compile", "compiled")),
             fn_sql(fn)]
    return _emit(path, sha, nbytes, stmts, 1 + len(fn))


# ============================================================ operator profile
def load_vit_op_profile(path, sha, nbytes):
    j = json.load(open(path))
    fine = "sum_ops_ms" in next(iter(j.values()))
    level = "fine" if fine else "coarse"
    tot_key = "sum_ops_ms" if fine else "total_ms"
    rows = []
    for n, d in j.items():
        total = _f(d.get(tot_key))
        for op, ms in d.items():
            if op == tot_key:
                continue
            rows.append({"source_path": path, "n_images": int(n), "op_name": op,
                         "ms": _f(ms), "total_ms": total,
                         "share": (_f(ms) / total) if total else None,
                         "profile_level": level})
    stmts = [bench_sql(_gpu_bench_row(path, {"experiment": os.path.basename(path)}, "opprofile")),
             ic.multi_upsert_sql("collector_vit_op_breakdown",
                                 ["source_path", "n_images", "op_name", "ms", "total_ms",
                                  "share", "profile_level"], rows,
                                 ["source_path", "n_images", "op_name"])]
    return _emit(path, sha, nbytes, stmts, 1 + len(rows))


# ============================================================ closed loop / MW
def load_silicon_closedloop(path, sha, nbytes):
    j = json.load(open(path))
    rows = [{"source_path": path, "window_name": w, "policy": j.get("policy"),
             "sla_ms": _f(j.get("sla_ms")), "static_c": _i(j.get("static_C")),
             "fc_worker_s": _f(d.get("fc_worker_s")),
             "static_worker_s": _f(d.get("static_worker_s")), "ratio": _f(d.get("ratio")),
             "aic_p99_ms": _f(d.get("aic_p99")), "aic_feasible": d.get("aic_feasible"),
             "silicon_p99_ms": _f(d.get("silicon_p99")),
             "silicon_feasible": d.get("silicon_feasible"),
             "sched_peak": _i(d.get("sched_peak"))}
            for w, d in (j.get("windows") or {}).items()]
    scal = [sc(path, "file", "aggregate_ratio_over_windows", j.get("aggregate_ratio_over_windows")),
            sc(path, "file", "all_silicon_feasible", j.get("all_silicon_feasible")),
            sc(path, "file", "policy", j.get("policy")),
            sc(path, "file", "static_C", j.get("static_C"))]
    stmts = [ic.multi_upsert_sql("collector_closedloop_window",
                                 ["source_path", "window_name", "policy", "sla_ms", "static_c",
                                  "fc_worker_s", "static_worker_s", "ratio", "aic_p99_ms",
                                  "aic_feasible", "silicon_p99_ms", "silicon_feasible",
                                  "sched_peak"], rows, ["source_path", "window_name"]),
             scalar_sql(scal)]
    return _emit(path, sha, nbytes, stmts, len(rows) + len(scal))


def load_silicon_multiworker(path, sha, nbytes):
    j = json.load(open(path))
    sla = _f(j.get("sla_ms"))
    wrows, prows = [], []
    for w, d in (j.get("windows") or {}).items():
        wrows.append({"source_path": path, "window_name": w, "sla_ms": sla,
                      "trace_offset": _i(d.get("offset")),
                      "max_requests": _i(d.get("max_requests")),
                      "n_image_reqs": _i(d.get("n_image_reqs")),
                      "total_images": _i(d.get("total_images")),
                      "grid_cstar_reported": _i(d.get("grid_cstar_reported")),
                      "aic_feasible_cstar": _i(d.get("aic_feasible_cstar")),
                      "silicon_feasible_cstar": _i(d.get("silicon_feasible_cstar")),
                      "aic_reproduces_grid": d.get("aic_reproduces_grid"),
                      "worker_inflation_x": _f(d.get("worker_inflation_x")),
                      "silicon_p99_at_aic_cstar": _f(d.get("silicon_p99_at_aic_cstar")),
                      "canonical_fn_source": j.get("canonical_fn_source")})
        for arm, key in (("aic", "aic_p99_by_W"), ("silicon", "silicon_p99_by_W")):
            for nw, pd in (d.get(key) or {}).items():
                prows.append({"source_path": path, "window_name": w, "arm": arm,
                              "n_workers": int(nw), "p99_ms": _f(pd.get("p99")),
                              "divergent": pd.get("div")})
    amp = j.get("single_worker_amplification") or {}
    scal = [sc(path, "file", "sla_ms", sla), sc(path, "file", "sweep_w_grid", j.get("sweep")),
            sc(path, "file", "canonical_fn_source", j.get("canonical_fn_source")),
            sc(path, "file", "single_worker_amplification_range", amp.get("range")),
            sc(path, "file", "single_worker_amplification_note", amp.get("note"))]
    stmts = [ic.multi_upsert_sql("collector_multiworker_window",
                                 ["source_path", "window_name", "sla_ms", "trace_offset",
                                  "max_requests", "n_image_reqs", "total_images",
                                  "grid_cstar_reported", "aic_feasible_cstar",
                                  "silicon_feasible_cstar", "aic_reproduces_grid",
                                  "worker_inflation_x", "silicon_p99_at_aic_cstar",
                                  "canonical_fn_source"], wrows,
                                 ["source_path", "window_name"]),
             ic.multi_upsert_sql("collector_multiworker_p99",
                                 ["source_path", "window_name", "arm", "n_workers", "p99_ms",
                                  "divergent"], prows,
                                 ["source_path", "window_name", "arm", "n_workers"]),
             scalar_sql(scal)]
    return _emit(path, sha, nbytes, stmts, len(wrows) + len(prows) + len(scal))


# ==================================================================== replays
def load_burst_fifo_replay(path, sha, nbytes):
    j = json.load(open(path))
    base = {"source_path": path, "window_name": j.get("window"),
            "n_image_reqs": _i(j.get("n_image_reqs")),
            "total_images": _i(j.get("total_images")), "horizon_s": _f(j.get("horizon_s")),
            "n_workers": _i(j.get("workers")), "cap": _i(j.get("cap")),
            "attn": j.get("attn_used")}
    rows = []
    for arm, key, f64 in (("aic", "replay_aic", j.get("f64_aic_ms")),
                          ("measured", "replay_measured", j.get("f64_measured_ms"))):
        d = j.get(key) or {}
        ed = d.get("encoder_delay_ms") or {}
        rows.append({**base, "arm": arm, "f64_ms": _f(f64), "p50_ms": _f(ed.get("p50")),
                     "p90_ms": _f(ed.get("p90")), "p99_ms": _f(ed.get("p99")),
                     "max_ms": _f(ed.get("max")), "busy_s": _f(d.get("busy_s"))})
    ref = j.get("sim_reference_encoder_delay_ms") or {}
    if ref:
        rows.append({**base, "arm": "sim_reference", "p50_ms": _f(ref.get("p50")),
                     "p90_ms": _f(ref.get("p90")), "p99_ms": _f(ref.get("p99")),
                     "max_ms": _f(ref.get("max"))})
    stmts = [_replay_sql(rows)]
    return _emit(path, sha, nbytes, stmts, len(rows))


def load_oneworker_silicon(path, sha, nbytes):
    """oneworker_artifact/silicon_burst{3,5}.json: silicon-vs-AIC single-worker replay + f(N)."""
    j = json.load(open(path))
    base = {"source_path": path, "window_name": j.get("window"),
            "n_image_reqs": _i(j.get("n_image_reqs")),
            "total_images": _i(j.get("total_images")), "n_workers": 1,
            "cap": _i(j.get("cap")), "attn": j.get("attn"),
            "sm_clock_mhz": _i(j.get("sm_clock_mhz"))}
    rows = []
    for arm, key, vkey, fnkey in (("silicon", "silicon_encoder_delay_ms", "verdict_silicon",
                                   "measured_fn"),
                                  ("aic", "aic_sim_encoder_delay_ms", "verdict_aic", "aic_fn")):
        d = j.get(key) or {}
        rows.append({**base, "arm": arm, "p50_ms": _f(d.get("p50")), "p90_ms": _f(d.get("p90")),
                     "p99_ms": _f(d.get("p99")), "max_ms": _f(d.get("max")),
                     "busy_s": _f(d.get("busy_s")), "verdict": j.get(vkey),
                     "f64_ms": _f((j.get(fnkey) or {}).get("64")),
                     "p99_ratio_over_aic": _f(j.get("p99_ratio_silicon_over_aic"))
                     if arm == "silicon" else 1.0})
    fn = []
    for fnkey, eng in (("measured_fn", j.get("attn") or "sdpa"), ("aic_fn", "aic")):
        for n, ms in (j.get(fnkey) or {}).items():
            fn.append({"source_path": path, "engine": eng,
                       "attn": j.get("attn") if fnkey == "measured_fn" else None,
                       "image_px": 448, "n_images": int(n), "mean_ms": _f(ms),
                       "ms_per_img": _f(ms) / int(n),
                       "sm_clock_mhz": _i(j.get("sm_clock_mhz")), "is_valid": True,
                       "note": j.get("note"), "raw": {"n": int(n), "ms": ms}})
    stmts = [_replay_sql(rows), fn_sql(fn),
             scalar_sql([sc(path, "file", "p99_ratio_silicon_over_aic",
                            j.get("p99_ratio_silicon_over_aic"))])]
    return _emit(path, sha, nbytes, stmts, len(rows) + len(fn) + 1)


def _replay_sql(rows):
    return ic.multi_upsert_sql("collector_replay_window",
                               ["source_path", "window_name", "arm", "n_image_reqs",
                                "total_images", "horizon_s", "n_workers", "cap", "attn",
                                "sm_clock_mhz", "f64_ms", "p50_ms", "p90_ms", "p99_ms",
                                "max_ms", "busy_s", "p99_ratio_over_aic", "verdict"], rows,
                               ["source_path", "window_name", "arm"])


# ============================================================ encoder sim stats
def _pct(j, field, p):
    return _f((j.get(field) or {}).get(p))


def load_encoder_stats_file(path, sha, nbytes):
    j = json.load(open(path))
    base = os.path.basename(path).replace(".stats.json", "")
    scenario, _, arm = base.partition("_ctrl_") if "_ctrl_" in base else base.partition("_treatment_")
    arm = ("ctrl_" if "_ctrl_" in base else "treatment_") + arm
    row = {"source_path": path, "arm": arm, "scenario": scenario,
           "requests": _i(j.get("requests")),
           "requests_with_images": _i(j.get("requests_with_images")),
           "total_images": _i(j.get("total_images")), "image_px": _i(j.get("image_px")),
           "encoder_workers": _i(j.get("encoder_workers")),
           "encoder_batch_images": _i(j.get("encoder_batch_images")),
           "text_only_fraction": _f(j.get("text_only_fraction")),
           "encoder_delay_p50_ms": _pct(j, "encoder_delay_ms", "p50"),
           "encoder_delay_p90_ms": _pct(j, "encoder_delay_ms", "p90"),
           "encoder_delay_p99_ms": _pct(j, "encoder_delay_ms", "p99"),
           "encoder_delay_max_ms": _pct(j, "encoder_delay_ms", "max"),
           "encoder_service_p99_ms": _pct(j, "encoder_service_ms", "p99"),
           "handoff_p99_ms": _pct(j, "handoff_ms", "p99"),
           "provisioned_worker_seconds": _f(j.get("provisioned_worker_seconds")),
           "busy_worker_seconds": _f(j.get("busy_worker_seconds")),
           "encoder_utilization": _f(j.get("encoder_utilization")),
           "sim_horizon_s": _f(j.get("sim_horizon_s")),
           "mean_images_per_s": _f(j.get("mean_images_per_s")),
           "offered_img_per_s": _f(j.get("offered_img_per_s")),
           "batches": _i(j.get("batches")), "encoder_forwards": _i(j.get("encoder_forwards")),
           "requests_chunked": _i(j.get("requests_chunked")),
           "service_memo_hits": _i(j.get("service_memo_hits")),
           "distinct_service_sizes_costed": _i(j.get("distinct_service_sizes_costed")),
           "queue_divergent": j.get("queue_divergent"),
           "has_worker_schedule": j.get("worker_schedule") is not None,
           "metrics": j}
    stmts = [ic.multi_upsert_sql("collector_encoder_stats", list(row), [row], "source_path",
                                 jsonb_cols=("metrics",))]
    return _emit(path, sha, nbytes, stmts, 1)


# ================================================================ kernel ledger
def load_kernel_ledger(path, sha, nbytes):
    j = json.load(open(path))
    n = _i(j.get("n_images"))
    tot = _f(j.get("total_kernel_ms"))
    rows = [{"source_path": path, "n_images": n, "entry_kind": "category", "entry_name": k,
             "ms": _f(v), "total_kernel_ms": tot}
            for k, v in (j.get("categories_ms") or {}).items()]
    rows += [{"source_path": path, "n_images": n, "entry_kind": "kernel", "entry_name": k,
              "ms": _f(v), "total_kernel_ms": tot}
             for k, v in (j.get("top_kernels") or {}).items()]
    stmts = [ic.multi_upsert_sql("collector_kernel_ledger",
                                 ["source_path", "n_images", "entry_kind", "entry_name", "ms",
                                  "total_kernel_ms"], rows,
                                 ["source_path", "n_images", "entry_kind", "entry_name"])]
    return _emit(path, sha, nbytes, stmts, len(rows))


# =========================================================== kernel perf rows
PERF_COLS = ["source_path", "row_idx", "framework", "version", "device", "op_name",
             "kernel_source", "batch_size", "isl", "num_heads", "head_dim", "attn_dtype",
             "gemm_dtype", "m", "n", "k", "latency_ms"]


def _perf_row(path, i, r):
    return {"source_path": path, "row_idx": i, "framework": r.get("framework"),
            "version": r.get("version"), "device": r.get("device"),
            "op_name": r.get("op_name"), "kernel_source": r.get("kernel_source"),
            "batch_size": _i(r.get("batch_size")), "isl": _i(r.get("isl")),
            "num_heads": _i(r.get("num_heads")), "head_dim": _i(r.get("head_dim")),
            "attn_dtype": r.get("attn_dtype"), "gemm_dtype": r.get("gemm_dtype"),
            "m": _i(r.get("m")), "n": _i(r.get("n")), "k": _i(r.get("k")),
            "latency_ms": _f(r.get("latency"))}


def _clean(d):
    return {k: (None if v in ("", None) else v) for k, v in d.items()}


def load_kernel_perf_csv(path, sha, nbytes):
    with open(path) as f:
        rows = [_perf_row(path, i, _clean(r)) for i, r in enumerate(_csv.DictReader(f))]
    stmts = [ic.multi_upsert_sql("collector_kernel_perf", PERF_COLS, rows,
                                 ["source_path", "row_idx"])]
    return _emit(path, sha, nbytes, stmts, len(rows))


def load_kernel_perf_parquet(path, sha, nbytes):
    import pyarrow.parquet as pq
    tbl = pq.read_table(path).to_pylist()
    rows = [_perf_row(path, i, r) for i, r in enumerate(tbl)]
    stmts = [ic.multi_upsert_sql("collector_kernel_perf", PERF_COLS, rows,
                                 ["source_path", "row_idx"])]
    return _emit(path, sha, nbytes, stmts, len(rows))


# ================================================================= cold start
def load_cold_start(path, sha, nbytes):
    rows = []
    for i, line in enumerate(open(path)):
        if not line.strip():
            continue
        j = json.loads(line)
        ph = j.get("phases_s") or {}
        rows.append({"source_path": path, "trial_idx": i,
                     "total_s_to_ready": _f(j.get("total_s_to_ready")),
                     "imports_s": _f(ph.get("imports")), "cuda_ctx_s": _f(ph.get("cuda_ctx")),
                     "load_ckpt_s": _f(ph.get("load_ckpt")), "to_gpu_s": _f(ph.get("to_gpu")),
                     "first_forward_s": _f(ph.get("first_forward")),
                     "second_forward_s": _f(ph.get("second_forward")),
                     "ckpt_bytes": _i(j.get("ckpt_bytes")), "gpu": j.get("gpu"),
                     "torch_version": j.get("torch"), "pid": _i(j.get("pid"))})
    stmts = [ic.multi_upsert_sql("collector_cold_start_trial",
                                 ["source_path", "trial_idx", "total_s_to_ready", "imports_s",
                                  "cuda_ctx_s", "load_ckpt_s", "to_gpu_s", "first_forward_s",
                                  "second_forward_s", "ckpt_bytes", "gpu", "torch_version",
                                  "pid"], rows, ["source_path", "trial_idx"])]
    return _emit(path, sha, nbytes, stmts, len(rows))


# ================================================================ aiperf smoke
def load_aiperf_report(path, sha, nbytes):
    j = json.load(open(path))
    row = {"source_path": path, "label": "two_pool",
           "completed_requests": _i(j.get("completed_requests")),
           "duration_ms": _f(j.get("duration_ms")),
           "mean_ttft_ms": _f(j.get("mean_ttft_ms")), "p99_ttft_ms": _f(j.get("p99_ttft_ms")),
           "mean_itl_ms": _f(j.get("mean_itl_ms")), "p99_itl_ms": _f(j.get("p99_itl_ms")),
           "mean_tpot_ms": _f(j.get("mean_tpot_ms")), "p99_tpot_ms": _f(j.get("p99_tpot_ms")),
           "mean_e2e_latency_ms": _f(j.get("mean_e2e_latency_ms")),
           "p99_e2e_latency_ms": _f(j.get("p99_e2e_latency_ms")),
           "max_e2e_latency_ms": _f(j.get("max_e2e_latency_ms")),
           "request_throughput_rps": _f(j.get("request_throughput_rps")),
           "output_throughput_tok_s": _f(j.get("output_throughput_tok_s")),
           "is_smoke": True, "metrics": j}
    stmts = [ic.multi_upsert_sql("collector_aiperf_report", list(row), [row], "source_path",
                                 jsonb_cols=("metrics",))]
    return _emit(path, sha, nbytes, stmts, 1)


# =============================================================== system spec
def load_system_spec(path, sha, nbytes):
    import yaml
    j = yaml.safe_load(open(path))
    rows = []

    def walk(prefix, node):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(f"{prefix}.{k}" if prefix else str(k), v)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(f"{prefix}[{i}]", v)
        else:
            rows.append({"source_path": path, "key_path": prefix,
                         "value_num": float(node) if isinstance(node, (int, float))
                         and not isinstance(node, bool) else None,
                         "value_text": str(node)})
    walk("", j)
    stmts = [ic.multi_upsert_sql("collector_system_spec",
                                 ["source_path", "key_path", "value_num", "value_text"], rows,
                                 ["source_path", "key_path"])]
    return _emit(path, sha, nbytes, stmts, len(rows))


# ========================================================= collection summary
def load_collection_summary(path, sha, nbytes):
    j = json.load(open(path))
    s = j.get("summary") or {}
    rows = [sc(path, "file", k, v) for k, v in s.items()
            if not isinstance(v, (dict, list)) or v]
    rows.append(sc(path, "file", "n_error_records", len(j.get("errors") or [])))
    stmts = [scalar_sql(rows)]
    return _emit(path, sha, nbytes, stmts, len(rows))


# ================================================================== registry
def _registry():
    """(path, handler) in load order. Only files that exist are attempted."""
    reg = []
    for name in ("anchor_sdpa_5x50", "anchor_flash_attention_2_5x50",
                 "anchor_sdpa_locked2400", "anchor_dense_sdpa_2400"):
        reg.append((f"{E}/{name}.json", load_anchor_bench))
    reg += [
        (f"{E}/anchor_master.json", load_anchor_master),
        (f"{E}/burst_anchor_all.json", load_burst_anchor_all),
        (f"{E}/fn_multires.json", load_fn_multires),
        (f"{E}/aic_multires.json", load_aic_multires),
        (f"{E}/fn_repro.json", load_fn_repro),
        (f"{E}/fn_silicon_CONTENDED_INVALID.json", load_fn_contended_invalid),
        (f"{E}/vllm_eager_dense.json", load_vllm_dense),
        (f"{E}/vllm_multires.json", load_vllm_dense),
        (f"{E}/vllm_eager_vit.json", load_vllm_eager_vit),
        (f"{E}/vit_compile.json", load_vit_compile),
        (f"{E}/vit_compile_dense.json", load_vit_compile_curve),
        (f"{E}/vit_compile_sweep.json", load_vit_compile_curve),
        (f"{E}/vit_op_profile.json", load_vit_op_profile),
        (f"{E}/vit_op_profile2.json", load_vit_op_profile),
        (f"{E}/silicon_closedloop.json", load_silicon_closedloop),
        (f"{E}/silicon_multiworker.json", load_silicon_multiworker),
        (f"{E}/burst3_fifo_replay.json", load_burst_fifo_replay),
        (f"{E}/oneworker_artifact/silicon_burst3.json", load_oneworker_silicon),
        (f"{E}/oneworker_artifact/silicon_burst5.json", load_oneworker_silicon),
    ]
    reg += [(p, load_encoder_stats_file)
            for p in sorted(glob.glob(f"{E}/*.stats.json"))]
    reg += [(f"{COLL}/phaseB_batch_validation/kernel_ledger_N1.json", load_kernel_ledger),
            (f"{COLL}/phaseB_batch_validation/kernel_ledger_N64.json", load_kernel_ledger),
            (f"{COLL}/phaseC_vit_shape_infill/encoder_attention_perf.txt", load_kernel_perf_csv),
            (f"{COLL}/phaseC_vit_shape_infill/gemm_perf.txt", load_kernel_perf_csv),
            (f"{COLL}/phase4_smoke/smoke_rows.csv", load_kernel_perf_csv),
            (f"{COLL}/phase5_limited/limit20.parquet", load_kernel_perf_parquet),
            (f"{COLL}/phaseD_cold_start/trials.jsonl", load_cold_start),
            (f"{COLL}/phase9_two_pool/two_pool_report.json", load_aiperf_report),
            (f"{COLL}/phase2_system_metadata/rtx_5090.yaml", load_system_spec),
            (f"{COLL}/collection_summary_vllm.json", load_collection_summary),
            (f"{COLL}/phase4_smoke/collection_summary_vllm.json", load_collection_summary)]
    return reg


def load_collector_silicon(idx, reload=False):
    """K21 entrypoint. Returns (files_loaded, rows_loaded)."""
    nf = nr = 0
    for path, fn in _registry():
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        n = fn(path, sha, nbytes)
        nf += 1
        nr += n
    return nf, nr


# Files under collector_artifacts/ deliberately NOT ingested, and why.
EXCLUDED_NOTES = {
    "phase9_two_pool/dynamo-venv/**": "checked-in Python virtualenv (7,540 files), not an artifact",
    "**/__pycache__/*.pyc": "compiled bytecode",
    "*.py, *.sh": "generator/benchmark source, not measurement output",
    "*.md, *.log, *.png, *.pdf": "prose, run logs and rendered figures",
    "phaseE/merged_fa2.csv, merged_sdpa.csv":
        "flattened re-emission of anchor_dense_*/anchor_flash_* rows[]; the JSON is "
        "full-precision and carries GPU state, so the JSON is ingested instead",
    "phaseE/oom_fa2.txt, oom_sdpa.txt": "empty files",
    "phaseE/reqs/*.json, phaseE/fc_schedules/*.json":
        "simulator INPUT request lists / worker schedules, not results",
    "phaseC/cases.json, phaseC/infill.done":
        "collector input shape list and progress marker, not measurements",
    "phaseB/{measured_f_n,measured_f_n_5x50,aic_f_n,aic_f_n_postinfill}.csv":
        "already ingested by loaders.load_collector (kind K12) into provenance.collector_fn",
    "phase0/1/2/3 result.txt, phaseA/phaseB_fallback result.txt, silicon_status.txt":
        "free-text run transcripts with no tabular content",
    "silicon_multiworker.json single_worker_amplification.by_window":
        "derived duplicate of the W=1 entries already in collector_multiworker_p99",
}


if __name__ == "__main__":
    import sys
    import time
    reload = "--reload" in sys.argv
    t0 = time.time()
    idx = ic.load_ingest_index()
    f, r = load_collector_silicon(idx, reload)
    print(f"[K21   collector       ] files={f:5d} rows={r:13,d}  {time.time()-t0:7.1f}s")
