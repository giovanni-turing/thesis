#!/usr/bin/env python3
"""K24 - family "predewma": Dynamo shipped predictors + EWMA cheap-forecaster ablation.

Feeds provenance.forecast_eval / forecast_eval_meta / ewma_ablation_cell
(DDL: provenance/schema/09_predictors_ewma.sql).

Run standalone from this directory:   python3 load_pred_ewma.py [--reload]
Or from main-style drivers:           load_pred_ewma(idx, reload) -> (files, rows)

DE-DUPLICATION DECISIONS (verified before writing, see module docstring of each helper):
  * consolidated.json["dynamo_predictors"] is a VERBATIM copy of the 8 singleton
    <predictor>_<resolution>.json objects (checked field-by-field: exact equality on all
    17 keys x 8 entries). The Dynamo rows are taken from the SINGLETON files at full float
    precision; the consolidated copy is skipped. consolidated.json is still ingested, for
    its fm_baseline_reference_h1 block (the only source of the FM/baseline reference rows)
    and its header metadata.
  * comparison_table.csv is 100% redundant: all 16 rows reproduce values already present at
    equal-or-better precision in the JSON artifacts (dynamo rows rounded to 4dp; fm_best and
    baseline rows identical to consolidated.json fm_baseline_reference_h1). It is NOT loaded;
    it is re-verified on every run and logged with kind K24dup, n_rows=0.
  * The 6 ewma_baseline_<scope>.json files are an exact subset of ewma_sweep.json: all 36
    cells match a sweep cell on the 6 factor columns AND on every value column (including
    ratio_vs_static == ratio). They are NOT loaded; logged with kind K24dup, n_rows=0.
"""
import argparse, glob, json, os, sys

import db
import ingest_common as ic

TESE = "/home/gio/tese"
DYN = f"{TESE}/predictors/results_dynamo"
VER = f"{TESE}/verification/results"
ANCHOR = f"{TESE}/collector_artifacts/phaseE_physical_anchor/static_c8_ctrl_aic.stats.json"

KIND = "K24"
KIND_DUP = "K24dup"          # file deliberately not loaded (duplicate of another artifact)

FE_COLS = ["family", "predictor", "resolution", "signal", "horizon_h", "metric",
           "context_window", "n_origins_available", "n_origins_used",
           "common_span_first_origin", "common_span_last_origin", "wape", "mae",
           "n_fail", "n_nonfinite", "fail_examples", "seconds", "orig_per_s",
           "is_best_fm", "precision_src", "is_valid", "source_path"]
FE_KEY = ["family", "predictor", "resolution"]

EW_COLS = ["model", "window_name", "lead_s", "rho", "quantile", "readiness", "p99_ms",
           "max_ms", "divergent", "ws", "ratio_vs_static", "feasible",
           "denom_static_c8_ws", "is_valid", "source_path"]
EW_KEY = ["model", "window_name", "lead_s", "rho", "quantile", "readiness"]

# fm_baseline_reference_h1 key -> (family, predictor)
REF_MAP = {"toto_uni": ("fm", "toto/uni"), "chronos_cov": ("fm", "chronos/cov"),
           "naive": ("baseline", "naive"), "ewma": ("baseline", "ewma"),
           "holt_winters": ("baseline", "holt_winters")}


def _prep(path, idx, reload):
    """None if the file should be skipped (worktree copy, or sha unchanged)."""
    if ic.is_worktree(path):
        return None
    if not os.path.exists(path):
        return None
    sha, nbytes = ic.file_meta(path)
    if not reload and idx.get(path) == sha:
        return None
    return sha, nbytes


def _run(*stmts):
    db.run_sql(";\n".join(s for s in stmts if s))


# ------------------------------------------------------------------ 5a dynamo
def _singleton_row(obj, path):
    return {"family": "dynamo", "predictor": obj["predictor"],
            "resolution": obj["resolution"], "signal": obj.get("signal"),
            "horizon_h": obj.get("horizon"), "metric": obj.get("metric"),
            "context_window": obj.get("window"),
            "n_origins_available": obj.get("n_origins_available"),
            "n_origins_used": obj.get("n_origins_used"),
            "common_span_first_origin": obj.get("common_span_first_origin"),
            "common_span_last_origin": obj.get("common_span_last_origin"),
            "wape": obj.get("wape"), "mae": obj.get("mae"),
            "n_fail": obj.get("n_fail"), "n_nonfinite": obj.get("n_nonfinite"),
            "fail_examples": [str(x) for x in (obj.get("fail_examples") or [])],
            "seconds": obj.get("seconds"), "orig_per_s": obj.get("orig_per_s"),
            "is_best_fm": False, "precision_src": "json_full", "is_valid": True,
            "source_path": path}


