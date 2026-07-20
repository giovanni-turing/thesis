#!/usr/bin/env python3
"""K22 - family "eda": trace exploratory characterization (analysis/trace_eda/*_stats.json).

Backs tex/trace-eda.tex (Ch.3): the characterization of the 1,000,000-request, 168-hour
AzureLMMInferenceDataset2025 multimodal trace.

Load strategy
-------------
The 14 stats JSONs are structurally heterogeneous (scalars, nested percentile maps,
correlation matrices, ragged arrays), so the primary target is ONE tall table,
provenance.eda_metric, populated by an EXHAUSTIVE recursive flattening: every leaf of
every file becomes a row keyed by (script, dotted metric_path). Nothing is dropped or
rounded. Four small typed entity tables (eda_burst_episode, eda_request_class,
eda_request_archetype, eda_silhouette) are projected on top for the entities a reviewer
joins on; every value in them also exists in eda_metric under its original path.

Deliberate exclusions (see EXCLUDED at the bottom of this file for the machine-readable
list): l_silhouette_scan.json is a 4-decimal RECOMPUTATION of
l_request_clusters_stats.json:silhouette_by_k - its numbers are NOT ingested as metrics,
only its `provenance` string is attached to the eda_silhouette rows it corroborates.
m_global_percentiles.md is a Markdown rendering of m_gen_and_global_stats.json. Also
skipped: figures/, series/, __pycache__/, cufile.log, REPORT.md, summary.md, *.py.

Run:  cd /home/gio/tese/provenance/loader && python3 load_trace_eda.py [--reload]
"""
import json, math, os, re, sys
import db
import ingest_common as ic

EDA = "/home/gio/tese/analysis/trace_eda"
KIND = "K22"

# The 14 stats files, in script order. Everything else in the directory is excluded.
SCRIPTS = ["a_quality", "b_marginals", "c_temporal", "d_signals", "e_comprehensive",
           "f_fourier", "f2_fourier_ctx", "g_ctx", "i_burst_anatomy", "j_classes",
           "k_episode_clusters", "l_request_clusters", "m_gen_and_global",
           "q_multires_tails"]

SILHOUETTE_SCAN = f"{EDA}/l_silhouette_scan.json"   # provenance string only (see module doc)

EXCLUDED = {
    f"{EDA}/l_silhouette_scan.json":
        "rounded (4dp) recomputation of l_request_clusters_stats.json:silhouette_by_k; "
        "its `provenance` string is ingested onto eda_silhouette, its numbers are not",
    f"{EDA}/m_global_percentiles.md":
        "Markdown rendering of m_gen_and_global_stats.json (same numbers, rounded)",
    f"{EDA}/REPORT.md": "prose EDA report, not a measurement artifact",
    f"{EDA}/summary.md": "prose summary, not a measurement artifact",
    f"{EDA}/cufile.log": "cuFile driver log, no thesis content",
    f"{EDA}/figures": "rendered figures (derived from the stats JSONs)",
    f"{EDA}/series": "materialized rate series (n_materialize_series.py output, not a stats file)",
    f"{EDA}/__pycache__": "bytecode",
}

# ---------------------------------------------------------------- facet parsing
SIGNALS = {
    "requests", "images", "ctx", "gen",
    "req_per_s", "img_per_s", "tokens_per_s",
    "requests_per_s", "images_per_s", "ctx_tokens_per_s", "gen_tokens_per_s",
    "NumImages", "ContextTokens", "GeneratedTokens",
    "NumImages_multimodal", "NumImages_imagebearing",
    "ctx_signal", "gen_signal", "ctx_total", "ctx_multimodal", "ctx_text_only",
}
STATS = {"mean", "median", "min", "max", "count", "cv2", "sum", "r2", "share",
         "p1", "p10", "p50", "p90", "p95", "p99", "p99.9",
         "0.5", "0.9", "0.99", "0.999"}
