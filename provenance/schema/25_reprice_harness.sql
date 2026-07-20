-- =====================================================================
-- 25_reprice_harness.sql
--
-- ADJUDICATION.md §2.3 -- the reprice harness (phase-E physical anchor).
--
-- FINDING, 2026-07-20: §2.3 IS ALREADY SATISFIED. It is listed as
-- OUTSTANDING in ADJUDICATION §2, but that status is stale. All four
-- stats files were ingested by loader K21
-- (load_collector_silicon.load_encoder_stats_file, registered via the
-- `glob(phaseE_physical_anchor/*.stats.json)` line of its _registry())
-- into provenance.collector_encoder_stats, keyed by source_path with
-- (scenario, arm) parsed from the filename:
--
--   scenario   arm              encoder_delay_p99_ms   thesis   line
--   winsched   treatment_vllm            605.612          606   closedloop.tex:606
--   winsched   ctrl_aic                  589.301          589   closedloop.tex:621
--   static_c8  treatment_vllm            692.008          692   closedloop.tex:635
--   static_c8  ctrl_aic                  646.943          647   closedloop.tex:638
--
-- provisioned_worker_seconds is present and matches too: 2,410,754.7 in
-- both winsched arms, 3,869,278.8 in both static-C8 arms. So is
-- encoder_batch_images = 64, which [E18] depends on, and the whole raw
-- JSON is preserved in collector_encoder_stats.metrics (jsonb).
-- collector_kernel_ledger is likewise loaded (K21, kernel_ledger_N1 /
-- kernel_ledger_N64), so §2.3's second paragraph is covered as well.
--
-- NO INGEST IS PERFORMED HERE. Re-ingesting would only risk disturbing
-- rows that are already correct. What this file adds is the thing §2.3
-- actually wanted and did not get: the four numbers, and the harness
-- delta the thesis quotes, expressed as RECOMPUTABLE CHECKS, so the
-- closedloop claims stop depending on someone remembering where the
-- values live.
--
-- Depends on: 06_collector.sql, 21_checks.sql.
-- Run order: 21 -> 22 -> 23 -> 24 -> 25 (21_checks.sql clears
-- check_definition, so it must come first).
-- =====================================================================
\set ON_ERROR_STOP on
SET search_path = provenance, public;


-- ---------------------------------------------------------------------
-- A convenience view. The four rows are a 2x2 (scenario x cost model)
-- and reading them as such is what makes the thesis's comparisons legible.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_reprice_harness AS
SELECT scenario,
       max(encoder_workers)                                             AS encoder_workers,
       max(encoder_batch_images)                                        AS encoder_batch_images,
       max(provisioned_worker_seconds)                                  AS provisioned_worker_seconds,
       max(encoder_delay_p99_ms) FILTER (WHERE arm = 'ctrl_aic')        AS aic_p99_ms,
       max(encoder_delay_p99_ms) FILTER (WHERE arm = 'treatment_vllm')  AS vllm_p99_ms,
       max(encoder_delay_p99_ms) FILTER (WHERE arm = 'treatment_vllm')
     - max(encoder_delay_p99_ms) FILTER (WHERE arm = 'ctrl_aic')        AS vllm_minus_aic_ms,
       bool_or(has_worker_schedule)                                     AS has_worker_schedule
  FROM provenance.collector_encoder_stats
 WHERE scenario IN ('winsched', 'static_c8')
 GROUP BY scenario;

COMMENT ON VIEW provenance.v_reprice_harness IS
  'ADJUDICATION §2.3. The phase-E reprice harness as a 2x2: scenario (winsched = the '
  'window-scheduled policy, static_c8 = the static C=8 baseline) x cost model (ctrl_aic = '
  'AIC-priced control, treatment_vllm = measured-vLLM-priced treatment). Backs '
  'closedloop.tex:606/621/635/638. Both arms of a scenario are the SAME schedule repriced '
  'under a different encoder cost model, which is why provisioned_worker_seconds is identical '
  'within a scenario -- that identity is check C231. has_worker_schedule is true only for '
  'winsched: the static baseline has no schedule to carry.';


INSERT INTO provenance.check_definition
    (check_id, title, severity, est_cost, expected, note, sql_text)
VALUES

