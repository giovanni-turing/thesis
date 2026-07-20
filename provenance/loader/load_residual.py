#!/usr/bin/env python3
"""K27/K28/K29 loaders -- the small residual artifacts that each back a
published number and did not fit any existing kind.

  K27  predictors/results/ewma_cal_manifest.json
         -> ewma_cal_manifest (1) + ewma_cal_coverage (8) + ewma_cal_param (24)
       The conformal calibration behind the EWMA predictor's intervals.

  K28  verification/rerun_b1_results.json
         -> rerun_b1_window (1) + rerun_b1_curve_point (~16)
       burst1's encoder optimum recomputed under the stage-conditional
       (image-bearing requests only) metric. NOT a correction of a published
       number -- see the rerun_b1_window table comment and the
       'alternative_metric' row in provenance.grid_correction.

  K29  analysis/trace_eda/series/rates_{1s,15s,30s,45s,1min}.parquet
         -> eda_rate_series (~2.76M, long format via COPY)
       The binned arrival-rate series the Hurst / Fano / CV^2 statistics in
       provenance.eda_metric are computed FROM, so those statistics become
       recomputable rather than merely recorded.

Run:  cd /home/gio/tese/provenance/loader && python3 load_residual.py [--reload]
"""
import json
import os
import sys

import db
import ingest_common as ic

TESE = "/home/gio/tese"
EWMA_CAL = f"{TESE}/predictors/results/ewma_cal_manifest.json"
RERUN_B1 = f"{TESE}/verification/rerun_b1_results.json"
EDA_SERIES = f"{TESE}/analysis/trace_eda/series"
RESOLUTIONS = ["1s", "15s", "30s", "45s", "1min"]
SIGNALS = ["requests", "images", "ctx", "gen"]

MANIFEST_ID = "ewma:cal_manifest"
RERUN_ID = "verify:rerun_b1"


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


# ------------------------------------------------------------------- K27
def load_ewma_cal(idx, reload):
    """K27: EWMA conformal calibration manifest."""
    if not os.path.exists(EWMA_CAL):
        print(f"[K27] MISSING {EWMA_CAL}", file=sys.stderr, flush=True)
        return 0, 0
    prep = _prep(EWMA_CAL, idx, reload)
    if prep is None:
        return 0, 0
    sha, nbytes = prep
    with open(EWMA_CAL) as f:
        d = json.load(f)

    nominal = d.get("nominal")
    man = {"manifest_id": MANIFEST_ID,
           "source_parquet": d.get("source"),
           "t0_eval": d.get("T0_eval"),
           "nominal": nominal,
           "resolution": d.get("resolution"),
           "n_calib": d.get("n_calib"),
           "n_eval": d.get("n_eval"),
           "wsc_k": (d.get("params") or {}).get("wsc_k"),
           "source_path": EWMA_CAL}

    cov = [{"manifest_id": MANIFEST_ID, "method": m, "split": s,
            "coverage": v, "nominal": nominal}
           for m, splits in (d.get("coverage") or {}).items()
           for s, v in splits.items()]

    par = [{"manifest_id": MANIFEST_ID, "param_kind": kind,
            "horizon": int(h), "value": v}
           for kind in ("add_qh", "mult_qh")
           for h, v in ((d.get("params") or {}).get(kind) or {}).items()]

    n = 1 + len(cov) + len(par)
    _run(ic.upsert_sql("ewma_cal_manifest", man, "manifest_id"),
         ic.multi_upsert_sql("ewma_cal_coverage",
                             ["manifest_id", "method", "split", "coverage", "nominal"],
                             cov, ["manifest_id", "method", "split"]),
         ic.multi_upsert_sql("ewma_cal_param",
                             ["manifest_id", "param_kind", "horizon", "value"],
                             par, ["manifest_id", "param_kind", "horizon"]),
         ic.ingest_sql(EWMA_CAL, sha, "K27", n, MANIFEST_ID, nbytes))
    return 1, n


# ------------------------------------------------------------------- K28
_B1_COLS = ["rerun_id", "window_name", "sla_ms", "trace_offset", "max_requests",
            "span_h", "total_reqs", "n_image_reqs", "grid_cstar_reported",
            "current_mixed_cstar", "current_mixed_p99", "image_p99_at_current_cstar",
            "corrected_image_cstar", "corrected_image_p99", "delta_workers",
            "gpuh_5090_old", "gpuh_5090_new", "gpuh_h100", "llm_gpus",
            "reproduces_grid_mixed_cstar", "source_path"]

_B1_PT_COLS = ["rerun_id", "window_name", "encoder_c", "mixed_p99_ms",
               "image_p99_ms", "divergent", "mixed_feasible", "image_feasible"]

_STALE_REASON = (
    "deployable_static_old/new were computed while burst5's C* was still the "
    "pre-correction 16, and burst5 was the window forcing the fleet-wide "
    "maximum; after the burst5 supersession the deployable static fleet is C=8 "
    "(see provenance.grid_correction, burst5:c_star:supersession)")


