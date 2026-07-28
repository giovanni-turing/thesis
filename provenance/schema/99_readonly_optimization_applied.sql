-- =====================================================================
-- 99_readonly_optimization_applied.sql -- schema `provenance`, PG 16
--
-- This is the AS-EXECUTED record of the read-only optimization, run
-- 2026-07-20 against the completed store (3,051 runs / ~94M rows / 19 GB).
--
-- It supersedes the PLAN in 99_readonly_optimization.sql, which was
-- written when the store was ~84M rows / 2,060 runs.  That file is kept
-- verbatim as the record of what was intended; this file records what was
-- actually applied, what was REJECTED ON MEASUREMENT, and why.
--
-- Method: every candidate was measured BEFORE and AFTER on a fixed
-- 9-query workload (see progress/readonly_optimization_bench/).  Anything
-- that did not demonstrably help was dropped rather than left in place,
-- per the standing rule that a useless index is a cost, not a neutral.
--
-- HEADLINE RESULT: for this store, indexing, physical ordering and
-- planner configuration are all measured no-ops.  MATERIALIZATION is the
-- entire win.  The reason is that the fact tables were ingested run-by-run
-- and are therefore already ~1.0 correlated on run_id, and the residual
-- cost of the heavy queries is the percentile sort and raw row count, not
-- I/O locality or row estimation.
-- =====================================================================
\set ON_ERROR_STOP on
SET search_path = provenance, public;


-- =====================================================================
-- 1.  PRE-FLIGHT GATES -- all passed on 2026-07-20.
--       GATE 1 orphan sweep .......... 0 / 0 / 0 / 0
--       GATE 2 window vocabulary ..... 0   (DEF-12 / DEC-7 now RESOLVED)
--       GATE 3 experiment='misc' ..... 0   (DEC-3 now RESOLVED)
-- Gate 2 passing is new since the plan was written; it is what allows the
-- runs_window_fk in section 3 to be enabled rather than left commented out.
-- =====================================================================


-- =====================================================================
-- 2.  VALIDATE the NOT VALID constraints.  APPLIED -- all 161 of them.
--     Total wall time ~10 s, not the "several hours" the plan budgeted:
--     the working set is cached and each parent VALIDATE recurses cheaply.
--     Zero violations, so no historical row broke an invariant during the
--     a16/a16_ft/g2/g3_32b/g6 ingests.
-- =====================================================================
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_pool_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_policy_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_quantile_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_actuation_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_engine_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_mode_vocab;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_rho_band;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_run_id_namespaced;
ALTER TABLE provenance.runs             VALIDATE CONSTRAINT runs_runtime_build_vocab;  -- not in the plan; added since
ALTER TABLE provenance.eda_rate_series  VALIDATE CONSTRAINT eda_rate_series_nonneg;
ALTER TABLE provenance.worker_schedule  VALIDATE CONSTRAINT worker_schedule_nonneg;
ALTER TABLE provenance.llm_request      VALIDATE CONSTRAINT llm_request_latency_nonneg;
ALTER TABLE provenance.llm_request      VALIDATE CONSTRAINT llm_request_e2e_nonneg;
ALTER TABLE provenance.llm_request      VALIDATE CONSTRAINT llm_request_tokens_nonneg;
ALTER TABLE provenance.composed_request VALIDATE CONSTRAINT composed_request_tokens_nonneg;
ALTER TABLE provenance.encoder_series   VALIDATE CONSTRAINT encoder_series_counters_nonneg;
ALTER TABLE provenance.forecast         VALIDATE CONSTRAINT forecast_horizon_nonneg;
ALTER TABLE provenance.forecast         VALIDATE CONSTRAINT forecast_model_vocab;


