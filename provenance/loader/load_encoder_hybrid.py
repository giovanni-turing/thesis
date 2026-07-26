#!/usr/bin/env python3
"""Ingest the COMPLETE encoder-hybrid controller family (2026-07-25/26) into
experiment='encoder_hybrid' (review Finding 4: the DB held only 4 of the family's runs,
without canonical policy/window identity). Three sub-families, one loader:

  aggregate  -- fc / re / hybrid over the 5.60-day aggregate window (749,601 req):
                the 0.7611x hybrid headline (2,944,979.7 / 3,869,278.4 static-C8 ws);
  folds      -- F1..F7 daily folds, 3 arms each, EXCEPT F1 which has no forecast arm
                (archive coverage begins mid-window; hybrid degenerates to reactive by
                construction -- see folds/F1_gen.log);
  combos     -- the F6 (e13-breaker) combination sweep: forecast quantile {p50,p70,p90}
                x pointwise-max x reactive, plus p70 vs 3 more-aggressive reactive arms.

Identity conventions:
  * run_ids match loader/runid.py scoped family ids (encoder_hybrid:folds:F2_fc, ...);
    the F6 arms keep the ALREADY-MIGRATED ids encoder_hybrid:F6_{fc,re,hybrid} whose
    canonical artifacts are the top-level F6_* files (schema/32_scope_misc_runids.sql).
  * BYTE-IDENTICAL duplicate artifacts are registered in ingest_log against the
    canonical run with kind K3d/K4d (n_rows=0) and are NOT ingested as second runs:
    folds/F6_* == F6_* (same run, copied into the fold set), and combos/{fc_p90,h_p90,
    re}.* == F6_{fc,hybrid,re}.* (the sweep's p90 column deterministically reproduced
    the F6 arms bit-for-bit -- sha256-asserted here on every load). K3d/K4d are outside
    ingest_common.PER_FILE_KINDS, so the collision guard ignores them while the
    file-path sha gate still stops the generic K3/K4 loaders from double-ingesting.
  * policy vocabulary is closed to {forecast,reactive,static} (C502 / runs_policy_vocab),
    so hybrid runs carry policy NULL + config.policy_family='hybrid' with both arms named.
  * quantile vocabulary is closed to {p50,p90,obs}, so p70 arms carry quantile NULL +
    config.forecast_quantile='p70' (same convention as load_langcalib).

Facts: encoder_run_summary per stats file (same field map as loaders.load_encoder_stats),
worker_schedule per sched file (delete-by-source_path then COPY, K4 conventions),
ingest_log per file with sha256. Idempotent: unchanged sha -> facts skipped; the run-row
upsert ALWAYS executes so canonical dims heal even for already-gated files.
Run: python3 provenance/loader/load_encoder_hybrid.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db, ingest_common as ic

ROOT = "/home/gio/tese/simulation/results/encoder_hybrid"
EXP = "encoder_hybrid"
CONV = "workload/trace_to_two_pool.py"
GEN_FC = "verification/scripts/forecast_schedule_issuetime.py"
GEN_RE = "verification/scripts/reactive_quantile_schedule.py"
COMB = "simulation/combine_schedules.py"

# offset / max-requests per window (simulation/windows.json; aggregate from
# simulation/run_encoder_hybrid.sh OFFSET=250399 MAXREQ=749601)
WINDOW_REPLAY = {
    "aggregate": (250399, 749601), "F1": (401, 173057), "F2": (173458, 183285),
    "F3": (356743, 186359), "F4": (543102, 135637), "F5": (678739, 72547),
    "F6": (751286, 84329), "F7": (835615, 164385),
}

_BATCH = "encoder hybrid family, ledger 2026-07-25 (F1 hybrid replayed 2026-07-26)"


def _fc_cfg(q, window):
    return {"arm": "forecast", "forecast_quantile": q,
            "forecaster": "chronos images 15s (predictors/results/chronos_images.parquet)",
            "generator": GEN_FC, "rho": 15, "cold_start_s": 30, "hysteresis_min": 3,
            "actuation": "issue-time", "window": window, "note": _BATCH}


def _re_cfg(window, mode="react_point", rho=15, extra=None):
    c = {"arm": "reactive", "mode": mode, "generator": GEN_RE, "rho": rho,
         "cold_start_s": 30, "hysteresis_min": 3,
         "signal": ("last-bin observed load" if mode == "react_point"
                    else "trailing-window quantile of observed load"),
         "window": window, "note": _BATCH}
    if extra:
        c.update(extra)
    return c


def _hy_cfg(window, fc_arm, re_arm, extra=None):
    c = {"arm": "hybrid", "policy_family": "hybrid",
         "combiner": f"pointwise max of the two arm schedules ({COMB})",
         "forecast_arm": fc_arm, "reactive_arm": re_arm, "window": window,
         "note": _BATCH}
    if extra:
        c.update(extra)
    return c


def _run(rid, window, policy, stem, cfg, quantile=None, model=None, rho=15,
         dirpath=ROOT, dups=()):
    """One run: canonical stats/sched paths derived from dirpath/stem; dups is a list of
    (path, canonical_path) byte-identical artifacts to register without ingesting."""
    return dict(rid=rid, window=window, policy=policy, quantile=quantile, model=model,
                rho=rho, stem=stem, dir=dirpath, cfg=cfg, dups=list(dups))


def discover():
    R = []
    # --- aggregate 5.60-day 3-way (run_encoder_hybrid.sh) ---------------------------
    R.append(_run(f"{EXP}:fc", "aggregate", "forecast", "fc",
                  _fc_cfg("p90", "aggregate"), quantile="p90", model="chronos"))
    R.append(_run(f"{EXP}:re", "aggregate", "reactive", "re", _re_cfg("aggregate")))
    R.append(_run(f"{EXP}:hybrid", "aggregate", None, "hybrid",
                  _hy_cfg("aggregate", "forecast p90/rho15/L30 issue-time",
                          "react_point rho15/L30")))
    # --- daily folds F1..F7 (run_encoder_hybrid_folds.sh) ---------------------------
    for n in range(1, 8):
        W = f"F{n}"
        fold_dir, top = f"{ROOT}/folds", (n == 6)
        # F6's canonical artifacts are the top-level F6_* files (already-migrated ids);
        # the folds/F6_* copies are byte-identical duplicates.
        d = ROOT if top else fold_dir
        rid_base = f"{EXP}:F6" if top else f"{EXP}:folds:F{n}"
        def dup(stem):
            return ([(f"{fold_dir}/{stem}.jsonl.stats.json", f"{ROOT}/{stem}.jsonl.stats.json"),
                     (f"{fold_dir}/{stem}.sched.json", f"{ROOT}/{stem}.sched.json")]
                    if top else [])
        if n != 1:  # F1 has no forecast arm: no archive coverage (folds/F1_gen.log)
            R.append(_run(f"{rid_base}_fc", W, "forecast", f"F{n}_fc", _fc_cfg("p90", W),
                          quantile="p90", model="chronos", dirpath=d, dups=dup(f"F{n}_fc")))
        R.append(_run(f"{rid_base}_re", W, "reactive", f"F{n}_re", _re_cfg(W),
                      dirpath=d, dups=dup(f"F{n}_re")))
        hy_extra = None
        if n == 1:
            hy_extra = {"degenerate": "no forecast rows cover window F1 (archive begins "
                        "mid-window); combiner --allow-missing fallback => hybrid schedule "
                        "== reactive schedule; replayed, not copied (folds/F1_gen.log)"}
        R.append(_run(f"{rid_base}_hybrid", W, None, f"F{n}_hybrid",
                      _hy_cfg(W, "forecast p90/rho15/L30 issue-time" if n != 1 else "(absent)",
                              "react_point rho15/L30", hy_extra),
                      dirpath=d, dups=dup(f"F{n}_hybrid")))
    # --- F6 combination sweep (run_encoder_hybrid_combos.sh + p70 extension) --------
    C = f"{ROOT}/combos"
    resweep = "combination sweep: is max(p90, react_point rho15) cost-minimal on F6/e13?"
    for q in ("p50", "p70"):
        R.append(_run(f"{EXP}:combos:fc_{q}", "F6", "forecast", f"fc_{q}",
                      dict(_fc_cfg(q, "F6"), sweep=resweep),
                      quantile=(q if q in ("p50", "p90") else None), model="chronos",
                      dirpath=C))
        R.append(_run(f"{EXP}:combos:h_{q}", "F6", None, f"h_{q}",
                      _hy_cfg("F6", f"forecast {q}/rho15/L30 issue-time",
                              "react_point rho15/L30", {"sweep": resweep}), dirpath=C))
    # combos/{fc_p90,h_p90,re}.* deterministically reproduced the F6 arms byte-for-byte:
    # registered below as duplicates of encoder_hybrid:F6_{fc,hybrid,re}, not as runs.
    for stem, canon in (("fc_p90", "F6_fc"), ("h_p90", "F6_hybrid"), ("re", "F6_re")):
        R.append(dict(rid=f"{EXP}:{canon}", dup_only=True, dups=[
            (f"{C}/{stem}.jsonl.stats.json", f"{ROOT}/{canon}.jsonl.stats.json"),
            (f"{C}/{stem}.sched.json", f"{ROOT}/{canon}.sched.json")]))
    # p70 near-miss vs 3 more-aggressive reactive arms (results-ledger 2026-07-25:
    # {react_quantile p90/240s, react_point rho12, react_point rho10}); the re_* arm
    # schedules are combiner inputs only (sched-only, never replayed standalone).
    for tag, mode, rho, extra in (
            ("rho10", "react_point", 10, None), ("rho12", "react_point", 12, None),
            ("rquant", "react_quantile", None,
             {"quantile": "p90", "react_window_s": 240,
              "note_rho": "generator default rho=15 not explicitly recorded"})):
        R.append(_run(f"{EXP}:combos:re_{tag}", "F6", "reactive", f"re_{tag}",
                      dict(_re_cfg("F6", mode, rho if rho else 15, extra),
                           sweep=resweep, sched_only=True), rho=rho, dirpath=C))
        R.append(_run(f"{EXP}:combos:h70_{tag}", "F6", None, f"h70_{tag}",
                      _hy_cfg("F6", "forecast p70/rho15/L30 issue-time",
                              f"{mode} {'rho%d' % rho if rho else 'p90/240s'}/L30",
                              {"sweep": resweep}), rho=None, dirpath=C))
    return R


# encoder_run_summary field map == loaders.load_encoder_stats (K3)
def _p(j, field, p):
    return (j.get(field) or {}).get(p)


def _enc_row(rid, j):
    return {
        "run_id": rid,
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


def _iso_mtime(path):
    import datetime
    return datetime.datetime.fromtimestamp(os.path.getmtime(path),
                                           datetime.timezone.utc).isoformat()


def main():
    idx = ic.load_ingest_index()
    n_runs = n_files = n_sched_rows = n_dups = 0
    for r in discover():
        dup_stmts = []
        for dpath, cpath in r.get("dups", ()):
            dsha, dnb = ic.file_meta(dpath)
            csha = ic.sha256_file(cpath)
            if dsha != csha:
                raise RuntimeError(f"DUPLICATE DIVERGED: {dpath} (sha {dsha[:12]}) != "
                                   f"{cpath} (sha {csha[:12]}); refusing to alias")
            kind = "K3d" if dpath.endswith(".stats.json") else "K4d"
            if idx.get(dpath) != dsha:
                dup_stmts.append(ic.ingest_sql(dpath, dsha, kind, 0, r["rid"], dnb))
                n_dups += 1
        if r.get("dup_only"):
            if dup_stmts:
                db.run_sql(";\n".join(dup_stmts))
            continue

        stats = f"{r['dir']}/{r['stem']}.jsonl.stats.json"
        sched = f"{r['dir']}/{r['stem']}.sched.json"
        has_stats = os.path.exists(stats)
        if not os.path.exists(sched):
            raise RuntimeError(f"missing schedule artifact: {sched}")
        off, maxreq = WINDOW_REPLAY[r["window"]]
        arts = [sched] + ([stats, f"{r['dir']}/{r['stem']}.jsonl.zst"] if has_stats else [])
        arts += [d for d, _ in r.get("dups", ())]
        cfg = dict(r["cfg"])
        cfg.setdefault("replay", "converter replay (not dynamo.replay); encoder pool only")
        run = {"run_id": r["rid"], "experiment": EXP, "pool": "encoder",
               "window_name": r["window"], "policy": r["policy"], "model": r["model"],
               "quantile": r["quantile"], "resolution": "15s", "rho": r["rho"],
               "cold_start_s": 30, "hysteresis_min": 3,
               "actuation": "issue-time" if r["policy"] == "forecast" else None,
               "kind": "K3" if has_stats else "K4",
               "source_path": stats if has_stats else sched,
               "artifact_paths": [a for a in arts if os.path.exists(a)],
               "command": (f"python {CONV} --offset {off} --max-requests {maxreq} "
                           f"--encoder-workers 2 --worker-schedule {sched}"
                           if has_stats else
                           f"schedule generated for pointwise-max combination only "
                           f"(never replayed standalone); see {GEN_RE}"),
               "run_utc": _iso_mtime(stats if has_stats else sched),
               "is_current": True, "config": cfg}
        stmts = [ic.run_upsert_sql(run)]  # ALWAYS: heals canonical dims on gated files
        n_runs += 1

        if has_stats:
            ssha, snb = ic.file_meta(stats)
            if idx.get(stats) != ssha:
                j = json.load(open(stats))
                assert j.get("requests") == maxreq, (r["rid"], j.get("requests"), maxreq)
                ic.guard_run_collision(r["rid"], stats, idx, "encoder_run_summary", "K3")
                stmts.append(ic.upsert_sql("encoder_run_summary", _enc_row(r["rid"], j),
                                           "run_id", jsonb_cols=("metrics",)))
                stmts.append(ic.ingest_sql(stats, ssha, "K3", 1, r["rid"], snb))
                n_files += 1
        db.run_sql(";\n".join(stmts + dup_stmts))

        csha, cnb = ic.file_meta(sched)
        if idx.get(sched) != csha:
            steps = json.load(open(sched))
            ic.guard_run_collision(r["rid"], sched, idx, "worker_schedule", "K4")
            db.run_sql(f"delete from provenance.worker_schedule where source_path={ic.lit(sched)}")
            n = db.copy_rows("worker_schedule",
                             ["run_id", "source_path", "step_index", "t_s", "worker_count"],
                             ((r["rid"], sched, i, s[0], s[1]) for i, s in enumerate(steps)))
            db.run_sql(ic.ingest_sql(sched, csha, "K4", n, r["rid"], cnb))
            n_files += 1
            n_sched_rows += n

    print(f"encoder_hybrid: {n_runs} runs upserted; {n_files} files (re)loaded; "
          f"{n_sched_rows} schedule rows; {n_dups} duplicate artifacts registered")
    for q in ("policy='forecast'", "policy='reactive'", "policy is null"):
        print(f"  {q}: " + db.scalar(
            f"select count(*) from provenance.runs where experiment='{EXP}' and {q}"))
    print("total encoder_hybrid runs:", db.scalar(
        f"select count(*) from provenance.runs where experiment='{EXP}'"))
    print("encoder_run_summary rows:", db.scalar(
        f"select count(*) from provenance.encoder_run_summary where run_id like '{EXP}:%'"))
    print("worker_schedule rows:", db.scalar(
        f"select count(*) from provenance.worker_schedule where run_id like '{EXP}:%'"))


if __name__ == "__main__":
    main()
