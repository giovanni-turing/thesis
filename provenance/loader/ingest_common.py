"""Idempotency + SQL builders shared by the per-kind loaders.

COLLISION GUARD
---------------
The delete-then-insert loaders (K2/K4/K5/K6/K10) clear every row for a run_id before
COPYing the new file in. If two DIFFERENT source files map to the same run_id, the second
file silently destroys the first file's rows. That is exactly what happened when whole
directories were missing from runid._DIR_EXP and every file in them fell back to
'misc:<stem>': 29,311 llm_request + 16,939 composed_request + 1,793 encoder_series +
76,776 forecast rows were lost without a single error.

`guard_run_collision()` makes that impossible: before a loader clears a run_id, it checks
ingest_log for any OTHER file already registered against that run_id, and raises
RunIdCollision naming both files. The legitimate case -- one run contributing several file
KINDS (foo.report.json + foo.requests.jsonl + foo.sched.json) -- is allowed, because those
share a (directory, stem) scope key. The check is free when the caller passes the ingest
index that main.py already loaded; otherwise it costs one indexed query.
"""
import hashlib, json, os
import db
from runid import run_scope_key

WORKTREE = "/.claude/worktrees/"

# Directories whose artifacts are still being WRITTEN by running generators. Ingesting a
# half-written file records a sha256 for incomplete data; it self-heals on the next sweep
# once the sha changes, but a partial load can also trip guard_run_collision() mid-run and
# abort an otherwise clean re-ingest. Keep these out until generation finishes, then clear
# the list (or set PROVENANCE_SKIP_DIRS="") and run main.py to pick them up.
# Generation finished 2026-07-20; the eight final tracks are now complete on disk and are ingested.
# Re-populate this list (or set PROVENANCE_SKIP_DIRS) if a generator is restarted.
_DEFAULT_SKIP = ""
SKIP_DIRS = tuple(s.strip() for s in
                  os.environ.get("PROVENANCE_SKIP_DIRS", _DEFAULT_SKIP).split(",") if s.strip())


def is_excluded(path):
    """True if a file must not be ingested: a git-worktree copy, or an artifact still being
    written by a live generator (SKIP_DIRS)."""
    p = path.replace("\\", "/")
    return WORKTREE in p or any(("/" + d) in p for d in SKIP_DIRS)


def is_worktree(path):
    # Every loader uses this as its skip predicate, so route the full exclusion through it.
    return is_excluded(path)


def sha256_file(path, buf=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()


# Kinds whose loaders derive run_id per source file from runid.parse() and then clear that
# run_id's rows before inserting. Only these are collision-checked.
#
# The BULK loaders (K20 grid, K22 trace_eda, K23 vllm_etl, ...) intentionally register a
# whole file set against one synthetic run_id ('grid:grid_summary', 'measured:vllm_h100_trace')
# and scope their deletes by script/source_path, not by run_id. Their ingest_log rows must
# NOT be read as collisions.
PER_FILE_KINDS = frozenset({"K1", "K2", "K3", "K4", "K5", "K6", "K10"})


class IngestIndex(dict):
    """file_path -> sha256, plus `.runs`: run_id -> {file_path: kind} for the collision guard.

    Subclasses dict so every existing `idx.get(path) == sha` call site is unchanged.
    """

    def __init__(self, pairs=(), runs=None):
        super().__init__(pairs)
        self.runs = runs if runs is not None else {}

    def note(self, run_id, path, kind=None):
        """Record a run_id->file binding made during THIS process, so two files loaded in
        the same pass collide as loudly as a file colliding with an earlier pass."""
        if run_id:
            self.runs.setdefault(run_id, {})[path] = kind


def load_ingest_index():
    """file_path -> sha256 for everything already loaded (one query)."""
    idx = IngestIndex()
    for p, s, rid, kind in db.rows(
            "select file_path, sha256, coalesce(run_id,''), coalesce(kind,'') "
            "from provenance.ingest_log"):
        idx[p] = s
        if rid:
            idx.runs.setdefault(rid, {})[p] = kind
    return idx


class RunIdCollision(RuntimeError):
    """Two different source files resolve to the same run_id."""


def _registered_paths(run_id, idx):
    """Paths already bound to run_id by a PER-FILE loader (bulk-loader rows excluded)."""
    if isinstance(idx, IngestIndex):
        return {p for p, k in idx.runs.get(run_id, {}).items() if k in PER_FILE_KINDS}
    return {p for p, in db.rows(
        "select file_path from provenance.ingest_log where run_id=" + lit(run_id) +
        " and kind in (" + ",".join(lit(k) for k in sorted(PER_FILE_KINDS)) + ")")}


def guard_run_collision(run_id, path, idx=None, table=None, kind=None):
    """Raise before any destructive write if `run_id` is already bound to a different run.

    Allowed: other files in the SAME directory with the SAME stem (the multi-kind case,
    e.g. run.report.json + run.requests.jsonl + run.sched.json).
    Rejected: anything else -- that is a run_id collision and clearing the run's rows
    would destroy the other file's data.
    """
    if not run_id:
        return
    scope = run_scope_key(path)
    clashes = sorted(p for p in _registered_paths(run_id, idx)
                     if p != path and run_scope_key(p) != scope)
    if clashes:
        raise RunIdCollision(
            "run_id %r is already registered to a DIFFERENT source file.\n"
            "  incoming : %s\n"
            "  existing : %s\n"
            "  table    : %s\n"
            "Loading would delete the existing file's rows. Fix runid._DIR_EXP / the\n"
            "run_id rule so these files get distinct run_ids, then re-run."
            % (run_id, path, "\n             ".join(clashes), table or "?"))
    if isinstance(idx, IngestIndex):
        idx.note(run_id, path, kind if kind in PER_FILE_KINDS else "K1")


# ---- SQL literal helpers -------------------------------------------------

def lit(v):
    if v is None:
        return "NULL"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, (int, float)):
        # JSON may carry NaN/Infinity (e.g. a percentile over an empty stage).
        # repr() would emit bare `nan`, which psql reads as an identifier;
        # Postgres double precision stores these natively as quoted literals,
        # so preserve them rather than flattening to NULL.
        if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
            return ("'NaN'::double precision" if v != v
                    else "'%sInfinity'::double precision" % ("-" if v < 0 else ""))
        return repr(v)
    if isinstance(v, (list, tuple)):
        if not v:
            return "ARRAY[]::text[]"
        # Type the array by its contents: all-numeric lists target double
        # precision[] columns (e.g. sweep_curve.speedups), everything else
        # text[]. Callers writing numbers into a text[] column must str() them.
        if all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
            return "ARRAY[" + ",".join(lit(x) for x in v) + "]::double precision[]"
        return "ARRAY[" + ",".join(lit(x) for x in v) + "]::text[]"
    return "'" + str(v).replace("'", "''") + "'"


