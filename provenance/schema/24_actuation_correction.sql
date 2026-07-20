-- =====================================================================
-- 24_actuation_correction.sql
--
-- ADJUDICATION.md §2.7 — the 560-cell target-time grid.
--
-- WHAT THE AUDIT EXPECTED vs WHAT WAS ACTUALLY IN THE STORE
-- ---------------------------------------------------------
-- §2.7 records `SELECT actuation, count(*) FROM factorial_cell GROUP BY 1`
-- returning "issue-time only (1,172 cells) — the expected state, since
-- the target-time grid is declared superseded", and asks for the
-- target-time grid to be INGESTED.
--
-- It is already ingested. It is ingested MISLABELLED. Of those 1,172
-- rows only 600 are issue-time; 572 are the target-time harness wearing
-- an issue-time label:
--
--     results_44.jsonl      560 cells   (gen_cells_44.py -> e2b_fleet.py
--                                        -> run_cell.py -> forecast_schedule.py)
--     pilot_results.jsonl    12 cells   (pilot_cells.jsonl, same harness;
--                                        parity-gated bit-exact against
--                                        the 560-grid, results-ledger.md:112)
--     factorial_issuetime/  600 cells   (run_44_factorial_issuetime.py ->
--                                        forecast_schedule_issuetime.py)
--
-- So the two actuations were not merely un-ingested, they were SILENTLY
-- POOLED — exactly the failure §2.7 exists to prevent. The corroborating
-- fingerprint is already visible in check C504's own note: "factorial_cell
-- readiness: strict=300 warm=300 NULL=572". Readiness is an issue-time-only
-- axis; the 572 NULLs are precisely these rows.
--
-- EVIDENCE that the 572 are target-time:
--   simulation/run_44_factorial_issuetime.py:5-8 — "The archived 560-cell
--     grid (gen_cells_44.py / run_cell.py) used the TARGET-time controller
--     (forecast_schedule.py) at leads {15,30,45,300}."
--   progress/results-ledger.md:416 — "560-cell grid relabeled target-time
--     exploratory".
--   Lead sets discriminate them without reference to any document:
--     target-time leads {15,30,45,300}, issue-time leads {15,30,45,165}.
--
-- WHY THE run_id IS RENAMED
-- -------------------------
-- loaders.load_factorial builds the identifier as
-- "factorial:<actuation>:<window>:...", so the wrong label is baked into
-- the primary key. Leaving it would (a) make the identifier itself
-- assert the falsehood and (b) cause the corrected loader to mint 560
-- NEW rows on the next --reload and orphan the old ones. Every old
-- identifier stays resolvable through provenance.run_id_alias.
--
-- NOTHING MEASURED CHANGES. p99_ms, max_ms, feasible, provisioned_ws,
-- busy_ws and the schedule columns are carried across untouched; only
-- the label and the identifier move.
--
-- Idempotent: safe to run repeatedly. Depends on 23_runtime_build_and_actuation.sql.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- A  the affected population, defined by SOURCE FILE (not by guesswork)
-- ---------------------------------------------------------------------
CREATE TEMP TABLE _tt_map ON COMMIT DROP AS
SELECT c.run_id                                                        AS old_run_id,
       replace(c.run_id, 'factorial:issue-time:', 'factorial:target-time:') AS new_run_id,
       c.source_path
  FROM provenance.factorial_cell c
 WHERE c.source_path IN ('/home/gio/tese/simulation/results/results_44.jsonl',
                         '/home/gio/tese/simulation/results/pilot_results.jsonl')
   AND c.run_id LIKE 'factorial:issue-time:%';

-- ---------------------------------------------------------------------
-- B  record the correction BEFORE applying it
-- ---------------------------------------------------------------------
INSERT INTO provenance.ingest_correction
  (correction_id, table_name, field, original_value, corrected_value,
   n_rows, source_path, evidence, rationale)
SELECT 'IC001', 'factorial_cell', 'actuation', 'issue-time', 'target-time',
       (SELECT count(*) FROM _tt_map),
       '/home/gio/tese/simulation/results/results_44.jsonl + pilot_results.jsonl',
       'simulation/run_44_factorial_issuetime.py:5-8; progress/results-ledger.md:112,416; '
       'lead set {15,30,45,300} vs the issue-time rebuild''s {15,30,45,165}',
       'loaders.load_factorial inferred actuation from the substring "target" in the '
       'file PATH. Neither results_44.jsonl nor pilot_results.jsonl contains it, so both '
       'target-time families fell through to the issue-time default and were pooled with '
       'the issue-time rebuild. The archived JSON carries no actuation field, so the '
       'label was never a measurement; the loader now classifies by explicit artifact '
       'identity instead of a path substring.'
