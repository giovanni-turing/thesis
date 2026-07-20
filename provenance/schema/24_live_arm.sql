-- =====================================================================
-- 24_live_arm.sql
--
-- ADJUDICATION.md §2.10 -- the LIVE ARM.
--
-- Backs tex/validation.tex's tab:val-anchor. Every "live" half of that
-- table was verified from disk during the audit and none of it was in
-- the store, so the table could be checked only by a human opening
-- three JSON files. These tables close that.
--
-- SOURCE: simulation/results/live51/live_runs/{live_fc,live_re,verify_flag}/
--         profile_export_aiperf.json   aiperf metric export
--         manager.jsonl                replica manager spawn/ack event log
--         planner.log.gz               dynamo planner log (gzipped)
--
-- THREE ARMS, AND WHAT THEY ARE:
--   live_fc      forecast-driven scaling, the live counterpart of the
--                simulated forecast arm.
--   live_re      reactive scaling, the live counterpart of the
--                simulated reactive arm.
--   verify_flag  a short control run used to verify the planner's
--                feature flag actually took effect. NOT a third policy
--                arm and NOT part of tab:val-anchor -- ingested because
--                leaving one of three sibling directories out is how
--                artifacts get quietly lost, and flagged as
--                is_thesis_arm = false so no future pass mistakes it
--                for one.
--
-- ================== THE ITL MAPPING. READ THIS. ======================
-- tab:val-anchor's "ITL p99" is aiperf's `inter_token_latency`, which is
-- the per-request MEAN inter-token time -- i.e. TPOT. It maps to
-- p99_tpot_ms in the simulation-side tables, NOT to p99_itl_ms.
-- aiperf's separate `inter_chunk_latency` is the true per-chunk ITL.
-- The two differ substantially (live_fc: 11.470 ms vs 5.520 ms), and
-- comparing the thesis's live "ITL p99" against a simulated p99_itl_ms
-- manufactured a phantom ~8 ms discrepancy during the audit (drove R16).
-- live_arm.itl_p99_ms is therefore named and commented as TPOT, and
-- chunk_latency_p99_ms is carried alongside it so the distinction is
-- impossible to lose again.
-- =====================================================================
--
-- INVARIANTS: idempotent; nothing overwritten; every non-obvious column
-- commented. Depends on: 01_schema.sql, 20_semantic.sql, 21_checks.sql.
-- Run order: 21 -> 22 -> 23 -> 24 (21_checks.sql clears check_definition).
-- =====================================================================
\set ON_ERROR_STOP on
SET search_path = provenance, public;


-- =====================================================================
-- A. live_arm -- one row per arm
-- =====================================================================
CREATE TABLE IF NOT EXISTS provenance.live_arm (
    arm                     text PRIMARY KEY,
    run_id                  text REFERENCES provenance.runs(run_id) ON DELETE CASCADE,
    policy                  text,
    is_thesis_arm           boolean NOT NULL DEFAULT true,

    -- aiperf headline latencies (tab:val-anchor)
    ttft_p99_ms             double precision,
    ttft_p50_ms             double precision,
    ttft_avg_ms             double precision,
    itl_p99_ms              double precision,
    itl_p50_ms              double precision,
    itl_avg_ms              double precision,
    chunk_latency_p99_ms    double precision,
    request_latency_p99_ms  double precision,
    request_latency_p50_ms  double precision,

    -- aiperf run shape
    request_count           bigint,
    error_request_count     bigint,
    benchmark_duration_s    double precision,
    output_token_throughput double precision,
    aiperf_version          text,
    benchmark_id            text,

    -- replica occupancy, integrated from manager.jsonl
    replica_seconds         double precision,
    manager_span_s          double precision,
    n_spawns                integer,
    max_n_live              integer,

    -- planner mixed-pass census, first fpm_window_s of FPM logging
    fpm_passes              integer,
    fpm_mixed_passes        integer,
    fpm_window_s            double precision,

    aiperf_path             text,
    manager_path            text,
    planner_log_path        text
);

COMMENT ON TABLE provenance.live_arm IS
  'ADJUDICATION §2.10. One row per live-hardware arm behind tex/validation.tex tab:val-anchor. '
  'These are MEASURED on a live Dynamo deployment, not simulated -- do not join them to '
  'simulation runs without saying which side is which. verify_flag is a flag-verification '
  'control, not a policy arm (is_thesis_arm = false).';