-- =====================================================================
-- 3.  REFERENTIAL INTEGRITY.  APPLIED, but NOT as the plan wrote it.
--
--     CORRECTION TO THE PLAN: PostgreSQL 16 rejects
--         ALTER TABLE <partitioned> ADD CONSTRAINT ... FOREIGN KEY ... NOT VALID
--     with "cannot add NOT VALID foreign key on partitioned table ...
--     This feature is not yet supported on partitioned tables."
--     So the plan's two-step ADD NOT VALID / VALIDATE dance is impossible
--     for llm_request, composed_request and encoder_series.  They are added
--     directly instead -- which is safe here precisely because GATE 1
--     already proved zero orphans, and because the store is read-only so
--     the brief ACCESS EXCLUSIVE lock blocks nobody.
--     Measured cost: 0.9 s / 1.9 s / 0.6 s respectively.
-- =====================================================================
-- Guarded so the whole file stays re-runnable: PostgreSQL has no
-- ADD CONSTRAINT IF NOT EXISTS, and VALIDATE on an already-valid
-- constraint is a silent no-op.
DO $$
DECLARE
  t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['llm_request','composed_request','encoder_series'] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c
                     JOIN pg_namespace n ON n.oid = c.connamespace
                    WHERE n.nspname = 'provenance'
                      AND c.conname = t || '_run_fk'
                      AND c.conrelid = ('provenance.' || t)::regclass) THEN
      EXECUTE format(
        'ALTER TABLE provenance.%I ADD CONSTRAINT %I FOREIGN KEY (run_id) '
        'REFERENCES provenance.runs(run_id) ON DELETE CASCADE', t, t || '_run_fk');
    END IF;
  END LOOP;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
                  WHERE n.nspname='provenance' AND c.conname='worker_schedule_run_fk') THEN
    ALTER TABLE provenance.worker_schedule
      ADD CONSTRAINT worker_schedule_run_fk FOREIGN KEY (run_id)
      REFERENCES provenance.runs(run_id) ON DELETE CASCADE NOT VALID;
  END IF;
END $$;
ALTER TABLE provenance.worker_schedule VALIDATE CONSTRAINT worker_schedule_run_fk;

-- ENABLED (the plan had this commented out because 130 runs would have
-- violated it).  DEF-12 / DEC-7 have since been resolved and GATE 2
-- returns 0, so the dimension FK is now true and enforced.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
                  WHERE n.nspname='provenance' AND c.conname='runs_window_fk') THEN
    ALTER TABLE provenance.runs
      ADD CONSTRAINT runs_window_fk FOREIGN KEY (window_name)
      REFERENCES provenance.windows(window_name);
  END IF;
END $$;

-- ALSO ENABLED (the plan had this commented out pending DEC-5).  The plan
-- was right that the FK belongs on resolved_run_id rather than the raw
-- run_id: verification.run_id still carries bare un-namespaced labels that
-- DEC-5 has not prefixed and which therefore still orphan (314 rows in
-- v_orphan_audit), whereas resolved_run_id measures 0 orphans of 305
-- non-null values.  So the FK goes on the canonicalised column and DEC-5
-- remains genuinely outstanding for the raw one.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
                  WHERE n.nspname='provenance' AND c.conname='verification_resolved_run_fk') THEN
    ALTER TABLE provenance.verification
      ADD CONSTRAINT verification_resolved_run_fk FOREIGN KEY (resolved_run_id)
      REFERENCES provenance.runs(run_id) NOT VALID;
  END IF;
END $$;
ALTER TABLE provenance.verification VALIDATE CONSTRAINT verification_resolved_run_fk;
COMMENT ON CONSTRAINT verification_resolved_run_fk ON provenance.verification IS
  'FK on resolved_run_id, NOT on the raw run_id column. The raw run_id carries bare (un-namespaced) labels that DEC-5 has not yet prefixed and which therefore still orphan; resolved_run_id is the canonicalised spine reference and is orphan-free (check C205). Added 2026-07-20 during the read-only optimization.';