def jsonb(d):
    return lit(json.dumps(d, ensure_ascii=True)) + "::jsonb"


# ---- statement builders (return SQL text; caller batches with `;`) --------

RUN_COLS = ["run_id", "experiment", "pool", "window_name", "policy", "model", "mode",
            "quantile", "resolution", "horizon_h", "lead_s", "cold_start_s", "rho",
            "hysteresis_min", "config_c", "tp", "n_replicas", "converter", "gpu", "engine",
            "actuation", "kind", "source_path", "artifact_paths", "command", "commit_sha",
            "run_utc", "feeds", "supersedes", "superseded_by", "config",
            # runtime/build discriminator (ADJUDICATION §2.2). Only emitted by loaders
            # that can EVIDENCE the build; run_upsert_sql writes a column only when the
            # caller's run dict actually carries it, so existing loaders are unaffected.
            "runtime_build", "runtime_version", "runtime_build_evidence"]


def run_upsert_sql(run):
    cols = [c for c in RUN_COLS if c in run]
    if "run_id" not in cols:
        raise ValueError("run dict needs run_id")
    vals = ",".join(jsonb(run[c]) if c == "config" and isinstance(run[c], (dict, list)) else lit(run[c])
                    for c in cols)
    upd = ",".join(f"{c}=excluded.{c}" for c in cols if c != "run_id")
    return (f"insert into provenance.runs ({','.join(cols)}) values ({vals}) "
            f"on conflict (run_id) do update set {upd}")


def _conflict(cols, keys):
    keys = list(keys) if isinstance(keys, (list, tuple)) else [keys]
    upd = ",".join(f"{c}=excluded.{c}" for c in cols if c not in keys)
    if not upd:
        return f"on conflict ({','.join(keys)}) do nothing"
    return f"on conflict ({','.join(keys)}) do update set {upd}"


def upsert_sql(table, colvals, key, jsonb_cols=()):
    """Single-row INSERT ... ON CONFLICT (key) DO UPDATE."""
    cols = list(colvals)
    vals = ",".join(jsonb(colvals[c]) if c in jsonb_cols else lit(colvals[c]) for c in cols)
    return (f"insert into provenance.{table} ({','.join(cols)}) values ({vals}) "
            f"{_conflict(cols, key)}")


def multi_upsert_sql(table, cols, rowdicts, key, jsonb_cols=()):
    """Multi-row INSERT ... ON CONFLICT (key) DO UPDATE. rowdicts use .get(col)."""
    if not rowdicts:
        return None
    tuples = ["(" + ",".join(jsonb(r.get(c)) if c in jsonb_cols else lit(r.get(c))
                             for c in cols) + ")" for r in rowdicts]
    return (f"insert into provenance.{table} ({','.join(cols)}) values {','.join(tuples)} "
            f"{_conflict(cols, key)}")


def ingest_sql(path, sha, kind, nrows, run_id, nbytes):
    return ("insert into provenance.ingest_log (file_path,sha256,kind,n_rows,run_id,bytes,loaded_at) "
            f"values ({lit(path)},{lit(sha)},{lit(kind)},{int(nrows)},{lit(run_id)},{int(nbytes)},now()) "
            "on conflict (file_path) do update set sha256=excluded.sha256,kind=excluded.kind,"
            "n_rows=excluded.n_rows,run_id=excluded.run_id,bytes=excluded.bytes,loaded_at=now()")


def delete_for_run_sql(table, run_id, keycol="run_id"):
    return f"delete from provenance.{table} where {keycol}={lit(run_id)}"


def file_meta(path):
    return sha256_file(path), os.path.getsize(path)
