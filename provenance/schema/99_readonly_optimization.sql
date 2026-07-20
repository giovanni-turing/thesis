-- =====================================================================
--            ⛔  DO NOT RUN UNTIL INGEST IS COMPLETE  ⛔
-- =====================================================================
-- 99_readonly_optimization.sql -- schema `provenance`, PostgreSQL 16
--
-- PRECONDITION, non-negotiable: the experiment families a16, a16_ft, g2,
-- g3_32b and g6 are FULLY LOADED and no loader is running.  Every
-- statement in this file either rewrites a heap, takes an ACCESS
-- EXCLUSIVE lock, or adds per-row write cost to future COPYs.  Running
-- any of it mid-ingest will, at best, make the remaining loads several
-- times slower; at worst it will block them behind a lock for hours.
--
-- Gate before you start:
--     SELECT count(*) FROM provenance.check_failures('moderate');
--     SELECT count(*) FROM provenance.runs WHERE experiment = 'misc';   -- want 0
--     -- and: no active loader process, `SELECT * FROM pg_stat_activity`
--
-- Budget several hours.  Every section is independently runnable and
-- restartable; run them IN ORDER (FILLFACTOR must precede CLUSTER, the
-- NOT VALID constraints must precede their VALIDATE).
--
-- Companion: 21_checks.sql (safe to run during ingest) already created
-- the CHECK constraints and vocabulary domains as NOT VALID.  This file
-- validates them and adds everything that was deliberately withheld.
-- =====================================================================
\set ON_ERROR_STOP on
SET search_path = provenance, public;
SET maintenance_work_mem = '4GB';           -- session-local; 16 GB store, adjust to host RAM
SET max_parallel_maintenance_workers = 4;
\timing on


-- =====================================================================
-- 1.  PRE-FLIGHT GATES.  Every one of these must return 0 (or true).
--     If a gate fails, STOP and fix the data -- do not "just skip" the
--     dependent statement, because the whole point of this file is that
--     the constraints below are true.
-- =====================================================================
\echo '=== GATE 1: orphan sweep on the raw facts (must all be 0) ==='
SELECT 'llm_request'      AS t, count(*) FROM provenance.llm_request x
  WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id)
UNION ALL SELECT 'composed_request', count(*) FROM provenance.composed_request x
  WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id)
UNION ALL SELECT 'encoder_series', count(*) FROM provenance.encoder_series x
  WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id)
UNION ALL SELECT 'worker_schedule', count(*) FROM provenance.worker_schedule x
  WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = x.run_id);

\echo '=== GATE 2: window vocabulary (DEF-12 / DEC-7 -- must be 0 for the windows FK) ==='
SELECT count(*) FROM provenance.runs r
 WHERE r.window_name IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM provenance.windows w WHERE w.window_name = r.window_name);

\echo '=== GATE 3: the full check suite (expect only the documented warns) ==='
SELECT * FROM provenance.check_all();


-- =====================================================================
-- 2.  VALIDATE the NOT VALID constraints created by 21_checks.sql.
--
--     RATIONALE: NOT VALID enforced them for every new row from the
--     moment they were created, but never proved the historical rows
--     comply.  VALIDATE does exactly one sequential scan per table and
--     takes only SHARE UPDATE EXCLUSIVE -- concurrent SELECTs keep
--     working, so this is safe to run against a live read-only store.
--     It is here rather than in 21_checks.sql purely because the scan
--     over 15-35M rows would have competed with the ingest for I/O.
--
--     Each predicate was verified at 0 violations when written, so these
--     are expected to succeed.  A failure means new data broke an
--     invariant during the remaining ingests -- exactly what you want to
--     learn here rather than after publishing.
-- =====================================================================
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_pool_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_policy_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_quantile_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_actuation_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_engine_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_mode_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_rho_band;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_run_id_namespaced;
ALTER TABLE provenance.eda_rate_series  VALIDATE CONSTRAINT eda_rate_series_nonneg;
ALTER TABLE provenance.worker_schedule  VALIDATE CONSTRAINT worker_schedule_nonneg;