_BIN_RE = re.compile(r"^(\d+(?:s|ms|min|h))$")
_BIN_SUFFIX_RE = re.compile(r"_(\d+(?:s|ms|min|h))$")
_FANO_PARENT = "fano_factor_by_window"
# c_temporal names its two aggregation windows window_1min / window_1s
_WINDOW_KEY_RE = re.compile(r"^window_(\d+(?:s|min|h))$")


def _facets(keys):
    """(signal, window_bin, stat) best-effort parse from the tuple of raw JSON keys."""
    ks = [k for k in keys if not k.startswith("[")]
    signal = window_bin = stat = None
    for i, k in enumerate(ks):
        if k in SIGNALS:
            signal = k
        m = _BIN_RE.match(k) or _WINDOW_KEY_RE.match(k)
        if m:
            window_bin = m.group(1)
        else:
            m2 = _BIN_SUFFIX_RE.search(k)
            if m2:
                window_bin = m2.group(1)
        if i > 0 and ks[i - 1] == _FANO_PARENT:
            window_bin = k          # bare s / 10s / min / 10min / h
    if ks and ks[-1] in STATS:
        stat = ks[-1]
    # normalise the ctx_*/gen_* container names to their bare signal
    if signal in ("ctx_signal", "ctx_total"):
        signal = "ctx"
    elif signal == "gen_signal":
        signal = "gen"
    return signal, window_bin, stat


# ------------------------------------------------------------------ flattening
def flatten(obj, keys=(), path=""):
    """Yield (path, keys, value) for every leaf. Lists index as name[0]; JSON nulls and
    empty containers are emitted too, so the key's existence is never lost."""
    if isinstance(obj, dict):
        if not obj:
            yield path, keys, "(empty object)"
            return
        for k, v in obj.items():
            kk = str(k)
            yield from flatten(v, keys + (kk,), f"{path}.{kk}" if path else kk)
    elif isinstance(obj, list):
        if not obj:
            yield path, keys, "(empty array)"
            return
        for i, v in enumerate(obj):
            yield from flatten(v, keys + (f"[{i}]",), f"{path}[{i}]")
    else:
        yield path, keys, obj


def _metric_row(script, run_id, path, keys, val):
    signal, window_bin, stat = _facets(keys)
    num = bl = txt = None
    if isinstance(val, bool):
        bl = val
    elif isinstance(val, (int, float)):
        if isinstance(val, float) and not math.isfinite(val):
            txt = repr(val)          # NaN/Inf kept as text; value_num stays NULL
        else:
            num = float(val)
    elif val is None:
        pass                          # JSON null: row exists, all value_* NULL
    else:
        txt = str(val)
    return {"script": script, "metric_path": path, "run_id": run_id, "signal": signal,
            "window_bin": window_bin, "stat": stat,
            "value_num": num, "value_bool": bl, "value_text": txt}


_METRIC_COLS = ["script", "metric_path", "run_id", "signal", "window_bin", "stat",
                "value_num", "value_bool", "value_text"]


# ------------------------------------------------------------- typed projections
_BURST_COLS = ["source_script", "start_ts", "peak_ts", "episode_kind", "rank_by_peak",
               "end_ts", "minutes", "onset_min", "decay_min", "duration_min",
               "peak_img_per_s", "peak_req_per_s", "ramp_img_per_s_per_min",
               "steepest_1min_jump_img_per_s", "ctx_p50", "cluster_id", "share_single",
               "share_tiled_small", "share_tiled_large", "share_frames",
               "dominant_class", "dominant_share", "run_id"]