('C230', 'reprice-harness p99s back the closedloop claims', 'error', 'cheap',
 'The four phase-E reprice arms must be present with encoder_delay_p99_ms rounding to the '
 'published 606 / 589 / 692 / 647 ms, and encoder_batch_images = 64 on all four.',
 'ADJUDICATION §2.3. Archived values 605.612 / 589.301 / 692.008 / 646.943. The probe asserts '
 'the published integers under ordinary rounding rather than the raw doubles, so it tests the '
 'claim the thesis actually makes (adjudication rule 1) and does not become brittle to a '
 'harmless re-export. encoder_batch_images = 64 is included because [E18] depends on it.',
 $$
 WITH e AS (
     SELECT scenario, arm, encoder_delay_p99_ms AS p99, encoder_batch_images AS b
       FROM provenance.collector_encoder_stats
      WHERE scenario IN ('winsched','static_c8')
 ), want(scenario, arm, published) AS (
     VALUES ('winsched','treatment_vllm',606), ('winsched','ctrl_aic',589),
            ('static_c8','treatment_vllm',692), ('static_c8','ctrl_aic',647)
 )
 SELECT count(*) = 4
        AND count(*) FILTER (WHERE e.p99 IS NULL
                                OR round(e.p99::numeric) <> w.published
                                OR e.b IS DISTINCT FROM 64) = 0,
        'arms=' || count(*) || ' detail=' ||
        coalesce(string_agg(w.scenario || '/' || w.arm || ' ' ||
                            coalesce(round(e.p99::numeric,3)::text,'NULL') ||
                            ' vs published ' || w.published, ', ' ORDER BY w.scenario, w.arm),
                 'NO ROWS')
   FROM want w LEFT JOIN e ON e.scenario = w.scenario AND e.arm = w.arm
 $$),

('C231', 'reprice arms share a schedule, so share provisioned worker-seconds', 'error', 'cheap',
 'Within each scenario the ctrl_aic and treatment_vllm arms must report identical '
 'provisioned_worker_seconds (winsched 2,410,754.7; static_c8 3,869,278.8).',
 'The structural invariant of a REPRICE experiment: the two arms are the same worker schedule '
 'costed under two different encoder cost models, so provisioning is identical by construction '
 'and only the latency moves. If this ever fails, the two arms are not a reprice pair and the '
 'closedloop comparison built on them does not mean what the chapter says it means.',
 $$
 WITH c AS (
     SELECT scenario, count(DISTINCT provisioned_worker_seconds) AS n_distinct, count(*) AS n_arms
       FROM provenance.collector_encoder_stats
      WHERE scenario IN ('winsched','static_c8')
      GROUP BY scenario
 )
 SELECT count(*) = 2 AND count(*) FILTER (WHERE n_distinct <> 1 OR n_arms <> 2) = 0,
        'scenarios=' || count(*) || ' detail=' ||
        coalesce(string_agg(scenario || ' arms=' || n_arms || ' distinct_ws=' || n_distinct,
                            ', ' ORDER BY scenario), 'NO ROWS')
   FROM c
 $$),

('C232', 'harness static-C8 AIC p99 agrees with the simulator to within 0.5 %', 'error', 'cheap',
 'The reprice harness''s static_c8 ctrl_aic p99 (646.943 ms) and the simulator''s own '
 'misc:week_static_C8 encoder_delay_p99_ms (644.44 ms) must agree to better than 0.5 %.',
 'closedloop.tex quotes this agreement as evidence the reprice harness reproduces the '
 'simulator rather than replacing it. Archived delta = 0.388 %. The 0.5 % threshold is the '
 'thesis''s own stated bound and is NOT to be loosened if this starts failing -- a failure '
 'means harness and simulator have genuinely diverged, which is a finding, not a tolerance '
 'problem.',
 $$
 WITH h AS (
     SELECT encoder_delay_p99_ms AS p99 FROM provenance.collector_encoder_stats
      WHERE scenario = 'static_c8' AND arm = 'ctrl_aic'
 ), s AS (
     SELECT encoder_delay_p99_ms AS p99 FROM provenance.encoder_run_summary
      WHERE run_id = 'misc:week_static_C8'
 )
 SELECT h.p99 IS NOT NULL AND s.p99 IS NOT NULL
        AND abs(h.p99 - s.p99) / s.p99 < 0.005,
        'harness=' || coalesce(h.p99::text,'NULL') || ' simulator=' || coalesce(s.p99::text,'NULL') ||
        ' delta=' || coalesce(round((abs(h.p99 - s.p99) / s.p99 * 100)::numeric, 4)::text,'n/a') || ' %'
   FROM h, s
 $$)

ON CONFLICT (check_id) DO UPDATE SET
    title = excluded.title, severity = excluded.severity, est_cost = excluded.est_cost,
    expected = excluded.expected, note = excluded.note, sql_text = excluded.sql_text;
