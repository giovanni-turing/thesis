"""K40/K41/K42 — ADJUDICATION.md §2.2 and §2.7.

K40  srcbuild language-pool runs
     `simulation/results/srcbuild/llm_head2k_{poly,aic}_src.json` are the reports
     that back thesis tab:sim-poly-aic. They were never ingested because K1's glob
     is `*.report.json` and these two files are named `*_src.json`. They arrive as
     NEW runs beside the wheel `sweeps:llm_head2k_{poly,aic}_s1` rows; nothing about
     the wheel rows is rewritten. The supersession is recorded per METRIC in
     provenance.metric_supersession, because the wheel runs remain the legitimate
     s=1 anchor of the Phase-2 speedup knee sweep.

K41  the runtime/build discriminator
     Backfills provenance.runs.runtime_build from the archived replay logs. The
     discriminator is a runtime log line, not an inference:

       dynamo 1.3.0 (source build)  "Using Lineage inactive backend (Tick)"
       ai-dynamo 1.2.1 (PyPI wheel) "Using Lineage inactive backend"

     The `(Tick)` suffix is emitted by the newer kvbm_logical::manager::builder and
     is present in every source-build log and absent from every wheel log. Verified
     against the two families whose driver pins the interpreter explicitly:
     run_44_riders.sh / run_32_reactive.sh / run_llm_week_*.sh / run_episode_twins.sh
     set REPLAY_PY to the dynamo .venv (source build) and all their logs carry
     `(Tick)`; the grid + sweeps logs take run_replay.sh's default (the wheel) and
     none of them do.

     Runs with no log on disk, and the encoder-pool / pure-Python families that
     never load a dynamo runtime at all, are left NULL. NEVER guessed.

K42  sweep manifests (§2.7)
     The `cells_*.jsonl` / `pilot_cells.jsonl` design files: what each sweep
     REQUESTED, as opposed to what came back. Carries the actuation dimension so a
     manifest can never be silently read as belonging to the other controller.
"""
import glob
import json
import os

import db
import ingest_common as ic
from loaders import _LLM_HOT, actuation_of
from runid import run_id_of

TESE = "/home/gio/tese"
SIM = f"{TESE}/simulation/results"
DATA = f"{TESE}/defense/anim/data"

SRC_MARKER = "Using Lineage inactive backend (Tick)"
WHEEL_MARKER = "Using Lineage inactive backend"

BUILD_META = {
    "source": ("1.3.0", "dynamo 1.3.0 built from source, maturin develop --release "
                          "--features aic-forward-pass (simulation/build_dynamo_src.sh); "
                          "Rust AIC path, AIC_VER=0.19.0"),
    "wheel":    ("1.2.1", "pinned ai-dynamo==1.2.1 PyPI wheel in the aiconfigurator uv "
                          "venv (run_replay.sh default REPLAY_PY); Python SDK AIC callback"),
}


def _prep(path, idx, reload):
    if ic.is_worktree(path):
        return None
    sha, nbytes = ic.file_meta(path)
    if not reload and idx.get(path) == sha:
        return None
    return sha, nbytes


# ========================================================================= K40
_SRCBUILD = {
    f"{SIM}/srcbuild/llm_head2k_poly_src.json": "sweeps:llm_head2k_poly_s1",
    f"{SIM}/srcbuild/llm_head2k_aic_src.json": "sweeps:llm_head2k_aic_s1",
}

# The tab:sim-poly-aic cells. Only these metrics move from the wheel row to the
# srcbuild row; everything else the wheel run backs is untouched.
_SUPERSEDED_METRICS = ["mean_ttft_ms", "p99_ttft_ms", "max_ttft_ms", "mean_itl_ms",
                       "mean_e2e_latency_ms", "p99_e2e_latency_ms"]