def _bursts(j, script, run_id, attribution=None):
    """Typed burst-episode rows for c_temporal / i_burst_anatomy / k_episode_clusters."""
    out = []
    if script == "c_temporal":
        for i, e in enumerate(j["burst_episodes_img_gt_p99"]["top6"]):
            out.append({"source_script": script, "start_ts": e["start"], "peak_ts": None,
                        "episode_kind": "raw", "rank_by_peak": i + 1, "end_ts": e["end"],
                        "minutes": e.get("minutes"),
                        "peak_img_per_s": e.get("peak_img_per_s"),
                        "peak_req_per_s": e.get("peak_req_per_s"), "run_id": run_id})
    elif script == "i_burst_anatomy":
        for i, e in enumerate(j["top6_by_peak"]):
            a = (attribution or {}).get(e["peak"], {})
            sh = a.get("shares", {})
            out.append({"source_script": script, "start_ts": e["start_baseline"],
                        "peak_ts": e["peak"], "episode_kind": "merged",
                        "rank_by_peak": i + 1, "end_ts": e.get("end_baseline"),
                        "onset_min": e.get("onset_minutes"),
                        "decay_min": e.get("decay_minutes"),
                        "peak_img_per_s": e.get("peak_img_per_s"),
                        "ramp_img_per_s_per_min": e.get("ramp_img_per_s_per_min"),
                        "steepest_1min_jump_img_per_s": e.get("steepest_1min_jump_img_per_s"),
                        "share_single": sh.get("single"),
                        "share_tiled_small": sh.get("tiled_small"),
                        "share_tiled_large": sh.get("tiled_large"),
                        "share_frames": sh.get("frames"),
                        "dominant_class": a.get("dominant_class"),
                        "dominant_share": a.get("dominant_share"), "run_id": run_id})
    elif script == "k_episode_clusters":
        for e in j["episodes"]:
            out.append({"source_script": script, "start_ts": e["start"], "peak_ts": e["peak"],
                        "episode_kind": "merged", "onset_min": e.get("onset_min"),
                        "duration_min": e.get("duration_min"),
                        "peak_img_per_s": e.get("peak_img_per_s"),
                        "ctx_p50": e.get("ctx_p50"), "cluster_id": e.get("cluster"),
                        "share_single": e.get("share_single"),
                        "share_tiled_small": e.get("share_tiled_small"),
                        "share_tiled_large": e.get("share_tiled_large"),
                        "share_frames": e.get("share_frames"), "run_id": run_id})
    return out


_CLASS_COLS = ["class_name", "requests", "request_share", "image_share", "ctx_p50",
               "gen_p50", "img_rate_cv2", "img_rate_mean", "run_id"]
_ARCH_COLS = ["cluster_id", "semantic_name", "n_requests", "img_p50", "ctx_p50", "gen_p50",
              "img_sum", "ctx_sum", "req_share", "img_share", "ctx_share", "run_id"]
_SIL_COLS = ["source_script", "k", "silhouette", "is_chosen", "is_argmax", "entity",
             "is_valid", "provenance_note", "run_id"]


def _silhouettes(j, script, run_id, note=None):
    scan = j["silhouette_by_k"]
    chosen = j.get("chosen_k")
    argmax = max(scan, key=lambda k: scan[k])
    entity = "burst_episode" if script == "k_episode_clusters" else "request"
    return [{"source_script": script, "k": int(k), "silhouette": v,
             "is_chosen": int(k) == int(chosen), "is_argmax": k == argmax,
             "entity": entity, "is_valid": True, "provenance_note": note,
             "run_id": run_id} for k, v in scan.items()]


