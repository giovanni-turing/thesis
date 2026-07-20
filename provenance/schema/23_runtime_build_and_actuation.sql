-- =====================================================================
-- 23_runtime_build_and_actuation.sql
--
-- ADJUDICATION.md §2.2 (srcbuild runtime rows + a runtime/build
-- discriminator) and §2.7 (sweep manifests + the 560-cell target-time
-- grid).  Structure only: this file creates the columns, vocabularies,
-- tables and views.  The ROWS are loaded by
-- provenance/loader/load_runtime_build.py (kinds K40/K41/K42), and the
-- actuation relabel is applied by 24_actuation_correction.sql.
--
-- The two invariants of 22_corrections.sql hold here as well:
--   1. NO ARCHIVED MEASUREMENT IS DESTROYED.  srcbuild rows arrive as
--      NEW runs beside the wheel rows; nothing about the wheel rows is
--      rewritten.  The supersession is expressed as data (a
--      metric_supersession row) and resolved by a view.
--   2. EVERY STATEMENT IS IDEMPOTENT.
--
-- Depends on: 01_schema.sql, 20_semantic.sql.
-- =====================================================================


-- =====================================================================
-- PART A — §2.2  the runtime/build discriminator
-- =====================================================================
-- COORDINATION NOTE. runs.runtime_build / runs.runtime_version are NOT
-- created here: they are created and owned by 23_config_columns.sql
-- (ADJUDICATION §2.12), whose vocabulary is 'source' | 'wheel'. This
-- file adopts that vocabulary rather than introducing a second one, and
-- adds exactly two things §2.12 could not supply:
--
--   1. ATTESTATION FOR THE WHEEL SIDE. §2.12 states, correctly for its
--      own probe, that "NO run log in the archive carries a wheel
--      marker, so 'wheel' is currently unattested". Its probe is the
--      log line "AIC: using pure-Rust RustAicCallback", which only the
--      source build emits — so its absence is ambiguous between "wheel"
--      and "no AIC at all".
--
--      There IS a wheel marker, in a line every replay emits regardless
--      of timing model. The KVBM builder logs
--
--        dynamo 1.3.0 (source)  "Using Lineage inactive backend (Tick)"
--        ai-dynamo 1.2.1 (wheel) "Using Lineage inactive backend"
--
--      The "(Tick)" suffix is the 1.3.0 inactive-backend tick source.
--      Presence => source; presence of the bare line WITHOUT the suffix
--      => wheel; absence of the line entirely => no dynamo runtime ran
--      (encoder-pool / pure-Python / converter-only logs) => NULL.
--
--      Cross-checked against the §2.12 probe over all 1,219 archived
--      logs under simulation/results + defense/anim/data:
--        (Tick) and RustAicCallback agree ............ 498 logs
--        (Tick) only, RustAicCallback absent .......... 1 log
--        bare line, no (Tick), no RustAicCallback .... 119 logs
--        neither line ................................ 601 logs
--        DISAGREEMENTS ............................... 0
--      The single (Tick)-only log is srcbuild/run_poly.log: a POLY run
--      executes no AIC callback at all, so the §2.12 probe is blind to
--      it by construction while the KVBM marker still sees it. The 119
--      are the wheel runs §2.12 had to leave NULL.
--
--   2. WHERE THE VALUE WAS READ FROM, per run (runtime_build_evidence).
--      §2.12's config_provenance tags the evidence CLASS; this names the
--      exact log file, so any single row can be re-verified with one
--      grep.
--
-- Rows whose build no artifact attests stay NULL. Never guessed.

ALTER TABLE provenance.runs
  ADD COLUMN IF NOT EXISTS runtime_build_evidence text;

COMMENT ON COLUMN provenance.runs.runtime_build_evidence IS
  'Absolute path of the archived replay log that runs.runtime_build was READ FROM, and '
  'the marker read. Complements 23_config_columns.sql''s config_provenance (which tags '
  'the evidence CLASS) by naming the exact file, so a single row can be re-verified with '
  'one grep. NULL where runtime_build is NULL or was set by the §2.12 pass rather than '
  'by the KVBM-marker pass (K41). See ADJUDICATION §2.2.';

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'runs_runtime_build_vocab') THEN
    ALTER TABLE provenance.runs
      ADD CONSTRAINT runs_runtime_build_vocab
      CHECK (runtime_build IS NULL OR runtime_build IN ('source', 'wheel')) NOT VALID;
  END IF;
END $$;

COMMENT ON CONSTRAINT runs_runtime_build_vocab ON provenance.runs IS
  'Vocabulary is 23_config_columns.sql''s: ''source'' (dynamo 1.3.0 built with '
  'maturin --features aic-forward-pass; in-core Rust AIC) or ''wheel'' (pinned '
  'ai-dynamo==1.2.1 PyPI wheel; per-request Python SDK AIC callback). NOT VALID so it '
  'gates new writes without re-scanning the existing 3,000 rows.';

