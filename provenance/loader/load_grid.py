#!/usr/bin/env python3
"""K20 loader -- family "grid": the static-optimal grid sweep.

Source tree: /home/gio/tese/simulation/results/grid/

Ingests (all via ingest_common.ingest_sql with kind K20, sha256-gated):
  grid_summary.json              -> grid_run_summary + grid_window (7)
                                    + curve cross-check into the point tables
  vision_<w>_C<C>.json      (48) -> grid_vision_point
  llm_<w>_C<C>_N<N>[_TP<tp>]_aic.json (58) -> grid_llm_point
  closeout/closeout_summary.json -> grid_closeout_run + grid_closeout_variant (35)
  logs/*.log (107) + closeout/logs/*.log (42) -> grid_command  (header lines only)

Deliberately NOT ingested (see 05_grid.sql header for the full rationale):
  traces/*.jsonl (49, simulator INPUT ~14 MB each) -- path recorded only
  reports/*.report.json (58) and closeout/reports/*.report.json (35)
      -- already loaded by kind K1 into llm_run_summary; soft-ref'd via report_run_id
  traces/*.jsonl.stats.json (49)
      -- already loaded by kind K3 into encoder_run_summary; soft-ref'd via stats_run_id
  closeout/{router,binding}_*.json (35) -- byte-identical dups of closeout_summary.results

Run:  cd /home/gio/tese/provenance/loader && python3 load_grid.py [--reload]
"""
import glob
import json
import os
import re
import sys

import db
import ingest_common as ic

GRID = "/home/gio/tese/simulation/results/grid"
KIND = "K20"
GRID_RUN_ID = "grid:grid_summary"
CLOSEOUT_RUN_ID = "grid:closeout_summary"

_KNOB = {"credit": "overlap_score_credit", "pls": "prefill_load_scale"}


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
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


# ------------------------------------------------------------------ summary
_SUMMARY_COLS = [
    "grid_run_id", "generated_utc", "timing", "sla_vision_p99_ms",
    "sla_llm_ttft_p99_ms", "sla_llm_itl_p99_ms", "n_windows", "n_vision_points",
    "n_llm_points", "n_failures", "failures", "static_encoder_workers",
    "static_llm_tp", "static_llm_workers", "static_llm_gpus",
    "static_binding_window", "static_note", "headline_note", "source_path", "raw"]

_WINDOW_COLS = [
    "grid_run_id", "window_name", "trace_offset", "max_requests", "requests",
    "span_s", "span_h", "mean_req_per_s", "mean_img_per_s", "peak_1min_img_per_s",
    "text_only_fraction", "c_star", "tp_star", "n_star", "llm_gpus",
    "gpu_hours_rtx5090", "gpu_hours_h100", "overprovision_vision_x",
    "overprovision_llm_x", "n_vision_points", "n_llm_points", "note", "source_path"]


