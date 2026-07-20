-- =====================================================================
-- 29_riders_probe_config.sql -- ADJUDICATION §2.4 (completion) checks.
--
-- 25_group_c.sql / 26_group_c_checks.sql landed the riders knee/belief
-- DERIVATION (capacity_belief_sample, capacity_knee_probe, capacity_derivation)
-- and repaired the four ladder rows' configuration (§2.5). What it did NOT do
-- was give the derivation's sixteen INPUT runs the same treatment: the knee
-- probes and the forecast-scale validation runs still carried NULL window_name,
-- lead_s, n_replicas and arrival_speedup on provenance.runs. The effect was
-- silent and bad: capacity_knee_probe.window_name said 'burst1', runs.window_name
-- said nothing, so `SELECT ... FROM runs WHERE window_name='burst1'` -- the
-- natural way to ask "what backs the burst1 knee?" -- returned none of the probes
-- that back closedloop.tex:328-337.
--
-- load_group_c.py::_load_probe_config now backfills those columns under the same
-- NULL-only rule as §2.5, recording every write in runs_config_backfill with its
-- evidence. The two checks below exist so the backfill cannot quietly rot into an
-- assertion: both re-derive the value from the ARCHIVED REPORT rather than trust
-- the stored dimension.
--
-- Idempotent: both are ON CONFLICT DO UPDATE upserts into check_definition.
-- Contract (21_checks.sql): sql_text returns exactly one (passed boolean, detail text).
-- =====================================================================
\set ON_ERROR_STOP on
SET search_path = provenance, public;

-- ---------------------------------------------------------------------
-- C408 -- the window a riders run is filed under is the window it actually ran
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C408',
 'every riders run''s window_name is re-derivable from its own report''s request count',
 'error',
 $q$
 WITH ident AS (
   -- num_requests identifies the window uniquely: 64,804 = burst1 and 25,639 = burst4
   -- occur on exactly one row of provenance.windows each.
   SELECT s.run_id, s.num_requests, r.window_name AS stored,
          (SELECT w.window_name FROM provenance.windows w
            WHERE w.requests = s.num_requests) AS derived
     FROM provenance.llm_run_summary s
     JOIN provenance.runs r USING (run_id)
    WHERE s.run_id LIKE 'riders:%'
 ), bad AS (
   SELECT string_agg(format('%s: stored %s, report implies %s (num_requests %s)',
                            run_id, coalesce(stored,'NULL'), coalesce(derived,'NONE'),
                            num_requests), '; ') AS msg
     FROM ident
    WHERE stored IS NULL OR derived IS NULL OR stored <> derived
 )
 SELECT bad.msg IS NULL AS passed,
        coalesce(bad.msg,
                 format('OK: %s riders runs, every window_name re-derived from its report',
                        (SELECT count(*) FROM ident))) AS detail
   FROM bad
 $q$,
 'passed = true',
 'cheap',
 'The window is NOT taken on the word of a file name or a shell script: it is recovered from '
 'the archived report''s own num_requests against provenance.windows.requests, which is unique '
 'for both 64,804 (burst1) and 25,639 (burst4). If a future re-ingest files a riders run under '
 'the wrong window, or a new window collides on request count, this goes red. Fix the data or '
 'the identification -- do not widen the join.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C409 -- the knee ladder's x-axis is confirmed by the runs' own wall clock
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C409',
 'runs.arrival_speedup on the knee probes reproduces the report duration and the probe row',
 'error',
 $q$
 WITH k AS (
   SELECT r.run_id, r.arrival_speedup AS run_speedup,
          p.arrival_speedup AS probe_speedup,
          (s.metrics->>'duration_ms')::float8 / 1000.0 AS dur_s,
          w.span_s
     FROM provenance.runs r
     JOIN provenance.llm_run_summary s USING (run_id)
     JOIN provenance.windows w ON w.window_name = r.window_name
     LEFT JOIN provenance.capacity_knee_probe p ON p.run_id = r.run_id
    WHERE r.run_id LIKE 'riders:%' AND r.arrival_speedup IS NOT NULL
 ), bad AS (
   SELECT string_agg(format('%s: speedup %s, probe %s, %s s x speedup = %s s vs window span %s s',
                            run_id, run_speedup, coalesce(probe_speedup::text,'NULL'),
                            round(dur_s::numeric,1), round((dur_s*run_speedup)::numeric,1),
                            round(span_s::numeric,1)), '; ') AS msg
     FROM k
    WHERE probe_speedup IS DISTINCT FROM run_speedup
       OR abs(dur_s * run_speedup - span_s) / span_s > 0.001
 )
 SELECT bad.msg IS NULL AS passed,
        coalesce(bad.msg,
                 format('OK: %s knee probes, arrival_speedup confirmed by wall clock to <0.1%%',
                        (SELECT count(*) FROM k))) AS detail
   FROM bad
 $q$,
 'passed = true',
 'cheap',
 'arrival_speedup is the x-axis of the tail-knee ladder, so it is the one dimension the '
 'derivation cannot survive being wrong about. Two independent confirmations are required: it '
 'must equal capacity_knee_probe.arrival_speedup, AND compressing the window''s own span by it '
 'must reproduce the replay duration recorded in the report (29,939.3 s / 1.25, / 1.5, / 2 give '
 'the three observed durations to within 0.008%%). The 0.1%% tolerance covers replay scheduling '
 'jitter only; it is two orders of magnitude looser than the observed error and must not be '
 'widened to accommodate a disagreement.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C405 (revised) -- make the backfill audit column-agnostic