CREATE INDEX IF NOT EXISTS runs_runtime_build_idx
  ON provenance.runs (runtime_build);


-- ---------------------------------------------------------------------
-- A.2  METRIC-SCOPED supersession
-- ---------------------------------------------------------------------
-- runs.superseded_by is a WHOLE-RUN pointer, and that is too blunt here.
-- The wheel `sweeps:llm_head2k_{poly,aic}_s1` rows are superseded by the
-- srcbuild rows ONLY for the tab:sim-poly-aic metrics; the same runs are
-- still the legitimate s=1 anchor of the Phase-2 speedup knee sweep, and
-- deleting them from the current set would silently break that.  So they
-- keep is_current = true, and the supersession is recorded per metric.

CREATE TABLE IF NOT EXISTS provenance.metric_supersession (
  superseded_run_id text   NOT NULL,
  metric            text   NOT NULL,
  current_run_id    text   NOT NULL,
  superseded_value  double precision,
  current_value     double precision,
  scope             text,
  rationale         text,
  source            text,
  recorded_utc      timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (superseded_run_id, metric)
);

COMMENT ON TABLE provenance.metric_supersession IS
  'Supersession at METRIC granularity, for the case where a later run replaces an '
  'earlier one for SOME published cells but not for the earlier run''s other roles. '
  'Both runs stay is_current; readers that care join through here. Created for '
  'ADJUDICATION.md §2.2 (srcbuild vs wheel, tab:sim-poly-aic).';
COMMENT ON COLUMN provenance.metric_supersession.metric IS
  'Column name in the owning summary table (e.g. llm_run_summary.mean_ttft_ms).';
COMMENT ON COLUMN provenance.metric_supersession.scope IS
  'Where the supersession applies — normally the thesis table/label whose cells are '
  'taken from current_run_id rather than superseded_run_id.';
COMMENT ON COLUMN provenance.metric_supersession.superseded_value IS
  'Value as ingested on the superseded run, copied here so the two are comparable '
  'without a join. The original row is never modified.';


-- ---------------------------------------------------------------------
-- A.3  the effective view for tab:sim-poly-aic
-- ---------------------------------------------------------------------
-- Resolves the §2.2 supersession for readers: one row per (timing model)
-- carrying BOTH sides plus the value the thesis publishes.

CREATE OR REPLACE VIEW provenance.llm_head2k_poly_aic_effective AS
SELECT
  w.run_id                       AS wheel_run_id,
  s.run_id                       AS srcbuild_run_id,
  CASE WHEN w.run_id LIKE '%poly%' THEN 'poly' ELSE 'aic' END AS timing,
  w.mean_ttft_ms                 AS wheel_mean_ttft_ms,
  s.mean_ttft_ms                 AS srcbuild_mean_ttft_ms,
  w.p99_ttft_ms                  AS wheel_p99_ttft_ms,
  s.p99_ttft_ms                  AS srcbuild_p99_ttft_ms,
  w.max_ttft_ms                  AS wheel_max_ttft_ms,
  s.max_ttft_ms                  AS srcbuild_max_ttft_ms,
  w.mean_itl_ms                  AS wheel_mean_itl_ms,
  s.mean_itl_ms                  AS srcbuild_mean_itl_ms,
  w.mean_e2e_latency_ms          AS wheel_mean_e2e_latency_ms,
  s.mean_e2e_latency_ms          AS srcbuild_mean_e2e_latency_ms,
  w.p99_e2e_latency_ms           AS wheel_p99_e2e_latency_ms,
  s.p99_e2e_latency_ms           AS srcbuild_p99_e2e_latency_ms,
  -- the published cell: srcbuild where it exists, wheel otherwise
  coalesce(s.mean_ttft_ms, w.mean_ttft_ms)  AS effective_mean_ttft_ms,
  coalesce(s.p99_ttft_ms,  w.p99_ttft_ms)   AS effective_p99_ttft_ms,
  coalesce(s.max_ttft_ms,  w.max_ttft_ms)   AS effective_max_ttft_ms,
  CASE WHEN s.run_id IS NULL THEN 'wheel' ELSE 'srcbuild' END AS effective_build
FROM provenance.llm_run_summary w
LEFT JOIN provenance.llm_run_summary s
       ON s.run_id = 'srcbuild:llm_head2k_'
                     || CASE WHEN w.run_id LIKE '%poly%' THEN 'poly' ELSE 'aic' END
                     || '_src'
WHERE w.run_id IN ('sweeps:llm_head2k_poly_s1', 'sweeps:llm_head2k_aic_s1');

