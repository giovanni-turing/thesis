"""Per-kind loaders (K1-K13). Each returns (files_loaded, rows_loaded).

Transport: small typed/projection rows go via batched INSERT ... ON CONFLICT (one psql
call per file); heavy raw rows stream through db.copy_rows (psql \\copy). Idempotency: a
file whose sha256 is unchanged in ingest_log is skipped unless reload=True.
"""
import glob, json, os, re
import db
import ingest_common as ic
from runid import parse, experiment_of, run_id_of

TESE = "/home/gio/tese"
DATA = f"{TESE}/defense/anim/data"
SIM = f"{TESE}/simulation/results"
PRED = f"{TESE}/predictors/results"
COLL = f"{TESE}/collector_artifacts"
VLLM = "/mnt/9d1dd233-5327-4660-a734-36a12ae92abd/vllm_trace_analysis"
ROOTS_RUNS = [DATA, SIM]


def iter_files(patterns, roots):
    seen = set()
    for root in roots:
        for pat in patterns:
            for p in sorted(glob.glob(os.path.join(root, "**", pat), recursive=True)):
                if ic.is_worktree(p) or p in seen:
                    continue
                seen.add(p)
                yield p


def _prep(path, idx, reload):
    if ic.is_worktree(path):
        return None
    sha, nbytes = ic.file_meta(path)
    if not reload and idx.get(path) == sha:
        return None
    return sha, nbytes


def _run(fn, *a):
    db.run_sql(";\n".join(s for s in a if s))


# ========================================================================= K9
def load_windows(idx, reload):
    path = f"{DATA}/windows_ext.json"
    prep = _prep(path, idx, reload)
    if not prep:
        return 0, 0
    # D42 (2026-07-27, escalation): byte-identity is a PRE-INGEST prerequisite.
    # Before any DB write, regenerate the nine-cell join from raw operands and
    # require the tracked artifact to be byte-identical -- a corrupt artifact or
    # a generator failure means ZERO K16 writes, in every invocation path
    # (gate A6, --data, manual). ~18 s, and only on write-bearing invocations.
    import subprocess as _sp, tempfile as _tf
    _tmp = _tf.NamedTemporaryFile(suffix=".json", delete=False)
    _tmp.close()
    os.unlink(_tmp.name)          # join script preloads an EXISTING --out; hand it a fresh path
    try:
        _rc = _sp.run(["/home/gio/tese/eda/.venv/bin/python",
                       "/home/gio/tese/simulation/composed_fill_join.py", "--out", _tmp.name],
                      capture_output=True, text=True, cwd="/home/gio/tese").returncode
        if _rc != 0:
            raise AssertionError(f"K16: pre-ingest regeneration failed (rc={_rc}); refusing to write")
        if open(_tmp.name, "rb").read() != open(path, "rb").read():
            raise AssertionError("K16: tracked artifact is NOT byte-identical to fresh regeneration; refusing to write")
    finally:
        if os.path.exists(_tmp.name):
            os.unlink(_tmp.name)
    sha, nbytes = prep
    d = json.load(open(path))
    rows = []
    for wname, w in d.items():
        rows.append({
            "window_name": wname, "trace_offset": w.get("offset"),
            "max_requests": w.get("max_requests"), "requests": w.get("requests"),
            "span_s": w.get("span_s"), "mean_req_per_s": w.get("mean_req_per_s"),
            "mean_img_per_s": w.get("mean_img_per_s"),
            "peak_1min_img_per_s": w.get("peak_1min_img_per_s"),
            "text_only_fraction": w.get("text_only_fraction"),
            "onset_min": w.get("onset_min"), "in_coverage": w.get("in_coverage"),
            "t0": w.get("t0"), "note": w.get("note")})
    cols = ["window_name", "trace_offset", "max_requests", "requests", "span_s",
            "mean_req_per_s", "mean_img_per_s", "peak_1min_img_per_s",
            "text_only_fraction", "onset_min", "in_coverage", "t0", "note"]
    _run(None, ic.multi_upsert_sql("windows", cols, rows, "window_name"),
         ic.ingest_sql(path, sha, "K9", len(rows), None, nbytes))
    return 1, len(rows)


# ========================================================================= K1
_LLM_HOT = ["completed_requests", "num_requests", "mean_ttft_ms", "median_ttft_ms",
            "p90_ttft_ms", "p95_ttft_ms", "p99_ttft_ms", "max_ttft_ms", "mean_itl_ms",
            "p99_itl_ms", "mean_tpot_ms", "p99_tpot_ms", "mean_e2e_latency_ms",
            "p90_e2e_latency_ms", "p99_e2e_latency_ms", "max_e2e_latency_ms", "p99_ttst_ms",
            "request_throughput_rps", "output_throughput_tok_s", "total_throughput_tok_s",
            "gpu_hours", "decode_worker_seconds", "prefill_worker_seconds",
            "prefix_cache_reused_ratio"]


def load_llm_reports(idx, reload):
    nf = nr = 0
    for path in iter_files(["*.report.json"], ROOTS_RUNS):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        run = parse(path, kind="K1", pool="language")
        # ON CONFLICT (run_id) DO UPDATE is destructive in the same way a DELETE is:
        # a colliding second file overwrites the first file's summary row.
        ic.guard_run_collision(run["run_id"], path, idx, "llm_run_summary", "K1")
        j = json.load(open(path))
        row = {"run_id": run["run_id"], "metrics": j}
        for c in _LLM_HOT:
            row[c] = j.get(c)
        _run(None, ic.run_upsert_sql(run),
             ic.upsert_sql("llm_run_summary", row, "run_id", jsonb_cols=("metrics",)),
             ic.ingest_sql(path, sha, "K1", 1, run["run_id"], nbytes))
        nf += 1
        nr += 1
    return nf, nr


# ========================================================================= K3
def _p(j, field, p):
    return (j.get(field) or {}).get(p)