-- The partitioned parents: VALIDATE recurses to every partition, one
-- scan each. These are the expensive ones -- run them one at a time.
ALTER TABLE provenance.llm_request      VALIDATE CONSTRAINT llm_request_latency_nonneg;
ALTER TABLE provenance.llm_request      VALIDATE CONSTRAINT llm_request_e2e_nonneg;
ALTER TABLE provenance.llm_request      VALIDATE CONSTRAINT llm_request_tokens_nonneg;
ALTER TABLE provenance.composed_request VALIDATE CONSTRAINT composed_request_tokens_nonneg;
ALTER TABLE provenance.encoder_series   VALIDATE CONSTRAINT encoder_series_counters_nonneg;
ALTER TABLE provenance.forecast         VALIDATE CONSTRAINT forecast_horizon_nonneg;
ALTER TABLE provenance.forecast         VALIDATE CONSTRAINT forecast_model_vocab;


-- =====================================================================
-- 3.  REFERENTIAL INTEGRITY.
--
--     RATIONALE for deferring: an FK adds an index probe into
--     provenance.runs for EVERY row inserted. On a COPY of 15M
--     composed_request rows that is 15M extra random reads. This is the
--     single most expensive thing you can do to an ingest, which is why
--     the design deliberately omitted FKs on the partitioned raw tables
--     and why they only appear here.
--
--     Added NOT VALID first (catalog-only, instant, ACCESS EXCLUSIVE for
--     milliseconds), then VALIDATE separately under SHARE UPDATE
--     EXCLUSIVE so reads are never blocked for long.
--
--     PRECONDITION: GATE 1 above returned 0 for all four tables.
-- =====================================================================
ALTER TABLE provenance.worker_schedule
  ADD CONSTRAINT worker_schedule_run_fk FOREIGN KEY (run_id)
  REFERENCES provenance.runs(run_id) ON DELETE CASCADE NOT VALID;
ALTER TABLE provenance.worker_schedule VALIDATE CONSTRAINT worker_schedule_run_fk;

ALTER TABLE provenance.llm_request
  ADD CONSTRAINT llm_request_run_fk FOREIGN KEY (run_id)
  REFERENCES provenance.runs(run_id) ON DELETE CASCADE NOT VALID;
ALTER TABLE provenance.llm_request VALIDATE CONSTRAINT llm_request_run_fk;

ALTER TABLE provenance.composed_request
  ADD CONSTRAINT composed_request_run_fk FOREIGN KEY (run_id)
  REFERENCES provenance.runs(run_id) ON DELETE CASCADE NOT VALID;
ALTER TABLE provenance.composed_request VALIDATE CONSTRAINT composed_request_run_fk;

ALTER TABLE provenance.encoder_series
  ADD CONSTRAINT encoder_series_run_fk FOREIGN KEY (run_id)
  REFERENCES provenance.runs(run_id) ON DELETE CASCADE NOT VALID;
ALTER TABLE provenance.encoder_series VALIDATE CONSTRAINT encoder_series_run_fk;

-- Dimension FK. GATED on GATE 2 returning 0. DEF-12 / DEC-7 must be
-- resolved first (canonicalise steady vs steady24h and friends); as of
-- the audit, 130 runs would violate this.
-- ALTER TABLE provenance.runs
--   ADD CONSTRAINT runs_window_fk FOREIGN KEY (window_name)
--   REFERENCES provenance.windows(window_name) NOT VALID;
-- ALTER TABLE provenance.runs VALIDATE CONSTRAINT runs_window_fk;

-- verification: only after DEC-5 (prefix the bare run_ids). The
-- resolved_run_id column is already orphan-free (check C205), so the FK
-- belongs on THAT column, not on the raw run_id.
-- ALTER TABLE provenance.verification
--   ADD CONSTRAINT verification_resolved_run_fk FOREIGN KEY (resolved_run_id)
--   REFERENCES provenance.runs(run_id) NOT VALID;
-- ALTER TABLE provenance.verification VALIDATE CONSTRAINT verification_resolved_run_fk;


