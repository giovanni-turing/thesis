-- =====================================================================
-- 35_forecast_source_linkage.sql -- schema `provenance`, PostgreSQL 16
--
-- APPLIED 2026-07-26, remediating adversarial-review Finding 12:
-- "Forecast facts cannot be relationally retracted or filtered to
-- current runs." The three forecast fact tables carried no run key:
--
--   forecast          : had source_tag (a file path) but NO run_id
--   forecast_metrics  : had NO run key and NO source path at all
--   quantile_coverage : had NO run key and NO source path at all
--
-- so a future correction/supersession (runs.is_current = false) could
-- not propagate relationally into these facts.
--
-- WHAT IS BACKFILLED, AND FROM WHERE
-- ----------------------------------
-- * forecast.run_id -- from the run spine via source_tag. Every one of
--   the 41 distinct forecast.source_tag values equals verbatim the
--   source_path of exactly one provenance.runs row (the K10 loader
--   derives run_id and source_path from the same parquet), and equals
--   verbatim the ingest_log.file_path of the K10 row carrying that same
--   run_id. The fill is therefore an exact, unique join, not a
--   heuristic.
--
-- * forecast_metrics.source_file -- from the K10m loader's own load
--   rules (loader/loaders.py load_forecast_metrics): h = -1 rows come
--   from metrics_overall.parquet; h = 1 rows from metrics_h1.parquet;
--   h in 2..12 from metrics_by_h.parquet. HONESTY NOTE: h = 1 rows were
--   first written by metrics_by_h and then UPSERTED (rmse enriched) by
--   metrics_h1, which loads after it; source_file records the LAST
--   writer, i.e. the file whose values the row now carries.
--
-- * forecast_metrics.run_id -- the FAMILY run whose forecasts the
--   metric row scores: (model, mode='uni', variate) -> run
--   'predictors:<model>_<variate>'; (model, mode='cov', variate) ->
--   run 'predictors:<model>_covariates' (the covariate parquet holds
--   all four variates of one model, so all four cov metric rows of a
--   model share its single covariates run). All 32 (model,mode,variate)
--   combinations resolve to an existing spine run; the gate below
--   aborts if any does not. Note the two lineage roles differ:
--   source_file = the metric artifact this row was LOADED from;
--   run_id = the forecast family the metric is ABOUT.
--
-- * quantile_coverage.source_file -- constant: every row was loaded
--   from predictors/results/metrics/quantile_coverage.json (K10qc).
--
-- * quantile_coverage.run_id -- same family rule: model '<m>_cov' ->
--   'predictors:<m>_covariates'; plain model -> 'predictors:<m>_<signal>'.
--   All 20 rows resolve.
--
-- WHAT CANNOT BE BACKFILLED (stated, not hidden)
-- ----------------------------------------------
-- * The ingest_log rows for the metric parquets, quantile_coverage.json
--   and the structural ablation keep run_id = NULL: they are multi-run
--   aggregate artifacts with no single backing run (the C207-documented
--   definitional class). The per-row run_id added HERE is the family
--   attribution; the ledger row correctly remains group-labelled.
-- * If a K10/K10m/K10qc source file is ever re-generated and re-loaded,
--   the loaders do not write these columns: pre-existing keys keep
--   their fill (upserts only touch loader-owned columns), but NEW keys
--   would arrive with NULL run_id. Check C216 (below) trips exactly
--   then, forcing re-adjudication -- same pattern as C214/C215.
--
-- forecast.run_id is deliberately UNINDEXED: current-run filtering
-- joins 22M rows against a 41-value spine dimension, which is a scan
-- either way, and runs rows are never deleted (retraction is
-- is_current = false), so the FK never needs reverse lookups.
-- =====================================================================
SET search_path = provenance, public;

BEGIN;

-- ---------------------------------------------------------------------
-- 1. forecast.run_id (22,003,500 rows; exact join on source_tag).
-- ---------------------------------------------------------------------
ALTER TABLE provenance.forecast ADD COLUMN IF NOT EXISTS run_id text;

UPDATE provenance.forecast f
   SET run_id = r.run_id
  FROM provenance.runs r
 WHERE r.source_path = f.source_tag
   AND f.run_id IS NULL;