COMMENT ON COLUMN provenance.live_arm.itl_p99_ms IS
  'aiperf `inter_token_latency` p99 = per-request MEAN inter-token time = TPOT. This is what '
  'tab:val-anchor prints as "ITL p99". Compare it to a simulated p99_TPOT_ms, NEVER to a '
  'p99_itl_ms -- doing so manufactures a phantom ~8 ms gap (audit R16). True per-chunk ITL is '
  'chunk_latency_p99_ms.';
COMMENT ON COLUMN provenance.live_arm.chunk_latency_p99_ms IS
  'aiperf `inter_chunk_latency` p99 -- the genuine per-chunk inter-token latency. Carried only '
  'so the distinction from itl_p99_ms/TPOT stays visible; tab:val-anchor does not print it.';
COMMENT ON COLUMN provenance.live_arm.replica_seconds IS
  'Provisioned replica-seconds: n_live integrated over t_wall across manager.jsonl, i.e. '
  'sum over consecutive events of (t_next - t) * n_live_at_t. The live-arm counterpart of '
  'encoder_run_summary.provisioned_worker_seconds. Recomputable from provenance.live_worker_event.';
COMMENT ON COLUMN provenance.live_arm.manager_span_s IS
  'Wall span of manager.jsonl (last t_wall - first t_wall). Shorter than benchmark_duration_s '
  'is normal: the manager starts and stops around the load generator.';
COMMENT ON COLUMN provenance.live_arm.fpm_mixed_passes IS
  'Scheduler passes in the planner log (base._log_fpm) with BOTH prefill_tok > 0 AND '
  'decode_kv > 0 -- a batch mixing prefill and decode work -- within the first fpm_window_s '
  'of FPM logging. The denominator is fpm_passes over the same window. Recomputable from '
  'provenance.live_fpm_pass.';
COMMENT ON COLUMN provenance.live_arm.fpm_window_s IS
  'Length of the census window, measured from the FIRST FPM line, not from benchmark start.';
COMMENT ON COLUMN provenance.live_arm.is_thesis_arm IS
  'False for verify_flag: a planner feature-flag verification control, ingested for '
  'completeness but not a tab:val-anchor row.';


-- =====================================================================
-- B. live_arm_metric -- the full aiperf export, long form
-- =====================================================================
CREATE TABLE IF NOT EXISTS provenance.live_arm_metric (
    arm         text NOT NULL REFERENCES provenance.live_arm(arm) ON DELETE CASCADE,
    metric      text NOT NULL,
    stat        text NOT NULL,
    value       double precision,
    unit        text,
    PRIMARY KEY (arm, metric, stat)
);

COMMENT ON TABLE provenance.live_arm_metric IS
  'Every scalar in each arm''s profile_export_aiperf.json, long form (metric, stat) -> value. '
  'The headline columns on live_arm are a convenience projection of rows in here; this table '
  'is the faithful record, so a future claim about any aiperf percentile is checkable without '
  'reopening the file. stat is aiperf''s own key: avg, min, max, std, p1, p5, p10, p25, p50, '
  'p75, p90, p95, p99.';


-- =====================================================================
-- C. live_worker_event -- manager.jsonl, verbatim
-- =====================================================================
CREATE TABLE IF NOT EXISTS provenance.live_worker_event (
    arm         text NOT NULL REFERENCES provenance.live_arm(arm) ON DELETE CASCADE,
    line_no     integer NOT NULL,
    event       text,
    seq         integer,
    pid         bigint,
    reason      text,
    n_live      integer,
    n_pending   integer,
    t_wall      double precision,
    t_rel_s     double precision,
    raw         jsonb,
    PRIMARY KEY (arm, line_no)
);

COMMENT ON TABLE provenance.live_worker_event IS
  'manager.jsonl verbatim, one row per line, keyed by file line number so the ingest order is '
  'preserved and live_arm.replica_seconds is recomputable. event vocabulary observed: spawn, '
  'spawn_scheduled, ack, decision, start, sigterm, shutdown. raw keeps the whole object so a '
  'field this schema did not anticipate is never lost.';