def _load_summary(idx, reload):
    """grid_summary.json -> grid_run_summary + grid_window.

    Returns (files, rows, curves) where curves = (vision_curve, llm_curve, per_window)
    keyed for the point loaders' cross-check columns. Curves are returned even when the
    file is skipped as unchanged, so the point loaders stay independent.
    """
    path = f"{GRID}/grid_summary.json"
    j = json.load(open(path))
    per_window = j.get("per_window") or {}
    windows = j.get("windows") or {}
    over = _g(j, "headline", "overprovision_vs_per_window") or {}
    static = _g(j, "headline", "static_all_windows") or {}

    vcurve = {(w, int(c)): v for w, pw in per_window.items()
              for c, v in (pw.get("vision_curve") or {}).items()}
    lcurve = {}
    for w, pw in per_window.items():
        for key, v in (pw.get("llm_curve") or {}).items():
            m = re.match(r"C(\d+)_TP(\d+)_N(\d+)$", key)
            if m:
                lcurve[(w, int(m.group(1)), int(m.group(2)), int(m.group(3)))] = v
    curves = (vcurve, lcurve, per_window, static)

    prep = _prep(path, idx, reload)
    if not prep:
        return 0, 0, curves
    sha, nbytes = prep

    wrows = []
    for wname, w in windows.items():
        pw = per_window.get(wname) or {}
        ov = over.get(wname) or {}
        gh = pw.get("gpu_hours") or {}
        wrows.append({
            "grid_run_id": GRID_RUN_ID, "window_name": wname,
            "trace_offset": w.get("offset"), "max_requests": w.get("max_requests"),
            "requests": w.get("requests"), "span_s": w.get("span_s"),
            "span_h": pw.get("span_h"), "mean_req_per_s": w.get("mean_req_per_s"),
            "mean_img_per_s": w.get("mean_img_per_s"),
            "peak_1min_img_per_s": w.get("peak_1min_img_per_s"),
            "text_only_fraction": w.get("text_only_fraction"),
            "c_star": pw.get("c_star"), "tp_star": pw.get("tp_star"),
            "n_star": pw.get("n_star"), "llm_gpus": pw.get("llm_gpus"),
            "gpu_hours_rtx5090": gh.get("rtx5090"), "gpu_hours_h100": gh.get("h100"),
            "overprovision_vision_x": ov.get("vision_x"),
            "overprovision_llm_x": ov.get("llm_x"),
            "n_vision_points": len(pw.get("vision_curve") or {}),
            "n_llm_points": len(pw.get("llm_curve") or {}),
            "note": w.get("note"), "source_path": path})

    raw = {k: v for k, v in j.items() if k != "per_window"}
    raw["per_window_scalars"] = {
        w: {k: v for k, v in pw.items() if k not in ("vision_curve", "llm_curve")}
        for w, pw in per_window.items()}
    failures = j.get("failures") or []

    srow = {
        "grid_run_id": GRID_RUN_ID, "generated_utc": j.get("generated_utc"),
        "timing": j.get("timing"),
        "sla_vision_p99_ms": _g(j, "sla", "vision_p99_ms"),
        "sla_llm_ttft_p99_ms": _g(j, "sla", "llm_ttft_p99_ms"),
        "sla_llm_itl_p99_ms": _g(j, "sla", "llm_itl_p99_ms"),
        "n_windows": len(windows), "n_vision_points": len(vcurve),
        "n_llm_points": len(lcurve), "n_failures": len(failures),
        "failures": failures,
        "static_encoder_workers": static.get("encoder_workers"),
        "static_llm_tp": static.get("llm_tp"),
        "static_llm_workers": static.get("llm_workers"),
        "static_llm_gpus": static.get("llm_gpus"),
        "static_binding_window": static.get("llm_config_binding_window"),
        "static_note": static.get("note"),
        "headline_note": _g(j, "headline", "note"),
        "source_path": path, "raw": raw}

    n = 1 + len(wrows)
    _run(ic.upsert_sql("grid_run_summary", srow, "grid_run_id",
                       jsonb_cols=("failures", "raw")),
         ic.multi_upsert_sql("grid_window", _WINDOW_COLS, wrows,
                             ["grid_run_id", "window_name"]),
         ic.ingest_sql(path, sha, KIND, n, GRID_RUN_ID, nbytes))
    return 1, n, curves


# ------------------------------------------------------------------- vision
_VISION_COLS = [
    "grid_run_id", "window_name", "encoder_workers", "offered_img_per_s",
    "horizon_s", "delay_p50_ms", "delay_p90_ms", "delay_p99_ms", "delay_max_ms",
    "encoder_utilization", "queue_divergent", "feasible", "is_c_star",
    "in_summary_curve", "curve_p99_ms", "stats_run_id", "trace_path", "stats_path",
    "source_path"]