COMMENT ON COLUMN provenance.forecast.run_id IS
 'Spine linkage added 2026-07-26 (schema/35, Finding 12): the provenance.runs row of the parquet this forecast row was loaded from. Backfilled by the exact, unique join runs.source_path = forecast.source_tag (41 tags, each matching exactly one run). Retraction/supersession now propagates relationally: filter through current_forecast or join runs.is_current. Deliberately unindexed (see schema/35 header).';
COMMENT ON COLUMN provenance.forecast.source_tag IS
 'Absolute path of the source parquet this row was loaded from (the K10 ingest_log.file_path). This IS the source_file linkage; run_id (schema/35) is its resolved spine key.';

-- ---------------------------------------------------------------------
-- 2. forecast_metrics.source_file + run_id.
-- ---------------------------------------------------------------------
ALTER TABLE provenance.forecast_metrics
  ADD COLUMN IF NOT EXISTS source_file text,
  ADD COLUMN IF NOT EXISTS run_id text;

UPDATE provenance.forecast_metrics
   SET source_file = CASE
         WHEN h = -1 THEN '/home/gio/tese/predictors/results/metrics/metrics_overall.parquet'
         WHEN h = 1  THEN '/home/gio/tese/predictors/results/metrics/metrics_h1.parquet'
         ELSE             '/home/gio/tese/predictors/results/metrics/metrics_by_h.parquet'
       END
 WHERE source_file IS NULL;

UPDATE provenance.forecast_metrics fm
   SET run_id = r.run_id
  FROM provenance.runs r
 WHERE fm.run_id IS NULL
   AND r.run_id = 'predictors:' || fm.model ||
                  CASE WHEN fm.mode = 'cov' THEN '_covariates' ELSE '_' || fm.variate END;

COMMENT ON COLUMN provenance.forecast_metrics.source_file IS
 'Metric artifact this row was loaded from (schema/35): h=-1 -> metrics_overall.parquet, h=1 -> metrics_h1.parquet (LAST writer; metrics_by_h wrote the row first, metrics_h1 upserted rmse), h=2..12 -> metrics_by_h.parquet. Mirrors the K10m loader''s own load rules.';
COMMENT ON COLUMN provenance.forecast_metrics.run_id IS
 'Spine linkage added 2026-07-26 (schema/35, Finding 12): the forecast FAMILY run this metric row scores -- predictors:<model>_<variate> (uni) or predictors:<model>_covariates (cov). Distinct role from source_file: run_id is what the metric is ABOUT, source_file is where it was LOADED from. Filter through current_forecast_metrics for current-runs-only analysis.';

-- ---------------------------------------------------------------------
-- 3. quantile_coverage.source_file + run_id.
-- ---------------------------------------------------------------------
ALTER TABLE provenance.quantile_coverage
  ADD COLUMN IF NOT EXISTS source_file text,
  ADD COLUMN IF NOT EXISTS run_id text;

UPDATE provenance.quantile_coverage
   SET source_file = '/home/gio/tese/predictors/results/metrics/quantile_coverage.json'
 WHERE source_file IS NULL;

UPDATE provenance.quantile_coverage qc
   SET run_id = r.run_id
  FROM provenance.runs r
 WHERE qc.run_id IS NULL
   AND r.run_id = CASE
         WHEN qc.model LIKE '%\_cov' ESCAPE '\'
           THEN 'predictors:' || left(qc.model, length(qc.model) - 4) || '_covariates'
         ELSE 'predictors:' || qc.model || '_' || qc.signal
       END;

COMMENT ON COLUMN provenance.quantile_coverage.source_file IS
 'Constant by construction (schema/35): every row was loaded from predictors/results/metrics/quantile_coverage.json (K10qc).';
COMMENT ON COLUMN provenance.quantile_coverage.run_id IS
 'Spine linkage added 2026-07-26 (schema/35, Finding 12): the forecast family run this coverage row is about -- predictors:<model>_<signal>, or predictors:<m>_covariates for the <m>_cov models. Filter through current_quantile_coverage.';

-- ---------------------------------------------------------------------
-- 4. Completeness gate. Abort rather than report.
-- ---------------------------------------------------------------------
DO $$
DECLARE
  n_f_null  bigint; n_f_total bigint;
  n_m_null  bigint; n_m_nosrc bigint; n_m_total bigint;
  n_q_null  bigint; n_q_total bigint;
  n_dangling bigint;