WHERE EXISTS (SELECT 1 FROM _tt_map)
ON CONFLICT (correction_id) DO UPDATE
  SET n_rows = excluded.n_rows;

INSERT INTO provenance.ingest_correction
  (correction_id, table_name, field, original_value, corrected_value,
   n_rows, source_path, evidence, rationale)
SELECT 'IC002', 'runs', 'is_current', 'true', 'false',
       (SELECT count(*) FROM _tt_map),
       '/home/gio/tese/simulation/results/results_44.jsonl + pilot_results.jsonl',
       'ADJUDICATION.md §2.7',
       'The target-time grid is superseded by the 60-cell issue-time rebuild, so it '
       'leaves provenance.current_factorial. It is retained in full in factorial_cell '
       'so the superseded grid stays AUDITABLE rather than invisible. Part D flags the '
       'cells that, though superseded as a grid, still back published table cells.'
WHERE EXISTS (SELECT 1 FROM _tt_map)
ON CONFLICT (correction_id) DO UPDATE
  SET n_rows = excluded.n_rows;

INSERT INTO provenance.run_id_alias (old_run_id, new_run_id, correction_id)
SELECT old_run_id, new_run_id, 'IC001' FROM _tt_map
ON CONFLICT (old_run_id) DO NOTHING;

-- ---------------------------------------------------------------------
-- C  apply: new runs rows -> repoint the cells -> drop the stale runs
-- ---------------------------------------------------------------------
-- C.1  the corrected runs rows (full copy; only actuation, is_current
--      and the identifier differ).
INSERT INTO provenance.runs
  (run_id, experiment, pool, window_name, policy, model, mode, quantile, resolution,
   horizon_h, lead_s, cold_start_s, rho, hysteresis_min, config_c, tp, n_replicas,
   converter, gpu, engine, actuation, kind, source_path, artifact_paths, command,
   commit_sha, run_utc, feeds, supersedes, superseded_by, is_current, config,
   window_name_as_ingested, runtime_build, runtime_version, runtime_build_evidence)
SELECT m.new_run_id, r.experiment, r.pool, r.window_name, r.policy, r.model, r.mode,
       r.quantile, r.resolution, r.horizon_h, r.lead_s, r.cold_start_s, r.rho,
       r.hysteresis_min, r.config_c, r.tp, r.n_replicas, r.converter, r.gpu, r.engine,
       'target-time', r.kind, r.source_path, r.artifact_paths, r.command, r.commit_sha,
       r.run_utc, r.feeds, r.supersedes, r.superseded_by, false, r.config,
       r.window_name_as_ingested, r.runtime_build, r.runtime_version, r.runtime_build_evidence
  FROM _tt_map m JOIN provenance.runs r ON r.run_id = m.old_run_id
ON CONFLICT (run_id) DO UPDATE
  SET actuation = 'target-time', is_current = false;

-- C.2  repoint the measurements (values untouched).
UPDATE provenance.factorial_cell c
   SET run_id = m.new_run_id,
       actuation = 'target-time'
  FROM _tt_map m
 WHERE c.run_id = m.old_run_id;

-- C.3  the now-unreferenced stale runs rows. Their identifiers survive in
--      provenance.run_id_alias and their content is byte-identical to the
--      corrected rows inserted in C.1 apart from the two corrected fields.
DELETE FROM provenance.runs r
 USING _tt_map m
 WHERE r.run_id = m.old_run_id
   AND NOT EXISTS (SELECT 1 FROM provenance.factorial_cell c WHERE c.run_id = r.run_id)
   AND NOT EXISTS (SELECT 1 FROM provenance.llm_run_summary x WHERE x.run_id = r.run_id)
   AND NOT EXISTS (SELECT 1 FROM provenance.encoder_run_summary x WHERE x.run_id = r.run_id);

-- ---------------------------------------------------------------------
-- D  superseded-but-still-published: do not let this go silent
-- ---------------------------------------------------------------------
-- The reactive rho=15 cells of the target-time grid at leads 15/30/45 are
-- the source of the thesis's reactive ladder (Tab. 7.3) and of the A2
-- defense animation (defense/anim/build/gen_a2_runs.py:9,
-- extract_a2.py:47 both name results_44.jsonl reactive rho15 cells).
-- They are superseded AS A GRID but they are not unused, so they say so.
UPDATE provenance.runs r
   SET feeds = 'thesis Tab. 7.3 reactive ladder + defense A2 '
               '(gen_a2_runs.py:9, extract_a2.py:47) — superseded as a grid '
               '(target-time actuation) but still the source of published cells'
  FROM provenance.factorial_cell c
 WHERE c.run_id = r.run_id
   AND c.actuation = 'target-time'
   AND c.policy = 'reactive'
   AND c.rho = 15
   AND c.cold_start_s IN (15, 30, 45)
   AND r.feeds IS DISTINCT FROM
       'thesis Tab. 7.3 reactive ladder + defense A2 '
       '(gen_a2_runs.py:9, extract_a2.py:47) — superseded as a grid '
       '(target-time actuation) but still the source of published cells';