def _load_vision(idx, reload, curves):
    vcurve, _, per_window, _ = curves
    nf = nr = 0
    for path in sorted(glob.glob(f"{GRID}/vision_*.json")):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        j = json.load(open(path))
        w = j.get("window")
        c = j.get("encoder_workers")
        d = j.get("encoder_delay_ms") or {}
        cur = vcurve.get((w, c))
        stats_path = j.get("stats")
        row = {
            "grid_run_id": GRID_RUN_ID, "window_name": w, "encoder_workers": c,
            "offered_img_per_s": j.get("offered_img_per_s"),
            "horizon_s": j.get("horizon_s"),
            "delay_p50_ms": d.get("p50"), "delay_p90_ms": d.get("p90"),
            "delay_p99_ms": d.get("p99"), "delay_max_ms": d.get("max"),
            "encoder_utilization": j.get("encoder_utilization"),
            "queue_divergent": j.get("queue_divergent"),
            "feasible": j.get("feasible"),
            "is_c_star": _g(per_window, w, "c_star") == c,
            "in_summary_curve": cur is not None,
            "curve_p99_ms": (cur or {}).get("p99"),
            "stats_run_id": ("grid:" + os.path.basename(stats_path)[:-len(".jsonl.stats.json")]
                             if stats_path else None),
            "trace_path": j.get("trace"), "stats_path": stats_path,
            "source_path": path}
        _run(ic.upsert_sql("grid_vision_point", row,
                           ["grid_run_id", "window_name", "encoder_workers"]),
             ic.ingest_sql(path, sha, KIND, 1, GRID_RUN_ID, nbytes))
        nf += 1
        nr += 1
    return nf, nr


# ---------------------------------------------------------------------- llm
_LLM_COLS = [
    "grid_run_id", "window_name", "encoder_workers", "tp", "llm_workers", "gpus",
    "timing", "ttft_mean_ms", "ttft_median_ms", "ttft_p90_ms", "ttft_p99_ms",
    "ttft_max_ms", "itl_mean_ms", "itl_median_ms", "itl_p90_ms", "itl_p99_ms",
    "itl_max_ms", "tpot_mean_ms", "tpot_median_ms", "tpot_p90_ms", "tpot_p99_ms",
    "tpot_max_ms", "completed_requests", "driver_wall_s", "feasible", "is_optimal",
    "is_static_config", "in_summary_curve", "curve_ttft_p99_ms", "curve_itl_p99_ms",
    "report_run_id", "report_path", "trace_path", "source_path"]

_PCT = ("mean", "median", "p90", "p99", "max")


def _load_llm(idx, reload, curves):
    _, lcurve, per_window, static = curves
    nf = nr = 0
    for path in sorted(glob.glob(f"{GRID}/llm_*.json")):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        j = json.load(open(path))
        w, c = j.get("window"), j.get("encoder_workers")
        n = j.get("llm_workers")
        # TP1 runs omit "tp"/"gpus" entirely (implicit tp=1); grid_summary's llm_curve
        # key spells them out as C<c>_TP1_N<n>, so normalize here.
        tp = j.get("tp") or 1
        gpus = j.get("gpus")
        if gpus is None:
            gpus = tp * n if n is not None else None
        pw = per_window.get(w) or {}
        cur = lcurve.get((w, c, tp, n)) or {}
        report_path = j.get("report")
        row = {
            "grid_run_id": GRID_RUN_ID, "window_name": w, "encoder_workers": c,
            "tp": tp, "llm_workers": n, "gpus": gpus,
            "timing": j.get("timing"),
            "completed_requests": j.get("completed_requests"),
            "driver_wall_s": j.get("driver_wall_s"),
            "feasible": j.get("feasible"),
            "is_optimal": (pw.get("c_star") == c and pw.get("tp_star") == tp
                           and pw.get("n_star") == n),
            "is_static_config": (static.get("llm_tp") == tp
                                 and static.get("llm_workers") == n),
            "in_summary_curve": bool(cur),
            "curve_ttft_p99_ms": cur.get("ttft_p99"),
            "curve_itl_p99_ms": cur.get("itl_p99"),
            "report_run_id": ("grid:" + os.path.basename(report_path)[:-len(".report.json")]
                              if report_path else None),
            "report_path": report_path, "trace_path": j.get("trace"),
            "source_path": path}
        for metric in ("ttft", "itl", "tpot"):
            blk = j.get(f"{metric}_ms") or {}
            for p in _PCT:
                row[f"{metric}_{p}_ms"] = blk.get(p)
        _run(ic.upsert_sql("grid_llm_point", row,
                           ["grid_run_id", "window_name", "encoder_workers", "tp",
                            "llm_workers"]),
             ic.ingest_sql(path, sha, KIND, 1, GRID_RUN_ID, nbytes))
        nf += 1
        nr += 1
    return nf, nr


