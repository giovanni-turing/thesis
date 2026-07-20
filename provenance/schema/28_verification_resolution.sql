-- =====================================================================
-- 28_verification_resolution.sql -- schema `provenance`, PostgreSQL 16
--
-- APPLIED 2026-07-20 during FINAL CERTIFICATION, against the settled,
-- read-only store (data generation complete, no loader running).
--
-- DEFECT FOUND BY THE CERTIFICATION SWEEP
-- ---------------------------------------
-- 75 of 380 provenance.verification rows carried resolved_run_id IS
-- NULL. C205 ("verification.resolved_run_id resolves to the spine")
-- passed anyway, because its predicate is
--     WHERE x.resolved_run_id IS NOT NULL AND NOT EXISTS (...)
-- i.e. it proves the NON-NULL pointers are sound but says nothing about
-- how many rows never got a pointer at all. C206 counts bare-run_id
-- orphans but is severity=info and, being a census, always returns true.
-- So the NULL population was covered by no check in either direction.
--
-- Of the 75, SIXTY-SIX have a run_id that is an EXACT, unique match to
-- an existing provenance.runs.run_id (e.g. 'g1:burst2_enc_fc_chronos_L30'
-- is present in runs verbatim). These are already namespaced; the
-- original resolver only rewrote BARE simulator ids into namespaced ones
-- and left already-namespaced ids untouched -- and therefore NULL. That
-- is a resolver gap, not a data problem: no measurement is missing, the
-- join pointer was simply never written.
--
-- WHAT THIS FILE DOES
-- -------------------
-- Fills those 66 NULLs with the exact match, and only where the match is
-- exact and unique. Nothing is overwritten: the UPDATE is gated on
-- resolved_run_id IS NULL, so no existing pointer can change. Every
-- write is recorded row-by-row in verification_resolution_backfill
-- (NULL -> value), mirroring the runs_config_backfill / C405 pattern
-- already established in this store.
--
-- THE REMAINING 9 ARE LEFT NULL, DELIBERATELY. They are not run
-- identities and no pointer would be truthful:
--   * 3 structural markers carrying no measurements at all --
--     'a16:cells', 'g1:_preflight', '_preflight'.
--   * 6 model-level AGGREGATE rows -- chronos/timesfm/toto x a14/a15 --
--     which do carry real numbers (completed, enc_p99, ttft_p99,
--     itl_p99, gpu_h) but summarise a whole forecast family across the
--     full trace. They have no single backing run by construction.
--     Inventing a resolved_run_id for them would be a fabricated join.
--
-- New check C214 makes this population visible instead of silent.
-- =====================================================================
SET search_path = provenance, public;

-- ---------------------------------------------------------------------
-- 1. Durable record of the backfill (written BEFORE the UPDATE, so the
--    pre-state is captured even if the UPDATE is rolled back).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.verification_resolution_backfill (
  source_path   text        NOT NULL,
  run_id        text        NOT NULL,
  old_value     text,                     -- always NULL: this only fills gaps
  new_value     text        NOT NULL,
  match_kind    text        NOT NULL,     -- 'exact': run_id present verbatim in runs
  rationale     text,
  recorded_utc  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (source_path, run_id)
);

COMMENT ON TABLE provenance.verification_resolution_backfill IS
 'Row-by-row record of the 2026-07-20 certification backfill of provenance.verification.resolved_run_id. Each row documents a NULL -> value fill where verification.run_id was already an exact, unique match to a provenance.runs.run_id that the original resolver skipped (it only rewrote BARE simulator ids, leaving already-namespaced ids NULL). old_value is always NULL by construction -- the UPDATE was gated on resolved_run_id IS NULL, so no pre-existing pointer could be overwritten. Mirrors the runs_config_backfill / C405 pattern. 66 rows expected.';
COMMENT ON COLUMN provenance.verification_resolution_backfill.old_value IS
 'Always NULL. Present so the NULL -> value transition is explicit and auditable rather than implied.';