--
-- The original C405 resolved the live value with a hardcoded
-- CASE column_name WHEN 'lead_s' ... WHEN 'tp' ... WHEN 'window_name' ... ELSE NULL,
-- which was exactly right for the three columns §2.5 backfilled and silently WRONG
-- the moment a fourth was added: n_replicas / policy / arrival_speedup resolved to
-- NULL, so a correctly-backfilled row reported live=<empty> and the check went red
-- on healthy data. Replacing the CASE with a to_jsonb() lookup keeps the assertion
-- identical in strength (old_value must be NULL; live must still equal new_value)
-- while making it total over provenance.runs' columns. This is a widening of
-- COVERAGE, not a loosening of the test: the revised check catches everything the
-- old one did, plus the columns the old one could not see.
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C405',
 'every runs_config_backfill row replaced a NULL and matches the current runs value',
 'error',
 $q$
 WITH b AS (
   SELECT b.run_id, b.column_name, b.old_value, b.new_value,
          to_jsonb(r) ->> b.column_name AS live_value
     FROM provenance.runs_config_backfill b
     JOIN provenance.runs r USING (run_id)
 ), cmp AS (
   SELECT b.*,
          -- Equal as VALUES, not as strings: '2' and '2.0' are the same n_replicas,
          -- and numeric columns render differently through jsonb than through str().
          (live_value IS NOT NULL AND new_value IS NOT NULL
           AND (live_value = new_value
                OR (live_value ~ '^-?[0-9]+(\.[0-9]+)?$'
                    AND new_value  ~ '^-?[0-9]+(\.[0-9]+)?$'
                    AND live_value::numeric = new_value::numeric))) AS agrees
     FROM b
 )
 SELECT count(*) FILTER (WHERE old_value IS NOT NULL OR NOT agrees) = 0 AS passed,
        coalesce(string_agg(format('%s.%s: old=%s new=%s live=%s',
                                   run_id, column_name, old_value, new_value, live_value), '; ')
                 FILTER (WHERE old_value IS NOT NULL OR NOT agrees),
                 format('OK: %s backfills over %s columns, all NULL->value, all still matching runs',
                        count(*), count(DISTINCT column_name))) AS detail
   FROM cmp
 $q$,
 'passed = true',
 'cheap',
 'Backfilling a NULL is the one edit this project makes to an archived row, so it is audited '
 'unconditionally: old_value must be NULL (the loader asserts it, this re-asserts it from the '
 'stored record) and the live value must still be what was written -- a later ingest that '
 'overwrites a backfilled dimension shows up here. Resolves the live value via to_jsonb() so '
 'the check covers every column of provenance.runs automatically; the earlier hardcoded CASE '
 'covered only lead_s/tp/window_name and reported NULL for anything else, which made healthy '
 'backfills look like defects. Numeric columns compare numerically, since ''2'' and ''2.0'' are '
 'the same value.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- Ledger. Scoped delete-then-insert: ledger_entry's key is a serial, so this is
-- how the group_c loader keeps its own entry idempotent. Nothing else writes
-- this section.
-- ---------------------------------------------------------------------
DELETE FROM provenance.ledger_entry WHERE section = 'ADJUDICATION §2.4 (probe config)';
INSERT INTO provenance.ledger_entry
    (section, name, entry_date, artifact_paths, command, feeds, supersedes, result_note)