def load_srcbuild(idx, reload):
    nf = nr = 0
    for path in sorted(_SRCBUILD):
        if not os.path.exists(path):
            print(f"[K40] MISSING {path}", flush=True)
            continue
        # NO ingest_log gating here. provenance.ingest_log is keyed by file_path with a
        # single owning `kind`, and these two files are already claimed by K26
        # (costmodel), which reads them for a different projection. Competing for the
        # row would make each pass look like a change to the other. K40 is idempotent
        # by construction instead: every write below is an upsert of values read
        # deterministically from the file.
        sha, nbytes = ic.file_meta(path)
        wheel_rid = _SRCBUILD[path]
        rid = run_id_of(path)                      # -> 'srcbuild:llm_head2k_poly_src'
        ic.guard_run_collision(rid, path, idx, "llm_run_summary", "K1")
        j = json.load(open(path))
        ver, note = BUILD_META["source"]
        run = {
            "run_id": rid, "experiment": "srcbuild", "pool": "language",
            "window_name": "head2k", "n_replicas": 2, "tp": 1,
            "converter": "aic" if "aic" in path else "poly",
            "engine": "vLLM", "kind": "K40", "source_path": path,
            "command": ("REPLAY_PY=/home/gio/tese/ai-dynamo/dynamo/.venv/bin/python "
                        "AIC_VER=0.19.0 bash simulation/run_replay.sh "
                        "simulation/results/sweeps/traces/llm_head2k.jsonl "
                        f"{'aic' if 'aic' in path else 'poly'} {path} 2"),
            "feeds": "tex/twopool.tex tab:sim-poly-aic (:61, :103-106)",
            "supersedes": wheel_rid,
            "runtime_build": "source", "runtime_version": ver,
            "runtime_build_evidence": path.rsplit("/", 1)[0] +
                                    ("/run_aic.log" if "aic" in path else "/run_poly.log"),
        }
        row = {"run_id": rid, "metrics": j}
        for c in _LLM_HOT:
            row[c] = j.get(c)

        # metric-scoped supersession, values copied from BOTH sides so the pair is
        # legible without a join. The wheel row itself is not modified.
        got = db.rows("select %s from provenance.llm_run_summary where run_id=%s"
                      % (",".join(_SUPERSEDED_METRICS), ic.lit(wheel_rid)))
        wv = ({m: (float(v) if v not in ("", None) else None)
               for m, v in zip(_SUPERSEDED_METRICS, got[0])} if got else {})
        ms = [{"superseded_run_id": wheel_rid, "metric": m, "current_run_id": rid,
               "superseded_value": wv.get(m), "current_value": j.get(m),
               "scope": "tex/twopool.tex tab:sim-poly-aic",
               "rationale": "The chapter states at :58-66 that these cells are the "
                            "SOURCE-BUILT in-core runtime. The wheel's AIC callback runs "
                            "per-request Python SDK predictions in-process and that wall "
                            "time bleeds into the simulated extreme tail; the source "
                            "build predicts in Rust in microseconds. Bulk of the "
                            "distribution is identical, the tail is not. "
                            "(progress/phase2-simulation.md:196-218)",
               "source": path} for m in _SUPERSEDED_METRICS]

        _stmts = [
            ic.run_upsert_sql(run),
            ic.upsert_sql("llm_run_summary", row, "run_id", jsonb_cols=("metrics",)),
            ic.multi_upsert_sql(
                "metric_supersession",
                ["superseded_run_id", "metric", "current_run_id", "superseded_value",
                 "current_value", "scope", "rationale", "source"],
                ms, ["superseded_run_id", "metric"]),
            # run-level pointer on the wheel row. superseded_by is metadata, not a
            # measurement; is_current stays TRUE because the wheel run is still the
            # s=1 anchor of the speedup knee sweep.
            "update provenance.runs set superseded_by=%s where run_id=%s "
            "and superseded_by is distinct from %s"
            % (ic.lit(rid), ic.lit(wheel_rid), ic.lit(rid)),
        ]
        db.run_sql(";\n".join(s for s in _stmts if s))
        nf += 1
        nr += 1
    return nf, nr


# ========================================================================= K41
def _classify_log(path):
    """-> 'source' | 'wheel' | None, reading only the marker lines."""
    try:
        with open(path, "r", errors="replace") as f:
            seen_wheel = False
            for line in f:
                if SRC_MARKER in line:
                    return "source"
                if WHEEL_MARKER in line:
                    seen_wheel = True
            return "wheel" if seen_wheel else None
    except OSError:
        return None