-- =====================================================================
-- 4.  INDEXES.  Every one justified; every one too write-costly for the
--     ingest window.  CONCURRENTLY throughout: it takes two passes and
--     is slower in wall-clock, but never blocks a reader.
--     NOTE: CREATE INDEX CONCURRENTLY cannot run inside a transaction
--     block, so do not wrap this section in BEGIN/COMMIT.
-- =====================================================================

-- ---------------------------------------------------------------------
-- 4.1  (run_id, time) on the raw facts.
--      RATIONALE: the dominant analytical access pattern on the raw
--      facts is "one run's rows, in time order" -- that is what every
--      per-run percentile, every time-series plot and check_run() does.
--      run_id alone is already indexed on every partition, but the sort
--      by time is redone on every query. Adding the time column turns
--      these into ordered index scans and removes the sort entirely.
--      COST DURING INGEST: one extra index maintenance per row on
--      15-35M row tables -- which is exactly why it waits until now.
--      Created per-partition so each build is short and interruptible.
-- ---------------------------------------------------------------------
CREATE INDEX CONCURRENTLY IF NOT EXISTS llm_request_run_t_idx
  ON provenance.llm_request (run_id, arrival_time_ms);
CREATE INDEX CONCURRENTLY IF NOT EXISTS composed_request_run_ts_idx
  ON provenance.composed_request (run_id, ts);
CREATE INDEX CONCURRENTLY IF NOT EXISTS encoder_series_run_t_idx
  ON provenance.encoder_series (run_id, t);
CREATE INDEX CONCURRENTLY IF NOT EXISTS worker_schedule_run_step_idx
  ON provenance.worker_schedule (run_id, step_index);
  -- NB: NOT unique -- 17 duplicate (run_id, step_index) groups exist
  -- (see 21_checks.sql B.5). A plain index is still the right access path.

-- ---------------------------------------------------------------------
-- 4.2  forecast evaluation key.
--      RATIONALE: forecast is queried as (model, variate, resolution, h)
--      and joined on origin -- that is precisely the grouping that
--      forecast_metrics reproduces (check C006/C007, currently a ~5 s
--      and ~60 s full scan). This index makes the recompute an index
--      scan instead. Add `mode` because uni and cov are separate
--      populations that must never be aggregated together.
--      DEPENDENCY: do this only AFTER the DEF-4 discriminator columns
--      (run_id / variant) land, so the index reflects the final shape.
-- ---------------------------------------------------------------------
CREATE INDEX CONCURRENTLY IF NOT EXISTS forecast_eval_key_idx
  ON provenance.forecast (model, mode, variate, resolution, h, origin);

-- ---------------------------------------------------------------------
-- 4.3  Spine dimension lookups.
--      RATIONALE: every comparison matrix in the thesis filters runs by
--      some subset of (experiment, policy, model, lead_s, rho). runs is
--      small, but it is joined against 35M-row facts, so a bad row
--      estimate here poisons the whole plan.
-- ---------------------------------------------------------------------
CREATE INDEX CONCURRENTLY IF NOT EXISTS runs_family_dims_idx
  ON provenance.runs (experiment, policy, model, lead_s, rho);
CREATE INDEX CONCURRENTLY IF NOT EXISTS runs_window_policy_idx
  ON provenance.runs (window_name, policy, quantile);

