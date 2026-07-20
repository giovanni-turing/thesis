-- =====================================================================
-- 23_config_columns.sql
--
-- ADJUDICATION.md §2.12 — "missing configuration columns (blocks future
-- audits)".  Run-level configuration facts that EXIST in the archived
-- artifacts but had no column in provenance.runs, so no query could
-- condition on them.
--
-- Invariants (same as 22_corrections.sql):
--   1. NOTHING ARCHIVED IS DESTROYED.  Every column here is NEW.  No
--      existing column is overwritten.  In particular `runs.commit_sha`
--      (the code commit that PRODUCED a run — unrecoverable, NULL on all
--      3,044 rows) is left untouched; the recoverable fact is a
--      DIFFERENT one and gets its own column, `artifact_commit_sha`.
--   2. EVERY STATEMENT IS IDEMPOTENT.  Safe to run repeatedly.
--   3. NO INVENTED DEFAULTS.  A value is written only where an archived
--      artifact, or an explicitly-tagged documentary mapping, supplies
--      it.  Everything else stays NULL and is reported as a coverage
--      fraction, not silently filled.
--
-- Every backfilled value carries its own evidence in
-- `runs.config_provenance` (jsonb, column -> evidence token):
--     "log:<path>"        parsed from that run's archived .log sidecar
--     "point:<path>"      read from that run's g3_32b points/*.json
--     "git:<path>"        `git log -1` over the archived artifact
--     "doc:<tex>#<label>" documented mapping, NOT a measurement
--     "by-construction:<ref>"  architectural fact, NOT a measurement
--
-- Depends on: 01_schema.sql.  Backfilled by loader/load_config_backfill.py.
-- =====================================================================


-- =====================================================================
-- PART A — the columns
-- =====================================================================

-- NOT OWNED HERE: runtime_build / runtime_version / runtime_build_source belong to
-- 23_runtime_build_and_actuation.sql (loader K32).  They were briefly written from
-- this file's "RustAicCallback" marker; K32's "(Tick)" marker is strictly better —
-- the two agree on all 493 source-build artifacts and K32 additionally resolves 110
-- wheel artifacts this marker leaves NULL.  Single owner, single vocabulary
-- ('srcbuild'/'wheel').  See PART D.

ALTER TABLE provenance.runs
  ADD COLUMN IF NOT EXISTS model_checkpoint     text,
  ADD COLUMN IF NOT EXISTS moe_tp               integer,
  ADD COLUMN IF NOT EXISTS aic_backend          text,
  ADD COLUMN IF NOT EXISTS aic_system           text,
  ADD COLUMN IF NOT EXISTS aic_perf_db_version  text,
  ADD COLUMN IF NOT EXISTS kv_block_size        integer,
  ADD COLUMN IF NOT EXISTS kv_eviction          text,
  ADD COLUMN IF NOT EXISTS arrival_speedup      double precision,
  ADD COLUMN IF NOT EXISTS artifact_commit_sha  text,
  ADD COLUMN IF NOT EXISTS config_provenance    jsonb;

COMMENT ON COLUMN provenance.runs.arrival_speedup IS
  'Offered-rate multiplier applied to the window''s replayed arrivals — the thesis '
  '"speedup" convention (offered_req_per_s = window mean_requests_per_s x speedup, '
  'sweep_load.py:185-188). NEVER the achieved rate: achieved is what came back and is a '
  'RESULT, not a configuration. Present at run level so language-pool tracks that have no '
  'encoder summary (notably the 232 g3_32b defence runs) can be conditioned on load. '
  'encoder_run_summary.arrival_speedup and sweep_point.speedup carry the same quantity for '
  'their own tracks; C414 enforces that they never disagree.';

COMMENT ON COLUMN provenance.runs.model_checkpoint IS
  'Served LLM checkpoint, the full HuggingFace id (e.g. Qwen/Qwen3-VL-8B-Instruct). '
  'DISTINCT FROM runs.model, which names the FORECAST model (chronos/toto/timesfm/ewma/...) '
  'and never the served model — the overload is why no query could previously select the '
  '32B arm. Parsed from the archived run .log line "AIC session initialized: ... model=<id>" '
  'or from defense/anim/data/g3_32b/points/*.json ."model". NULL where no such sidecar exists.';

