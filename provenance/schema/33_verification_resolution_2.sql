-- =====================================================================
-- 33_verification_resolution_2.sql -- schema `provenance`, PostgreSQL 16
--
-- APPLIED 2026-07-26, adjudicating the C214 regression flagged by the
-- adversarial review (Finding 9): C214 reported 69 of 440 verification
-- rows without resolved_run_id where its own note expects exactly 9.
--
-- WHAT HAPPENED
-- -------------
-- The a11 lead-sweep re-ingest (defense/anim/data/a11_runs/
-- verification.json, extended by the L60/L120/L300 x {chronos,timesfm,
-- toto,reactive} x {burst1,3,4,5,week} sweep, ledger 2026-07-25) added
-- 60 verification rows through loader K8b. K8b writes run_id but never
-- resolved_run_id -- that column is owned by the resolution passes
-- (schema/28) -- and no resolution pass ran after the re-ingest. This
-- is the exact resolver gap 28_verification_resolution.sql repaired
-- once already, recurring on new data. The 60 split into:
--
--   * 52 rows whose run_id is an EXACT verbatim match to an existing
--     provenance.runs.run_id (48 burst{1,3,4,5} L-sweep rows + 4
--     week_*_L60 rows). No measurement is missing; the pointer was
--     simply never written. Backfilled below, row-by-row recorded in
--     verification_resolution_backfill, same gate as schema/28.
--
--   * 8 rows -- a11:week_{fc_chronos,fc_timesfm,fc_toto,reactive}_
--     {L120,L300} -- that are FAILED REPLAY ATTEMPTS, not runs. Their
--     verification.json entries carry only
--         {"error": "replay rc=127 (see week_*.log)"}
--     (rc=127 = command not found), every measurement column is NULL,
--     and NO artifact exists on disk: no .log (despite the error
--     message pointing at one), no .report.json, no .requests.jsonl
--     (verified 2026-07-26; the a11_runs directory holds week artifacts
--     for L60 only). A spine row would assert a run that never
--     executed, so none is created. They are annotated as known-
--     unresolvable via the new unresolved_reason column instead.
--
-- The remaining 9 NULLs are the standing schema/28 population (3
-- structural markers, 6 model-level aggregates), unchanged; they now
-- also carry an explicit unresolved_reason so the adjudication lives in
-- the rows themselves, not only in a check note.
--
-- Post-state: 440 rows, 52 newly filled, 17 deliberately NULL (9 + 8),
-- every NULL annotated. C214's tripwire moves 9 -> 17; new C215
-- asserts every unresolved row carries its adjudication.
-- =====================================================================
SET search_path = provenance, public;

BEGIN;

-- ---------------------------------------------------------------------
-- 1. Row-by-row record of the fill (before the UPDATE, as in schema/28).
-- ---------------------------------------------------------------------
INSERT INTO provenance.verification_resolution_backfill
       (source_path, run_id, old_value, new_value, match_kind, rationale)
SELECT v.source_path, v.run_id, NULL, r.run_id, 'exact',
       'C214 regression adjudication 2026-07-26: row added by the a11 L-sweep re-ingest (loader K8b, which never writes resolved_run_id); verification.run_id matches provenance.runs.run_id verbatim. Same resolver gap as the 2026-07-20 certification backfill, recurring on new data. Filling the pointer adds no measurement and changes no value.'
  FROM provenance.verification v
  JOIN provenance.runs r ON r.run_id = v.run_id
 WHERE v.resolved_run_id IS NULL
ON CONFLICT (source_path, run_id) DO NOTHING;

-- ---------------------------------------------------------------------
-- 2. The fill. Gated on IS NULL: strictly additive, exact match only.
-- ---------------------------------------------------------------------
UPDATE provenance.verification v
   SET resolved_run_id = r.run_id
  FROM provenance.runs r
 WHERE r.run_id = v.run_id
   AND v.resolved_run_id IS NULL;

-- ---------------------------------------------------------------------
-- 3. unresolved_reason -- the adjudication moves into the store.
-- ---------------------------------------------------------------------
ALTER TABLE provenance.verification
  ADD COLUMN IF NOT EXISTS unresolved_reason text;

COMMENT ON COLUMN provenance.verification.unresolved_reason IS
 'Adjudication for rows that deliberately carry resolved_run_id IS NULL. NULL on every resolved row. Introduced 2026-07-26 (schema/33) so the reason a row cannot be joined to the spine is queryable per-row rather than living only in C214''s note. C215 asserts the invariant: unresolved implies annotated.';