# ----------------------------------------------------------------- closeout
_CO_SUM_COLS = [
    "closeout_run_id", "generated_utc", "binding_c", "binding_tp", "binding_n",
    "n_variants", "n_results", "n_verdict_flips", "n_binding_infeasible",
    "n_failures", "conclusion", "router_variants", "router_verdict_flips",
    "binding_infeasible", "failures", "source_path"]

_CO_VAR_COLS = [
    "closeout_run_id", "tag", "family", "window_name", "encoder_workers", "tp",
    "llm_workers", "variant", "variant_knob", "variant_value", "ttft_p99_ms",
    "itl_p99_ms", "feasible", "wall_s", "report_run_id", "source_path"]

_TAG_RE = re.compile(r"^(router|binding)_(\w+?)_C(\d+)_TP(\d+)_N(\d+)(?:_(.+))?$")


def _parse_tag(tag):
    m = _TAG_RE.match(tag)
    if not m:
        return {}
    family, w, c, tp, n, variant = m.groups()
    knob = val = None
    if variant:
        mv = re.match(r"([a-z]+)([\d.]+)$", variant)
        if mv:
            knob = _KNOB.get(mv.group(1), mv.group(1))
            val = float(mv.group(2))
    return {"family": family, "window_name": w, "encoder_workers": int(c),
            "tp": int(tp), "llm_workers": int(n), "variant": variant,
            "variant_knob": knob, "variant_value": val}


def _load_closeout(idx, reload):
    path = f"{GRID}/closeout/closeout_summary.json"
    prep = _prep(path, idx, reload)
    if not prep:
        return 0, 0
    sha, nbytes = prep
    j = json.load(open(path))
    results = j.get("results") or {}
    flips = j.get("router_verdict_flips") or []
    infeas = j.get("binding_infeasible") or []
    failures = j.get("failures") or []
    bc = j.get("binding_config") or {}

    srow = {
        "closeout_run_id": CLOSEOUT_RUN_ID, "generated_utc": j.get("generated_utc"),
        "binding_c": bc.get("c"), "binding_tp": bc.get("tp"), "binding_n": bc.get("n"),
        "n_variants": len(j.get("router_variants") or {}), "n_results": len(results),
        "n_verdict_flips": len(flips), "n_binding_infeasible": len(infeas),
        "n_failures": len(failures), "conclusion": j.get("conclusion"),
        "router_variants": j.get("router_variants") or {},
        "router_verdict_flips": flips, "binding_infeasible": infeas,
        "failures": failures, "source_path": path}

    vrows = []
    for key, r in results.items():
        tag = r.get("tag") or key      # results{} keys are truncated for the binding family
        row = {"closeout_run_id": CLOSEOUT_RUN_ID, "tag": tag,
               "ttft_p99_ms": r.get("ttft_p99"), "itl_p99_ms": r.get("itl_p99"),
               "feasible": r.get("feasible"), "wall_s": r.get("wall_s"),
               "report_run_id": "grid:" + tag, "source_path": path}
        row.update(_parse_tag(tag))
        vrows.append(row)

    n = 1 + len(vrows)
    _run(ic.upsert_sql("grid_closeout_run", srow, "closeout_run_id",
                       jsonb_cols=("router_variants", "router_verdict_flips",
                                   "binding_infeasible", "failures")),
         ic.multi_upsert_sql("grid_closeout_variant", _CO_VAR_COLS, vrows,
                             ["closeout_run_id", "tag"]),
         ic.ingest_sql(path, sha, KIND, n, CLOSEOUT_RUN_ID, nbytes))
    return 1, n