COMMENT ON COLUMN provenance.runs.moe_tp IS
  'Mixture-of-Experts tensor-parallel degree, distinct from runs.tp (attention/dense TP). '
  'Non-NULL only for the MoE arms (Qwen3-VL-30B-A3B, Qwen3-VL-235B-A22B); NULL — not 1 — '
  'for dense models, where the parameter does not apply. Source: g3_32b points/*.json.';

COMMENT ON COLUMN provenance.runs.aic_backend IS
  'aiconfigurator inference backend whose performance database supplied the timing '
  'predictions (''vllm'' throughout). From the log line "AIC session initialized: backend=".';

COMMENT ON COLUMN provenance.runs.aic_system IS
  'aiconfigurator system key naming the GPU whose collected performance data was replayed '
  '(''h100_sxm'' throughout the simulated fleet). NOT the GPU the simulation ran on, and NOT '
  'the RTX 5090 of the physical encoder anchor — runs.gpu carries that, and carries it for '
  'only the 2 measured-silicon rows. Keeping the two apart is the point of this column.';

COMMENT ON COLUMN provenance.runs.aic_perf_db_version IS
  'Version of the aiconfigurator PERFORMANCE DATABASE loaded for the run (''0.19.0''), from '
  'the log line "Loading database for system=..., backend=..., version=". This is NOT the '
  'aiconfigurator PACKAGE version, which tab:ap-env pins at 0.10.0 (editable, data branch). '
  'The two numbers differ legitimately and have been mistaken for each other before.';

COMMENT ON COLUMN provenance.runs.kv_block_size IS
  'KV-cache block size in tokens used by the mocker KV manager (64 throughout). From the log '
  'line "KvManager initialized ... with block_size <n>". Governs prefix-cache hit '
  'granularity, hence the prefix_cache_reused_ratio columns in llm_run_summary.';

COMMENT ON COLUMN provenance.runs.kv_eviction IS
  'KV-cache eviction policy of the mocker KV manager (''Lineage'' throughout), from the log '
  'line "eviction=". Recorded because prefix-cache reuse figures are policy-dependent.';

COMMENT ON COLUMN provenance.runs.artifact_commit_sha IS
  'Git commit at which the run''s primary artifact is ARCHIVED in this repository '
  '(`git log -1 -- <source_path>`). This is deliberately NOT runs.commit_sha, which means '
  'the code commit that PRODUCED the run and remains NULL on all rows because no artifact '
  'records it. artifact_commit_sha answers "which tree state contains this measurement", '
  'not "which code made it" — do not substitute one for the other in a reproduction claim. '
  'NULL for artifacts that are untracked (most of defense/anim/data/ is gitignored).';

COMMENT ON COLUMN provenance.runs.config_provenance IS
  'Per-column evidence map for every value backfilled by 23_config_columns.sql: '
  '{"<column>": "<evidence token>"}. Tokens: "log:<path>" parsed from the run''s archived '
  'log sidecar; "point:<path>" from a g3_32b points/*.json; "git:<path>"; '
  '"doc:<tex>#<label>" for a documented mapping; "by-construction:<ref>" for an '
  'architectural fact. Any column NOT keyed here was not backfilled. This is what makes the '
  'measured/documented/by-construction distinction queryable instead of a matter of trust.';


-- =====================================================================
-- PART B — §2.12 runs.tp for pool='encoder': backfill TP=1
-- =====================================================================
-- ADJUDICATION §2.12 row 2 and §5.1.  The encoder pool is not
-- tensor-parallel; TP=1 is an ARCHITECTURAL fact, not a measurement, and
-- §5.1 is explicit that "a populated tp=1 would record the
-- configuration, not the analytic zero".  It is therefore written with a
-- by-construction provenance tag, never silently.
--
-- Only rows where tp IS NULL are touched, so no ingested value is
-- overwritten and the statement is idempotent.
-- =====================================================================