def load_encoder_stats(idx, reload):
    nf = nr = 0
    for path in iter_files(["*.jsonl.stats.json"], ROOTS_RUNS):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        run = parse(path, kind="K3", pool="encoder")
        ic.guard_run_collision(run["run_id"], path, idx, "encoder_run_summary", "K3")
        j = json.load(open(path))
        row = {
            "run_id": run["run_id"],
            "requests": j.get("requests"), "requests_with_images": j.get("requests_with_images"),
            "total_images": j.get("total_images"), "image_px": j.get("image_px"),
            "encoder_workers": j.get("encoder_workers"),
            "encoder_batch_images": j.get("encoder_batch_images"),
            "text_only_fraction": j.get("text_only_fraction"),
            "encoder_delay_p50_ms": _p(j, "encoder_delay_ms", "p50"),
            "encoder_delay_p90_ms": _p(j, "encoder_delay_ms", "p90"),
            "encoder_delay_p99_ms": _p(j, "encoder_delay_ms", "p99"),
            "encoder_delay_max_ms": _p(j, "encoder_delay_ms", "max"),
            "encoder_service_p99_ms": _p(j, "encoder_service_ms", "p99"),
            "handoff_p99_ms": _p(j, "handoff_ms", "p99"),
            "provisioned_worker_seconds": j.get("provisioned_worker_seconds"),
            "busy_worker_seconds": j.get("busy_worker_seconds"),
            "encoder_utilization": j.get("encoder_utilization"),
            "arrival_speedup": j.get("arrival_speedup"),
            "mean_images_per_s": j.get("mean_images_per_s"),
            "offered_img_per_s": j.get("offered_img_per_s"),
            "queue_divergent": j.get("queue_divergent"),
            "chunk_dispatch": j.get("chunk_dispatch"), "batches": j.get("batches"),
            "encoder_forwards": j.get("encoder_forwards"), "metrics": j}
        _run(None, ic.run_upsert_sql(run),
             ic.upsert_sql("encoder_run_summary", row, "run_id", jsonb_cols=("metrics",)),
             ic.ingest_sql(path, sha, "K3", 1, run["run_id"], nbytes))
        nf += 1
        nr += 1
    return nf, nr


# ========================================================================= K7
_FC_RUN_COLS = ["run_id", "experiment", "pool", "window_name", "policy", "model",
                "quantile", "resolution", "rho", "cold_start_s", "lead_s", "hysteresis_min",
                "actuation", "kind", "source_path", "is_current"]
_FC_COLS = ["run_id", "window_name", "resolution", "rho", "cold_start_s", "lead_s",
            "hysteresis_min", "policy", "quantile", "model", "actuation", "readiness",
            "p99_ms", "max_ms", "feasible", "provisioned_ws", "busy_ws", "sched_steps",
            "sched_min_workers", "sched_max_workers", "source_path"]


# Which CONTROLLER produced a factorial results file. This used to be inferred from
# the substring "target" in the path, which silently mislabelled the two target-time
# families -- neither results_44.jsonl nor pilot_results.jsonl contains that substring,
# so both were pooled with the issue-time rebuild (572 rows; see ADJUDICATION §2.7 and
# schema/24_actuation_correction.sql). Actuation is not recoverable from the archived
# JSON -- it carries no such field -- so it is declared here by artifact identity:
#
#   target-time  worker READY AT the target bin (verification/scripts/forecast_schedule.py,
#                driven by run_cell.py via e2b_fleet.py). Leads {15,30,45,300}. SUPERSEDED.
#   issue-time   decision ISSUED at t, worker ready at t+lead
#                (verification/scripts/forecast_schedule_issuetime.py, driven by
#                simulation/run_44_factorial_issuetime.py). Leads {15,30,45,165}. CURRENT.
#
# Evidence: simulation/run_44_factorial_issuetime.py:5-8; progress/results-ledger.md:112,416.
_TARGET_TIME_RESULTS = frozenset({
    f"{SIM}/results_44.jsonl",
    f"{SIM}/pilot_results.jsonl",
    f"{SIM}/results_week_canary.jsonl",
})

# Whole FAMILIES (directories) whose every artifact came from the target-time controller.
# Same declaration-by-identity rule as _TARGET_TIME_RESULTS: the directory is named, the
# evidence is cited, nothing is inferred from the spelling of a path.
#
#   week_matrix  simulation/run_week_matrix.sh:5 sets SCHED=simulation/forecast_schedule.py
#                -- the TARGET-time generator -- and sweeps leads {15,30,45,300}, the
#                target-time lead set. Corroborated in the successor's own docstring:
#                simulation/run_44_week_surface_issuetime.py:6-7, "the archived
#                run_week_matrix.sh was target-time at L=300". SUPERSEDED by
#                results/week_surface_issuetime/ (issue-time, leads {15,30,45,165}).
_TARGET_TIME_DIRS = (
    f"{SIM}/week_matrix/",
)


def actuation_of(path):
    """'target-time' | 'issue-time' for a factorial results file. Explicit, never guessed
    from a path substring -- see _TARGET_TIME_RESULTS / _TARGET_TIME_DIRS."""
    p = path.replace("\\", "/")
    if p in _TARGET_TIME_RESULTS or p.startswith(_TARGET_TIME_DIRS):
        return "target-time"
    if "target" in p.lower():
        return "target-time"
    return "issue-time"


# Dimensions that a family's artifacts CARRY but do not RECORD, declared by artifact
# identity for the same reason actuation is. A week-surface record names only
# (model, quantile, rho, lead): the window and the controller settings live in the
# generator's argv, not in the JSON.
#
#   week_surface_issuetime  run_44_week_surface_issuetime.py:47-49 passes
#                           --window aggregate; the file's own "surface" string reads
#                           "...= 96 warm-pool aggregate cells; issue-time". The
#                           issue-time generator takes no --resolution/--hysteresis-min,
#                           so those stay NULL rather than being invented.
#   week_matrix             run_week_matrix.sh:17-18 passes --window aggregate
#                           --resolution 15s --hysteresis-min 3.
#
# 'aggregate', not 'week': provenance.windows has no 'week' row, so 'week' would break
# C209 (runs.window_name drawn from the windows dimension). span_s 483659.8 matches the
# stats files' sim_horizon_s 483659.846.
_FAMILY_DIMS = {
    f"{SIM}/week_surface_issuetime/": {
        "window": "aggregate", "policy": "forecast", "readiness": "warm"},
    f"{SIM}/week_matrix/": {
        "window": "aggregate", "resolution": "15s", "hysteresis_min": 3},
}


def _family_dims(path):
    p = path.replace("\\", "/")
    for prefix, dims in _FAMILY_DIMS.items():
        if p.startswith(prefix):
            return dims
    return {}