BEGIN
  SELECT count(*), count(*) FILTER (WHERE run_id IS NULL)
    INTO n_f_total, n_f_null FROM provenance.forecast;
  SELECT count(*), count(*) FILTER (WHERE run_id IS NULL),
         count(*) FILTER (WHERE source_file IS NULL)
    INTO n_m_total, n_m_null, n_m_nosrc FROM provenance.forecast_metrics;
  SELECT count(*), count(*) FILTER (WHERE run_id IS NULL)
    INTO n_q_total, n_q_null FROM provenance.quantile_coverage;

  IF n_f_total <> 22003500 OR n_m_total <> 41600 OR n_q_total <> 20 THEN
    RAISE EXCEPTION 'row counts moved during linkage backfill: forecast=% (expected 22,003,500), metrics=% (41,600), coverage=% (20)',
      n_f_total, n_m_total, n_q_total;
  END IF;
  IF n_f_null <> 0 OR n_m_null <> 0 OR n_m_nosrc <> 0 OR n_q_null <> 0 THEN
    RAISE EXCEPTION 'linkage incomplete: forecast NULL run_id=%, metrics NULL run_id=%, metrics NULL source_file=%, coverage NULL run_id=%',
      n_f_null, n_m_null, n_m_nosrc, n_q_null;
  END IF;

  SELECT (SELECT count(*) FROM provenance.forecast_metrics fm
           WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = fm.run_id))
       + (SELECT count(*) FROM provenance.quantile_coverage qc
           WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = qc.run_id))
    INTO n_dangling;
  IF n_dangling <> 0 THEN
    RAISE EXCEPTION '% dangling run_id values in metric/coverage linkage', n_dangling;
  END IF;
  RAISE NOTICE 'OK: forecast 22,003,500 / metrics 41,600 / coverage 20 rows fully spine-linked, 0 dangling';
END $$;

-- ---------------------------------------------------------------------
-- 5. Foreign keys (small tables validated inline; the 22M-row forecast
--    FK is validated in the same transaction -- the scan is the cost of
--    making the linkage a constraint rather than a convention).
-- ---------------------------------------------------------------------
ALTER TABLE provenance.forecast_metrics
  ADD CONSTRAINT forecast_metrics_run_fk FOREIGN KEY (run_id) REFERENCES provenance.runs(run_id);
ALTER TABLE provenance.quantile_coverage
  ADD CONSTRAINT quantile_coverage_run_fk FOREIGN KEY (run_id) REFERENCES provenance.runs(run_id);
ALTER TABLE provenance.forecast
  ADD CONSTRAINT forecast_run_fk FOREIGN KEY (run_id) REFERENCES provenance.runs(run_id);

COMMIT;

-- ---------------------------------------------------------------------
-- 6. Current-only views joined to the run spine (naming follows the
--    existing current_* convention: current_runs, current_llm_summary,
--    ...). These are the retraction-propagation surface Finding 12
--    demanded: mark a run superseded (is_current = false) and its
--    forecast facts leave these views relationally, no text edits.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.current_forecast AS
SELECT f.*
  FROM provenance.forecast f
  JOIN provenance.runs r ON r.run_id = f.run_id
 WHERE r.is_current;

COMMENT ON VIEW provenance.current_forecast IS
 'forecast restricted to rows whose backing run is current (runs.is_current). Added 2026-07-26 (schema/35, Finding 12). Today identical to the base table (all 41 predictors runs are current); it exists so retraction/supersession propagates relationally instead of requiring text edits. For the manuscript-census population use v_forecast_thesis_corpus.';

CREATE OR REPLACE VIEW provenance.current_forecast_metrics AS
SELECT fm.*
  FROM provenance.forecast_metrics fm
  JOIN provenance.runs r ON r.run_id = fm.run_id
 WHERE r.is_current;

COMMENT ON VIEW provenance.current_forecast_metrics IS
 'forecast_metrics restricted to rows whose forecast-family run is current. Added 2026-07-26 (schema/35, Finding 12). run_id is the family run the metric SCORES; source_file is the metric artifact it was LOADED from.';

CREATE OR REPLACE VIEW provenance.current_quantile_coverage AS
SELECT qc.*
  FROM provenance.quantile_coverage qc
  JOIN provenance.runs r ON r.run_id = qc.run_id
 WHERE r.is_current;

