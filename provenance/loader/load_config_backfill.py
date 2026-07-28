"""ADJUDICATION §2.12 — backfill the run-level configuration columns added by
schema/23_config_columns.sql.

WHAT IS RECOVERABLE, AND FROM WHERE
-----------------------------------
Nothing here is guessed.  Four evidence classes, each tagged per column in
`runs.config_provenance` so a later audit can tell a measurement from a mapping:

  log:<path>    The archived per-run `.log` sidecar written by dynamo.replay.  These
                carry, verbatim:
                  "AIC session initialized: backend=vllm, system=h100_sxm,
                   model=Qwen/Qwen3-VL-8B-Instruct, tp=2"
                  "Loading database for system='h100_sxm', backend='vllm', version='0.19.0'"
                  "AIC: using pure-Rust RustAicCallback (no GIL on the predict hot path)"
                  "KvManager initialized ... with block_size 64, eviction=Lineage"
                Log discovery mirrors the run's own naming: <stem>.log, and the
                .sim/.ctl/.conv variants, and a sibling logs/<stem>.log.

  point:<path>  defense/anim/data/g3_32b/points/*.json, which record model/tp/moe_tp/
                aic_version/aic_system explicitly as fields.

  git:<path>    `git log -1 -- <source_path>` — the commit ARCHIVING the artifact.
                Written to artifact_commit_sha, never to commit_sha.

  by-construction:<ref>   runs.tp = 1 for pool='encoder' only, applied by
                schema/23_config_columns.sql PART B, never by this module.

SHARED WITH THE §2.2 PASS
-------------------------
runtime_build / runtime_version are also written by load_runtime_build.py. That is
safe, and deliberate, because both passes read the SAME log marker
("Using Lineage inactive backend (Tick)" = 1.3.0 source build, the bare line =
1.2.1 wheel) and write the SAME vocabulary, and both COALESCE rather than
overwrite. An earlier revision of this module used "AIC: using pure-Rust
RustAicCallback" instead; cross-tabulated over every archived log the two markers
agree on all 493 source-build artifacts, but the RustAicCallback line is absent
from wheel logs, so it could not see the 110 wheel artifacts. The Lineage marker
is used here for that reason. The two passes differ only in reach: this one maps
log -> run through runs.source_path, the §2.2 one re-derives a run_id from the log
filename, which resolves far fewer runs.

WHAT IS NOT RECOVERABLE (left NULL, reported as coverage)
---------------------------------------------------------
  * runs.commit_sha — the code commit that produced a run.  No artifact records it.
    Untouched, still NULL on all rows.  artifact_commit_sha is NOT a substitute.
  * runs.engine — populated on 2 of 3,044 rows and left that way; no simulated run
    artifact names an engine, and defaulting it to 'vLLM' would manufacture a fact.
  * Anything for a run whose artifact has no log/point sidecar (converter-only logs
    carry interpolation warnings and no configuration at all).

IDEMPOTENCY
-----------
The UPDATE is keyed on run_id and writes the same values from the same files every
time; `runs` is not an ingest_log-tracked row store, so re-running loads 0 CHANGED
rows (verified by comparing a pre/post digest).  Re-run freely.
"""
import json
import os
import re
import subprocess
import sys

import db

ROOT = "/home/gio/tese"

_SUFFIXES = (
    ".requests.jsonl", ".jsonl.stats.json", ".stats.json", ".report.json",
    ".sched.json", ".series.json", ".g6mix.json", ".jsonl", ".json",
    ".parquet", ".csv",
)


def _stem(path):
    for suf in _SUFFIXES:
        if path.endswith(suf):
            return path[: -len(suf)]
    return path


def _log_paths(path):
    """Every archived log sidecar belonging to this run's artifact."""
    stem = _stem(path)
    d, base = os.path.dirname(path), os.path.basename(_stem(path))
    cands = [
        stem + ".log", stem + ".sim.log", stem + ".ctl.log", stem + ".conv.log",
        os.path.join(d, "logs", base + ".log"),
        os.path.join(os.path.dirname(d), "logs", base + ".log"),
    ]
    return [c for c in cands if os.path.exists(c)]