def _norm_cell(rec, fdims, fam=None):
    """Normalize a factorial record to a uniform dims+metrics dict. Handles three shapes:
      1. nested {cell:{...}, p99_ms,...}                        (results_44)
      2. flat   {window,model,lead,readiness,p99_ms,...}        (factorial_issuetime)
      3. flat   {model,quantile,rho,lead,p99_ms,...} with NO    (week_surface_issuetime)
                'window' key and 'aggregate_feasible' in place
                of 'feasible'

    Shape 3 used to fall through the guard below and return None for every record, so
    week_surface_issuetime_results.json ingested as K7 with n_rows=0 -- all 96 issue-time
    week cells silently absent from factorial_cell. The window it lacks is supplied by
    `fam` (_FAMILY_DIMS), not guessed.
    """
    if not isinstance(rec, dict):
        return None
    fam = fam or {}
    c = rec.get("cell")
    src = c if isinstance(c, dict) else rec
    flat_ok = "p99_ms" in rec and ("window" in rec or (fam.get("window") and "lead" in rec))
    if not (isinstance(c, dict) or flat_ok):
        return None
    if rec.get("error"):                      # converter/gen failures carry no cell
        return None
    feasible = rec.get("feasible")
    if feasible is None:
        feasible = rec.get("aggregate_feasible")
    if rec.get("p99_ms") is None and feasible is None:
        return None
    g = src.get
    return {
        "window": g("window") or fam.get("window"), "model": g("model"),
        "resolution": g("resolution") or fdims.get("resolution") or fam.get("resolution"),
        "rho": g("rho") if g("rho") is not None else fdims.get("rho"),
        "cold_start_s": g("cold_start_s") if g("cold_start_s") is not None else g("lead"),
        "lead_s": g("lead") if g("lead") is not None else g("cold_start_s"),
        "hysteresis_min": (g("hysteresis_min") if g("hysteresis_min") is not None
                           else fam.get("hysteresis_min")),
        "policy": g("policy") or fdims.get("policy") or fam.get("policy") or "forecast",
        "quantile": g("quantile") or fdims.get("quantile"),
        "readiness": g("readiness") or fam.get("readiness"),
        "p99_ms": rec.get("p99_ms"), "max_ms": rec.get("max_ms"),
        "feasible": feasible, "provisioned_ws": rec.get("provisioned_ws"),
        "busy_ws": rec.get("busy_ws"), "schedule": rec.get("schedule") or {},
    }


def _factorial_records(path):
    if path.endswith(".jsonl"):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)
        return
    d = json.load(open(path))
    if isinstance(d, list):
        yield from d
    elif isinstance(d, dict):
        if "cell" in d:
            yield d
        elif isinstance(d.get("results"), list):     # {grid, results:[cells]}
            yield from d["results"]
        else:
            for v in d.values():
                if isinstance(v, dict) and "cell" in v:
                    yield v
                elif isinstance(v, list):
                    for x in v:
                        if isinstance(x, dict) and "cell" in x:
                            yield x


def load_factorial(idx, reload):
    # per-run artifacts (handled by K1/K3/K4/K5) that also end in .json — never factorial cells
    exc = (".sched.json", ".jsonl.stats.json", ".stats.json", ".report.json",
           ".series.json", ".requests.jsonl")
    dirs = ["factorial_issuetime", "week_surface_issuetime", "aggregate44",
            "aggregate44_rho", "aggregate44_strict", "rerun_verify"]
    files = list(iter_files(["results_*.jsonl", "pilot_results.jsonl"], [SIM]))
    for dsub in dirs:
        for p in sorted(glob.glob(f"{SIM}/{dsub}/**/*.json", recursive=True)):
            if not ic.is_worktree(p) and not p.endswith(exc):
                files.append(p)
    nf = nr = 0
    for path in dict.fromkeys(files):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        actuation = actuation_of(path)
        fdims = parse(path)
        fam = _family_dims(path)
        runs, cells = [], []
        for rec in _factorial_records(path):
            nd = _norm_cell(rec, fdims, fam)
            if not nd:
                continue
            rid = ("factorial:%s:%s:%s:L%s:%s:res%s:rho%s:cs%s:hy%s:%s:%s" % (
                actuation, nd["window"], nd["model"], nd["lead_s"], nd["readiness"],
                nd["resolution"], nd["rho"], nd["cold_start_s"], nd["hysteresis_min"],
                nd["policy"], nd["quantile"]))
            runs.append({"run_id": rid, "experiment": "factorial", "pool": "encoder",
                         "window_name": nd["window"], "policy": nd["policy"],
                         "model": nd["model"], "quantile": nd["quantile"],
                         "resolution": nd["resolution"], "rho": nd["rho"],
                         "cold_start_s": nd["cold_start_s"], "lead_s": nd["lead_s"],
                         "hysteresis_min": nd["hysteresis_min"], "actuation": actuation,
                         "kind": "K7", "source_path": path,
                         # C507: the two actuations must never be pooled in a published
                         # aggregate, and current_factorial is what the analytical views
                         # read. Deriving is_current from the actuation here makes that
                         # structural instead of a one-off UPDATE that a re-ingest of a
                         # target-time file would silently undo (runs.is_current DEFAULTs
                         # to true). See schema/24_actuation_correction.sql:129.
                         "is_current": actuation == "issue-time"})
            sch = nd["schedule"]
            cells.append({"run_id": rid, "window_name": nd["window"],
                          "resolution": nd["resolution"], "rho": nd["rho"],
                          "cold_start_s": nd["cold_start_s"], "lead_s": nd["lead_s"],
                          "hysteresis_min": nd["hysteresis_min"], "policy": nd["policy"],
                          "quantile": nd["quantile"], "model": nd["model"],
                          "actuation": actuation, "readiness": nd["readiness"],
                          "p99_ms": nd["p99_ms"], "max_ms": nd["max_ms"],
                          "feasible": nd["feasible"], "provisioned_ws": nd["provisioned_ws"],
                          "busy_ws": nd["busy_ws"], "sched_steps": sch.get("steps"),
                          "sched_min_workers": sch.get("min_workers"),
                          "sched_max_workers": sch.get("max_workers"), "source_path": path})
        if not cells:
            db.run_sql(ic.ingest_sql(path, sha, "K7", 0, None, nbytes))
            continue
        for i in range(0, len(cells), 500):
            _run(None,
                 ic.multi_upsert_sql("runs", _FC_RUN_COLS, runs[i:i+500], "run_id"),
                 ic.multi_upsert_sql("factorial_cell", _FC_COLS, cells[i:i+500], "run_id"))
        db.run_sql(ic.ingest_sql(path, sha, "K7", len(cells), None, nbytes))
        nf += 1
        nr += len(cells)
    return nf, nr