-- 3a. The 8 failed week replays: no run happened, no artifacts exist.
UPDATE provenance.verification
   SET unresolved_reason =
       'KNOWN-UNRESOLVABLE (adjudicated 2026-07-26, schema/33): failed replay attempt, not a run. verification.json records only {"error": "replay rc=127"}; every measurement column is NULL and no artifact exists on disk (no .log, .report.json or .requests.jsonl for week L120/L300 -- only the L60 week artifacts exist). Creating a spine row would assert a run that never executed.'
 WHERE resolved_run_id IS NULL
   AND run_id ~ '^a11:week_(fc_(chronos|timesfm|toto)|reactive)_L(120|300)$';

-- 3b. The 3 structural markers (schema/28 population, reason now in-row).
UPDATE provenance.verification
   SET unresolved_reason =
       'KNOWN-UNRESOLVABLE (adjudicated 2026-07-20, schema/28; annotated in-row 2026-07-26, schema/33): structural marker carrying no measurements -- not a run identity, no truthful pointer exists.'
 WHERE resolved_run_id IS NULL
   AND run_id IN ('a16:cells', 'g1:_preflight', '_preflight');

-- 3c. The 6 model-level aggregates (schema/28 population, reason in-row).
UPDATE provenance.verification
   SET unresolved_reason =
       'KNOWN-UNRESOLVABLE (adjudicated 2026-07-20, schema/28; annotated in-row 2026-07-26, schema/33): model-level AGGREGATE row (chronos/timesfm/toto x a14/a15) summarising an entire forecast family over the full trace; it has no single backing run by construction, so any resolved_run_id would be a fabricated join.'
 WHERE resolved_run_id IS NULL
   AND run_id IN ('chronos', 'timesfm', 'toto');

-- ---------------------------------------------------------------------
-- 4. Conservation + correctness gate. Abort rather than report.
-- ---------------------------------------------------------------------
DO $$
DECLARE
  n_total      int;
  n_dangling   int;
  n_null       int;
  n_unannotated int;
  n_filled     int;
BEGIN
  SELECT count(*) INTO n_total FROM provenance.verification;
  SELECT count(*) INTO n_dangling FROM provenance.verification v
   WHERE v.resolved_run_id IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = v.resolved_run_id);
  SELECT count(*) INTO n_null FROM provenance.verification WHERE resolved_run_id IS NULL;
  SELECT count(*) INTO n_unannotated FROM provenance.verification
   WHERE resolved_run_id IS NULL AND unresolved_reason IS NULL;
  SELECT count(*) INTO n_filled FROM provenance.verification_resolution_backfill;

  IF n_total <> 440 THEN
    RAISE EXCEPTION 'verification row count changed: % (expected 440)', n_total;
  END IF;
  IF n_dangling <> 0 THEN
    RAISE EXCEPTION 'dangling resolved_run_id pointers: %', n_dangling;
  END IF;
  IF n_null <> 17 THEN
    RAISE EXCEPTION 'unresolved rows = % (expected exactly 17: 9 schema/28 + 8 failed week replays)', n_null;
  END IF;
  IF n_unannotated <> 0 THEN
    RAISE EXCEPTION '% unresolved rows carry no unresolved_reason', n_unannotated;
  END IF;
  IF n_filled <> 118 THEN
    RAISE EXCEPTION 'backfill record has % rows (expected 118 = 66 from schema/28 + 52 from schema/33)', n_filled;
  END IF;
  RAISE NOTICE 'OK: 440 rows, 52 newly filled (118 recorded total), 17 deliberately NULL, all annotated, 0 dangling';
END $$;

COMMIT;

-- ---------------------------------------------------------------------
-- 5. C214 -- tripwire re-armed at the repaired expectation.
--    Same SQL, same deliberate-fail design; only expected/note move.
-- ---------------------------------------------------------------------
UPDATE provenance.check_definition
   SET expected = '0 verification rows without a resolved_run_id. CURRENTLY 17 -- see note.',
       note = 'KNOWN FAILING, ACCEPTED, AND DELIBERATELY NOT EXEMPTED. Created 2026-07-20 (schema/28) after C205 was found to prove only that NON-NULL pointers resolve; re-adjudicated 2026-07-26 (schema/33) after the adversarial review caught the count at 69, not the documented 9. The regression was the schema/28 resolver gap recurring on new data: the a11 L-sweep re-ingest added 60 rows via loader K8b, which never writes resolved_run_id. 52 were exact verbatim matches to existing runs.run_id and were backfilled (recorded row-by-row in verification_resolution_backfill, now 118 rows total). 8 are a11:week_*_{L120,L300} FAILED REPLAYS (rc=127): error-only entries, all measurement columns NULL, zero artifacts on disk -- no spine row can truthfully exist, so they are annotated known-unresolvable via verification.unresolved_reason instead. The prior 9 (3 structural markers: a16:cells, g1:_preflight, _preflight; 6 model-level aggregates: chronos/timesfm/toto x a14/a15) stand, now also annotated in-row. Expected detail: exactly 17, every one carrying unresolved_reason (C215 enforces the annotation invariant). Any other count is a new defect to adjudicate, not a tolerance to adjust. If a loader ingests new verification.json data, the resolution pass (exact-match fill, schema/28 section 2 form) must be re-run -- twice now this was forgotten.'
 WHERE check_id = 'C214';