-- =====================================================================
-- 4.  INDEXES.  NET RESULT: NONE ADDED.  This is a measured decision.
--
-- Every index the plan proposed was either already present or measured at
-- no benefit.  Detail, so this is not relitigated later:
--
-- 4.1  (run_id, time) on the raw facts -- REJECTED.
--      Tested as llm_request_a11 (run_id, ttft_ms, arrival_time_ms) and
--      (run_id, arrival_time_ms) INCLUDE (ttft_ms).
--        per-run LATERAL aggregate: 0.95 s -> 0.83 s  (13%)
--        single-run ordered scan:   0.107 s -> 0.096 s (10%, client-bound)
--      Cost: 245 MB per large partition, i.e. >1.5 GB across llm_request
--      alone, for a ~10% gain on queries that materialization removes
--      entirely.  Total buffer touches actually ROSE (125k -> 271k).
--      The ordered-scan case did not even use the index -- the planner
--      still sorted, because the sibling partitions lack the index so no
--      MergeAppend ordered path is available.  Both test indexes dropped.
--
-- 4.2  forecast_eval_key_idx -- REJECTED as redundant.  forecast_key_idx
--      on (model, variate, resolution, h) already exists on every
--      partition.  The leaderboard recompute is a full-table aggregate
--      that must read point/y_true anyway, so no index serves it.
--
-- 4.3  runs_family_dims_idx / runs_window_policy_idx -- REJECTED.
--      provenance.runs is 3,051 rows / 5.7 MB.  The projection-join query
--      it was meant to serve already runs in 25 ms, entirely seq-scan
--      bound on tables of a few hundred pages.  runs_dims_idx already
--      exists for the (pool, window_name, policy, model) shape.
--
-- 4.4  ingest_log_* / runs_source_path_idx -- REJECTED.
--      ingest_log is 4,148 rows / 1 MB.  A seq scan is ~130 pages; no
--      btree probe beats that, and these are not hot-path lookups.
--
-- 4.5  vllm_token_itl_req_idx -- ALREADY EXISTS, as (request_id, token_idx),
--      a strictly better version of what the plan proposed.
--      vllm_stat_metric_idx -- ALREADY EXISTS as vllm_stat_path_idx.
--      eda_metric_signal_idx -- ALREADY EXISTS; eda_metric is 1,475 rows
--      / 184 kB, where the existing indexes are already surplus.
-- =====================================================================


-- =====================================================================
-- 5.  MATERIALIZED VIEWS.  APPLIED -- and this is where all the gain is.
-- =====================================================================

-- 5.1  mv_llm_p99_check was already fresh (178 materialized / 178 live) --
--      DEF-10 had been resolved before this run.  Refreshed anyway.
REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;

-- 5.2  Per-run percentiles recomputed from raw rows.
--      Replaces a 7.5 s full recompute over 18.9M rows (which spilled
--      ~340 MB to temp) with a 32 kB / 178-row lookup.
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

-- 5.3  Worker-seconds integral per run (check C005).
--      Replaces a 0.47 s window-function + join with a 0.026 s lookup.
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

-- 5.4  The infraction picture.  This is the single most expensive
--      routinely-read object in the store: v_infraction runs a LATERAL
--      aggregate over llm_request once per run, and the planner
--      underestimates its outer row count by 55x (est 35, actual 1,938),
--      which is what picks the nested loop.  That misestimate comes from
--      joining a view-computed sla_metric against a 5-row VALUES list, so
--      no column statistic or extended statistic can fix it --
--      materialization is the only lever.
CREATE MATERIALIZED VIEW IF NOT EXISTS provenance.mv_infraction AS
  SELECT * FROM provenance.v_infraction;
CREATE UNIQUE INDEX IF NOT EXISTS mv_infraction_pk
  ON provenance.mv_infraction (run_id, sla_metric);

-- 5.5  Freeze the current check_all() verdict.
CREATE MATERIALIZED VIEW IF NOT EXISTS provenance.mv_check_results AS
  SELECT now() AS evaluated_at, * FROM provenance.check_all();