# ------------------------------------------------------------------------ loader
def load_trace_eda(idx, reload=False):
    """Load family "eda" (K22). Returns (files_loaded, rows_loaded)."""
    nf = nr = 0
    scan_note = None
    if os.path.exists(SILHOUETTE_SCAN):
        scan_note = json.load(open(SILHOUETTE_SCAN)).get("provenance")

    for script in SCRIPTS:
        path = f"{EDA}/{script}_stats.json"
        if not os.path.exists(path):
            print(f"  MISSING {path}", file=sys.stderr)
            continue
        if ic.is_worktree(path):
            continue
        sha, nbytes = ic.file_meta(path)
        if not reload and idx.get(path) == sha:
            continue
        j = json.load(open(path))
        run_id = f"eda:{script}"
        run = {"run_id": run_id, "experiment": "eda", "pool": "both",
               "window_name": "fulltrace", "kind": KIND, "source_path": path,
               "feeds": "tex/trace-eda.tex",
               "config": {"script": f"{script}.py", "corpus": "AzureLMMInferenceDataset2025",
                          "requests": 1000000, "duration_hours": 168,
                          "compute": "cuDF/cuML/CuPy 26.06 on RTX 5090"}}

        stmts = [ic.run_upsert_sql(run),
                 f"delete from provenance.eda_metric where script={ic.lit(script)}"]

        mrows = [_metric_row(script, run_id, p, k, v) for p, k, v in flatten(j)]
        n = len(mrows)
        # chunk the tall insert so a single statement stays reasonable
        for i in range(0, len(mrows), 500):
            stmts.append(ic.multi_upsert_sql("eda_metric", _METRIC_COLS, mrows[i:i + 500],
                                             ["script", "metric_path"]))

        # ---- typed projections
        if script in ("c_temporal", "i_burst_anatomy", "k_episode_clusters"):
            attribution = None
            if script == "i_burst_anatomy":
                jp = f"{EDA}/j_classes_stats.json"
                if os.path.exists(jp):
                    attribution = {a["peak"]: a for a in
                                   json.load(open(jp)).get("burst_attribution_top6", [])}
            brows = _bursts(j, script, run_id, attribution)
            stmts.append(f"delete from provenance.eda_burst_episode "
                         f"where source_script={ic.lit(script)}")
            stmts.append(ic.multi_upsert_sql("eda_burst_episode", _BURST_COLS, brows,
                                             ["source_script", "start_ts"]))
            n += len(brows)

        if script == "j_classes":
            crows = [{"class_name": name, "requests": c.get("requests"),
                      "request_share": c.get("request_share"),
                      "image_share": c.get("image_share"), "ctx_p50": c.get("ctx_p50"),
                      "gen_p50": c.get("gen_p50"), "img_rate_cv2": c.get("img_rate_cv2"),
                      "img_rate_mean": c.get("img_rate_mean"), "run_id": run_id}
                     for name, c in j["classes"].items()]
            stmts.append(ic.multi_upsert_sql("eda_request_class", _CLASS_COLS, crows,
                                             "class_name"))
            n += len(crows)

        if script == "l_request_clusters":
            arows = [{"cluster_id": int(cid), "semantic_name": c.get("semantic_name"),
                      "n_requests": c.get("n"), "img_p50": c.get("img_p50"),
                      "ctx_p50": c.get("ctx_p50"), "gen_p50": c.get("gen_p50"),
                      "img_sum": c.get("img_sum"), "ctx_sum": c.get("ctx_sum"),
                      "req_share": c.get("req_share"), "img_share": c.get("img_share"),
                      "ctx_share": c.get("ctx_share"), "run_id": run_id}
                     for cid, c in j["clusters"].items()]
            stmts.append(ic.multi_upsert_sql("eda_request_archetype", _ARCH_COLS, arows,
                                             "cluster_id"))
            n += len(arows)

        if script in ("k_episode_clusters", "l_request_clusters"):
            note = scan_note if script == "l_request_clusters" else None
            srows = _silhouettes(j, script, run_id, note)
            stmts.append(ic.multi_upsert_sql("eda_silhouette", _SIL_COLS, srows,
                                             ["source_script", "k"]))
            n += len(srows)

        stmts.append(ic.ingest_sql(path, sha, KIND, n, run_id, nbytes))
        db.run_sql(";\n".join(s for s in stmts if s))
        nf += 1
        nr += n

    # l_silhouette_scan.json: not a metric source (rounded recomputation). Only its
    # `provenance` string is used, attached above. Logged so the corpus is accounted for
    # and so re-runs are a no-op.
    if os.path.exists(SILHOUETTE_SCAN):
        sha, nbytes = ic.file_meta(SILHOUETTE_SCAN)
        if reload or idx.get(SILHOUETTE_SCAN) != sha:
            db.run_sql(ic.ingest_sql(SILHOUETTE_SCAN, sha, KIND, 0,
                                     "eda:l_request_clusters", nbytes))
            nf += 1
    return nf, nr


if __name__ == "__main__":
    from ingest_common import load_ingest_index
    reload = "--reload" in sys.argv
    f, r = load_trace_eda(load_ingest_index(), reload)
    print(f"[{KIND}   trace_eda       ] files={f:5d} rows={r:13,d}")