def load_runtime_build(idx, reload):
    """Backfill runs.runtime_build from the archived replay logs.

    STATELESS: writes no provenance.ingest_log rows. ingest_log is keyed by file_path
    with one owning `kind`, and these logs are already claimed by the K26/K34/K35
    passes that read them for other projections; competing for the row would make each
    pass look like a change to the other. Idempotency comes from the write itself
    (COALESCE + a deterministic marker read), not from a sha gate.

    COMPLEMENTS the §2.12 config backfill (load_config_backfill.py), it does not
    fight it. Where that pass already wrote 'source' from the RustAicCallback line,
    this one leaves the value alone and only records WHICH log attests it. Where it
    had to leave NULL -- the entire wheel population, plus poly runs that execute no
    AIC callback at all -- this one fills it in from the KVBM marker. A genuine
    CONFLICT (the two probes disagreeing on a run) is raised, never silently
    resolved; over all 1,219 archived logs there are currently zero.
    """
    logs = [p for p in sorted(set(glob.glob(f"{SIM}/**/*.log", recursive=True)) |
                              set(glob.glob(f"{DATA}/**/*.log", recursive=True)))
            if not ic.is_worktree(p)]
    nf = nr = nnull = 0
    stmts, conflicts = [], []
    for path in logs:
        build = _classify_log(path)
        nf += 1
        if build is None:
            # No dynamo runtime banner at all: an encoder-pool / pure-Python /
            # converter-only log. runtime_build stays NULL -- the question is not
            # meaningful for these runs, so NULL is the honest answer, not a gap.
            nnull += 1
            continue
        rid = run_id_of(path)
        ver, _note = BUILD_META[build]
        conflicts.append((rid, build, path))
        stmts.append(
            # COALESCE: never overwrite a value another pass already attested.
            "update provenance.runs set "
            "runtime_build=coalesce(runtime_build,%s), "
            "runtime_version=coalesce(runtime_version,%s), "
            "runtime_build_evidence=%s "
            "where run_id=%s and (runtime_build is null or runtime_version is null "
            "or runtime_build_evidence is distinct from %s)"
            % (ic.lit(build), ic.lit(ver), ic.lit(path), ic.lit(rid), ic.lit(path)))
        nr += 1
    for i in range(0, len(stmts), 200):
        db.run_sql(";\n".join(stmts[i:i + 200]))

    # Disagreement audit AFTER the write: the COALESCE above cannot have changed an
    # already-attested value, so anything that differs now was written by the other
    # pass from other evidence and must be surfaced, not hidden.
    bad = []
    for i in range(0, len(conflicts), 300):
        chunk = conflicts[i:i + 300]
        got = dict((r[0], r[1]) for r in db.rows(
            "select run_id, coalesce(runtime_build,'') from provenance.runs where run_id in (%s)"
            % ",".join(ic.lit(rid) for rid, _, _ in chunk)))
        for rid, build, path in chunk:
            if rid in got and got[rid] and got[rid] != build:
                bad.append((rid, got[rid], build, path))
    if bad:
        print("[K41] MARKER CONFLICT on %d runs -- another pass attests a different "
              "build. NOT resolved automatically:" % len(bad), flush=True)
        for rid, stored, mine, path in bad[:20]:
            print(f"        {rid}: stored={stored} kvbm-marker={mine}  ({path})", flush=True)
    print(f"[K41] logs read={nf} attested={nr} no-runtime-banner(NULL)={nnull} "
          f"conflicts={len(bad)}", flush=True)
    return nf, nr