COMMENT ON COLUMN provenance.verification_resolution_backfill.match_kind IS
 'How the target was established. Only ''exact'' is used: verification.run_id appears verbatim as a provenance.runs.run_id. No fuzzy, prefix or heuristic matching was performed -- an inexact match would be a fabricated join.';

BEGIN;

INSERT INTO provenance.verification_resolution_backfill
       (source_path, run_id, old_value, new_value, match_kind, rationale)
SELECT v.source_path, v.run_id, NULL, r.run_id, 'exact',
       'Certification sweep 2026-07-20: verification.run_id is already namespaced and matches provenance.runs.run_id verbatim; the original resolver only rewrote bare simulator ids and left this NULL. Filling the pointer adds no measurement and changes no value.'
  FROM provenance.verification v
  JOIN provenance.runs r ON r.run_id = v.run_id
 WHERE v.resolved_run_id IS NULL
ON CONFLICT (source_path, run_id) DO NOTHING;

-- ---------------------------------------------------------------------
-- 2. The fill itself. Gated on IS NULL: strictly additive.
-- ---------------------------------------------------------------------
UPDATE provenance.verification v
   SET resolved_run_id = r.run_id
  FROM provenance.runs r
 WHERE r.run_id = v.run_id
   AND v.resolved_run_id IS NULL;

-- ---------------------------------------------------------------------
-- 3. Conservation + correctness gate. Abort rather than report.
--    - row count of verification must be unchanged (380)
--    - no non-null pointer may dangle
--    - exactly the 9 known non-run labels may remain NULL
-- ---------------------------------------------------------------------
DO $$
DECLARE
  n_total    int;
  n_dangling int;
  n_null     int;
  n_filled   int;
BEGIN
  SELECT count(*) INTO n_total FROM provenance.verification;
  SELECT count(*) INTO n_dangling FROM provenance.verification v
   WHERE v.resolved_run_id IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM provenance.runs r WHERE r.run_id = v.resolved_run_id);
  SELECT count(*) INTO n_null FROM provenance.verification WHERE resolved_run_id IS NULL;
  SELECT count(*) INTO n_filled FROM provenance.verification_resolution_backfill;

  IF n_total <> 380 THEN
    RAISE EXCEPTION 'verification row count changed: % (expected 380)', n_total;
  END IF;
  IF n_dangling <> 0 THEN
    RAISE EXCEPTION 'dangling resolved_run_id pointers: %', n_dangling;
  END IF;
  IF n_null <> 9 THEN
    RAISE EXCEPTION 'unresolved rows = % (expected exactly the 9 non-run labels)', n_null;
  END IF;
  IF n_filled <> 66 THEN
    RAISE EXCEPTION 'backfill record has % rows (expected 66)', n_filled;
  END IF;
  RAISE NOTICE 'OK: 380 rows, 66 filled, 9 deliberately NULL, 0 dangling';
END $$;

COMMIT;

-- ---------------------------------------------------------------------
-- 4. C214 -- close the hole C205 left open.
--
--    NOTE ON SEVERITY. This is registered at `warn` and it FAILS, by
--    design. It could be made to pass by exempting the 9 labels, but
--    that would narrow the population -- the exact move the standing
--    rules forbid -- and would also hide any FUTURE unresolved row
--    behind the exemption. A check that fails with a precisely
--    characterised population is worth more than one that passes
--    vacuously. The number 9 is the tripwire: any other value means a
--    new unresolved row appeared and must be adjudicated.
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C214',
 'every verification row carries a resolved_run_id',
 'warn',
 $q$SELECT count(*) = 0,
       format('%s of %s verification rows have no resolved_run_id (%s)',
              count(*), (SELECT count(*) FROM provenance.verification),
              coalesce(string_agg(DISTINCT run_id, ', '), 'none'))
  FROM provenance.verification v
 WHERE v.resolved_run_id IS NULL$q$,
 '0 verification rows without a resolved_run_id. CURRENTLY 9 -- see note.',
 'cheap',
 'KNOWN FAILING, ACCEPTED, AND DELIBERATELY NOT EXEMPTED. Created 2026-07-20 by the final certification sweep, which found that C205 proved only that NON-NULL pointers resolve and never counted the rows that had no pointer at all -- 75 of 380 at the time. 66 of those 75 were an exact verbatim match to an existing runs.run_id that the original resolver had skipped (it rewrote only BARE simulator ids); they were backfilled by schema/28_verification_resolution.sql and recorded row-by-row in verification_resolution_backfill. The 9 that remain are NOT run identities and no truthful pointer exists for them: 3 are structural markers with no measurements (a16:cells, g1:_preflight, _preflight) and 6 are model-level AGGREGATE rows (chronos/timesfm/toto x a14/a15) that carry real numbers but summarise an entire forecast family over the full trace, so they have no single backing run by construction. Exempting them would narrow the population and would mask any future unresolved row, so the check is left failing. Expected detail: exactly 9. Any other count is a new defect to adjudicate, not a tolerance to adjust.'
)
ON CONFLICT (check_id) DO UPDATE
  SET title = EXCLUDED.title, severity = EXCLUDED.severity,
      sql_text = EXCLUDED.sql_text, expected = EXCLUDED.expected,
      est_cost = EXCLUDED.est_cost, note = EXCLUDED.note;