# ========================================================================= K8
def load_coverage(idx, reload):
    path = f"{DATA}/coverage_manifest.json"
    prep = _prep(path, idx, reload)
    if not prep:
        return 0, 0
    # D42 (2026-07-27, escalation): byte-identity is a PRE-INGEST prerequisite.
    # Before any DB write, regenerate the nine-cell join from raw operands and
    # require the tracked artifact to be byte-identical -- a corrupt artifact or
    # a generator failure means ZERO K16 writes, in every invocation path
    # (gate A6, --data, manual). ~18 s, and only on write-bearing invocations.
    import subprocess as _sp, tempfile as _tf
    _tmp = _tf.NamedTemporaryFile(suffix=".json", delete=False)
    _tmp.close()
    os.unlink(_tmp.name)          # join script preloads an EXISTING --out; hand it a fresh path
    try:
        _rc = _sp.run(["/home/gio/tese/eda/.venv/bin/python",
                       "/home/gio/tese/simulation/composed_fill_join.py", "--out", _tmp.name],
                      capture_output=True, text=True, cwd="/home/gio/tese").returncode
        if _rc != 0:
            raise AssertionError(f"K16: pre-ingest regeneration failed (rc={_rc}); refusing to write")
        if open(_tmp.name, "rb").read() != open(path, "rb").read():
            raise AssertionError("K16: tracked artifact is NOT byte-identical to fresh regeneration; refusing to write")
    finally:
        if os.path.exists(_tmp.name):
            os.unlink(_tmp.name)
    sha, nbytes = prep
    j = json.load(open(path))
    rows = [{"manifest_path": path, "fleet": r.get("fleet"), "run": r.get("run"),
             "pool": r.get("pool"), "requests": r.get("requests"), "expect": r.get("expect"),
             "is_full": r.get("full"), "ok": r.get("ok")} for r in j.get("rows", [])]
    cov_cols = ["manifest_path", "fleet", "run", "pool", "requests", "expect", "is_full", "ok"]
    meta = {"manifest_path": path, "trace_requests": j.get("trace_requests"),
            "forecast_span_requests": j.get("forecast_span_requests"),
            "context_days_requests": j.get("context_days_requests"),
            "complete": (j.get("guarantee") or {}).get("complete"),
            "per_model_maxspan": j.get("per_model_maxspan"), "coverage": j.get("coverage"),
            "guarantee": j.get("guarantee")}
    _run(None,
         ic.multi_upsert_sql("coverage", cov_cols, rows, ["manifest_path", "fleet", "run", "pool"]),
         ic.upsert_sql("coverage_meta", meta, "manifest_path",
                       jsonb_cols=("per_model_maxspan", "coverage", "guarantee")),
         ic.ingest_sql(path, sha, "K8", len(rows), None, nbytes))
    return 1, len(rows)


# ======================================================================== K8b
def load_verification(idx, reload):
    nf = nr = 0
    for path in iter_files(["verification.json"], ROOTS_RUNS):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        j = json.load(open(path))
        # verification.json keys are BARE run ids ('burst1_reactive'); provenance.runs uses
        # experiment-prefixed ids ('a11:burst1_reactive'). Writing the bare id left 320/320
        # verification rows unjoinable. The prefix is the experiment of the verification.json's
        # OWN directory -- the sibling artifacts it verifies live there.
        exp = experiment_of(path)
        rows = []
        for bare, v in j.items():
            # a16_runs/verification.json carries a scalar '_note' alongside the per-run objects;
            # anything that is not a per-run dict is metadata, not a verification row.
            if not isinstance(v, dict):
                continue
            rid = bare if ":" in bare else f"{exp}:{bare}"
            rows.append({"source_path": path, "run_id": rid, "stage": v.get("stage"),
                         "requests": v.get("requests"), "completed": v.get("completed"),
                         "enc_p99": v.get("enc_p99"), "enc_max": v.get("enc_max"),
                         "ttft_p99": v.get("ttft_p99"), "itl_p99": v.get("itl_p99"),
                         "provisioned_ws": v.get("provisioned_ws"), "gpu_h": v.get("gpu_h"),
                         "queue_divergent": v.get("queue_divergent")})
        cols = ["source_path", "run_id", "stage", "requests", "completed", "enc_p99",
                "enc_max", "ttft_p99", "itl_p99", "provisioned_ws", "gpu_h", "queue_divergent"]
        _run(None, ic.multi_upsert_sql("verification", cols, rows, ["source_path", "run_id"]),
             ic.ingest_sql(path, sha, "K8b", len(rows), None, nbytes))
        nf += 1
        nr += len(rows)
    return nf, nr


# ================================================================ K10 metrics
_FM_COLS = ["model", "mode", "span", "resolution", "variate", "candidate", "h",
            "mae", "rmse", "wape"]
_FM_KEY = ["model", "mode", "span", "resolution", "variate", "candidate", "h"]


def load_forecast_metrics(idx, reload):
    import pyarrow.parquet as pq
    nf = nr = 0
    # h: -1 = aggregated over horizons; by_h carries its own h 1..12; h1 is the h=1 slice
    # and is loaded AFTER by_h because it additionally carries rmse for that key.
    for fname, hfix in [("metrics_overall.parquet", -1), ("metrics_by_h.parquet", None),
                        ("metrics_h1.parquet", 1)]:
        path = f"{PRED}/metrics/{fname}"
        if not os.path.exists(path):
            continue
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        rows = []
        for r in pq.read_table(path).to_pylist():
            row = {c: r.get(c) for c in _FM_COLS}
            row["h"] = r.get("h") if hfix is None else hfix
            rows.append(row)
        for i in range(0, len(rows), 1000):
            db.run_sql(ic.multi_upsert_sql("forecast_metrics", _FM_COLS, rows[i:i+1000], _FM_KEY))
        db.run_sql(ic.ingest_sql(path, sha, "K10m", len(rows), None, nbytes))
        nf += 1
        nr += len(rows)
    # quantile coverage
    qc = f"{PRED}/metrics/quantile_coverage.json"
    prep = _prep(qc, idx, reload)
    if prep:
        sha, nbytes = prep
        j = json.load(open(qc))
        rows = [{"model": m, "signal": sig, "detail": det}
                for m, sigs in j.items() for sig, det in sigs.items()]
        cols = ["model", "signal", "detail"]
        db.run_sql(ic.multi_upsert_sql("quantile_coverage", cols, rows, ["model", "signal"],
                   jsonb_cols=("detail",)))
        db.run_sql(ic.ingest_sql(qc, sha, "K10qc", len(rows), None, nbytes))
        nf += 1
        nr += len(rows)
    # structural ablation (one-off structured analysis, kept lossless as jsonb)
    ab = f"{PRED}/metrics/additive_structural_ablation.json"
    prep = _prep(ab, idx, reload) if os.path.exists(ab) else None
    if prep:
        sha, nbytes = prep
        db.run_sql(ic.upsert_sql("analysis_artifact",
                   {"name": "additive_structural_ablation", "source_path": ab,
                    "payload": json.load(open(ab))}, "name", jsonb_cols=("payload",)))
        db.run_sql(ic.ingest_sql(ab, sha, "K10ab", 1, None, nbytes))
        nf += 1
        nr += 1
    return nf, nr


