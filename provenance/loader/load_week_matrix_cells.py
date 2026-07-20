"""K7w — project the week_matrix sweep into provenance.factorial_cell.

WHY THIS EXISTS
---------------
sweep_manifest_coverage reported cells_week 112 requested / 0 returned. The 112 cells
were not missing from disk and not missing from the spine: repair3_week_matrix.py had
already loaded all 112 runs rows (K3 encoder_run_summary + K4 worker_schedule). What was
missing was the FACTORIAL projection — the graded (dims -> p99, cost, feasible) row that
factorial_cell holds and that every feasibility rollup reads. week_matrix is the one
factorial family with no `*_results.json`: run_week_matrix.sh deletes the per-request
jsonl and keeps only `<tag>.jsonl.stats.json` + `<tag>.sched.json`, so the cell has to be
projected from the stats file rather than parsed from a results file. That is why
loaders.load_factorial (which globs results files) never saw it.

ACTUATION
---------
Declared by loaders.actuation_of(), which resolves week_matrix through the explicit
_TARGET_TIME_DIRS identity table — never a path substring. week_matrix is TARGET-TIME
(run_week_matrix.sh:5 -> simulation/forecast_schedule.py; leads {15,30,45,300}) and is
SUPERSEDED by results/week_surface_issuetime/ (issue-time, leads {15,30,45,165}). The
runs rows are therefore demoted to is_current=false, exactly as
schema/24_actuation_correction.sql:129 did for the other target-time families. Without
that demotion these 112 cells would enter current_factorial and break C507 — the
invariant that the two actuations are never pooled in a published aggregate.

Nothing is destroyed: the cells stay fully queryable via factorial_cell with
actuation='target-time', which is how the other 572 superseded cells are already held.

INGEST_LOG
----------
ingest_log's primary key is file_path, so re-registering the 112 `*.jsonl.stats.json`
paths under K7w would OVERWRITE their existing K3 registration and erase the record that
the encoder summaries were loaded. It does not do that. The pass registers exactly one
new row, against the sweep's own job list (`jobs.txt`, a real on-disk file not previously
ingested), carrying the 112-row count. Per-cell provenance lives in
factorial_cell.source_path, which points at the individual stats file.

FEASIBLE
--------
The stats files record no verdict, so it is derived with the SAME rule the sibling
issue-time surface records in its own header ("aggregate_feasible = p99<1000 & not
divergent") and the same 1000 ms p99 encoder-delay SLA that factorial_cell.feasible is
COMMENTed with. Derived, not invented, and identical to the surface it is compared
against — the two families are graded by one rule or neither comparison means anything.

Idempotent: pure upserts keyed on run_id plus one ingest_log upsert. Run it twice; the
second run changes nothing (verified).
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import db
import ingest_common as ic
import loaders as L
from runid import parse

WM = "/home/gio/tese/simulation/results/week_matrix"
JOBS = f"{WM}/jobs.txt"
SLA_P99_MS = 1000.0

# loaders._FC_RUN_COLS minus 'kind' -- see the note in build().
_RUN_COLS = [c for c in L._FC_RUN_COLS if c != "kind"]


def _p(j, block, stat):
    b = j.get(block)
    return b.get(stat) if isinstance(b, dict) else None


def build():
    runs, cells = [], []
    for path in sorted(glob.glob(f"{WM}/*.jsonl.stats.json")):
        if ic.is_worktree(path):
            continue
        j = json.load(open(path))
        d = parse(path)
        act = L.actuation_of(path)                 # explicit identity table, never a substring
        assert act == "target-time", f"{path}: unexpected actuation {act!r}"
        fam = L._family_dims(path)
        lead = d.get("lead_s")
        sch = j.get("worker_schedule") or {}
        p99 = _p(j, "encoder_delay_ms", "p99")
        divergent = j.get("queue_divergent")
        feasible = None
        if p99 is not None:
            feasible = bool(p99 < SLA_P99_MS and not divergent)

        dims = {
            "window_name": fam["window"],           # 'aggregate' (C209 vocabulary)
            "resolution": fam["resolution"],        # '15s'   (run_week_matrix.sh:17)
            "hysteresis_min": fam["hysteresis_min"],  # 3     (run_week_matrix.sh:18)
            "rho": d.get("rho"),
            "cold_start_s": lead,
            "lead_s": lead,
            # reactive cells carry no model/quantile: run_week_matrix.sh passes a dummy
            # 'p90 chronos' on the reactive line purely to pick a timeline parquet, and
            # the reactive controller reads neither. cells_week's manifest rows record
            # them as NULL/NULL, and the coverage join matches on these columns.
            "policy": d.get("policy"),
            "model": d.get("model") if d.get("policy") != "reactive" else None,
            "quantile": d.get("quantile") if d.get("policy") != "reactive" else None,
        }
        # NB: 'kind' is deliberately absent -- these spine rows already exist from the
        # K3/K4 load (repair3_week_matrix.py) and carry kind='K4'. multi_upsert_sql
        # writes every column in its list, so including 'kind' here would overwrite that
        # record with K7w. The factorial projection is an ADDITIONAL fact about these
        # runs, not a re-ingest of them; see _RUN_COLS below.
        runs.append(dict(dims, run_id=d["run_id"], experiment="factorial", pool="encoder",
                         actuation=act, source_path=path, is_current=False))
        cells.append(dict(dims, run_id=d["run_id"], actuation=act, readiness=None,
                          p99_ms=p99,
                          max_ms=_p(j, "encoder_delay_ms", "max"),
                          feasible=feasible,
                          provisioned_ws=j.get("provisioned_worker_seconds"),
                          busy_ws=j.get("busy_worker_seconds"),
                          sched_steps=sch.get("steps"),
                          sched_min_workers=sch.get("min_workers"),
                          sched_max_workers=sch.get("max_workers"),
                          source_path=path))
    return runs, cells


def main():
    runs, cells = build()
    if not cells:
        print("no week_matrix stats files found", file=sys.stderr)
        return 1
    for i in range(0, len(cells), 200):
        db.run_sql(ic.multi_upsert_sql("runs", _RUN_COLS, runs[i:i + 200], "run_id"))
        db.run_sql(ic.multi_upsert_sql("factorial_cell", L._FC_COLS, cells[i:i + 200], "run_id"))
    sha, nbytes = ic.file_meta(JOBS)
    db.run_sql(ic.ingest_sql(JOBS, sha, "K7w", len(cells), None, nbytes))
    nfeas = sum(1 for c in cells if c["feasible"])
    print(f"[K7w] week_matrix cells={len(cells)} feasible={nfeas} "
          f"infeasible={len(cells) - nfeas} actuation=target-time is_current=false")
    return 0


if __name__ == "__main__":
    sys.exit(main())