def _point_path(path):
    d, base = os.path.dirname(path), os.path.basename(_stem(path))
    cand = os.path.join(os.path.dirname(d), "points", base + ".json")
    return cand if os.path.exists(cand) else None


_RE_SESSION = re.compile(
    r"AIC session initialized: backend=(\S+?), system=(\S+?), model=(\S+?), tp=(\d+)")
_RE_PERFDB = re.compile(
    r"Loading database for system='([^']+)', backend='([^']+)', version='([^']+)'")
# The dynamo.replay build discriminator, shared verbatim with
# load_runtime_build.py (§2.2). The "(Tick)" suffix is emitted only by the newer
# kvbm_logical::manager::builder in the 1.3.0 source build; the 1.2.1 wheel logs the
# bare line. Not an inference from run age — a runtime banner.
_SRC_MARKER = "Using Lineage inactive backend (Tick)"
_WHEEL_MARKER = "Using Lineage inactive backend"
_RUNTIME_VERSION = {"source": "1.3.0", "wheel": "1.2.1"}


def _classify_build(text):
    """-> 'source' | 'wheel' | None. None = no dynamo runtime banner at all
    (encoder-pool / converter-only logs), where the question is not meaningful."""
    if _SRC_MARKER in text:
        return "source"
    if _WHEEL_MARKER in text:
        return "wheel"
    return None


_RE_BLOCK = re.compile(r"block_size (\d+)")
_RE_EVICT = re.compile(r"eviction=(\w+)")

# Cap the read: these logs are per-request-chatty and only the header carries config.
_LOG_READ_BYTES = 400_000


def _from_logs(path):
    """(values, provenance) parsed from the run's archived logs."""
    vals, prov = {}, {}
    logs = _log_paths(path)
    if not logs:
        return vals, prov
    text = ""
    for lg in logs:
        try:
            with open(lg, errors="replace") as fh:
                text += fh.read(_LOG_READ_BYTES)
        except OSError:
            continue
    tag = "log:" + os.path.relpath(logs[0], ROOT)

    def put(col, val):
        if val is not None and col not in vals:
            vals[col] = val
            prov[col] = tag

    m = _RE_SESSION.search(text)
    if m:
        put("aic_backend", m.group(1))
        put("aic_system", m.group(2))
        put("model_checkpoint", m.group(3))
        put("tp", int(m.group(4)))
    m = _RE_PERFDB.search(text)
    if m:
        put("aic_system", m.group(1))
        put("aic_backend", m.group(2))
        put("aic_perf_db_version", m.group(3))
    # Shared with the §2.2 pass (load_runtime_build._classify_log), deliberately the
    # SAME marker and SAME vocabulary, so the two passes cannot disagree. This one
    # reaches more runs only because it maps log -> run via runs.source_path rather
    # than re-deriving a run_id from the log filename.
    build = _classify_build(text)
    if build:
        put("runtime_build", build)
        put("runtime_version", _RUNTIME_VERSION[build])
    m = _RE_BLOCK.search(text)
    if m:
        put("kv_block_size", int(m.group(1)))
    m = _RE_EVICT.search(text)
    if m:
        put("kv_eviction", m.group(1))
    return vals, prov


def _from_point(path):
    """(values, provenance) read from a g3_32b points/*.json sidecar."""
    vals, prov = {}, {}
    pt = _point_path(path)
    if not pt:
        return vals, prov
    try:
        with open(pt) as fh:
            d = json.load(fh)
    except (OSError, ValueError):
        return vals, prov
    tag = "point:" + os.path.relpath(pt, ROOT)
    for src, col in (("aic_version", "aic_perf_db_version"),
                     ("aic_system", "aic_system"),
                     ("model", "model_checkpoint"),
                     ("tp", "tp"),
                     ("moe_tp", "moe_tp"),
                     # window_name is an EXISTING column, NULL on all 232 g3_32b runs
                     # even though every point file records "window": "head2k". Left
                     # NULL it silently drops the whole 32B arm from every
                     # window-conditioned query. 'head2k' is already a member of the
                     # provenance.windows dimension, so C209 stays green.
                     ("window", "window_name"),
                     ("speedup", "arrival_speedup")):
        if d.get(src) is not None:
            vals[col] = d[src]
            prov[col] = tag
    return vals, prov


