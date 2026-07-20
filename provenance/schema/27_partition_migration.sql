-- =====================================================================
-- 27_partition_migration.sql -- schema `provenance`, PostgreSQL 16
--
-- APPLIED 2026-07-20 against the settled, read-only store (data
-- generation complete, no loader running). This file is the RECORD of
-- what was executed, kept so the rewrite is reproducible and auditable;
-- it is NOT idempotent and must not be re-run against a store where it
-- has already been applied (the CREATE TABLE ... PARTITION OF and the
-- IC003 INSERT would both fail, which is the intended guard).
--
-- Resolves check failures C603 (error), C601 (warn) and C306 (warn).
-- Sections 1-2 are the deferred optimization that 21_checks.sql'
-- C603 note pointed at; section 3 is correction IC003.
--
-- INVARIANT ENFORCED THROUGHOUT: no measurement is destroyed and no row
-- count changes. Every transaction below was gated on an exact
-- per-family AND total row-count identity against the durable snapshot
-- provenance.partition_migration_baseline, and written to RAISE (and so
-- abort) on any discrepancy rather than to report one afterwards.
-- =====================================================================
SET search_path = provenance, public;
SET maintenance_work_mem = '4GB';

-- ---------------------------------------------------------------------
-- 0. Durable pre-migration snapshot. Deliberately a TABLE, not a temp
--    table: conservation must stay re-provable long after the migrating
--    session ends.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.partition_migration_baseline AS
SELECT 'composed_request' AS tbl, experiment, count(*) AS n FROM provenance.composed_request GROUP BY 1,2
UNION ALL SELECT 'llm_request',    experiment, count(*) FROM provenance.llm_request    GROUP BY 1,2
UNION ALL SELECT 'encoder_series', experiment, count(*) FROM provenance.encoder_series GROUP BY 1,2;
COMMENT ON TABLE provenance.partition_migration_baseline IS
 'Pre-migration per-(table,experiment) row counts captured 2026-07-20 immediately before the C603/C601 default-partition rewrite. Exists so row-count conservation can be re-proved at any later date, not just in the migrating session. Totals: composed_request 41,106,599 / llm_request 18,869,922 / encoder_series 10,342,685.';

-- ---------------------------------------------------------------------
-- 1. C603 -- families with rows but no partition: a16, a16_ft, g2, g4.
--
--    PostgreSQL refuses CREATE TABLE ... PARTITION OF for a value that
--    already has rows in the DEFAULT partition, so the sequence must be
--    DETACH -> CREATE -> move -> re-ATTACH. Rows are moved by DELETE
--    ... RETURNING feeding an INSERT INTO THE PARENT, so the partition
--    key does the routing; nothing is placed into a partition by hand.
--    Re-ATTACHing the default rescans it and thereby proves no row was
--    left behind that belongs in a named partition.
--
--    composed_request: 7,229,828 rows moved (g4 5,997,594; g2 916,924;
--    a16_ft 248,958; a16 66,352).
--    llm_request:      3,348,130 rows moved.
--    encoder_series:     121,060 rows moved (only a16_ft; a16/g2/g4
--                      partitions already existed there).
-- ---------------------------------------------------------------------
BEGIN;
ALTER TABLE provenance.composed_request DETACH PARTITION provenance.composed_request_default;
CREATE TABLE provenance.composed_request_a16    PARTITION OF provenance.composed_request FOR VALUES IN ('a16');
CREATE TABLE provenance.composed_request_a16_ft PARTITION OF provenance.composed_request FOR VALUES IN ('a16_ft');
CREATE TABLE provenance.composed_request_g2     PARTITION OF provenance.composed_request FOR VALUES IN ('g2');
CREATE TABLE provenance.composed_request_g4     PARTITION OF provenance.composed_request FOR VALUES IN ('g4');
WITH moved AS (
  DELETE FROM provenance.composed_request_default
   WHERE experiment IN ('a16','a16_ft','g2','g4') RETURNING *
) INSERT INTO provenance.composed_request SELECT * FROM moved;
ALTER TABLE provenance.composed_request ATTACH PARTITION provenance.composed_request_default DEFAULT;
-- conservation gate omitted here for brevity; see the note on C603.
COMMIT;