COMMENT ON VIEW provenance.current_quantile_coverage IS
 'quantile_coverage restricted to rows whose forecast-family run is current. Added 2026-07-26 (schema/35, Finding 12).';

-- ---------------------------------------------------------------------
-- 7. v_forecast_thesis_corpus keeps its exact population semantics
--    (mode IN (uni,cov); pinned census 21,404,640) and now ALSO carries
--    the spine key, appended last so no consumer breaks.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_forecast_thesis_corpus AS
SELECT model, mode, variate, resolution, origin, h, step, ts, y_true, point,
       p10, p20, p30, p40, p50, p60, p70, p80, p90, source_tag, run_id
  FROM provenance.forecast
 WHERE mode = ANY (ARRAY['uni'::text, 'cov'::text]);

COMMENT ON VIEW provenance.v_forecast_thesis_corpus IS
 'The forecast rows this thesis reports on: mode IN (''uni'',''cov''), i.e. provenance.forecast minus the two post-manuscript families (*_expctx reforecasts, ewma_cal_* calibration variants). count(*) = 21,404,640, which is exactly the "21.4 million archived rows" of intro.tex:431. Use this view for any archived-row claim; count(*) over the base table (22,003,500) over-counts by including artifacts written after the manuscript. EXTENDED 2026-07-26 (schema/35): run_id appended (spine linkage, Finding 12); the population predicate and pinned census are unchanged. The view deliberately does NOT filter runs.is_current -- it pins the manuscript census; current_forecast is the retraction-aware surface.';

-- ---------------------------------------------------------------------
-- 8. C216 -- the linkage is an invariant, not a one-off. Any future
--    reload that lands forecast facts without a resolving spine key
--    fails this check until re-adjudicated (pattern of C214/C215).
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C216',
 'forecast fact tables carry complete run-spine linkage',
 'warn',
 $q$SELECT (f.n + m.n + q.n) = 0,
       format('%s forecast, %s forecast_metrics, %s quantile_coverage rows lack run_id (all three must be 0)',
              f.n, m.n, q.n)
  FROM (SELECT count(*) n FROM provenance.forecast WHERE run_id IS NULL) f,
       (SELECT count(*) n FROM provenance.forecast_metrics WHERE run_id IS NULL OR source_file IS NULL) m,
       (SELECT count(*) n FROM provenance.quantile_coverage WHERE run_id IS NULL OR source_file IS NULL) q$q$,
 'Every forecast, forecast_metrics and quantile_coverage row carries a non-null spine run_id (and, for the two metric tables, a source_file). 0 violations.',
 'moderate',
 'Added 2026-07-26 (schema/35) remediating adversarial-review Finding 12: the three forecast fact tables had no run keys, so corrections could not propagate relationally. schema/35 backfilled forecast.run_id (exact join runs.source_path = source_tag, 22,003,500 rows), forecast_metrics.source_file+run_id (K10m loader rules + family-run mapping, 41,600 rows) and quantile_coverage.source_file+run_id (20 rows), all FK-enforced against provenance.runs. The loaders do NOT write these columns, so a re-generated source file that introduces NEW primary keys lands with NULL linkage -- this check trips exactly then, and the fix is to re-run the schema/35 backfill rules (or extend them), not to exempt the rows. FK enforcement makes dangling keys impossible; this check covers the NULL direction the FK cannot.'
)
ON CONFLICT (check_id) DO UPDATE
  SET title = EXCLUDED.title, severity = EXCLUDED.severity,
      sql_text = EXCLUDED.sql_text, expected = EXCLUDED.expected,
      est_cost = EXCLUDED.est_cost, note = EXCLUDED.note;

-- Reclaim the dead tuples of the 22M-row backfill (space is reused,
-- file size is not shrunk; that is fine). PARALLEL 0: the container's
-- /dev/shm is too small for parallel vacuum workers on the 5.5 GB
-- partitioned table ("could not resize shared memory segment" on the
-- first application, 2026-07-26 -- everything before this point had
-- already COMMITted; only the vacuum needed the serial retry).
VACUUM (ANALYZE, PARALLEL 0) provenance.forecast;
VACUUM (ANALYZE, PARALLEL 0) provenance.forecast_metrics;
VACUUM (ANALYZE, PARALLEL 0) provenance.quantile_coverage;