# ========================================================================= K42
# manifest file -> (manifest_id, results file, actuation, generator, note).
# ACTUATION IS DECLARED, NOT INFERRED. It is the actuation of the harness that
# consumed the manifest, and it is asserted here against named evidence so a
# manifest can never be silently attributed to the other controller.
_MANIFESTS = {
    f"{SIM}/cells_44.jsonl": (
        "cells_44", f"{SIM}/results_44.jsonl", "target-time",
        "simulation/gen_cells_44.py -> simulation/e2b_fleet.py -> run_cell.py",
        "The 4.4 fleet matrix: 5 in-span windows x 4 leads {15,30,45,300} x 4 rho "
        "{10,15,20,25} x (2 quantiles x 3 TSFMs forecast + 1 reactive) = 480 + 80 = 560. "
        "Seed-0 shuffled so any prefix is representative; launched as a 60-cell canary "
        "wave then 500 at concurrency 500."),
    f"{SIM}/cells_44_wave1.jsonl": (
        "cells_44_wave1", f"{SIM}/results_44.jsonl", "target-time",
        "first 60 lines of cells_44.jsonl (launch wave 1, concurrency 60)",
        "The canary wave, not an independent design: it is the 60-line prefix of "
        "cells_44.jsonl. Its results are inside results_44.jsonl, so its coverage row "
        "is a subset, not an additional sweep."),
    f"{SIM}/cells_week.jsonl": (
        "cells_week", None, "target-time",
        "week-scale sweep manifest -> simulation/results/week_matrix/",
        "The week-scale (aggregate-window) sweep. ADJUDICATION §2.7 notes only 19 of "
        "its combinations are in provenance.runs; the manifest makes the shortfall "
        "queryable via provenance.sweep_manifest_coverage."),
    f"{SIM}/cells_week_canary.jsonl": (
        "cells_week_canary", f"{SIM}/results_week_canary.jsonl", "target-time",
        "3-cell canary for the week sweep",
        "All 3 requested cells returned a converter ERROR rather than a graded cell "
        "(results_week_canary.jsonl carries {error:'converter'}), which is why "
        "factorial_cell has no rows from this file. Ingesting the manifest is what "
        "makes that a recorded 3/3 failure instead of an absence."),
    f"{SIM}/pilot_cells.jsonl": (
        "pilot_cells", f"{SIM}/pilot_results.jsonl", "target-time",
        "fleet pilot lead sweep -> simulation/e2b_fleet.py --concurrency 12",
        "The 12-cell pilot that the 560-cell grid was parity-gated against, bit-exact "
        "(results-ledger.md:112). Same harness, therefore same target-time actuation."),
}

_SMC_COLS = ["manifest_id", "cell_ix", "window_name", "resolution", "rho", "cold_start_s",
             "hysteresis_min", "policy", "quantile", "model", "cell"]


def load_sweep_manifests(idx, reload):
    nf = nr = 0
    for path in sorted(_MANIFESTS):
        if not os.path.exists(path):
            print(f"[K42] MISSING {path}", flush=True)
            continue
        prep = _prep(path, idx, reload)
        if not prep:
            continue
        sha, nbytes = prep
        mid, results_path, act, generator, note = _MANIFESTS[path]
        cells = [json.loads(l) for l in open(path) if l.strip()]
        # Cross-check the declaration against the factorial loader's own table, so the
        # manifest and its graded cells can never end up on opposite sides.
        if results_path and actuation_of(results_path) != act:
            raise RuntimeError(
                "actuation disagreement for %s: manifest declares %r, "
                "loaders.actuation_of(%s) says %r"
                % (path, act, results_path, actuation_of(results_path)))
        man = {"manifest_id": mid, "manifest_path": path, "actuation": act,
               "n_cells": len(cells), "generator": generator,
               "results_path": results_path, "is_current": act != "target-time",
               "note": note}
        rows = [{"manifest_id": mid, "cell_ix": i,
                 "window_name": c.get("window"), "resolution": c.get("resolution"),
                 "rho": c.get("rho"), "cold_start_s": c.get("cold_start_s"),
                 "hysteresis_min": c.get("hysteresis_min"), "policy": c.get("policy"),
                 "quantile": c.get("quantile"), "model": c.get("model"), "cell": c}
                for i, c in enumerate(cells)]
        stmts = [ic.upsert_sql("sweep_manifest", man, "manifest_id")]
        for i in range(0, len(rows), 500):
            stmts.append(ic.multi_upsert_sql("sweep_manifest_cell", _SMC_COLS,
                                             rows[i:i + 500], ["manifest_id", "cell_ix"],
                                             jsonb_cols=("cell",)))
        stmts.append(ic.ingest_sql(path, sha, "K42", len(rows), None, nbytes))
        db.run_sql(";\n".join(s for s in stmts if s))
        nf += 1
        nr += len(rows)
    return nf, nr