def _load_dynamo_singletons(idx, reload, report):
    """The 8 <predictor>_<resolution>.json files: full-precision Dynamo WAPE rows."""
    nf = nr = 0
    paths = sorted(p for p in glob.glob(f"{DYN}/*.json")
                   if os.path.basename(p) != "consolidated.json")
    for path in paths:
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        arr = json.load(open(path))
        if not isinstance(arr, list) or len(arr) != 1:
            report.append(f"SKIP {path}: expected a 1-element JSON array, got "
                          f"{type(arr).__name__} len={len(arr) if hasattr(arr,'__len__') else '?'}")
            continue
        row = _singleton_row(arr[0], path)
        _run(ic.multi_upsert_sql("forecast_eval", FE_COLS, [row], FE_KEY),
             ic.ingest_sql(path, sha, KIND, 1, None, nbytes))
        nf += 1
        nr += 1
    return nf, nr


def _load_consolidated(idx, reload, report):
    """consolidated.json: FM/baseline reference rows + header metadata.

    The dynamo_predictors block is verified verbatim-equal to the singleton files and then
    dropped from the stored payload so no number is persisted twice.
    """
    path = f"{DYN}/consolidated.json"
    prep = _prep(path, idx, reload)
    if not prep:
        return 0, 0
    sha, nbytes = prep
    j = json.load(open(path))
    dyn = j.get("dynamo_predictors") or {}

    # --- verify the verbatim-duplicate claim against the singleton files
    mism = []
    for stem, obj in sorted(dyn.items()):
        sp = f"{DYN}/{stem}.json"
        if not os.path.exists(sp):
            mism.append(f"{stem}: no singleton file")
            continue
        if json.load(open(sp))[0] != obj:
            mism.append(f"{stem}: consolidated copy DIFFERS from singleton")
    report.append(f"consolidated.dynamo_predictors: {len(dyn)} entries, "
                  + ("all verbatim-equal to singleton files (not re-loaded)"
                     if not mism else "MISMATCH -> " + "; ".join(mism)))

    horizon, signal = j.get("horizon"), j.get("signal")
    metric, span = j.get("metric"), j.get("span")
    rows = []
    for res, ref in sorted((j.get("fm_baseline_reference_h1") or {}).items()):
        best = ref.get("best_fm")
        named = set()
        for key, (fam, pred) in REF_MAP.items():
            if key not in ref:
                continue
            named.add(pred)
            rows.append({"family": fam, "predictor": pred, "resolution": res,
                         "signal": signal, "horizon_h": horizon, "metric": metric,
                         "wape": ref[key], "is_best_fm": (pred == best),
                         "fail_examples": None, "precision_src": "json_ref_4dp",
                         "is_valid": True, "source_path": path})
        # best_fm may name a variant absent from the per-model dict (15s: toto/cov)
        if best and best not in named:
            rows.append({"family": "fm", "predictor": best, "resolution": res,
                         "signal": signal, "horizon_h": horizon, "metric": metric,
                         "wape": ref.get("best_fm_wape"), "is_best_fm": True,
                         "fail_examples": None, "precision_src": "json_ref_4dp",
                         "is_valid": True, "source_path": path})
        elif best and ref.get("best_fm_wape") != ref.get(
                next((k for k, v in REF_MAP.items() if v[1] == best), None)):
            report.append(f"NOTE {res}: best_fm_wape != per-model wape for {best}")

    meta = {"source_path": path, "description": j.get("description"), "metric": metric,
            "horizon_h": horizon, "signal": signal, "span": span,
            "payload": {k: v for k, v in j.items() if k != "dynamo_predictors"}}
    _run(ic.multi_upsert_sql("forecast_eval", FE_COLS, rows, FE_KEY),
         ic.upsert_sql("forecast_eval_meta", meta, "source_path", jsonb_cols=("payload",)),
         ic.ingest_sql(path, sha, KIND, len(rows), None, nbytes))
    return 1, len(rows)


def _check_comparison_csv(idx, reload, report):
    """comparison_table.csv is a rounded projection of the JSON artifacts -> verify, don't load."""
    import csv as _csv
    path = f"{DYN}/comparison_table.csv"
    prep = _prep(path, idx, reload)
    if not prep:
        return 0, 0
    sha, nbytes = prep
    cons = json.load(open(f"{DYN}/consolidated.json"))
    dyn, ref = cons["dynamo_predictors"], cons["fm_baseline_reference_h1"]
    bad, n = [], 0
    for r in _csv.DictReader(open(path)):
        n += 1
        res, w = r["resolution"], float(r["wape"])
        ns, name = r["predictor"].split(":", 1)
        if ns == "dynamo":
            src = dyn.get(f"{name}_{res}", {}).get("wape")
            ok = src is not None and round(src, 4) == w
        elif ns == "fm_best":
            ok = ref[res].get("best_fm") == name and ref[res].get("best_fm_wape") == w
        else:
            key = next((k for k, v in REF_MAP.items() if v[1] == name), None)
            ok = key is not None and ref[res].get(key) == w
        if not ok:
            bad.append(f"{res}/{r['predictor']}={w}")
    report.append(f"comparison_table.csv: {n} rows, all reproducible from the JSON artifacts"
                  if not bad else
                  f"comparison_table.csv: {n} rows, UNRECONCILED -> {', '.join(bad)}")
    db.run_sql(ic.ingest_sql(path, sha, KIND_DUP, 0, None, nbytes))
    return 1, 0