# ======================================================================== K12
def load_collector(idx, reload):
    import csv as _csv
    specs = [
        (f"{COLL}/phaseB_batch_validation/measured_f_n.csv", "measured"),
        (f"{COLL}/phaseB_batch_validation/measured_f_n_5x50.csv", "measured_5x50"),
        (f"{COLL}/phaseB_batch_validation/aic_f_n.csv", "aic"),
        (f"{COLL}/phaseB_batch_validation/aic_f_n_postinfill.csv", "aic_postinfill"),
    ]
    n_alt = ("n_images", "batch", "n", "n_img")           # image-count column, varies by file
    int_cols = ("patches", "iters", "sm_clock_mhz")
    float_cols = ("mean_ms", "p50_ms", "min_ms", "aic_ms", "aic_ms_per_img")
    cols = ["source_path", "engine", "gpu", "image_px", "n_images", "patches", "mean_ms",
            "p50_ms", "min_ms", "aic_ms", "aic_ms_per_img", "iters", "sm_clock_mhz"]
    nf = nr = 0
    for path, engine in specs:
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        rows = []
        with open(path) as f:
            for rec in _csv.DictReader(f):
                nval = next((rec[c] for c in n_alt if rec.get(c) not in (None, "")), None)
                if nval is None:
                    continue                                   # can't key without image count
                r = {"source_path": path, "engine": engine, "gpu": "rtx_5090",
                     "image_px": 448, "n_images": int(float(nval))}
                for c in int_cols:
                    if rec.get(c) not in (None, ""):
                        r[c] = int(float(rec[c]))
                for c in float_cols:
                    if rec.get(c) not in (None, ""):
                        r[c] = float(rec[c])
                rows.append(r)
        db.run_sql(ic.multi_upsert_sql("collector_fn", cols, rows,
                   ["source_path", "engine", "image_px", "n_images"]))
        db.run_sql(ic.ingest_sql(path, sha, "K12", len(rows), None, nbytes))
        nf += 1
        nr += len(rows)
    return nf, nr


# ======================================================================== K15
def load_composed_e2e(idx, reload):
    """A12 request-linked ingress->first-token join (a12_data.json windows[*].runs[*].stats)."""
    path = f"{DATA}/a12_data.json"
    prep = _prep(path, idx, reload) if os.path.exists(path) else None
    if not prep:
        return 0, 0
    sha, nbytes = prep
    cols = ["window_name", "arm", "model", "policy", "requests", "enc_p99_ms", "ttft_p99_ms",
            "e2e_p99_ms", "e2e_max_ms", "itl_p99_ms", "gpu_hours", "composed_trace", "source_path"]
    rows = []
    for win, wd in (json.load(open(path)).get("windows") or {}).items():
        for arm, r in (wd.get("runs") or {}).items():
            s = r.get("stats") or {}
            if "e2e_p99" not in s:
                continue
            model = arm[3:] if arm.startswith("fc_") else None
            rows.append({"window_name": win, "arm": arm, "model": model,
                         "policy": "forecast" if arm.startswith("fc_") else arm,
                         "requests": s.get("requests"), "enc_p99_ms": s.get("enc_p99"),
                         "ttft_p99_ms": s.get("ttft_p99"), "e2e_p99_ms": s.get("e2e_p99"),
                         "e2e_max_ms": s.get("e2e_max"), "itl_p99_ms": s.get("itl_p99"),
                         "gpu_hours": s.get("gpu_h"), "composed_trace": s.get("composed_trace"),
                         "source_path": path})
    db.run_sql(ic.multi_upsert_sql("composed_e2e", cols, rows,
               ["source_path", "window_name", "arm"]))
    db.run_sql(ic.ingest_sql(path, sha, "K15", len(rows), None, nbytes))
    return 1, len(rows)