def _git_sha(path):
    rel = os.path.relpath(path, ROOT)
    if rel.startswith(".."):
        return None, None
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%H", "--", rel],
                           cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None, None
    sha = r.stdout.strip()
    return (sha, "git:" + rel) if sha else (None, None)


_COLS = ("model_checkpoint", "moe_tp", "tp", "runtime_build", "runtime_version",
         "aic_backend", "aic_system", "aic_perf_db_version", "kv_block_size",
         "kv_eviction", "arrival_speedup", "window_name", "artifact_commit_sha")


_INT_COLS = ("moe_tp", "tp", "kv_block_size")
_FLOAT_COLS = ("arrival_speedup",)

_STAGE_DDL = """
DROP TABLE IF EXISTS provenance._config_backfill_stage;
CREATE UNLOGGED TABLE provenance._config_backfill_stage (
  run_id text PRIMARY KEY, vals jsonb, prov jsonb);
"""


def extract():
    """path -> (values, provenance), one filesystem/git pass per distinct artifact."""
    cache = {}
    for (path,) in db.rows("SELECT DISTINCT source_path FROM provenance.runs "
                           "WHERE source_path IS NOT NULL"):
        vals, prov = _from_logs(path)
        pv, pp = _from_point(path)
        # The point file is the authoritative structured record where both exist.
        vals.update(pv)
        prov.update(pp)
        sha, stag = _git_sha(path)
        if sha:
            vals["artifact_commit_sha"] = sha
            prov["artifact_commit_sha"] = stag
        if vals:
            cache[path] = (vals, prov)
    return cache


def run():
    cache = extract()
    pairs = db.rows("SELECT run_id, source_path FROM provenance.runs "
                    "WHERE source_path IS NOT NULL")

    db.run_sql(_STAGE_DDL)
    staged = db.copy_rows(
        "_config_backfill_stage", ("run_id", "vals", "prov"),
        ((rid, json.dumps(cache[p][0]), json.dumps(cache[p][1]))
         for rid, p in pairs if p in cache))

    # COALESCE keeps any value that was already ingested: this only FILLS NULLs,
    # so no archived measurement is overwritten (R40) and re-running is a no-op.
    # EXCEPTION (D77, bridge 257): artifact_commit_sha is recomputed archival
    # LINEAGE (`git log -1 -- source_path`), not a measurement -- when the
    # staged Git SHA is non-null it must REFRESH the row, or a later artifact
    # commit could never advance the pin. Staged-first COALESCE keeps the
    # pass idempotent (same SHA rewrites itself) while measured/config
    # fields retain fill-only semantics.
    def _set(c):
        cast = ("::integer" if c in _INT_COLS
                else "::double precision" if c in _FLOAT_COLS else "")
        if c == "artifact_commit_sha":
            return f"{c} = COALESCE((s.vals ->> '{c}'){cast}, r.{c})"
        return f"{c} = COALESCE(r.{c}, (s.vals ->> '{c}'){cast})"
    sets = ", ".join(_set(c) for c in _COLS)
    db.run_sql(
        f"UPDATE provenance.runs r SET {sets}, "
        "config_provenance = COALESCE(r.config_provenance, '{}'::jsonb) || s.prov "
        "FROM provenance._config_backfill_stage s WHERE r.run_id = s.run_id;"
        "DROP TABLE provenance._config_backfill_stage;")

    print(f"load_config_backfill: {staged} run rows staged from "
          f"{len(cache)} distinct artifacts")
    for col, n, pct in db.rows("SELECT column_name, n_populated, pct_populated "
                               "FROM provenance.v_config_coverage "
                               "ORDER BY pct_populated DESC, column_name"):
        print(f"  {col:<22} {n:>5}  {pct:>6}%")
    return len(cache), staged


def load_config_backfill(idx=None, reload=False):
    """main.py entry point (K34).

    A POST-PASS, not a file ingest: it writes no new rows, registers nothing in
    ingest_log and clears no run_id, so guard_run_collision has nothing to guard —
    there is no delete-then-insert step that a second file could destroy. It must
    run AFTER every ingest, since it can only annotate runs that already exist.
    Returns (artifacts_inspected, run_rows_staged) for main.py's tally.
    """
    return run()


if __name__ == "__main__":
    sys.exit(0 if run() is not None else 1)