COMMENT ON COLUMN provenance.live_worker_event.reason IS
  'Why the manager spawned: "initial" for the pre-load replicas, "lead+<N>s" for a scaling '
  'action taken N seconds of lead time ahead of predicted demand.';
COMMENT ON COLUMN provenance.live_worker_event.t_rel_s IS
  'Seconds since the first event in this arm''s manager.jsonl.';


-- =====================================================================
-- D. live_spawn_latency -- spawn -> registered
-- =====================================================================
CREATE TABLE IF NOT EXISTS provenance.live_spawn_latency (
    arm             text NOT NULL REFERENCES provenance.live_arm(arm) ON DELETE CASCADE,
    seq             integer NOT NULL,
    reason          text,
    t_spawn         double precision,
    t_registered    double precision,
    latency_s       double precision,
    PRIMARY KEY (arm, seq)
);

COMMENT ON TABLE provenance.live_spawn_latency IS
  'End-to-end replica registration latency: a spawn in manager.jsonl paired to the first '
  'subsequent "Discovery Added" line in planner.log.gz. This is the number validation.tex '
  'quotes as the live control-loop actuation cost. INITIAL SPAWNS ARE EXCLUDED (reason = '
  '''initial''): they fire before the planner is fully subscribed, so their apparent latency '
  '(~3.3 s) measures planner startup, not replica registration. Over the two thesis arms the '
  'five non-initial spawns give 0.954-0.996 s, mean 0.9858 s.';
COMMENT ON COLUMN provenance.live_spawn_latency.t_registered IS
  'Timestamp of the first "Discovery Added event received" line at or after t_spawn. Discovery '
  'lines arrive in bursts (one worker registers several endpoints); the FIRST is taken, so this '
  'is the earliest instant the planner could route to the new replica.';


-- =====================================================================
-- E. live_fpm_pass -- planner scheduler passes
-- =====================================================================
CREATE TABLE IF NOT EXISTS provenance.live_fpm_pass (
    arm                 text NOT NULL REFERENCES provenance.live_arm(arm) ON DELETE CASCADE,
    idx                 integer NOT NULL,
    ts_utc              timestamptz,
    t_rel_s             double precision,
    engine_id           text,
    dp_rank             integer,
    wall_time_s         double precision,
    prefill_tok         integer,
    prefill_req         integer,
    decode_kv           integer,
    decode_req          integer,
    queued_prefill_tok  integer,
    queued_decode_kv    integer,
    is_mixed            boolean,
    PRIMARY KEY (arm, idx)
);

COMMENT ON TABLE provenance.live_fpm_pass IS
  'One row per base._log_fpm line in planner.log.gz: a decode-engine scheduler pass, with the '
  'work it scheduled (sched(...)) and the work still queued (queued(...)). Ingested for the '
  'whole log, not just the census window, so live_arm.fpm_mixed_passes is recomputable and so '
  'is any other window a future question needs.';
COMMENT ON COLUMN provenance.live_fpm_pass.is_mixed IS
  'prefill_tok > 0 AND decode_kv > 0: the pass batched prefill and decode work together. '
  'This is the definition behind the mixed-pass rates in ADJUDICATION §2.10 (live_fc 2/184, '
  'live_re 2/24, verify_flag 3/207 over the first 300 s of FPM logging).';
COMMENT ON COLUMN provenance.live_fpm_pass.t_rel_s IS
  'Seconds since the FIRST FPM line in this arm''s planner log.';

CREATE INDEX IF NOT EXISTS live_fpm_pass_mixed_idx
    ON provenance.live_fpm_pass (arm, is_mixed);


-- =====================================================================
-- F. the resolved read
-- =====================================================================
CREATE OR REPLACE VIEW provenance.v_live_anchor AS
SELECT a.arm,
       a.policy,
       a.ttft_p99_ms,
       a.itl_p99_ms                              AS tpot_p99_ms,
       a.chunk_latency_p99_ms,
       a.request_count,
       a.replica_seconds,
       a.manager_span_s,
       round((a.replica_seconds / NULLIF(a.manager_span_s, 0))::numeric, 4) AS mean_replicas,
       a.fpm_mixed_passes,
       a.fpm_passes,
       round((a.fpm_mixed_passes::numeric / NULLIF(a.fpm_passes, 0)), 5)    AS mixed_pass_rate,
       s.n_spawn_pairs,
       s.min_latency_s,
       s.max_latency_s,
       s.mean_latency_s
  FROM provenance.live_arm a
  LEFT JOIN LATERAL (
        SELECT count(*)   AS n_spawn_pairs,
               min(latency_s) AS min_latency_s,
               max(latency_s) AS max_latency_s,
               avg(latency_s) AS mean_latency_s
          FROM provenance.live_spawn_latency l
         WHERE l.arm = a.arm
  ) s ON true
 WHERE a.is_thesis_arm;

COMMENT ON VIEW provenance.v_live_anchor IS
  'ADJUDICATION §2.10. The live half of tex/validation.tex tab:val-anchor in one row per arm, '
  'restricted to the two thesis arms (verify_flag excluded). NOTE the column is named '
  'tpot_p99_ms, not itl_p99_ms: the table''s "ITL p99" is aiperf inter_token_latency, which is '
  'TPOT. See the comment on provenance.live_arm.itl_p99_ms.';


-- =====================================================================
-- G. checks
-- =====================================================================
INSERT INTO provenance.check_definition
    (check_id, title, severity, est_cost, expected, note, sql_text)
VALUES

('C220', 'live replica-seconds recompute from the event log', 'error', 'cheap',
 'live_arm.replica_seconds must equal n_live integrated over t_wall across that arm''s '
 'live_worker_event rows, to within 1e-6 s.',
 'Makes the §2.10 replica-seconds figures (live_fc 6062.954568, live_re 1798.852786) derived '
 'rather than transcribed. If someone edits either the summary or the event log, this breaks.',
 $$
 WITH stepped AS (
     SELECT arm, n_live,
            lead(t_wall) OVER (PARTITION BY arm ORDER BY t_wall, line_no) - t_wall AS dt
       FROM provenance.live_worker_event
      WHERE n_live IS NOT NULL AND t_wall IS NOT NULL
 ), tot AS (
     SELECT arm, coalesce(sum(n_live * dt), 0) AS rs
       FROM stepped WHERE dt IS NOT NULL GROUP BY arm
 )
 SELECT count(*) FILTER (WHERE abs(a.replica_seconds - t.rs) > 1e-6) = 0,
        'arms=' || count(*) || ' mismatched=' ||
        coalesce(string_agg(a.arm || '(' || a.replica_seconds || '<>' || t.rs || ')', ', ')
                 FILTER (WHERE abs(a.replica_seconds - t.rs) > 1e-6), 'none')
   FROM provenance.live_arm a JOIN tot t USING (arm)
 $$),

('C221', 'live mixed-pass census recomputes from the pass log', 'error', 'cheap',
 'live_arm.fpm_passes and .fpm_mixed_passes must equal the count of live_fpm_pass rows with '
 't_rel_s <= fpm_window_s, and of those the ones with is_mixed.',
 'The §2.10 rates are live_fc 2/184, live_re 2/24, verify_flag 3/207 over a 300 s window. '
 'This probe reconstructs both numerator and denominator from the per-pass rows.',
 $$
 WITH c AS (
     SELECT a.arm, a.fpm_passes, a.fpm_mixed_passes,
            count(p.*) AS n, count(p.*) FILTER (WHERE p.is_mixed) AS n_mixed
       FROM provenance.live_arm a
       LEFT JOIN provenance.live_fpm_pass p
              ON p.arm = a.arm AND p.t_rel_s <= a.fpm_window_s
      GROUP BY a.arm, a.fpm_passes, a.fpm_mixed_passes
 )
 SELECT count(*) FILTER (WHERE fpm_passes IS DISTINCT FROM n
                            OR fpm_mixed_passes IS DISTINCT FROM n_mixed) = 0,
        'arms=' || count(*) || ' detail=' ||
        string_agg(arm || ' ' || n_mixed || '/' || n, ', ' ORDER BY arm)
   FROM c
 $$),

('C222', 'live headline latencies agree with the long-form aiperf export', 'error', 'cheap',
 'live_arm.ttft_p99_ms / itl_p99_ms / chunk_latency_p99_ms must equal the corresponding '
 '(metric, p99) rows in live_arm_metric exactly.',
 'Guards the convenience projection against drifting from the faithful record -- in particular '
 'against itl_p99_ms ever being repointed at inter_chunk_latency, which is the exact confusion '
 'that produced audit finding R16.',
 $$
 WITH m AS (
     SELECT arm,
            max(value) FILTER (WHERE metric='time_to_first_token'  AND stat='p99') AS ttft,
            max(value) FILTER (WHERE metric='inter_token_latency'  AND stat='p99') AS itl,
            max(value) FILTER (WHERE metric='inter_chunk_latency'  AND stat='p99') AS chunk
       FROM provenance.live_arm_metric GROUP BY arm
 )
 SELECT count(*) FILTER (WHERE a.ttft_p99_ms IS DISTINCT FROM m.ttft
                            OR a.itl_p99_ms  IS DISTINCT FROM m.itl
                            OR a.chunk_latency_p99_ms IS DISTINCT FROM m.chunk) = 0,
        'arms=' || count(*) || ' mismatched=' ||
        coalesce(string_agg(a.arm, ', ')
                 FILTER (WHERE a.ttft_p99_ms IS DISTINCT FROM m.ttft
                            OR a.itl_p99_ms  IS DISTINCT FROM m.itl
                            OR a.chunk_latency_p99_ms IS DISTINCT FROM m.chunk), 'none')
   FROM provenance.live_arm a JOIN m USING (arm)
 $$),

('C223', 'live TPOT and per-chunk ITL are distinct columns', 'warn', 'cheap',
 'For every arm, itl_p99_ms (aiperf inter_token_latency = TPOT) must differ from '
 'chunk_latency_p99_ms (true per-chunk ITL). Equality would mean the two were sourced from '
 'the same aiperf field.',
 'Not a data-quality invariant about the deployment -- a wiring invariant about this schema. '
 'The observed gaps are large (live_fc 11.470 vs 5.520 ms; live_re 150.745 vs 161.787 ms), so '
 'exact equality can only mean a loader bug. Severity warn, not error: if a future arm '
 'genuinely produced one chunk per token these would legitimately coincide, and that should '
 'be looked at rather than crash the suite.',
 $$
 SELECT count(*) FILTER (WHERE itl_p99_ms = chunk_latency_p99_ms) = 0,
        'arms=' || count(*) || ' coincident=' ||
        coalesce(string_agg(arm, ', ') FILTER (WHERE itl_p99_ms = chunk_latency_p99_ms), 'none')
   FROM provenance.live_arm
 $$),

('C224', 'live arm runs carry the deployment TP', 'error', 'cheap',
 'Every provenance.runs row with experiment = ''live'' must have tp = 2, from '
 'simulation/live51/engine_args.json ("aic_tp_size": 2).',
 'ADJUDICATION §2.10 backfill. tp was NULL on all seven pre-existing live rows, which is why '
 'several tab:val-anchor claims were unadjudicable against the DB.',
 $$
 SELECT count(*) FILTER (WHERE tp IS DISTINCT FROM 2) = 0,
        'live runs=' || count(*) || ' wrong_tp=' ||
        coalesce(string_agg(run_id, ', ') FILTER (WHERE tp IS DISTINCT FROM 2), 'none')
   FROM provenance.runs WHERE experiment = 'live'
 $$),

('C225', 'live spawn-latency pairs exclude initial spawns and stay sub-second', 'error', 'cheap',
 'live_spawn_latency must contain no reason = ''initial'' row, and every latency_s must lie '
 'in (0, 2) seconds.',
 'The band is deliberately loose. The point is not to pin 0.9858 s -- that would be asserting '
 'the measurement -- but to catch the two ways this pairing goes wrong: pairing a spawn to a '
 'Discovery line from a different scaling action (would blow past 2 s), and letting initial '
 'spawns in (which measure planner startup at ~3.3 s, not registration).',
 $$
 SELECT count(*) FILTER (WHERE reason = 'initial' OR latency_s <= 0 OR latency_s >= 2) = 0,
        'pairs=' || count(*) || ' bad=' ||
        coalesce(string_agg(arm || ':' || seq, ', ')
                 FILTER (WHERE reason = 'initial' OR latency_s <= 0 OR latency_s >= 2), 'none')
   FROM provenance.live_spawn_latency
 $$)

ON CONFLICT (check_id) DO UPDATE SET
    title = excluded.title, severity = excluded.severity, est_cost = excluded.est_cost,
    expected = excluded.expected, note = excluded.note, sql_text = excluded.sql_text;
