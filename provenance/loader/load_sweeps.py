#!/usr/bin/env python3
"""K25 loader -- family "sweeps": the saturation-knee arrival-speedup sweep.

Source tree: /home/gio/tese/simulation/results/sweeps/

Backs thesis tab:sim-knees and fig:sim-knees. The sweep asks, per (pool,
window, timing): as arrival speedup s rises, at what s does the pool's p99
first cross its SLA bound?

Ingests (kind K25, sha256-gated via ingest_common.ingest_sql):
  {llm,vision}_<window>_<timing>_s<N>.json (30) -> sweep_point
  summary.json                                  -> sweep_run + sweep_window (2)
                                                   + sweep_curve (6)
                                                   + sweep_decoupling (4)

Deliberately NOT ingested (already owned by earlier kinds, soft-ref'd by run_id
from sweep_point.report_run_id / series_run_id):
  reports/*.report.json      (19) -> K1 llm_run_summary
  series/*.series.json       (12) -> K5 encoder_series
  traces/*.jsonl.stats.json  (14) -> K3 encoder_run_summary
  traces/*.jsonl             (14) -> K6 composed_request
  logs/*.log                 (32) -- driver stdout, no facts not in the JSONs
  knees.{pdf,png}, burst_queue.{pdf,png}, README.md -- rendered outputs

The series files ARE read (not ingested) to derive the queue-depth summary
columns on sweep_point, which no artifact carries: the sweep records
`queue_divergent` but never the actual backlog. Full per-second trajectories
stay in provenance.encoder_series under K5.

Cross-check the knees this loader trusts from summary.json against the points:

  SELECT c.pool, c.window_name, c.timing, c.knee_speedup,
         max(p.speedup) FILTER (WHERE NOT p.over_threshold
                                 AND coalesce(p.itl_ok, true)) AS recomputed
    FROM provenance.sweep_curve c
    JOIN provenance.sweep_point p USING (sweep_run_id, pool, window_name, timing)
   GROUP BY 1,2,3,4;

Run:  cd /home/gio/tese/provenance/loader && python3 load_sweeps.py [--reload]
"""
import glob
import json
import os
import sys

import db
import ingest_common as ic

SWEEPS = "/home/gio/tese/simulation/results/sweeps"
KIND = "K25"
SWEEP_RUN_ID = "sweeps:summary"

# pool -> (sla metric name, sweep_run threshold column)
_SLA = {"llm": ("ttft_p99", "thr_ttft_p99_ms"),
        "vision": ("encoder_delay_p99", "thr_encoder_delay_p99_ms")}


def _prep(path, idx, reload):
    """None if the file is unchanged since last ingest (or lives in a worktree)."""
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


def _g(d, *path):
    """Nested get; None if any hop is missing."""
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _run_id_for(path):
    """Soft-ref run_id of an artifact owned by another kind (K1/K5 convention)."""
    if not path:
        return None
    import runid
    return runid.parse(path)["run_id"]


# ------------------------------------------------------------ queue depth
def _queue_summary(series_path):
    """(max, mean, final, busy_max) encoder queue depth from a K5 series file.

    Read, not ingested: the per-second rows belong to provenance.encoder_series.
    """
    if not series_path or not os.path.exists(series_path):
        return None, None, None, None
    try:
        with open(series_path) as f:
            rows = json.load(f).get("series") or []
    except (OSError, ValueError):
        return None, None, None, None
    if not rows:
        return None, None, None, None
    q = [r.get("queue_imgs_end") or 0 for r in rows]
    b = [r.get("busy_workers_end") or 0 for r in rows]
    return max(q), sum(q) / len(q), q[-1], max(b)