# -------------------------------------------------------------------- 5b ewma
_FACT = ("model", "window", "lead", "rho", "q", "readiness")
_VALS = ("p99_ms", "max_ms", "divergent", "ws", "feasible")


def _load_ewma_sweep(idx, reload, report):
    path = f"{VER}/ewma_sweep.json"
    prep = _prep(path, idx, reload)
    if not prep:
        return 0, 0
    sha, nbytes = prep
    j = json.load(open(path))
    denom = j.get("denom_static_c8_ws")
    rows = [{"model": c["model"], "window_name": c["window"], "lead_s": c["lead"],
             "rho": c["rho"], "quantile": c["q"], "readiness": c["readiness"],
             "p99_ms": c.get("p99_ms"), "max_ms": c.get("max_ms"),
             "divergent": c.get("divergent"), "ws": c.get("ws"),
             # NORMALIZED: 'ratio' here, 'ratio_vs_static' in the baseline files
             "ratio_vs_static": c.get("ratio"), "feasible": c.get("feasible"),
             "denom_static_c8_ws": denom, "is_valid": True, "source_path": path}
            for c in j.get("cells", [])]
    for i in range(0, len(rows), 500):
        db.run_sql(ic.multi_upsert_sql("ewma_ablation_cell", EW_COLS, rows[i:i + 500], EW_KEY))
    db.run_sql(ic.ingest_sql(path, sha, KIND, len(rows), None, nbytes))
    _crosscheck_denom(denom, report)
    return 1, len(rows)


def _crosscheck_denom(denom, report):
    """ewma_sweep denom_static_c8_ws vs the phaseE physical anchor. Reported, not reconciled."""
    if denom is None or not os.path.exists(ANCHOR):
        return
    anchor = json.load(open(ANCHOR)).get("provisioned_worker_seconds")
    if anchor is None:
        return
    d = anchor - denom
    report.append(f"CROSS-CHECK denom_static_c8_ws={denom} vs "
                  f"static_c8_ctrl_aic.stats.json provisioned_worker_seconds={anchor}: "
                  f"delta={d:+.1f} ws ({abs(d)/anchor:.2e} relative) - "
                  + ("EXACT" if d == 0 else "discrepancy confirmed, NOT reconciled"))


def _check_ewma_baselines(idx, reload, report):
    """The 6 ewma_baseline_<scope>.json files: verify subset-of-sweep, then don't load."""
    sweep = {}
    for c in json.load(open(f"{VER}/ewma_sweep.json")).get("cells", []):
        sweep[tuple(c[f] for f in _FACT)] = c
    nf = tot = missing = vdiff = 0
    for path in sorted(glob.glob(f"{VER}/ewma_baseline_*.json")):
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        n = 0
        for c in json.load(open(path)):
            n += 1
            tot += 1
            s = sweep.get(tuple(c[f] for f in _FACT))
            if s is None:
                missing += 1
                report.append(f"NOT IN SWEEP: {os.path.basename(path)} "
                              f"{tuple(c[f] for f in _FACT)} -> would be LOST; loading needed")
                continue
            if any(c[v] != s[v] for v in _VALS) or c.get("ratio_vs_static") != s.get("ratio"):
                vdiff += 1
                report.append(f"VALUE DIFF: {os.path.basename(path)} "
                              f"{tuple(c[f] for f in _FACT)}")
        db.run_sql(ic.ingest_sql(path, sha, KIND_DUP, 0, None, nbytes))
        nf += 1
    if nf:
        report.append(f"ewma_baseline_*.json: {nf} files / {tot} cells checked against "
                      f"ewma_sweep.json ({len(sweep)} cells): missing={missing} "
                      f"value-diffs={vdiff}"
                      + ("  -> exact subset, sweep loaded alone" if not (missing or vdiff)
                         else "  -> NOT a clean subset, see lines above"))
    return nf, 0


# ------------------------------------------------------------------ entrypoint
def load_pred_ewma(idx, reload=False, report=None):
    """Load family "predewma". Returns (files_ingested, rows_loaded)."""
    rep = report if report is not None else []
    nf = nr = 0
    for fn in (_load_dynamo_singletons, _load_consolidated, _check_comparison_csv,
               _load_ewma_sweep, _check_ewma_baselines):
        f, r = fn(idx, reload, rep)
        nf += f
        nr += r
    return nf, nr


def main():
    ap = argparse.ArgumentParser(description="K24 predictors + EWMA ablation loader")
    ap.add_argument("--reload", action="store_true", help="ignore ingest_log sha, reload")
    a = ap.parse_args()
    report = []
    idx = ic.load_ingest_index()
    nf, nr = load_pred_ewma(idx, a.reload, report)
    for line in report:
        print(f"  . {line}", flush=True)
    print(f"[{KIND:6} predewma        ] files={nf:5d} rows={nr:13,d}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