UPDATE provenance.runs
   SET tp = 1,
       config_provenance =
         COALESCE(config_provenance, '{}'::jsonb)
         || jsonb_build_object('tp', 'by-construction:ADJUDICATION#5.1')
 WHERE pool = 'encoder'
   AND tp IS NULL;


-- =====================================================================
-- PART C — coverage view
-- =====================================================================
-- Reports, per configuration column, how many runs carry a value and by
-- what class of evidence.  The whole point of §2.12 is that a future
-- audit can SEE the gap instead of rediscovering it, so the gap is a
-- first-class queryable object.
-- =====================================================================

CREATE OR REPLACE VIEW provenance.v_config_coverage AS
WITH cols(col) AS (
  VALUES ('model_checkpoint'), ('moe_tp'), ('tp'), ('runtime_build'),
         ('runtime_version'), ('aic_backend'), ('aic_system'),
         ('aic_perf_db_version'), ('kv_block_size'), ('kv_eviction'),
         ('arrival_speedup'), ('window_name'),
         ('artifact_commit_sha'), ('gpu'), ('engine'), ('commit_sha')
),
tot AS (SELECT count(*)::numeric n FROM provenance.runs)
SELECT c.col AS column_name,
       (SELECT n FROM tot)::bigint                        AS n_runs,
       count(*) FILTER (WHERE to_jsonb(r) ->> c.col IS NOT NULL) AS n_populated,
       round(100.0 * count(*) FILTER (WHERE to_jsonb(r) ->> c.col IS NOT NULL)
             / (SELECT n FROM tot), 2)                    AS pct_populated,
       count(*) FILTER (WHERE r.config_provenance ->> c.col LIKE 'log:%')    AS n_from_log,
       count(*) FILTER (WHERE r.config_provenance ->> c.col LIKE 'point:%')  AS n_from_point,
       count(*) FILTER (WHERE r.config_provenance ->> c.col LIKE 'git:%')    AS n_from_git,
       count(*) FILTER (WHERE r.config_provenance ->> c.col LIKE 'doc:%')    AS n_documentary,
       count(*) FILTER (WHERE r.config_provenance ->> c.col
                              LIKE 'by-construction:%')                      AS n_by_construction
  FROM cols c CROSS JOIN provenance.runs r
 GROUP BY c.col
 ORDER BY 4 DESC, 1;

-- =====================================================================
-- PART D — retire the documentary runtime_version tag
-- =====================================================================
-- An earlier revision of this file derived runtime_version from a
-- DOCUMENTARY mapping (apendice.tex tab:ap-env applied to a detected
-- build).  The sibling §2.2 pass established the far better
-- "Using Lineage inactive backend (Tick)" log marker, which attests the
-- build DIRECTLY and additionally resolves the wheel population.  Both
-- passes now read that marker and write the same vocabulary
-- ('source'/'wheel' -> 1.3.0/1.2.1), so runtime_version is evidenced by a
-- log line, not by a document.
--
-- Only the stale PROVENANCE TAG is rewritten; the VALUES are untouched and
-- are re-attested from the logs on the next K34 pass.  Idempotent.
-- =====================================================================

UPDATE provenance.runs
   SET config_provenance = config_provenance - 'runtime_version'
 WHERE config_provenance ->> 'runtime_version' = 'doc:apendice.tex#tab:ap-env';


COMMENT ON VIEW provenance.v_config_coverage IS
  'Coverage of every run-level configuration column: how many of the 3,044 runs carry a '
  'value, and by what class of evidence (archived log, g3_32b point file, git, documentary '
  'mapping, by-construction). Columns with pct_populated = 0 (commit_sha, engine) are '
  'UNRECOVERABLE gaps, deliberately left NULL rather than defaulted — see ADJUDICATION '
  '§2.12. Read this before conditioning a query on any configuration column.';