# ------------------------------------------------------------ points (30)
_POINT_COLS = [
    "sweep_run_id", "pool", "window_name", "timing", "speedup",
    "llm_workers", "encoder_workers", "image_px", "encoder_batch_images", "mechanism",
    "base_req_per_s", "base_img_per_s", "base_input_tok_per_s", "base_output_tok_per_s",
    "offered_req_per_s", "offered_img_per_s", "offered_input_tok_per_s",
    "offered_output_tok_per_s", "offered_total_tok_per_s",
    "requests", "total_images", "horizon_s",
    "measured_req_per_s", "measured_output_tok_s", "measured_total_tok_s",
    "measured_duration_ms", "completed_requests", "sim_wall_time_ms", "driver_wall_s",
    "ttft_mean_ms", "ttft_median_ms", "ttft_p90_ms", "ttft_p99_ms", "ttft_max_ms",
    "tpot_mean_ms", "tpot_median_ms", "tpot_p90_ms", "tpot_p99_ms", "tpot_max_ms",
    "itl_mean_ms", "itl_median_ms", "itl_p90_ms", "itl_p99_ms", "itl_max_ms",
    "e2e_mean_ms", "e2e_median_ms", "e2e_p90_ms", "e2e_p99_ms", "e2e_max_ms", "itl_ok",
    "enc_delay_p50_ms", "enc_delay_p90_ms", "enc_delay_p99_ms", "enc_delay_max_ms",
    "enc_service_p50_ms", "enc_service_p90_ms", "enc_service_p99_ms",
    "enc_batch_service_p50_ms", "enc_batch_service_p90_ms", "enc_batch_service_p99_ms",
    "enc_batch_service_max_ms",
    "handoff_p50_ms", "handoff_p90_ms", "handoff_p99_ms", "handoff_max_ms",
    "encoder_utilization", "queue_divergent", "batches", "vision_sim_end_s",
    "queue_imgs_max", "queue_imgs_mean", "queue_imgs_final", "busy_workers_max",
    "sla_metric", "sla_metric_p99_ms", "sla_threshold_ms", "over_threshold",
    "exit_code", "trace_path", "report_path", "stats_path", "series_path",
    "report_run_id", "series_run_id", "source_path",
]

_POINT_KEY = ["sweep_run_id", "pool", "window_name", "timing", "speedup"]

# (json dict, json key) -> column, for the distribution sub-objects
_DIST = {
    "ttft_ms": [("mean", "ttft_mean_ms"), ("median", "ttft_median_ms"),
                ("p90", "ttft_p90_ms"), ("p99", "ttft_p99_ms"), ("max", "ttft_max_ms")],
    "tpot_ms": [("mean", "tpot_mean_ms"), ("median", "tpot_median_ms"),
                ("p90", "tpot_p90_ms"), ("p99", "tpot_p99_ms"), ("max", "tpot_max_ms")],
    "itl_ms": [("mean", "itl_mean_ms"), ("median", "itl_median_ms"),
               ("p90", "itl_p90_ms"), ("p99", "itl_p99_ms"), ("max", "itl_max_ms")],
    "e2e_ms": [("mean", "e2e_mean_ms"), ("median", "e2e_median_ms"),
               ("p90", "e2e_p90_ms"), ("p99", "e2e_p99_ms"), ("max", "e2e_max_ms")],
    "encoder_delay_ms": [("p50", "enc_delay_p50_ms"), ("p90", "enc_delay_p90_ms"),
                         ("p99", "enc_delay_p99_ms"), ("max", "enc_delay_max_ms")],
    "encoder_service_ms": [("p50", "enc_service_p50_ms"), ("p90", "enc_service_p90_ms"),
                           ("p99", "enc_service_p99_ms")],
    "encoder_batch_service_ms": [("p50", "enc_batch_service_p50_ms"),
                                 ("p90", "enc_batch_service_p90_ms"),
                                 ("p99", "enc_batch_service_p99_ms"),
                                 ("max", "enc_batch_service_max_ms")],
    "handoff_ms": [("p50", "handoff_p50_ms"), ("p90", "handoff_p90_ms"),
                   ("p99", "handoff_p99_ms"), ("max", "handoff_max_ms")],
}