def load_rerun_b1(idx, reload):
    """K28: per-window C* under the stage-conditional (image-only) metric.

    Despite the filename, the artifact covers ALL SEVEN windows, so both
    child tables are keyed by window_name as well as rerun_id.
    """
    if not os.path.exists(RERUN_B1):
        print(f"[K28] MISSING {RERUN_B1}", file=sys.stderr, flush=True)
        return 0, 0
    prep = _prep(RERUN_B1, idx, reload)
    if prep is None:
        return 0, 0
    sha, nbytes = prep
    with open(RERUN_B1) as f:
        d = json.load(f)

    wins = d.get("windows") or {}
    run = {"rerun_id": RERUN_ID, "sla_ms": d.get("sla_ms"), "n_windows": len(wins),
           "deployable_static_old": d.get("deployable_static_old"),
           "deployable_static_new": d.get("deployable_static_new"),
           "burst5_c16_image_p99": d.get("burst5_c16_image_p99"),
           "burst5_c16_mixed_p99": d.get("burst5_c16_mixed_p99"),
           "deployable_is_stale": True, "stale_reason": _STALE_REASON,
           "source_path": RERUN_B1}
    nrows = 1
    stmts = [ic.upsert_sql("rerun_b1_run", run, "rerun_id")]
    for wname, w in wins.items():
        row = {"rerun_id": RERUN_ID, "window_name": wname,
               "sla_ms": d.get("sla_ms"),
               "trace_offset": w.get("offset"),
               "max_requests": w.get("max_requests"),
               "span_h": w.get("span_h"),
               "total_reqs": w.get("total_reqs"),
               "n_image_reqs": w.get("n_image_reqs"),
               "grid_cstar_reported": w.get("grid_cstar_reported"),
               "current_mixed_cstar": w.get("current_mixed_cstar"),
               "current_mixed_p99": w.get("current_mixed_p99"),
               "image_p99_at_current_cstar": w.get("image_p99_at_current_cstar"),
               "corrected_image_cstar": w.get("corrected_image_cstar"),
               "corrected_image_p99": w.get("corrected_image_p99"),
               "delta_workers": w.get("delta_workers"),
               "gpuh_5090_old": w.get("gpuh_5090_old"),
               "gpuh_5090_new": w.get("gpuh_5090_new"),
               "gpuh_h100": w.get("gpuh_h100"),
               "llm_gpus": w.get("llm_gpus"),
               "reproduces_grid_mixed_cstar": w.get("reproduces_grid_mixed_cstar"),
               "source_path": RERUN_B1}
        pts = [{"rerun_id": RERUN_ID, "window_name": wname, "encoder_c": int(c),
                "mixed_p99_ms": p.get("mixed_p99"), "image_p99_ms": p.get("image_p99"),
                "divergent": p.get("div"),
                "mixed_feasible": p.get("mixed_feas"),
                "image_feasible": p.get("image_feas")}
               for c, p in (w.get("curve") or {}).items()]
        stmts.append(ic.multi_upsert_sql("rerun_b1_window", _B1_COLS, [row],
                                         ["rerun_id", "window_name"]))
        stmts.append(ic.multi_upsert_sql("rerun_b1_curve_point", _B1_PT_COLS, pts,
                                         ["rerun_id", "window_name", "encoder_c"]))
        nrows += 1 + len(pts)

    if not stmts:
        return 0, 0
    _run(*stmts, ic.ingest_sql(RERUN_B1, sha, "K28", nrows, RERUN_ID, nbytes))
    return 1, nrows


# ------------------------------------------------------------------- K29
def load_eda_rates(idx, reload):
    """K29: binned arrival-rate series, wide parquet -> long rows via COPY."""
    import pyarrow.parquet as pq

    nf = nr = 0
    for res in RESOLUTIONS:
        path = f"{EDA_SERIES}/rates_{res}.parquet"
        if not os.path.exists(path):
            print(f"[K29] MISSING {path}", file=sys.stderr, flush=True)
            continue
        prep = _prep(path, idx, reload)
        if prep is None:
            continue
        sha, nbytes = prep

        tbl = pq.read_table(path)
        cols = set(tbl.schema.names)
        signals = [s for s in SIGNALS if s in cols]
        ts = tbl.column("window_start").to_pylist()
        data = {s: tbl.column(s).to_pylist() for s in signals}

        # rewrite this resolution wholesale so a --reload cannot leave orphans
        db.run_sql("delete from provenance.eda_rate_series "
                   f"where resolution={ic.lit(res)}")

        def rows():
            for s in signals:
                vals = data[s]
                for t, v in zip(ts, vals):
                    yield (res, t.isoformat(sep=" "), s, v)

        n = db.copy_rows("eda_rate_series",
                         ["resolution", "ts", "signal", "value"], rows())
        db.run_sql(ic.ingest_sql(path, sha, "K29", n, f"eda:rates_{res}", nbytes))
        nf += 1
        nr += n
    return nf, nr


def main():
    reload = "--reload" in sys.argv
    idx = ic.load_ingest_index()
    for kind, name, fn in (("K27", "ewma_cal", load_ewma_cal),
                           ("K28", "rerun_b1", load_rerun_b1),
                           ("K29", "eda_rates", load_eda_rates)):
        nf, nr = fn(idx, reload)
        print(f"[{kind:5} {name:16}] files={nf:5d} rows={nr:13,d}", flush=True)


if __name__ == "__main__":
    main()