# ======================================================================== K16
def load_composed_e2e_fill(idx, reload):
    """Composed-coverage fill campaign: 9 more request-linked cells (2026-07-26).

    Same table, same key, same semantics as K15 -- a SEPARATE kind only because the
    rows come from a different artifact (simulation/composed_fill_join.py's output
    rather than defense/anim/build/extract_a12.py's), and composed_e2e is keyed by
    (source_path, window_name, arm) so the two sources coexist without collision.

    The cells: static C=8 on burst1/3/4/5 and the calm day, forecast-p90 (Chronos)
    and reactive on the calm day, and the full-trace static C=8 / reactive pair.
    Absent by protocol, not by omission: burst2/burst6 (the calibration split) and
    any full-trace forecast (the archive's first 1.4 days are that forecast's own
    context). Backs tex/closedloop.tex tab:cl-ledger-joint.

    The policy vocabulary is K15's, not the artifact's: 'forecast' (not
    'forecast_p90') so v_joint_e2e reads uniformly across all 29 arms.
    """
    path = f"{SIM}/composed_fill/composed_fill_joined.json"
    # D28.1: the artifact is a committed repo object -- absence is corruption, not a skip
    if not os.path.exists(path):
        raise FileNotFoundError(f"K16: committed artifact missing: {path}")
    prep = _prep(path, idx, reload)
    if not prep:
        return 0, 0
    # D42 (2026-07-27, escalation): byte-identity is a PRE-INGEST prerequisite.
    # Before any DB write, regenerate the nine-cell join from raw operands and
    # require the tracked artifact to be byte-identical -- a corrupt artifact or
    # a generator failure means ZERO K16 writes, in every invocation path
    # (gate A6, --data, manual). ~18 s, and only on write-bearing invocations.
    import subprocess as _sp, tempfile as _tf
    _tmp = _tf.NamedTemporaryFile(suffix=".json", delete=False)
    _tmp.close()
    os.unlink(_tmp.name)          # join script preloads an EXISTING --out; hand it a fresh path
    try:
        _rc = _sp.run(["/home/gio/tese/eda/.venv/bin/python",
                       "/home/gio/tese/simulation/composed_fill_join.py", "--out", _tmp.name],
                      capture_output=True, text=True, cwd="/home/gio/tese").returncode
        if _rc != 0:
            raise AssertionError(f"K16: pre-ingest regeneration failed (rc={_rc}); refusing to write")
        if open(_tmp.name, "rb").read() != open(path, "rb").read():
            raise AssertionError("K16: tracked artifact is NOT byte-identical to fresh regeneration; refusing to write")
    finally:
        if os.path.exists(_tmp.name):
            os.unlink(_tmp.name)
    sha, nbytes = prep
    cols = ["window_name", "arm", "model", "policy", "requests", "enc_p99_ms", "ttft_p99_ms",
            "e2e_p99_ms", "e2e_max_ms", "itl_p99_ms", "gpu_hours", "composed_trace",
            "source_path", "window_name_as_ingested"]
    # D28.3: the nine cell identities are pinned -- a shortened/altered artifact fails
    # D36 (2026-07-27): exact tuple pinning -- outer key, inner cell, window and arm
    # are each independently asserted against the expected map, never derived from
    # one another by concatenation.
    EXPECTED_TUPLES = {
        "burst1_static_C8":      ("burst1",    "static_C8"),
        "burst3_static_C8":      ("burst3",    "static_C8"),
        "burst4_static_C8":      ("burst4",    "static_C8"),
        "burst5_static_C8":      ("burst5",    "static_C8"),
        "steady24h_static_C8":   ("steady24h", "static_C8"),
        "steady24h_fc_chronos":  ("steady24h", "fc_chronos"),
        "steady24h_reactive":    ("steady24h", "reactive"),
        "fulltrace_static_C8":   ("fulltrace", "static_C8"),
        "fulltrace_reactive":    ("fulltrace", "reactive"),
    }
    data = json.load(open(path))
    got_cells = set(data)
    if got_cells != set(EXPECTED_TUPLES):
        raise AssertionError(f"K16: cell identity mismatch: missing={sorted(set(EXPECTED_TUPLES)-got_cells)} "
                             f"extra={sorted(got_cells-set(EXPECTED_TUPLES))}")
    for outer, (ew, ea) in EXPECTED_TUPLES.items():
        d0 = data[outer]
        if d0.get("cell") != outer or d0.get("window") != ew or d0.get("arm") != ea:
            raise AssertionError(f"K16: tuple mismatch at {outer}: cell={d0.get('cell')!r} "
                                 f"window={d0.get('window')!r} arm={d0.get('arm')!r} "
                                 f"expected ({outer!r}, {ew!r}, {ea!r})")
    rows = []
    for cell, d in sorted(data.items()):
        # D28.2: a broken cell is an error, never a silent skip
        if "error" in d:
            raise AssertionError(f"K16: cell {cell} carries error: {d['error']!r}")
        if "e2e_p99" not in d:
            raise AssertionError(f"K16: cell {cell} lacks e2e_p99")
        arm = d["arm"]
        model = arm[3:] if arm.startswith("fc_") else None
        policy = "forecast" if arm.startswith("fc_") else (
            "static" if arm.startswith("static") else arm)
        # the join asserts these itself; re-assert here so a silently truncated
        # artifact cannot reach the store
        if d.get("requests") != d.get("expected") or d.get("requests") != d.get("completed_requests"):
            raise AssertionError("%s: population disagreement trace=%r window=%r report=%r"
                                 % (cell, d.get("requests"), d.get("expected"),
                                    d.get("completed_requests")))
        if abs(float(d.get("alignment_drift_ms", 1e9))) >= 1.0:
            raise AssertionError("%s: arrival alignment drift %r ms" % (cell, d["alignment_drift_ms"]))
        rows.append({"window_name": d["window"], "arm": arm, "model": model, "policy": policy,
                     "requests": d["requests"], "enc_p99_ms": d["enc_p99"],
                     "ttft_p99_ms": d["ttft_p99"], "e2e_p99_ms": d["e2e_p99"],
                     "e2e_max_ms": d["e2e_max"], "itl_p99_ms": d["itl_p99"],
                     "gpu_hours": d["gpu_h"], "composed_trace": d["composed_trace"],
                     "source_path": path, "window_name_as_ingested": d["window"]})
    if len(rows) != 9:
        raise AssertionError(f"K16: expected exactly 9 rows, built {len(rows)}")
    # D28.4 + D28.r4 (2026-07-27): source-scoped REPLACEMENT executed ATOMICALLY --
    # delete, insert and ingest-log land in ONE transaction in ONE psql session, so
    # a mid-sequence failure can never leave the store drained or half-replaced.
    stmts = ["BEGIN",
             "DELETE FROM provenance.composed_e2e WHERE source_path = '%s'" % path.replace("'", "''"),
             ic.multi_upsert_sql("composed_e2e", cols, rows,
                                 ["source_path", "window_name", "arm"]),
             ic.ingest_sql(path, sha, "K16", len(rows), None, nbytes),
             "COMMIT"]
    db.run_sql(";\n".join(stmts) + ";")
    return 1, len(rows)


# ======================================================================== K14
def load_cost_accounting(idx, reload):
    import csv as _csv
    path = f"{DATA}/a2_cost_accounting.csv"
    prep = _prep(path, idx, reload)
    if not prep:
        return 0, 0
    # D42 (2026-07-27, escalation): byte-identity is a PRE-INGEST prerequisite.
    # Before any DB write, regenerate the nine-cell join from raw operands and
    # require the tracked artifact to be byte-identical -- a corrupt artifact or
    # a generator failure means ZERO K16 writes, in every invocation path
    # (gate A6, --data, manual). ~18 s, and only on write-bearing invocations.
    import subprocess as _sp, tempfile as _tf
    _tmp = _tf.NamedTemporaryFile(suffix=".json", delete=False)
    _tmp.close()
    os.unlink(_tmp.name)          # join script preloads an EXISTING --out; hand it a fresh path
    try:
        _rc = _sp.run(["/home/gio/tese/eda/.venv/bin/python",
                       "/home/gio/tese/simulation/composed_fill_join.py", "--out", _tmp.name],
                      capture_output=True, text=True, cwd="/home/gio/tese").returncode
        if _rc != 0:
            raise AssertionError(f"K16: pre-ingest regeneration failed (rc={_rc}); refusing to write")
        if open(_tmp.name, "rb").read() != open(path, "rb").read():
            raise AssertionError("K16: tracked artifact is NOT byte-identical to fresh regeneration; refusing to write")
    finally:
        if os.path.exists(_tmp.name):
            os.unlink(_tmp.name)
    sha, nbytes = prep
    cols = ["window_name", "policy", "lead_s", "p99_ms", "provisioned_ws", "warmup_ws",
            "total_from_order_ws", "warmup_frac", "source_path"]
    rows = []
    with open(path) as f:
        for r in _csv.DictReader(f):
            rows.append({"window_name": r["window"], "policy": r["policy"],
                         "lead_s": int(r["lead_s"]), "p99_ms": float(r["p99_ms"]),
                         "provisioned_ws": float(r["provisioned_ws"]),
                         "warmup_ws": float(r["warmup_ws"]),
                         "total_from_order_ws": float(r["total_from_order_ws"]),
                         "warmup_frac": float(r["warmup_frac"]), "source_path": path})
    db.run_sql(ic.multi_upsert_sql("cost_accounting", cols, rows,
               ["source_path", "window_name", "policy", "lead_s"]))
    db.run_sql(ic.ingest_sql(path, sha, "K14", len(rows), None, nbytes))
    return 1, len(rows)