def _point_row(pt, thresholds, source_path):
    """One sweep_point row from a per-point dict (same shape in summary.points[])."""
    pool = pt.get("pool")
    r = {"sweep_run_id": SWEEP_RUN_ID, "pool": pool,
         "window_name": pt.get("window"), "timing": pt.get("timing"),
         "speedup": pt.get("speedup"),
         "llm_workers": pt.get("llm_workers"),
         "encoder_workers": pt.get("encoder_workers"),
         "image_px": pt.get("image_px"),
         "encoder_batch_images": pt.get("encoder_batch_images"),
         "mechanism": pt.get("mechanism"),
         "base_req_per_s": _g(pt, "base", "req_per_s"),
         "base_img_per_s": _g(pt, "base", "img_per_s"),
         "base_input_tok_per_s": _g(pt, "base", "input_tok_per_s"),
         "base_output_tok_per_s": _g(pt, "base", "output_tok_per_s"),
         "offered_req_per_s": _g(pt, "offered", "req_per_s"),
         "offered_img_per_s": _g(pt, "offered", "img_per_s"),
         "offered_input_tok_per_s": _g(pt, "offered", "input_tok_per_s"),
         "offered_output_tok_per_s": _g(pt, "offered", "output_tok_per_s"),
         "offered_total_tok_per_s": _g(pt, "offered", "total_tok_per_s"),
         "requests": pt.get("requests") or _g(pt, "base", "requests"),
         "total_images": pt.get("total_images"),
         "horizon_s": pt.get("horizon_s") or _g(pt, "base", "horizon_s"),
         "measured_req_per_s": _g(pt, "measured", "request_throughput_rps"),
         "measured_output_tok_s": _g(pt, "measured", "output_throughput_tok_s"),
         "measured_total_tok_s": _g(pt, "measured", "total_throughput_tok_s"),
         "measured_duration_ms": _g(pt, "measured", "duration_ms"),
         "completed_requests": _g(pt, "measured", "completed_requests"),
         "sim_wall_time_ms": _g(pt, "measured", "sim_wall_time_ms"),
         "driver_wall_s": _g(pt, "measured", "driver_wall_s"),
         "itl_ok": pt.get("_itl_ok"),
         "encoder_utilization": pt.get("encoder_utilization"),
         "queue_divergent": pt.get("queue_divergent"),
         "batches": pt.get("batches"),
         "vision_sim_end_s": pt.get("vision_sim_end_s"),
         "exit_code": pt.get("exit_code"),
         "trace_path": pt.get("trace"),
         "report_path": pt.get("report"),
         "stats_path": pt.get("stats"),
         "series_path": pt.get("series"),
         "source_path": source_path}

    for obj, pairs in _DIST.items():
        sub = pt.get(obj) or {}
        for jk, col in pairs:
            r[col] = sub.get(jk)

    r["report_run_id"] = _run_id_for(pt.get("report"))
    r["series_run_id"] = _run_id_for(pt.get("series"))

    (r["queue_imgs_max"], r["queue_imgs_mean"],
     r["queue_imgs_final"], r["busy_workers_max"]) = _queue_summary(pt.get("series"))

    metric_name, thr_key = _SLA.get(pool, (None, None))
    r["sla_metric"] = metric_name
    r["sla_metric_p99_ms"] = (r.get("ttft_p99_ms") if pool == "llm"
                              else r.get("enc_delay_p99_ms"))
    r["sla_threshold_ms"] = thresholds.get(thr_key)
    if r["sla_metric_p99_ms"] is not None and r["sla_threshold_ms"] is not None:
        r["over_threshold"] = r["sla_metric_p99_ms"] > r["sla_threshold_ms"]
    return r


def _thresholds(summary):
    t = summary.get("thresholds") or {}
    return {"thr_encoder_delay_p99_ms": t.get("vision_encoder_delay_p99_ms"),
            "thr_ttft_p99_ms": t.get("llm_ttft_p99_ms"),
            "thr_itl_p99_ms": t.get("llm_itl_p99_ms"),
            "threshold_note": t.get("note")}