# --------------------------------------------------------------------- logs
_CMD_COLS = ["log_path", "grid_run_id", "stage", "artifact_stem", "window_name",
             "encoder_workers", "tp", "llm_workers", "variant", "cmd", "cwd",
             "log_bytes"]


def _log_header(path, max_lines=8):
    """Read only the leading '# key: value' comment block."""
    out = {}
    with open(path, errors="replace") as f:
        for _ in range(max_lines):
            line = f.readline()
            if not line.startswith("# "):
                break
            k, _, v = line[2:].partition(": ")
            out[k.strip()] = v.strip()
    return out


def _stage_of(stem, is_closeout):
    if is_closeout:
        return "closeout_binding" if stem.startswith("binding") else "closeout_router"
    return "llm" if stem.startswith("grid_llm_") else "trace"


def _load_logs(idx, reload):
    nf = nr = 0
    pending = []
    for pat, is_co in ((f"{GRID}/logs/*.log", False),
                       (f"{GRID}/closeout/logs/*.log", True)):
        for path in sorted(glob.glob(pat)):
            prep = _prep(path, idx, reload)
            if not prep:
                continue
            sha, nbytes = prep
            stem = os.path.basename(path)[:-len(".log")]
            hdr = _log_header(path)
            row = {"log_path": path, "grid_run_id": GRID_RUN_ID,
                   "stage": _stage_of(stem, is_co), "artifact_stem": stem,
                   "cmd": hdr.get("cmd"), "cwd": hdr.get("cwd"),
                   "log_bytes": nbytes}
            if is_co:
                row.update({k: v for k, v in _parse_tag(stem).items()
                            if k != "family"})
            else:
                m = re.match(r"grid_(?:llm_)?(\w+?)_C(\d+)(?:_N(\d+))?(?:_TP(\d+))?",
                             stem)
                if m:
                    row["window_name"] = m.group(1)
                    row["encoder_workers"] = int(m.group(2))
                    row["llm_workers"] = int(m.group(3)) if m.group(3) else None
                    row["tp"] = int(m.group(4)) if m.group(4) else (
                        1 if stem.startswith("grid_llm_") else None)
            pending.append((path, sha, nbytes, row))
            nf += 1
            nr += 1

    for i in range(0, len(pending), 50):        # batch: 149 small rows
        chunk = pending[i:i + 50]
        _run(ic.multi_upsert_sql("grid_command", _CMD_COLS,
                                 [r for _, _, _, r in chunk], "log_path"),
             *[ic.ingest_sql(p, s, KIND, 1, GRID_RUN_ID, b)
               for p, s, b, _ in chunk])
    return nf, nr


# ------------------------------------------------------------------- driver
def load_grid(idx, reload):
    """K20 entrypoint. Returns (files_loaded, rows_loaded)."""
    nf = nr = 0
    f, r, curves = _load_summary(idx, reload)
    nf += f
    nr += r
    for fn in (_load_vision, _load_llm):
        f, r = fn(idx, reload, curves)
        nf += f
        nr += r
    for fn in (_load_closeout, _load_logs):
        f, r = fn(idx, reload)
        nf += f
        nr += r
    return nf, nr


def main():
    reload = "--reload" in sys.argv
    idx = ic.load_ingest_index()
    nf, nr = load_grid(idx, reload)
    print(f"[K20   grid            ] files={nf:5d} rows={nr:13,d}", flush=True)


if __name__ == "__main__":
    main()