COMMIT;

-- ---------------------------------------------------------------------
-- E  the C505 vocabulary check now describes the true domain
-- ---------------------------------------------------------------------
-- This is a WIDENING, not a relaxation: 'target-time' is a second
-- actuation mode that genuinely exists on disk and that the store
-- previously could not represent. C505's own note anticipated it —
-- "If a second actuation mode is ever simulated this check fires and the
-- domain must be widened." The check still fails on any THIRD value.
UPDATE provenance.check_definition
   SET expected = 'actuation is issue-time or target-time (or NULL) in runs and factorial_cell.',
       note = 'Widened 2026-07-20 (ADJUDICATION §2.7). Observed: issue-time 600 rows '
              '(the factorial_issuetime rebuild), target-time 572 rows (results_44.jsonl '
              '560 + pilot_results.jsonl 12), NULL elsewhere. The two actuations are NOT '
              'comparable cell-for-cell: target-time makes the worker READY AT the target '
              'bin, issue-time ISSUES the decision at t for readiness at t+lead. Anything '
              'that aggregates factorial_cell without filtering actuation is wrong. A '
              'THIRD value still fires this check.',
       sql_text = $$SELECT (a+b) = 0, format('unknown actuation values -- runs=%s factorial_cell=%s', a, b)
    FROM (SELECT (SELECT count(*) FROM provenance.runs
                   WHERE actuation IS NOT NULL AND actuation NOT IN ('issue-time','target-time')) a,
                 (SELECT count(*) FROM provenance.factorial_cell
                   WHERE actuation IS NOT NULL AND actuation NOT IN ('issue-time','target-time')) b) q$$
 WHERE check_id = 'C505';


-- ---------------------------------------------------------------------
-- F  new invariants, so this cannot silently regress
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
  (check_id, title, severity, est_cost, expected, note, sql_text)
VALUES
('C507', 'the two actuations are never pooled in a published aggregate', 'error', 'cheap',
 'provenance.current_factorial contains exactly one actuation (issue-time).',
 'The whole point of §2.7. current_factorial is what the analytical views (v_infeasible, '
 'the feasibility rollups) read, so if a target-time run ever regains is_current the '
 'superseded exploratory grid silently re-enters every aggregate. Fires on 2 distinct '
 'actuations, not on 0 rows.',
 $$SELECT count(DISTINCT actuation) <= 1,
          format('distinct actuations in current_factorial = %s (%s)',
                 count(DISTINCT actuation), string_agg(DISTINCT actuation, ','))
     FROM provenance.current_factorial$$),

('C508', 'every renamed run_id is still resolvable', 'error', 'cheap',
 'Every provenance.run_id_alias.new_run_id exists in provenance.runs.',
 'A rename is only non-destructive if the forwarding address is live. If this fires, an '
 'identifier quoted in an older query, note or audit document has become unresolvable.',
 $$SELECT count(*) = 0, format('%s aliases point at a missing run', count(*))
     FROM provenance.run_id_alias a
    WHERE NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = a.new_run_id)$$),

('C509', 'runtime_build is attested, never asserted', 'error', 'cheap',
 'Every runs.runtime_build carries evidence: runtime_build_evidence (a log path) or a '
 'config_provenance tag from the §2.12 pass.',
 'ADJUDICATION §2.2. The value of the discriminator is that it is READ from an artifact. '
 'A row with a build and no evidence is a guess, which is exactly what this column must '
 'never contain. Observed 2026-07-20: 605 attested (495 source / 110 wheel), 0 unattested.',
 $$SELECT count(*) = 0,
          format('%s runs carry runtime_build with no evidence of any kind', count(*))
     FROM provenance.runs
    WHERE runtime_build IS NOT NULL
      AND runtime_build_evidence IS NULL
      AND (config_provenance IS NULL OR config_provenance ->> 'runtime_build' IS NULL)$$)
ON CONFLICT (check_id) DO UPDATE
  SET title = excluded.title, severity = excluded.severity, est_cost = excluded.est_cost,
      expected = excluded.expected, note = excluded.note, sql_text = excluded.sql_text;