# ======================================================================== K13
def load_ledger(idx, reload):
    path = f"{TESE}/progress/results-ledger.md"
    prep = _prep(path, idx, reload)
    if not prep:
        return 0, 0
    # D42 (2026-07-27, escalation): byte-identity is a PRE-INGEST prerequisite.
    # Before any DB write, regenerate the nine-cell join from raw operands and
    # require the tracked artifact to be byte-identical -- a corrupt artifact or
    # a generator failure means ZERO K16 writes, in every invocation path
    # (gate A6, --data, manual). ~18 s, and only on write-bearing invocations.
    import subprocess as _sp, tempfile as _tf
    _tmp = _tf.NamedTemporaryFile(suffix=".json", delete=False)
    _tmp.close()
    os.unlink(_tmp.name)          # join script preloads an EXISTING --out; hand it a fresh path
    try:
        _rc = _sp.run(["/home/gio/tese/eda/.venv/bin/python",
                       "/home/gio/tese/simulation/composed_fill_join.py", "--out", _tmp.name],
                      capture_output=True, text=True, cwd="/home/gio/tese").returncode
        if _rc != 0:
            raise AssertionError(f"K16: pre-ingest regeneration failed (rc={_rc}); refusing to write")
        if open(_tmp.name, "rb").read() != open(path, "rb").read():
            raise AssertionError("K16: tracked artifact is NOT byte-identical to fresh regeneration; refusing to write")
    finally:
        if os.path.exists(_tmp.name):
            os.unlink(_tmp.name)
    sha, nbytes = prep
    text = open(path).read()
    section = None
    blocks = re.split(r"(?m)^(#{2,3}\s+.*)$", text)
    rows = []
    # blocks alternate: [pre, heading1, body1, heading2, body2, ...]
    for i in range(1, len(blocks), 2):
        heading = blocks[i].lstrip("#").strip()
        body = blocks[i + 1] if i + 1 < len(blocks) else ""
        if blocks[i].startswith("## "):
            section = heading

        def field(name):
            m = re.search(r"(?im)^\s*%s\s*:\s*(.+)$" % re.escape(name), body)
            return m.group(1).strip() if m else None
        dm = re.search(r"\((\d{4}-\d{2}-\d{2})\)", heading) or None
        arts = field("artifact")
        rows.append({"section": section, "name": heading,
                     "entry_date": (dm.group(1) if dm else field("date")),
                     "artifact_paths": [a.strip() for a in re.split(r"[,\s]+", arts) if a.strip()] if arts else None,
                     "command": field("command"), "feeds": field("feeds"),
                     "supersedes": field("supersedes"),
                     "result_note": field("result") or field("finding"),
                     "commit_sha": field("commit"), "run_id": None,
                     "raw": (blocks[i] + body)[:8000]})
    cols = ["section", "name", "entry_date", "artifact_paths", "command", "feeds",
            "supersedes", "result_note", "commit_sha", "run_id", "raw"]
    db.run_sql("delete from provenance.ledger_entry")
    for i in range(0, len(rows), 200):
        tuples = ["(" + ",".join(ic.lit(r.get(c)) for c in cols) + ")" for r in rows[i:i+200]]
        db.run_sql(f"insert into provenance.ledger_entry ({','.join(cols)}) values {','.join(tuples)}")
    db.run_sql(ic.ingest_sql(path, sha, "K13", len(rows), None, nbytes))
    return 1, len(rows)


# ==================================================================== RAW: K2
_LLM_REQ_FIELDS = ["uuid", "session_id", "turn_index", "arrival_time_ms", "first_admit_ms",
                   "first_token_ms", "last_token_ms", "ttft_ms", "ttst_ms", "e2e_latency_ms",
                   "itl_ms", "input_length", "requested_output_length", "output_length",
                   "reused_input_tokens", "prefill_worker_idx", "decode_worker_idx",
                   "prefill_admit_ms", "source_held_ms", "destination_reserved_ms",
                   "destination_activated_ms", "decode_admit_ms", "source_released_ms",
                   "decode_reused_input_tokens", "prefill_route_overlap_tokens",
                   "decode_route_overlap_tokens", "terminal_status"]
_LLM_REQ_COLS = ["experiment", "run_id"] + _LLM_REQ_FIELDS


def _llm_req_rows(path, exp, rid):
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            yield (exp, rid) + tuple(r.get(k) for k in _LLM_REQ_FIELDS)


def load_llm_requests(idx, reload):
    nf = nr = 0
    for path in iter_files(["*.requests.jsonl"], ROOTS_RUNS):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        run = parse(path, kind="K2", pool="language")
        rid, exp = run["run_id"], run["experiment"]
        ic.guard_run_collision(rid, path, idx, "llm_request", "K2")
        db.run_sql(ic.run_upsert_sql(run) + ";" + ic.delete_for_run_sql("llm_request", rid))
        n = db.copy_rows("llm_request", _LLM_REQ_COLS, _llm_req_rows(path, exp, rid))
        db.run_sql(ic.ingest_sql(path, sha, "K2", n, rid, nbytes))
        nf += 1
        nr += n
    return nf, nr


# ==================================================================== RAW: K5
_SER_COLS = ["experiment", "run_id", "t", "img_arrived", "img_completed",
             "queue_imgs_end", "busy_workers_end"]


def load_encoder_series(idx, reload):
    nf = nr = 0
    for path in iter_files(["*.series.json"], ROOTS_RUNS):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        run = parse(path, kind="K5", pool="encoder")
        rid, exp = run["run_id"], run["experiment"]
        d = json.load(open(path))
        run["config"] = {"freq_s": d.get("freq_s"), "arrival_speedup": d.get("arrival_speedup")}
        ser = d.get("series", [])

        def rows():
            for s in ser:
                yield (exp, rid, s.get("t"), s.get("img_arrived"), s.get("img_completed"),
                       s.get("queue_imgs_end"), s.get("busy_workers_end"))
        ic.guard_run_collision(rid, path, idx, "encoder_series", "K5")
        db.run_sql(ic.run_upsert_sql(run) + ";" + ic.delete_for_run_sql("encoder_series", rid))
        n = db.copy_rows("encoder_series", _SER_COLS, rows())
        db.run_sql(ic.ingest_sql(path, sha, "K5", n, rid, nbytes))
        nf += 1
        nr += n
    return nf, nr


# ==================================================================== RAW: K6
_COMP_COLS = ["experiment", "run_id", "line_index", "ts", "input_length",
              "output_length", "hash_ids"]


def _is_composed(path):
    if path.endswith(".requests.jsonl"):
        return False
    base = os.path.basename(path)
    if base.startswith(("results_", "cells_", "pilot_")):
        return False
    try:
        with open(path) as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    return isinstance(r, dict) and "hash_ids" in r and "timestamp" in r and "uuid" not in r
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    return False