def _load_points(idx, reload, thresholds):
    """The 30 per-point JSONs at the top level of sweeps/."""
    nf = nr = 0
    pending = []
    for path in sorted(glob.glob(f"{SWEEPS}/*.json")):
        if os.path.basename(path) == "summary.json":
            continue
        prep = _prep(path, idx, reload)
        if prep is None:
            continue
        sha, nbytes = prep
        with open(path) as f:
            pt = json.load(f)
        if not pt.get("pool"):
            continue
        pending.append((path, sha, nbytes, _point_row(pt, thresholds, path)))
        nf += 1
        nr += 1

    for i in range(0, len(pending), 10):
        chunk = pending[i:i + 10]
        _run(ic.multi_upsert_sql("sweep_point", _POINT_COLS,
                                 [r for _, _, _, r in chunk], _POINT_KEY),
             *[ic.ingest_sql(p, s, KIND, 1, SWEEP_RUN_ID, b)
               for p, s, b, _ in chunk])
    return nf, nr


# ---------------------------------------------------------- summary.json
_CURVE_COLS = ["sweep_run_id", "pool", "window_name", "timing", "sla_metric",
               "threshold_ms", "n_points", "speedups", "metric_ms", "offered",
               "offered_unit", "metric_at_s1_ms", "offered_at_s1",
               "knee_speedup", "knee_offered", "knee_metric_ms",
               "first_over_speedup", "first_over_metric_ms", "knee_is_itl_bound",
               "knee_censored", "over_at_s1", "saturated_in_range", "monotonic_ok",
               "monotonicity_violations", "source_path"]
_CURVE_KEY = ["sweep_run_id", "pool", "window_name", "timing"]

_DEC_COLS = ["sweep_run_id", "window_name", "llm_timing", "vision_knee_speedup",
             "llm_knee_speedup", "knees_differ", "llm_over_vision_knee_ratio",
             "source_path"]
_DEC_KEY = ["sweep_run_id", "window_name", "llm_timing"]


def _curve_row(key, c, points_by_key, path):
    """One sweep_curve row; derives the columns summary.json does not carry."""
    pool, window, timing = key.split("|")
    speeds = c.get("speedups") or []
    metric = c.get("metric") or []
    offered = c.get("offered") or []
    knee = c.get("knee_speedup")
    first_over = c.get("first_over_speedup")

    def at(s, arr):
        """Value in an index-aligned array at speedup s."""
        if s is None:
            return None
        try:
            return arr[speeds.index(s)]
        except (ValueError, IndexError):
            return None

    # ITL-bound: the point AFTER the knee still meets TTFT but fails ITL.
    itl_bound = None
    if pool == "llm" and knee is not None:
        succ = [s for s in speeds if s > knee]
        if succ:
            nxt = points_by_key.get((pool, window, timing, succ[0]))
            if nxt is not None:
                over_ttft = nxt.get("over_threshold")
                ok_itl = nxt.get("itl_ok")
                if over_ttft is not None and ok_itl is not None:
                    itl_bound = (not over_ttft) and (not ok_itl)

    return {"sweep_run_id": SWEEP_RUN_ID, "pool": pool, "window_name": window,
            "timing": timing,
            "sla_metric": _SLA.get(pool, (None, None))[0],
            "threshold_ms": c.get("threshold"),
            "n_points": len(speeds),
            "speedups": speeds, "metric_ms": metric, "offered": offered,
            "offered_unit": "img_per_s" if pool == "vision" else "req_per_s",
            "metric_at_s1_ms": at(1.0, metric),
            "offered_at_s1": at(1.0, offered),
            "knee_speedup": knee,
            "knee_offered": at(knee, offered),
            "knee_metric_ms": at(knee, metric),
            "first_over_speedup": first_over,
            "first_over_metric_ms": at(first_over, metric),
            "knee_is_itl_bound": itl_bound,
            "knee_censored": (not c.get("saturated_in_range")
                              if c.get("saturated_in_range") is not None else None),
            "over_at_s1": (first_over == 1.0) if first_over is not None else None,
            "saturated_in_range": c.get("saturated_in_range"),
            "monotonic_ok": c.get("monotonic_ok"),
            "monotonicity_violations": [str(v) for v in
                                        (c.get("monotonicity_violations") or [])],
            "source_path": path}