COMMENT ON VIEW provenance.llm_head2k_poly_aic_effective IS
  'ADJUDICATION.md §2.2. Puts the wheel (ai-dynamo 1.2.1) and srcbuild (dynamo 1.3.0) '
  'head2k isolation runs side by side and names the value the thesis publishes in '
  'tab:sim-poly-aic (srcbuild). Neither underlying row is modified.';


-- =====================================================================
-- PART B — §2.7  actuation as a first-class, non-mixing dimension
-- =====================================================================
-- Two DIFFERENT controllers produced encoder factorial cells:
--
--   target-time  the archived exploratory grid (gen_cells_44.py ->
--                run_cell.py -> verification/scripts/forecast_schedule.py):
--                a scale-up is scheduled so the worker is READY AT the
--                target bin.  Leads {15,30,45,300}s.
--   issue-time   the rebuild (simulation/run_44_factorial_issuetime.py ->
--                forecast_schedule_issuetime.py): the decision is ISSUED
--                at t and the worker becomes ready at t+lead.  Leads
--                {15,30,45,165}s.  This is what the manuscript now
--                frames the encoder result on.
--
-- The target-time grid is SUPERSEDED, not wrong, and must stay auditable
-- rather than invisible — but it must never be silently averaged in with
-- the issue-time rebuild.  The vocabulary is therefore WIDENED (an
-- extension: 'target-time' is a real value the store previously could
-- not represent), not weakened.

ALTER TABLE provenance.runs           DROP CONSTRAINT IF EXISTS runs_actuation_vocab;
ALTER TABLE provenance.factorial_cell DROP CONSTRAINT IF EXISTS factorial_cell_actuation_vocab;

ALTER TABLE provenance.runs
  ADD CONSTRAINT runs_actuation_vocab
  CHECK (actuation IS NULL OR actuation IN ('issue-time', 'target-time')) NOT VALID;

ALTER TABLE provenance.factorial_cell
  ADD CONSTRAINT factorial_cell_actuation_vocab
  CHECK (actuation IS NULL OR actuation IN ('issue-time', 'target-time'));