-- ---------------------------------------------------------------------
-- 4.4  Provenance lookups by file.
--      RATIONALE: "which artifact produced this row" and "has this file
--      been loaded" are the two questions the ledger exists to answer.
-- ---------------------------------------------------------------------
CREATE INDEX CONCURRENTLY IF NOT EXISTS ingest_log_kind_idx    ON provenance.ingest_log (kind);
CREATE INDEX CONCURRENTLY IF NOT EXISTS ingest_log_sha_idx     ON provenance.ingest_log (sha256);
CREATE INDEX CONCURRENTLY IF NOT EXISTS ingest_log_run_idx     ON provenance.ingest_log (run_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS runs_source_path_idx   ON provenance.runs (source_path);

-- ---------------------------------------------------------------------
-- 4.5  vLLM ETL access paths.
--      RATIONALE: the measured-vs-simulated chapter walks these tables
--      per run and per request. The unique indexes from 21_checks.sql
--      B.4 already cover (run_id, ...) prefixes for most of them; these
--      fill the remaining shapes.
-- ---------------------------------------------------------------------
CREATE INDEX CONCURRENTLY IF NOT EXISTS vllm_token_itl_req_idx
  ON provenance.vllm_token_itl (request_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS vllm_stat_metric_idx
  ON provenance.vllm_stat (metric_path);
CREATE INDEX CONCURRENTLY IF NOT EXISTS eda_metric_signal_idx
  ON provenance.eda_metric (signal, stat);


-- =====================================================================
-- 5.  MATERIALIZED VIEWS.
--     RATIONALE: each of these is expensive (full scan + sort per run),
--     read constantly, and -- by definition, once ingest ends -- stable.
--     Materializing during ingest would just mean refreshing forever.
-- =====================================================================

-- 5.1  Fix DEF-10 first: mv_llm_p99_check was stale (80 rows vs 101 live),
--      so v_llm_drift -- a correctness guard -- silently checked 79% of runs.
REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;
SELECT * FROM provenance.v_mv_freshness;          -- expect is_fresh = true

-- 5.2  Per-run percentiles recomputed from raw rows: the evidence layer
--      behind every published latency number, and the backing store for
--      provenance.check_run(). Turning this into a matview converts the
--      C002/C003 identity checks from a full scan into a hash join.
CREATE MATERIALIZED VIEW IF NOT EXISTS provenance.mv_llm_percentiles AS
SELECT run_id,
       count(*)                                                       AS n,
       avg(ttft_ms)                                                   AS mean_ttft_ms,
       percentile_cont(0.50) WITHIN GROUP (ORDER BY ttft_ms)          AS p50_ttft_ms,
       percentile_cont(0.90) WITHIN GROUP (ORDER BY ttft_ms)          AS p90_ttft_ms,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY ttft_ms)          AS p95_ttft_ms,
       percentile_cont(0.99) WITHIN GROUP (ORDER BY ttft_ms)          AS p99_ttft_ms,
       max(ttft_ms)                                                   AS max_ttft_ms,
       percentile_cont(0.90) WITHIN GROUP (ORDER BY e2e_latency_ms)   AS p90_e2e_ms,
       percentile_cont(0.99) WITHIN GROUP (ORDER BY e2e_latency_ms)   AS p99_e2e_ms,
       max(e2e_latency_ms)                                            AS max_e2e_ms,
       percentile_cont(0.99) WITHIN GROUP (ORDER BY itl_ms)           AS p99_itl_ms
  FROM provenance.llm_request GROUP BY 1;
CREATE UNIQUE INDEX IF NOT EXISTS mv_llm_percentiles_pk
  ON provenance.mv_llm_percentiles (run_id);

-- 5.3  The worker-seconds integral (check C005) per run. Same argument:
--      a window function over 215k schedule rows joined to a max() over
--      encoder_series, recomputed on every cost question.
CREATE MATERIALIZED VIEW IF NOT EXISTS provenance.mv_worker_seconds AS
WITH sch AS (
    SELECT run_id, t_s, worker_count,
           lead(t_s) OVER (PARTITION BY run_id ORDER BY step_index) AS t_next
      FROM provenance.worker_schedule WHERE is_valid IS NOT FALSE),
hor AS (SELECT run_id, max(t)::double precision AS horizon_s
          FROM provenance.encoder_series GROUP BY 1)
SELECT s.run_id, h.horizon_s,
       sum(s.worker_count * (coalesce(s.t_next, h.horizon_s) - s.t_s)) AS integral_ws,
       count(*) AS steps
  FROM sch s JOIN hor h USING (run_id)
 GROUP BY 1, 2;
CREATE UNIQUE INDEX IF NOT EXISTS mv_worker_seconds_pk
  ON provenance.mv_worker_seconds (run_id);

-- 5.4  Materialize the orphan / backing audits so dashboards stop
--      rescanning 35M rows to answer "is this run auditable".
CREATE MATERIALIZED VIEW IF NOT EXISTS provenance.mv_run_status AS
  SELECT * FROM provenance.v_run_status;
CREATE UNIQUE INDEX IF NOT EXISTS mv_run_status_pk ON provenance.mv_run_status (run_id);

-- 5.5  Freeze the current check_all() verdict, so "was the store green
--      when we published" is answerable later.
CREATE MATERIALIZED VIEW IF NOT EXISTS provenance.mv_check_results AS
  SELECT now() AS evaluated_at, * FROM provenance.check_all();

-- REFRESH ORDER after any future load:
--   REFRESH MATERIALIZED VIEW CONCURRENTLY provenance.mv_llm_percentiles;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY provenance.mv_worker_seconds;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY provenance.mv_run_status;
--   REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;
--   REFRESH MATERIALIZED VIEW provenance.mv_check_results;
-- (CONCURRENTLY needs the unique index each of them has, and does not
--  block readers -- worth it for the three that dashboards hit.)


-- =====================================================================
-- 6.  FILLFACTOR.  MUST precede section 7 -- it takes effect on rewrite,
--     and CLUSTER is the rewrite.
--     RATIONALE: the store is append-only during ingest and read-only
--     after, so there is no reason to reserve free space for HOT
--     updates. 100 maximizes tuples per page => fewer pages read per
--     sequential scan, which is what every aggregate here does.
-- =====================================================================
ALTER TABLE provenance.llm_request      SET (fillfactor = 100);
ALTER TABLE provenance.composed_request SET (fillfactor = 100);
ALTER TABLE provenance.encoder_series   SET (fillfactor = 100);
ALTER TABLE provenance.forecast         SET (fillfactor = 100);
ALTER TABLE provenance.worker_schedule  SET (fillfactor = 100);
ALTER TABLE provenance.measured_request SET (fillfactor = 100);
ALTER TABLE provenance.eda_rate_series  SET (fillfactor = 100);
ALTER TABLE provenance.vllm_token_itl   SET (fillfactor = 100);


-- =====================================================================
-- 7.  PHYSICAL ORDERING (CLUSTER).
--     RATIONALE: the raw facts are ALWAYS read as "one run's rows, in
--     time order". Clustering on (run_id, time) collapses each per-run
--     scan from a scatter across the whole heap into a near-contiguous
--     read -- typically an order of magnitude fewer pages for a
--     single-run percentile.
--     COST: rewrites the whole table under ACCESS EXCLUSIVE. Catastrophic
--     during ingest, ideal after it.
--     DO IT PER PARTITION so each lock is short and the whole thing can
--     be interrupted and resumed. Uses the 4.1 indexes, so section 4
--     must have completed.
--     CLUSTER does not maintain ordering for future inserts -- which is
--     fine, because there are none.
-- =====================================================================
CLUSTER provenance.llm_request_a13      USING llm_request_a13_run_id_arrival_time_ms_idx;
CLUSTER provenance.llm_request_a11      USING llm_request_a11_run_id_arrival_time_ms_idx;
CLUSTER provenance.llm_request_a12      USING llm_request_a12_run_id_arrival_time_ms_idx;
CLUSTER provenance.llm_request_a14      USING llm_request_a14_run_id_arrival_time_ms_idx;
CLUSTER provenance.llm_request_a15      USING llm_request_a15_run_id_arrival_time_ms_idx;
CLUSTER provenance.composed_request_a13 USING composed_request_a13_run_id_ts_idx;
CLUSTER provenance.composed_request_a11 USING composed_request_a11_run_id_ts_idx;
CLUSTER provenance.encoder_series_a13   USING encoder_series_a13_run_id_t_idx;
-- ... continue for the remaining large partitions; enumerate them with:
--   SELECT c.relname, pg_size_pretty(pg_relation_size(c.oid))
--     FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
--    WHERE n.nspname='provenance' AND c.relispartition
--    ORDER BY pg_relation_size(c.oid) DESC LIMIT 30;
-- Index names are auto-generated per partition; confirm them with \d
-- on each partition before running, they are NOT guessable reliably.


-- =====================================================================
-- 8.  SPLIT THE DEFAULT PARTITIONS.
--     RATIONALE: composed_request_default held 15,238,525 rows -- 43.6%
--     of the largest relation -- because unmapped directories fell
--     through to experiment='misc'. A default partition can never be
--     pruned, so nearly half the table is scanned for every query that
--     should have touched one family.
--     This is a DETACH + redistribute + ATTACH: a full scan and rewrite.
--     It gets more expensive the longer it is left, which is exactly why
--     the EMPTY partitions for a16/g2/g3_32b/g6 are created BEFORE their
--     load (§6.2 of the remediation plan), not here.
--     PRECONDITION: DEC-3 resolved -- the dir->experiment map extended so
--     experiment='misc' is empty (check C306).
-- =====================================================================
-- BEGIN;
-- ALTER TABLE provenance.composed_request DETACH PARTITION provenance.composed_request_default;
-- CREATE TABLE provenance.composed_request_g3_32b PARTITION OF provenance.composed_request FOR VALUES IN ('g3_32b');
-- CREATE TABLE provenance.composed_request_g2     PARTITION OF provenance.composed_request FOR VALUES IN ('g2');
-- CREATE TABLE provenance.composed_request_g6     PARTITION OF provenance.composed_request FOR VALUES IN ('g6');
-- CREATE TABLE provenance.composed_request_a16    PARTITION OF provenance.composed_request FOR VALUES IN ('a16');
-- -- ... one per newly-mapped family ...
-- INSERT INTO provenance.composed_request SELECT * FROM provenance.composed_request_default;
-- DROP TABLE provenance.composed_request_default;
-- CREATE TABLE provenance.composed_request_default PARTITION OF provenance.composed_request DEFAULT;
-- COMMIT;
-- Repeat for llm_request (94,731 default rows) and encoder_series (1,793).


-- =====================================================================
-- 9.  STATISTICS TARGETS.
--     RATIONALE: the default 100 histogram buckets badly under-describe
--     run_id, which has hundreds-to-thousands of distinct values and
--     drives every partition-pruning and join-order decision on the raw
--     facts. Under-estimating rows-per-run is what turns a nested loop
--     into a disaster on a 35M-row table.
--     Raising the target costs ANALYZE time, not query time.
-- =====================================================================
ALTER TABLE provenance.llm_request      ALTER COLUMN run_id     SET STATISTICS 1000;
ALTER TABLE provenance.composed_request ALTER COLUMN run_id     SET STATISTICS 1000;
ALTER TABLE provenance.encoder_series   ALTER COLUMN run_id     SET STATISTICS 1000;
ALTER TABLE provenance.worker_schedule  ALTER COLUMN run_id     SET STATISTICS 1000;
ALTER TABLE provenance.forecast         ALTER COLUMN model      SET STATISTICS 500;
ALTER TABLE provenance.forecast         ALTER COLUMN variate    SET STATISTICS 200;
ALTER TABLE provenance.runs             ALTER COLUMN experiment SET STATISTICS 500;

-- Multivariate statistics: experiment and run_id are near-functionally
-- dependent (the run_id PREFIX *is* the experiment -- constraint
-- runs_run_id_namespaced makes that structural). The planner cannot know
-- this without being told, and without it, a filter on both columns has
-- its selectivity multiplied twice.
CREATE STATISTICS IF NOT EXISTS provenance.llm_request_exp_run_stat (dependencies, ndistinct)
  ON experiment, run_id FROM provenance.llm_request;
CREATE STATISTICS IF NOT EXISTS provenance.composed_request_exp_run_stat (dependencies, ndistinct)
  ON experiment, run_id FROM provenance.composed_request;
CREATE STATISTICS IF NOT EXISTS provenance.encoder_series_exp_run_stat (dependencies, ndistinct)
  ON experiment, run_id FROM provenance.encoder_series;
CREATE STATISTICS IF NOT EXISTS provenance.forecast_key_stat (dependencies, ndistinct)
  ON model, variate, resolution, h FROM provenance.forecast;


-- =====================================================================
-- 10. PARTITION-WISE PLANNING.
--     RATIONALE: off by default in PG16, but both are pure wins on a
--     star schema whose fact tables share a partition key -- they let
--     per-partition aggregates and joins run independently, and in
--     parallel. Set globally once verified, not per-session.
-- =====================================================================
ALTER SYSTEM SET enable_partitionwise_aggregate = on;
ALTER SYSTEM SET enable_partitionwise_join      = on;
SELECT pg_reload_conf();


-- =====================================================================
-- 11. FINAL PASS: reclaim the churn from the rewrites, refresh all stats.
--     VACUUM FULL is intentionally NOT used -- CLUSTER in section 7
--     already rewrote the large partitions compactly, so VACUUM FULL
--     would only repeat that work under the same exclusive lock.
--     ANALYZE must come AFTER section 9, or the raised statistics
--     targets have no effect until the next autovacuum.
-- =====================================================================
VACUUM (ANALYZE, VERBOSE) provenance.llm_request;
VACUUM (ANALYZE, VERBOSE) provenance.composed_request;
VACUUM (ANALYZE, VERBOSE) provenance.encoder_series;
VACUUM (ANALYZE, VERBOSE) provenance.forecast;
VACUUM (ANALYZE, VERBOSE) provenance.worker_schedule;
VACUUM (ANALYZE, VERBOSE) provenance.measured_request;
VACUUM ANALYZE provenance.runs;
-- then, catching everything else in the schema:
VACUUM ANALYZE;


-- =====================================================================
-- 12. POST-OPTIMIZATION ACCEPTANCE.
--     Run these and record the output in the results ledger alongside
--     the date -- this is the "the store was green when we published"
--     artifact.
-- =====================================================================
\echo '=== ACCEPTANCE ==='
SELECT * FROM provenance.check_all();                  -- expect only documented warns
SELECT * FROM provenance.v_orphan_audit;               -- expect 0 / 0 / 0
SELECT * FROM provenance.v_mv_freshness;               -- expect is_fresh = true
SELECT count(*) FROM provenance.v_id_collision;        -- expect only benign path-keyed families
SELECT count(*) FROM provenance.runs WHERE experiment = 'misc';  -- expect 0

-- Constraint inventory: nothing should still be NOT VALID.
SELECT c.conrelid::regclass AS tbl, c.conname, c.contype, c.convalidated
  FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
 WHERE n.nspname = 'provenance' AND NOT c.convalidated
 ORDER BY 1, 2;

-- Index inventory + sizes, for the record.
SELECT i.indexrelid::regclass AS idx, i.indrelid::regclass AS tbl,
       pg_size_pretty(pg_relation_size(i.indexrelid)) AS size
  FROM pg_index i JOIN pg_class c ON c.oid = i.indrelid
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE n.nspname = 'provenance'
 ORDER BY pg_relation_size(i.indexrelid) DESC LIMIT 40;

-- Freeze the verdict.
REFRESH MATERIALIZED VIEW provenance.mv_check_results;