-- ---------------------------------------------------------------------
-- 6. C215 -- unresolved implies annotated. This one PASSES, and any
--    future unresolved-but-unadjudicated row fails it immediately,
--    which is the alarm C214 alone could not raise precisely.
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C215',
 'every unresolved verification row carries an unresolved_reason',
 'warn',
 $q$SELECT count(*) = 0,
       format('%s of %s unresolved verification rows lack an unresolved_reason (%s)',
              count(*),
              (SELECT count(*) FROM provenance.verification WHERE resolved_run_id IS NULL),
              coalesce(string_agg(DISTINCT run_id, ', '), 'none'))
  FROM provenance.verification v
 WHERE v.resolved_run_id IS NULL
   AND v.unresolved_reason IS NULL$q$,
 'Every row with resolved_run_id IS NULL carries a non-null unresolved_reason. 0 violations.',
 'cheap',
 'Companion to C214, added 2026-07-26 (schema/33). C214 counts the unresolved population and deliberately fails at its documented size (17); C215 asserts the INVARIANT that every member of that population carries an in-row adjudication. A new unresolved row therefore trips BOTH: C214''s count moves off 17 and C215 fails until the row is either resolved (exact-match fill recorded in verification_resolution_backfill) or annotated with the reason no truthful pointer exists.'
)
ON CONFLICT (check_id) DO UPDATE
  SET title = EXCLUDED.title, severity = EXCLUDED.severity,
      sql_text = EXCLUDED.sql_text, expected = EXCLUDED.expected,
      est_cost = EXCLUDED.est_cost, note = EXCLUDED.note;

-- ---------------------------------------------------------------------
-- 7. v_verification_resolved -- expose the adjudication; comment updated
--    (the old comment pinned "exactly 9", which is now stale).
--    Column list unchanged except unresolved_reason APPENDED (legal for
--    CREATE OR REPLACE VIEW; no consumer breaks).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW provenance.v_verification_resolved AS
SELECT v.source_path, v.run_id, v.stage, v.requests, v.completed,
       v.enc_p99, v.enc_max, v.ttft_p99, v.itl_p99, v.provisioned_ws,
       v.gpu_h, v.queue_divergent,
       (SELECT count(*) FROM provenance.runs q
         WHERE split_part(q.run_id, ':', 2) = v.run_id) AS n_candidates,
       coalesce(
         v.resolved_run_id,
         (SELECT min(q.run_id) FROM provenance.runs q
           WHERE split_part(q.run_id, ':', 2) = v.run_id
             AND (SELECT count(*) FROM provenance.runs z
                   WHERE split_part(z.run_id, ':', 2) = v.run_id) = 1)
       ) AS resolved_run_id,
       CASE
         WHEN v.resolved_run_id IS NOT NULL THEN 'stored'
         WHEN (SELECT count(*) FROM provenance.runs z
                WHERE split_part(z.run_id, ':', 2) = v.run_id) = 1 THEN 'unique_suffix'
         ELSE 'unresolved'
       END AS resolution_source,
       v.unresolved_reason
  FROM provenance.verification v;

COMMENT ON VIEW provenance.v_verification_resolved IS
 'verification joined to the spine. ALWAYS join on resolved_run_id, never on the bare run_id. Rewritten 2026-07-20 (schema/28) to prefer the stored, audited column over the unique-suffix heuristic; extended 2026-07-26 (schema/33) with unresolved_reason. Exactly 17 rows are unresolved and must stay that way: 3 structural markers + 6 model-level aggregates (schema/28) + 8 a11 week L120/L300 FAILED replays with zero artifacts (schema/33). Each carries its adjudication in unresolved_reason -- see checks C214 (population size) and C215 (annotation invariant).';