COMMENT ON COLUMN provenance.factorial_cell.actuation IS
  'Which controller scheduled the scale-ups. ''issue-time'' = decision issued at t, '
  'worker ready at t+lead (forecast_schedule_issuetime.py; the manuscript''s frame). '
  '''target-time'' = worker ready AT the target bin (forecast_schedule.py; the '
  'archived exploratory grid, SUPERSEDED but retained). The two are NOT comparable '
  'cell-for-cell and must never be pooled — filter on this column, or use '
  'provenance.current_factorial. See ADJUDICATION.md §2.7.';

COMMENT ON COLUMN provenance.runs.actuation IS
  'See provenance.factorial_cell.actuation. ''target-time'' runs additionally carry '
  'is_current = false.';


-- ---------------------------------------------------------------------
-- B.2  the current (non-superseded) factorial population
-- ---------------------------------------------------------------------
-- No new view is needed: provenance.current_factorial (02_views.sql)
-- already restricts factorial_cell to is_current runs, so marking the
-- target-time runs is_current = false removes them from it and from
-- everything built on it (v_infeasible, ...). Readers who WANT the
-- archived grid query provenance.factorial_cell directly and filter
-- actuation = 'target-time'.
--
-- CAVEAT recorded honestly: the target-time reactive rho=15 cells are
-- superseded AS A GRID but a handful of them are still the source of
-- published cells (thesis Tab. 7.3 / defense A2 reactive ladder). Those
-- runs therefore carry runs.feeds naming the table they still back, so
-- "superseded" never reads as "unused". See 24_actuation_correction.sql
-- part D.


-- ---------------------------------------------------------------------
-- B.3  sweep manifests: the cells that were REQUESTED
-- ---------------------------------------------------------------------
-- A manifest is the design of a sweep. Ingesting it is what makes
-- "requested but never returned" a queryable fact rather than an
-- absence: results_week_canary.jsonl, for instance, has 3 requested
-- cells of which 3 errored in the converter and 0 produced a cell.

CREATE TABLE IF NOT EXISTS provenance.sweep_manifest (
  manifest_id    text NOT NULL PRIMARY KEY,
  manifest_path  text NOT NULL,
  actuation      text,
  n_cells        integer,
  generator      text,
  results_path   text,
  is_current     boolean NOT NULL DEFAULT true,
  note           text,
  recorded_utc   timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE provenance.sweep_manifest IS
  'One row per sweep CELLS file: the design of a factorial sweep (what was requested), '
  'as distinct from provenance.factorial_cell (what came back). ADJUDICATION.md §2.7.';
COMMENT ON COLUMN provenance.sweep_manifest.actuation IS
  'Actuation model of the harness that consumed this manifest. Carried here so a '
  'manifest can never be silently read as belonging to the other actuation.';
COMMENT ON COLUMN provenance.sweep_manifest.generator IS
  'Script that WROTE the manifest, and the driver that consumed it.';
COMMENT ON COLUMN provenance.sweep_manifest.is_current IS
  'false for manifests of superseded sweeps (all target-time manifests).';

CREATE TABLE IF NOT EXISTS provenance.sweep_manifest_cell (
  manifest_id    text NOT NULL REFERENCES provenance.sweep_manifest(manifest_id) ON DELETE CASCADE,
  cell_ix        integer NOT NULL,
  window_name    text,
  resolution     text,
  rho            numeric,
  cold_start_s   integer,
  hysteresis_min integer,
  policy         text,
  quantile       text,
  model          text,
  cell           jsonb,
  PRIMARY KEY (manifest_id, cell_ix)
);

COMMENT ON TABLE provenance.sweep_manifest_cell IS
  'The individual requested cells of a sweep manifest, in file order (cell_ix is the '
  '0-based line number — the manifests are seed-0 shuffled so any PREFIX is a '
  'representative sample, which is how the launch waves were cut).';
COMMENT ON COLUMN provenance.sweep_manifest_cell.cell_ix IS
  '0-based line number in the manifest file. Load-bearing: the wave-1 canary is the '
  'first 60 lines of cells_44.jsonl.';
COMMENT ON COLUMN provenance.sweep_manifest_cell.cell IS
  'The manifest record verbatim, so a dimension not projected into a column is not lost.';

CREATE INDEX IF NOT EXISTS sweep_manifest_cell_dims_idx
  ON provenance.sweep_manifest_cell (window_name, policy, model, quantile);


-- ---------------------------------------------------------------------
-- B.4  requested-vs-returned coverage
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.sweep_manifest_coverage AS
SELECT m.manifest_id,
       m.actuation,
       m.n_cells                                   AS requested,
       count(f.run_id)                             AS returned,
       m.n_cells - count(f.run_id)                 AS missing,
       m.results_path
  FROM provenance.sweep_manifest m
  LEFT JOIN provenance.sweep_manifest_cell c ON c.manifest_id = m.manifest_id
  LEFT JOIN provenance.factorial_cell f
         ON f.source_path  = m.results_path
        AND f.window_name  IS NOT DISTINCT FROM c.window_name
        AND f.policy       IS NOT DISTINCT FROM c.policy
        AND f.quantile     IS NOT DISTINCT FROM c.quantile
        AND f.model        IS NOT DISTINCT FROM c.model
        AND f.rho          IS NOT DISTINCT FROM c.rho
        AND f.cold_start_s IS NOT DISTINCT FROM c.cold_start_s
 GROUP BY m.manifest_id, m.actuation, m.n_cells, m.results_path;

COMMENT ON VIEW provenance.sweep_manifest_coverage IS
  'Requested (manifest) vs returned (factorial_cell) per sweep. A non-zero `missing` '
  'is a real gap — cells that were designed and launched but produced no graded '
  'result (converter errors, aborted waves).';


-- =====================================================================
-- PART C — visible record of INGEST-METADATA corrections
-- =====================================================================
-- grid_correction records corrections to measured VALUES. This records
-- corrections to the LABELS a loader attached to rows — including
-- run_id renames, so an identifier that appeared in an earlier query,
-- note or audit document stays resolvable forever.

CREATE TABLE IF NOT EXISTS provenance.ingest_correction (
  correction_id   text NOT NULL PRIMARY KEY,
  table_name      text NOT NULL,
  field           text NOT NULL,
  original_value  text,
  corrected_value text,
  n_rows          integer,
  source_path     text,
  evidence        text,
  rationale       text,
  recorded_utc    timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE provenance.ingest_correction IS
  'Corrections to ingest METADATA (labels, dimensions, run_id spelling) as opposed to '
  'corrections to measured values (see provenance.grid_correction). Every row names '
  'the on-disk evidence that settled it. Nothing here changes a measurement.';
COMMENT ON COLUMN provenance.ingest_correction.evidence IS
  'The archived file or source line that decides the correction.';

CREATE TABLE IF NOT EXISTS provenance.run_id_alias (
  old_run_id    text NOT NULL PRIMARY KEY,
  new_run_id    text NOT NULL,
  correction_id text REFERENCES provenance.ingest_correction(correction_id),
  recorded_utc  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE provenance.run_id_alias IS
  'old_run_id -> new_run_id for every run identifier this store has ever renamed. '
  'Join through here when resolving a run_id quoted in an older query, note or audit '
  'document. Renames happen only when the identifier ENCODED a wrong label.';