-- NOT MATERIALIZED, deliberately:
--
--   v_run_status -- the plan proposed mv_run_status.  Built, measured,
--     and DROPPED.  The live view already answers in 0.15 s, so the
--     matview saves 130 ms; and it is an AUDIT view ("is this run
--     auditable / orphaned").  Caching an audit is how mv_llm_p99_check
--     came to silently check 79% of runs (DEF-10).  A 130 ms saving does
--     not justify reintroducing that failure mode.
--
--   the forecast-accuracy recompute (check C006/C007) -- 1.4 s over 22M
--     rows.  Left live ON PURPOSE.  Its entire value is being an
--     INDEPENDENT recomputation of forecast_metrics from raw; a cached
--     copy could go stale against the table it exists to cross-check, and
--     the check would then compare stale to stale and pass vacuously.
--     1.4 s is an acceptable price for a check that cannot rot.


-- =====================================================================
-- 5b. FRESHNESS GUARDS.  One per new matview, in the style of
--     v_mv_freshness / mv_llm_p99_check: compare materialized row count
--     against the live population and expose is_fresh.
--     These are deliberately expensive -- they recompute the live side --
--     because they are run when auditing, not on the read path.
-- =====================================================================
CREATE OR REPLACE VIEW provenance.v_mv_freshness_all AS
SELECT 'mv_llm_p99_check'::text AS matview,
       (SELECT count(*) FROM provenance.mv_llm_p99_check)                       AS materialized_rows,
       (SELECT count(*) FROM (SELECT l.run_id FROM provenance.llm_request l GROUP BY l.run_id) q
          JOIN provenance.llm_run_summary s USING (run_id))                     AS live_rows
UNION ALL
SELECT 'mv_llm_percentiles',
       (SELECT count(*) FROM provenance.mv_llm_percentiles),
       (SELECT count(DISTINCT run_id) FROM provenance.llm_request)
UNION ALL
SELECT 'mv_worker_seconds',
       (SELECT count(*) FROM provenance.mv_worker_seconds),
       (SELECT count(*) FROM (
          SELECT s.run_id FROM provenance.worker_schedule s
           WHERE s.is_valid IS NOT FALSE
             AND EXISTS (SELECT 1 FROM provenance.encoder_series e WHERE e.run_id = s.run_id)
           GROUP BY s.run_id) q)
UNION ALL
SELECT 'mv_infraction',
       (SELECT count(*) FROM provenance.mv_infraction),
       (SELECT count(*) FROM provenance.v_infraction)
UNION ALL
-- D92 (bridge 283): the check-results cache was on the refresh contract but
-- absent from this surface, so v_mv_stale could report clean while it was
-- a week stale. Freshness proxy: one row per enabled check definition.
SELECT 'mv_check_results',
       (SELECT count(*) FROM provenance.mv_check_results),
       (SELECT count(*) FROM provenance.check_definition WHERE is_enabled);

CREATE OR REPLACE VIEW provenance.v_mv_stale AS
  SELECT *, materialized_rows = live_rows AS is_fresh
    FROM provenance.v_mv_freshness_all
   WHERE materialized_rows IS DISTINCT FROM live_rows;

COMMENT ON MATERIALIZED VIEW provenance.mv_llm_percentiles IS
  'Per-run latency percentiles recomputed from raw provenance.llm_request. The evidence layer behind every published latency number and the backing store for check_run(). Replaces a 7.5 s / 18.9M-row recompute. Refresh with REFRESH MATERIALIZED VIEW CONCURRENTLY; verify with provenance.v_mv_freshness_all.';
COMMENT ON MATERIALIZED VIEW provenance.mv_worker_seconds IS
  'Per-run provisioned worker-seconds integral (the C005 identity): sum of worker_count over each schedule step, with the final step extended to the encoder_series horizon. Replaces a 0.47 s window-function recompute. Freshness: v_mv_freshness_all.';
COMMENT ON MATERIALIZED VIEW provenance.mv_infraction IS
  'Materialized provenance.v_infraction -- per-run SLA violation accounting including the raw-backed request counts. Materialized because the live view runs a LATERAL aggregate over llm_request once per run (2.2 s) under a 55x row underestimate. STALENESS RISK: this is an audit surface; always check provenance.v_mv_stale before citing it.';
COMMENT ON VIEW provenance.v_mv_freshness_all IS
  'One row per materialized view: materialized row count vs the live population it summarizes. Expensive by design (recomputes the live side); run when auditing, not on the read path.';
COMMENT ON VIEW provenance.v_mv_stale IS
  'Freshness guard. Returns ZERO ROWS when every materialized view matches its live population. Any row is a stale matview that must be refreshed before its numbers are cited.';

-- REFRESH ORDER after any future load:
--   REFRESH MATERIALIZED VIEW CONCURRENTLY provenance.mv_llm_percentiles;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY provenance.mv_worker_seconds;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY provenance.mv_infraction;
--   REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;
--   REFRESH MATERIALIZED VIEW provenance.mv_check_results;
--   SELECT * FROM provenance.v_mv_stale;   -- must return 0 rows


-- =====================================================================
-- 6.  FILLFACTOR -- NOT APPLIED.  No-op.
--     The plan proposed SET (fillfactor = 100) on the fact tables to
--     "maximize tuples per page".  100 is ALREADY the PostgreSQL default
--     for heap tables; pg_class.reloptions is NULL on every one of them,
--     which is exactly that default.  The statement would have changed
--     nothing except to dirty the catalog and force a needless rewrite
--     when combined with section 7.
-- =====================================================================


-- =====================================================================
-- 7.  PHYSICAL ORDERING (CLUSTER) -- REJECTED ON MEASUREMENT.
--
--     The plan predicted "typically an order of magnitude fewer pages for
--     a single-run percentile".  Measured, it is zero.
--
--     Tested on llm_request_a11 (correlation 0.80 -> 1.00 after CLUSTER):
--        per-run percentile aggregate  0.97 s -> 0.99 s
--        buffer reads               123,651 -> 123,916
--     Tested on llm_request_a12, the WORST-correlated large partition
--     (0.49 -> 1.00 after CLUSTER):
--        per-run percentile aggregate  0.805 s -> 0.831 s
--        buffer reads                95,041 -> 95,268
--
--     In both cases the planner's cost estimate roughly halved
--     (390k -> 181k on a12) while actual time and actual I/O did not move
--     at all.  The premise is false for this store: the loaders wrote
--     each run's rows contiguously, so the heap is ALREADY ~1.0
--     correlated on run_id almost everywhere --
--        composed_request_a6 0.99999976, encoder_series_a13 1.0,
--        llm_request_a13 1.0, llm_request_a15 1.0, composed_request_g4 0.96
--     -- and the residual cost is the percentile sort and the sheer row
--     count, neither of which physical ordering touches.
--
--     a11 and a12 remain clustered as a side effect of the experiment.
--     That is harmless (correlation 1.0 is not worse) and was left rather
--     than rewritten back.  No other partition was clustered: a full heap
--     rewrite per partition is not worth a measured zero.
-- =====================================================================


-- =====================================================================
-- 8.  SPLIT THE DEFAULT PARTITIONS -- NOT NEEDED.
--     The plan's premise was composed_request_default holding 15.2M rows
--     (43.6% of the relation) because unmapped directories fell through to
--     experiment='misc'.  DEC-3 has since been resolved: the dir->experiment
--     map was extended and the real family partitions created, so
--     experiment='misc' is now 0 rows and the default partitions are
--     effectively empty.  Nothing to redistribute.
-- =====================================================================


-- =====================================================================
-- 9.  STATISTICS TARGETS -- NOT APPLIED beyond a plain ANALYZE.
--
--     A schema-wide ANALYZE was run (6 s) and IS the right maintenance.
--     The raised targets and extended statistics were NOT applied, because
--     the estimates they were meant to fix are already accurate:
--
--       single run_id filter on llm_request:  est 64,132 vs actual 64,804
--                                             (1.0% error)
--       full grouped scan (Q3):            est 18,868,933 vs actual
--                                             18,869,922 (0.005% error)
--
--     The plan's rationale for the multivariate (experiment, run_id)
--     statistics -- "a filter on both columns has its selectivity
--     multiplied twice" -- does not occur in practice, because a filter on
--     experiment is consumed by PARTITION PRUNING before it can be applied
--     as a selectivity multiplier.  Verified on the combined filter: the
--     plan prunes to llm_request_a11 and applies experiment only as a
--     residual Filter, with the estimate unchanged at 64,132.
--
--     The one genuinely bad estimate in the workload (v_infraction, 55x
--     low) is not a column-statistics problem at all -- see 5.4 -- so
--     raising targets would have cost ANALYZE time for nothing.
-- =====================================================================
ANALYZE;


-- =====================================================================
-- 10. PARTITION-WISE PLANNING -- REJECTED ON MEASUREMENT.
--
--     The plan asserted both settings are "pure wins on a star schema
--     whose fact tables share a partition key".  Two things are wrong.
--     First, the fact tables do NOT share a partition key with forecast:
--     llm_request / composed_request / encoder_series partition on
--     `experiment`, forecast partitions on `model`.  Second, no analytical
--     query in the workload groups or joins on `experiment`, so
--     partitionwise aggregation has nothing to attach to.
--
--     Measured, repeated, alternating on/off (mean of 3 each):
--       forecast leaderboard recompute   off 1.394 s / 1.392 s
--                                        on  1.721 s / 1.719 s   (23% WORSE)
--       per-run percentile recompute     off 7.594 s / on 7.535 s (noise)
--       infraction view                  off 2.121 s / on 2.241 s (worse)
--
--     ALTER SYSTEM SET enable_partitionwise_aggregate = on;  -- NOT RUN
--     ALTER SYSTEM SET enable_partitionwise_join      = on;  -- NOT RUN
--
--     ALSO TESTED AND REJECTED: raising work_mem from the 4 MB default.
--     At 256 MB the forecast recompute went 1.399 s -> 3.462 s (2.5x
--     WORSE -- the planner switches to a HashAggregate that thrashes),
--     while the per-run percentile recompute improved only 7.66 s ->
--     7.24 s (5%).  work_mem left at 4 MB.
-- =====================================================================


-- =====================================================================
-- 11. FINAL PASS.
-- =====================================================================
VACUUM (ANALYZE) provenance.llm_request;
VACUUM (ANALYZE) provenance.composed_request;
VACUUM (ANALYZE) provenance.encoder_series;
VACUUM (ANALYZE) provenance.forecast;
VACUUM (ANALYZE) provenance.worker_schedule;
VACUUM (ANALYZE) provenance.measured_request;
VACUUM ANALYZE provenance.runs;
VACUUM ANALYZE;


-- =====================================================================
-- 12. POST-OPTIMIZATION ACCEPTANCE.
-- =====================================================================
SELECT * FROM provenance.check_all();
SELECT * FROM provenance.v_orphan_audit;
SELECT * FROM provenance.v_mv_freshness;
SELECT * FROM provenance.v_mv_stale;                              -- expect 0 rows
SELECT count(*) FROM provenance.runs WHERE experiment = 'misc';   -- expect 0

SELECT c.conrelid::regclass AS tbl, c.conname, c.contype, c.convalidated
  FROM pg_constraint c JOIN pg_namespace n ON n.oid = c.connamespace
 WHERE n.nspname = 'provenance' AND NOT c.convalidated
 ORDER BY 1, 2;                                                   -- expect 0 rows

REFRESH MATERIALIZED VIEW provenance.mv_check_results;