def _load_summary(idx, reload):
    """summary.json -> sweep_run + sweep_window + sweep_curve + sweep_decoupling.

    Returns (files, rows, thresholds) -- thresholds are needed by _load_points
    even when summary.json itself is unchanged, so they are always parsed.
    """
    path = f"{SWEEPS}/summary.json"
    with open(path) as f:
        s = json.load(f)
    thr = _thresholds(s)

    prep = _prep(path, idx, reload)
    if prep is None:
        return 0, 0, thr
    sha, nbytes = prep

    points = s.get("points") or []
    curves = s.get("curves") or {}
    sanity = s.get("sanity") or {}

    run = {"sweep_run_id": SWEEP_RUN_ID,
           "generated_utc": s.get("generated_utc"),
           "mech_llm": _g(s, "mechanisms", "llm"),
           "mech_vision": _g(s, "mechanisms", "vision"),
           "n_points": len(points),
           "n_curves": len(curves),
           "all_exit_codes_zero": sanity.get("all_exit_codes_zero"),
           "n_offered_scaling_issues": len(sanity.get("offered_scaling_issues") or []),
           "n_nonmonotonic_curves": len(sanity.get("nonmonotonic_curves") or []),
           "source_path": path}
    run.update(thr)

    wins = [{"sweep_run_id": SWEEP_RUN_ID, "window_name": w,
             "trace_offset": v.get("offset"), "max_requests": v.get("max_requests"),
             "note": v.get("note"), "source_path": path}
            for w, v in (s.get("windows") or {}).items()]

    # index summary points so the curve derivation can look up the successor point
    pbk = {(p.get("pool"), p.get("window"), p.get("timing"), p.get("speedup")):
           _point_row(p, thr, path) for p in points}

    curve_rows = [_curve_row(k, c, pbk, path) for k, c in curves.items()]

    dec_rows = []
    for k, d in (s.get("decoupling") or {}).items():
        window, llm_tag = k.split("|")
        dec_rows.append({"sweep_run_id": SWEEP_RUN_ID, "window_name": window,
                         "llm_timing": llm_tag.replace("llm-", ""),
                         "vision_knee_speedup": d.get("vision_knee_speedup"),
                         "llm_knee_speedup": d.get("llm_knee_speedup"),
                         "knees_differ": d.get("knees_differ"),
                         "llm_over_vision_knee_ratio": d.get("llm_over_vision_knee_ratio"),
                         "source_path": path})

    nrows = 1 + len(wins) + len(curve_rows) + len(dec_rows)
    _run(ic.upsert_sql("sweep_run", run, "sweep_run_id"),
         ic.multi_upsert_sql("sweep_window",
                             ["sweep_run_id", "window_name", "trace_offset",
                              "max_requests", "note", "source_path"],
                             wins, ["sweep_run_id", "window_name"]),
         ic.multi_upsert_sql("sweep_curve", _CURVE_COLS, curve_rows, _CURVE_KEY),
         ic.multi_upsert_sql("sweep_decoupling", _DEC_COLS, dec_rows, _DEC_KEY),
         ic.ingest_sql(path, sha, KIND, nrows, SWEEP_RUN_ID, nbytes))
    return 1, nrows, thr


# ------------------------------------------------------------------ driver
def load_sweeps(idx, reload):
    """K25 entrypoint. Returns (files_loaded, rows_loaded)."""
    nf, nr, thr = _load_summary(idx, reload)
    f, r = _load_points(idx, reload, thr)
    return nf + f, nr + r


def main():
    reload = "--reload" in sys.argv
    idx = ic.load_ingest_index()
    nf, nr = load_sweeps(idx, reload)
    print(f"[K25   sweeps          ] files={nf:5d} rows={nr:13,d}", flush=True)


if __name__ == "__main__":
    main()