def load_composed(idx, reload):
    nf = nr = 0
    for path in iter_files(["*.jsonl"], ROOTS_RUNS):
        if not _is_composed(path):
            continue
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        run = parse(path, kind="K6", pool="both")
        rid, exp = run["run_id"], run["experiment"]

        def rows():
            with open(path) as f:
                for i, line in enumerate(f):
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    yield (exp, rid, i, r.get("timestamp"), r.get("input_length"),
                           r.get("output_length"), r.get("hash_ids") or [])
        ic.guard_run_collision(rid, path, idx, "composed_request", "K6")
        db.run_sql(ic.run_upsert_sql(run) + ";" + ic.delete_for_run_sql("composed_request", rid))
        n = db.copy_rows("composed_request", _COMP_COLS, rows())
        db.run_sql(ic.ingest_sql(path, sha, "K6", n, rid, nbytes))
        nf += 1
        nr += n
    return nf, nr


# ==================================================================== RAW: K4
_SCHED_COLS = ["run_id", "source_path", "step_index", "t_s", "worker_count"]


def load_worker_schedule(idx, reload):
    nf = nr = 0
    for path in iter_files(["*.sched.json"], ROOTS_RUNS):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        run = parse(path, kind="K4")
        rid = run["run_id"]
        steps = json.load(open(path))
        ic.guard_run_collision(rid, path, idx, "worker_schedule", "K4")

        def rows():
            for i, pair in enumerate(steps):
                yield (rid, path, i, pair[0], pair[1])
        db.run_sql(ic.run_upsert_sql(run) + ";" +
                   f"delete from provenance.worker_schedule where source_path={ic.lit(path)}")
        n = db.copy_rows("worker_schedule", _SCHED_COLS, rows())
        db.run_sql(ic.ingest_sql(path, sha, "K4", n, rid, nbytes))
        nf += 1
        nr += n
    return nf, nr


# ============================================================= RAW: K10 forecast
_FCAST_COLS = ["source_tag", "model", "mode", "variate", "resolution", "origin", "h", "step",
               "ts", "y_true", "point", "p10", "p20", "p30", "p40", "p50", "p60", "p70",
               "p80", "p90"]


_FCAST_DATA = ["variate", "resolution", "origin", "h", "step", "ts", "y_true", "point",
               "p10", "p20", "p30", "p40", "p50", "p60", "p70", "p80", "p90"]


def load_forecast(idx, reload):
    import pyarrow.parquet as pq
    nf = nr = 0
    for path in sorted(glob.glob(f"{PRED}/*.parquet")):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        pf = pq.ParquetFile(path)
        names = set(pf.schema_arrow.names)
        if "variate" not in names or "point" not in names:
            continue  # not a forecast parquet
        sha, nbytes = prep
        meta = {k.decode(): v.decode() for k, v in (pf.schema_arrow.metadata or {}).items()}
        model = meta.get("model") or os.path.basename(path).split("_")[0]
        mode = meta.get("mode")
        try:
            variate0 = pf.read_row_group(0, columns=["variate"]).column("variate")[0].as_py()
        except Exception:
            variate0 = None
        run = {"run_id": f"predictors:{os.path.basename(path)[:-8]}", "experiment": "predictors",
               "pool": "encoder", "model": model, "mode": mode, "kind": "K10",
               "source_path": path, "config": meta}
        ic.guard_run_collision(run["run_id"], path, idx, "forecast", "K10")
        # provenance.forecast carries no run_id/source_path, so before source_tag existed the
        # idempotent delete could only be scoped by (model, mode, variate) -- which is NOT
        # unique across parquets (the EWMA calibration variants all share it) and so wiped
        # sibling variants. Scope the delete by the source file itself.
        db.run_sql(ic.run_upsert_sql(run) + ";" +
                   f"delete from provenance.forecast where model={ic.lit(model)} "
                   f"and source_tag={ic.lit(path)}")

        def rows():
            for batch in pf.iter_batches(batch_size=50000):
                d = batch.to_pydict()
                m = len(d["variate"])
                for i in range(m):
                    yield (path, model, mode) + tuple(
                        (d[c][i] if d.get(c) is not None else None) for c in _FCAST_DATA)
        n = db.copy_rows("forecast", _FCAST_COLS, rows())
        db.run_sql(ic.ingest_sql(path, sha, "K10", n, run["run_id"], nbytes))
        nf += 1
        nr += n
    return nf, nr


# ============================================================= RAW: K11 measured
def load_measured(idx, reload):
    import pyarrow.parquet as pq
    path = f"{VLLM}/out/per_request.parquet"
    prep = _prep(path, idx, reload)
    if not prep:
        return 0, 0
    # D42 (2026-07-27, escalation): byte-identity is a PRE-INGEST prerequisite.
    # Before any DB write, regenerate the nine-cell join from raw operands and
    # require the tracked artifact to be byte-identical -- a corrupt artifact or
    # a generator failure means ZERO K16 writes, in every invocation path
    # (gate A6, --data, manual). ~18 s, and only on write-bearing invocations.
    import subprocess as _sp, tempfile as _tf
    _tmp = _tf.NamedTemporaryFile(suffix=".json", delete=False)
    _tmp.close()
    os.unlink(_tmp.name)          # join script preloads an EXISTING --out; hand it a fresh path
    try:
        _rc = _sp.run(["/home/gio/tese/eda/.venv/bin/python",
                       "/home/gio/tese/simulation/composed_fill_join.py", "--out", _tmp.name],
                      capture_output=True, text=True, cwd="/home/gio/tese").returncode
        if _rc != 0:
            raise AssertionError(f"K16: pre-ingest regeneration failed (rc={_rc}); refusing to write")
        if open(_tmp.name, "rb").read() != open(path, "rb").read():
            raise AssertionError("K16: tracked artifact is NOT byte-identical to fresh regeneration; refusing to write")
    finally:
        if os.path.exists(_tmp.name):
            os.unlink(_tmp.name)
    sha, nbytes = prep
    tcols = [c for c, in db.rows(
        "select column_name from information_schema.columns "
        "where table_schema='provenance' and table_name='measured_request' "
        "order by ordinal_position")]
    pf = pq.ParquetFile(path)
    pcols = set(pf.schema_arrow.names)
    use = [c for c in tcols if c in pcols]
    db.run_sql("truncate provenance.measured_request")

    def rows():
        for batch in pf.iter_batches(batch_size=20000):
            d = batch.to_pydict()
            m = len(d[use[0]])
            for i in range(m):
                yield tuple(d[c][i] for c in use)
    n = db.copy_rows("measured_request", use, rows())
    run = {"run_id": "measured:vllm_per_request", "experiment": "eda", "pool": "language",
           "kind": "K11", "source_path": path, "gpu": "h100_sxm", "engine": "vLLM"}
    db.run_sql(ic.run_upsert_sql(run) + ";" + ic.ingest_sql(path, sha, "K11", n, run["run_id"], nbytes))
    return 1, n