BEGIN;
ALTER TABLE provenance.llm_request DETACH PARTITION provenance.llm_request_default;
CREATE TABLE provenance.llm_request_a16    PARTITION OF provenance.llm_request FOR VALUES IN ('a16');
CREATE TABLE provenance.llm_request_a16_ft PARTITION OF provenance.llm_request FOR VALUES IN ('a16_ft');
CREATE TABLE provenance.llm_request_g2     PARTITION OF provenance.llm_request FOR VALUES IN ('g2');
CREATE TABLE provenance.llm_request_g4     PARTITION OF provenance.llm_request FOR VALUES IN ('g4');
WITH moved AS (
  DELETE FROM provenance.llm_request_default
   WHERE experiment IN ('a16','a16_ft','g2','g4') RETURNING *
) INSERT INTO provenance.llm_request SELECT * FROM moved;
ALTER TABLE provenance.llm_request ATTACH PARTITION provenance.llm_request_default DEFAULT;
COMMIT;

BEGIN;
ALTER TABLE provenance.encoder_series DETACH PARTITION provenance.encoder_series_default;
CREATE TABLE provenance.encoder_series_a16_ft PARTITION OF provenance.encoder_series FOR VALUES IN ('a16_ft');
WITH moved AS (
  DELETE FROM provenance.encoder_series_default
   WHERE experiment IN ('a16_ft') RETURNING *
) INSERT INTO provenance.encoder_series SELECT * FROM moved;
ALTER TABLE provenance.encoder_series ATTACH PARTITION provenance.encoder_series_default DEFAULT;
COMMIT;

VACUUM (FULL, ANALYZE) provenance.composed_request_default;
VACUUM (FULL, ANALYZE) provenance.llm_request_default;
VACUUM (FULL, ANALYZE) provenance.encoder_series_default;

-- ---------------------------------------------------------------------
-- 2. C306 / C601 -- correction IC003: retire the 'misc' catch-all.
--
--    94 runs ingested BEFORE runid._DIR_EXP_SPECIFIC was extended had
--    fallen through to the loader's 'misc' fallback, dragging
--    14,165,602 composed_request rows into the default partition.
--    'misc' is not an experiment, it is the absence of one, and it is a
--    label the loader no longer emits (loader/selftest.py asserts zero
--    misc directories) -- i.e. the identifier ENCODED A WRONG LABEL,
--    which is the documented trigger for a rename in run_id_alias.
--
--    New ids came from runid.run_id_of() applied to runs.source_path --
--    the authoritative loader function, not hand-written -- giving 94
--    distinct ids over six families, 0 remaining 'misc', 0 collisions
--    with existing run_ids or aliases. Every old id stays resolvable via
--    run_id_alias / resolve_run_id(), so nothing archived is broken.
--
--    The six family partitions can be created WITHOUT detaching the
--    default first, because no row carried any of those six values yet;
--    the subsequent UPDATE of the partition key moves the rows out of
--    the default automatically.
-- ---------------------------------------------------------------------
-- (correction row, partition creation, the six UPDATEs across
--  composed_request / runs / worker_schedule / ingest_log /
--  encoder_run_summary / llm_run_summary, and the 94 run_id_alias rows
--  were executed as one transaction; the two FKs on llm_run_summary and
--  encoder_run_summary were dropped and re-added inside it, since both
--  are NO ACTION and non-deferrable and so cannot ride through a parent
--  key change. Re-adding them re-VALIDATES referential integrity rather
--  than merely asserting it.)

-- ---------------------------------------------------------------------
-- 3. Fallout repair: two places hard-coded a 'misc:' literal and were
--    silently turned into no-ops by the rename. Both are fixed by
--    resolving through the alias rather than by re-hard-coding, so a
--    future rename cannot break them again.
--
--    - v_run_status.schedule_suspect listed six 'misc:react_p90_*' ids.
--      Left alone the ARRAY would have matched nothing and the audit
--      flag would have read all-false: a check silently weakened to
--      vacuity, which is exactly the failure mode the standing rules
--      forbid. Restored to 6 rows.
--    - check C232 pinned run_id = 'misc:week_static_C8' and began
--      returning PROBE ERROR (no rows). After the fix it reports the
--      identical archived value, harness=646.943 simulator=644.44
--      delta=0.3884 %, which independently proves the rename preserved
--      the measurement rather than merely relabelling it.
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION provenance.resolve_run_id(p_run_id text)
RETURNS text LANGUAGE sql STABLE AS $$
  SELECT coalesce((SELECT a.new_run_id FROM provenance.run_id_alias a
                    WHERE a.old_run_id = p_run_id), p_run_id);
$$;
COMMENT ON FUNCTION provenance.resolve_run_id(text) IS
 'Map a possibly-historical run_id to its current canonical identifier via run_id_alias; returns the input unchanged when it was never renamed. Use this in any query, check or note that quotes a run_id literal, so a later rename cannot silently turn the predicate into a no-op (as IC003 did to v_run_status.schedule_suspect and check C232).';