VALUES (
 'ADJUDICATION §2.4 (probe config)',
 'riders knee/belief derivation — INPUT runs given the configuration they ran under',
 DATE '2026-07-20',
 ARRAY['provenance/schema/29_riders_probe_config.sql',
       'provenance/loader/load_group_c.py',
       '/home/gio/tese/simulation/results/riders44'],
 'python provenance/loader/load_group_c.py && psql -f provenance/schema/29_riders_probe_config.sql',
 'closedloop.tex:328,331,337 — the tail-aware capacity conversion (belief / r_tail -> '
 'FORECAST_REQ_SCALE=8). The derivation was already recomputable from capacity_belief_sample '
 'and capacity_knee_probe; this makes its INPUT RUNS reachable by the dimensions anyone would '
 'query them by.',
 'the NULL window_name / lead_s / n_replicas / arrival_speedup on the sixteen non-ladder '
 'riders:* rows, and the NULL policy / n_replicas on the four riders:ladder_* rows',
 '51 further NULL-only backfills recorded in runs_config_backfill (63 total over 6 columns). '
 'window_name is re-derived from each report''s own num_requests against provenance.windows '
 '(64,804 = burst1, 25,639 = burst4, both unique) rather than asserted from a filename — C408. '
 'arrival_speedup on the three tp2knee rungs is confirmed twice over: it equals '
 'capacity_knee_probe.arrival_speedup and it reproduces the report duration from the window '
 'span to within 0.008% (29,939.3/1.25/1.5/2) — C409. C405 was rewritten column-agnostically '
 '(to_jsonb lookup) because its hardcoded three-column CASE reported healthy backfills as '
 'defects. NOT DONE, deliberately: lead_s stays NULL on the three tp2knee rows (no archived '
 'file states a startup_time for the knee probes) and policy stays NULL on them (no file '
 'settles whether they ran planner-less); guessing either would invent a dimension. New view '
 'v_riders_probe_config. Loader idempotent over three consecutive passes.'
);

-- ---------------------------------------------------------------------
-- A queryable surface for the derivation's inputs.
-- ---------------------------------------------------------------------
-- runs.arrival_speedup already carries the project-wide convention comment
-- (offered_req_per_s = window mean x speedup) and is used by 93 distinct values
-- across the sweeps; it is deliberately NOT re-commented here. What needed saying
-- is riders-specific, so it is said on the view.
CREATE OR REPLACE VIEW provenance.v_riders_probe_config AS
SELECT r.run_id, r.window_name, r.policy, r.lead_s, r.tp, r.n_replicas,
       r.arrival_speedup,
       p.probe_kind, p.forecast_req_scale, p.offered_rps_per_replica,
       p.implied_r_tail, p.passes, p.is_superseded,
       s.num_requests, s.p99_ttft_ms, s.p99_itl_ms, s.gpu_hours,
       (SELECT bool_or(true) FROM provenance.runs_config_backfill b
         WHERE b.run_id = r.run_id) AS has_backfilled_config
  FROM provenance.runs r
  LEFT JOIN provenance.capacity_knee_probe p ON p.run_id = r.run_id
  LEFT JOIN provenance.llm_run_summary s ON s.run_id = r.run_id
 WHERE r.run_id LIKE 'riders:%';

COMMENT ON VIEW provenance.v_riders_probe_config IS
 'ADJUDICATION §2.4/§2.5. The twenty riders runs with the configuration they actually ran '
 'under, joined to their knee-probe row and their report. Answers "what backs the burst1 knee?" '
 'in one query, which is exactly what was impossible before the config backfill: eleven of '
 'these rows had a NULL window_name while capacity_knee_probe already knew the answer. '
 'has_backfilled_config flags rows whose configuration was RECONSTRUCTED from run_44_riders.sh '
 'or results-ledger.md rather than read out of the artifact -- join runs_config_backfill for '
 'the per-column evidence before treating a dimension as ingested. Rows with a NULL probe_kind '
 'are the four reactive ladder runs and the fc_lead sweep, which are not knee rungs. lead_s is '
 'NULL on the three tp2knee rows because no archived file states a startup_time for them; that '
 'gap is real and is not filled by guessing.';