-- ---------------------------------------------------------------------
-- 5. C205 keeps its predicate (it tests what its title claims -- that
--    pointers which exist are sound) but its note now points at C214 so
--    a reader cannot mistake it for full coverage.
-- ---------------------------------------------------------------------
UPDATE provenance.check_definition
   SET note = 'Observed 0 orphans -- DEF-2 (320/320 unjoinable) is REPAIRED via the resolved_run_id column. The bare verification.run_id remains unprefixed by design; see C206. SCOPE WARNING added 2026-07-20: this check is deliberately restricted to resolved_run_id IS NOT NULL, so it proves existing pointers are sound and says NOTHING about rows carrying no pointer. That population is C214''s job -- read the two together. Before 2026-07-20 it was covered by neither, which hid 66 fillable NULLs.'
 WHERE check_id = 'C205';

-- ---------------------------------------------------------------------
-- 6. v_verification_resolved -- the view was SHADOWING the stored column.
--
-- DEFECT. The view did not read verification.resolved_run_id at all. It
-- recomputed its own pointer with
--     split_part(runs.run_id, ':', 2) = verification.run_id
-- i.e. it compared the LOCAL part of a spine id against the whole of
-- verification.run_id. That works for a BARE simulator id ('burst3_x')
-- and can never match an ALREADY-NAMESPACED one ('g1:burst2_enc_...'),
-- because the left side is by construction colon-free. So every one of
-- the 66 rows repaired in section 2 still read as n_candidates = 0 /
-- resolved_run_id = NULL through the view -- and SCHEMA_GUIDE section
-- 2.12 tells agents to join THE VIEW. The store knew the answer and the
-- documented access path threw it away.
--
-- FIX: prefer the stored, audited column; fall back to the old unique
-- suffix heuristic only where the column is NULL. Strictly more
-- resolving than before and never less: every pointer the old view
-- produced is still produced (the heuristic is unchanged and is what
-- populated the column for the bare ids in the first place).
--
-- n_candidates is KEPT with its original meaning so nothing that reads
-- it breaks, and resolution_source is added so a reader can always tell
-- which mechanism answered.
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
       END AS resolution_source
  FROM provenance.verification v;

COMMENT ON VIEW provenance.v_verification_resolved IS
 'verification joined to the spine. ALWAYS join on resolved_run_id, never on the bare run_id. Rewritten 2026-07-20: it previously ignored the stored verification.resolved_run_id column and recomputed a pointer via split_part(runs.run_id,'':'',2) = verification.run_id, which can only ever match a BARE simulator id -- so the 66 already-namespaced rows read as unresolvable through the view even though the table had resolved them. It now prefers the stored column and falls back to the unique-suffix heuristic, so it is strictly more resolving and never less. resolution_source says which mechanism answered: stored | unique_suffix | unresolved. Exactly 9 rows are unresolved and must stay that way (3 structural markers, 6 model-level aggregates) -- see check C214.';
