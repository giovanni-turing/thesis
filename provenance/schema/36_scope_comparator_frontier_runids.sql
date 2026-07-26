-- 36_scope_comparator_frontier_runids.sql -- rename the 313 pre-mapping 'misc:*' runs of
-- the decisive comparator-frontier experiment (shortening plan v3 section 8.2, commit
-- 4babe1c) to their scoped family run_ids (2026-07-26). Companion to loader/runid.py
-- gaining ("/comparator_frontier/", "comparator_frontier", True): the loader selftest
-- reported 725 files under simulation/results/comparator_frontier/{adversarial,calib,
-- checks,eval,eval_family} mapping to experiment 'misc' (selftest B), and the DB check
-- C306 reported the misc default partition growing to 313 runs.
--
-- Structure of this file follows 32_scope_misc_runids.sql: copy -> repoint FK children ->
-- fix ingest_log -> delete old, in one transaction. Idempotent: the JOIN on the old ids
-- matches nothing on a second run.
--
-- New id derivation (verified collision-free over all 313 rows, 2026-07-26):
--   old run_id  = 'misc:' || <stem>
--   source_path = .../comparator_frontier/<seg>/<stem><suffix>,  <seg> in
--                 {adversarial, calib, checks, eval, eval_family}, depth always 2 and
--                 never an artifact-by-kind segment, so runid.run_id_of() yields
--   new run_id  = 'comparator_frontier:' || <seg> || ':' || <stem>
-- which is exactly what the expression below builds; 313 old ids -> 313 distinct new ids.
BEGIN;

CREATE TEMP TABLE _mig(old_id text PRIMARY KEY, new_id text, new_exp text) ON COMMIT DROP;

INSERT INTO _mig(old_id, new_id, new_exp)
SELECT r.run_id,
       'comparator_frontier:'
         || split_part(split_part(r.source_path, '/comparator_frontier/', 2), '/', 1)
         || ':' || substr(r.run_id, 6),
       'comparator_frontier'
FROM provenance.runs r
WHERE r.experiment = 'misc'
  AND r.run_id LIKE 'misc:%'
  AND r.source_path LIKE '%/comparator_frontier/%';

-- fail closed rather than half-migrate: every misc row must be a comparator_frontier row,
-- and the derived ids must stay injective.
DO $$
DECLARE n_mig bigint; n_misc bigint; n_new bigint;
BEGIN
  SELECT count(*) INTO n_mig FROM _mig;
  SELECT count(*) INTO n_misc FROM provenance.runs WHERE experiment = 'misc';
  SELECT count(DISTINCT new_id) INTO n_new FROM _mig;
  IF n_mig <> n_misc THEN
    RAISE EXCEPTION 'misc partition holds % rows but only % are comparator_frontier; '
                    'register the remaining families in loader/runid.py first',
                    n_misc, n_mig;
  END IF;
  IF n_new <> n_mig THEN
    RAISE EXCEPTION 'derived run_ids are not injective: % rows -> % ids', n_mig, n_new;
  END IF;
  RAISE NOTICE '36_scope_comparator_frontier_runids: rescoping % run(s)', n_mig;
END $$;

-- 1. copy runs rows under the new ids (all other columns unchanged)
INSERT INTO provenance.runs
SELECT (jsonb_populate_record(NULL::provenance.runs,
        to_jsonb(r) || jsonb_build_object('run_id', m.new_id, 'experiment', m.new_exp))).*
FROM provenance.runs r JOIN _mig m ON r.run_id = m.old_id;

-- 2. repoint every FK child (generic over the catalog; NOTICE per touched table)
DO $$
DECLARE c record; n bigint;
BEGIN
  FOR c IN
    SELECT ct.conrelid::regclass AS tbl, a.attname AS col
    FROM pg_constraint ct
    JOIN pg_attribute a ON a.attrelid = ct.conrelid AND a.attnum = ANY (ct.conkey)
    WHERE ct.confrelid = 'provenance.runs'::regclass AND ct.contype = 'f'
  LOOP
    EXECUTE format('UPDATE %s t SET %I = m.new_id FROM _mig m WHERE t.%I = m.old_id',
                   c.tbl, c.col, c.col);
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n > 0 THEN RAISE NOTICE '%.%: % row(s) repointed', c.tbl, c.col, n; END IF;
  END LOOP;
END $$;

-- 3. bookkeeping references that are not FK-enforced
UPDATE provenance.ingest_log t SET run_id = m.new_id FROM _mig m WHERE t.run_id = m.old_id;
UPDATE provenance.runs t SET supersedes = m.new_id FROM _mig m WHERE t.supersedes = m.old_id;
UPDATE provenance.runs t SET superseded_by = m.new_id FROM _mig m WHERE t.superseded_by = m.old_id;

-- 4. drop the old rows.
--
-- WHY THE RI TRIGGERS ARE SUPPRESSED HERE (differs from 32_scope_misc_runids.sql, which
-- moved 5 rows and could afford the default path). provenance.runs is referenced by ~130
-- FK children totalling ~30 GB, and the eight forecast_<model> tables (2.8 GB each) carry
-- NO index on run_id. A plain DELETE fires one RI probe per (deleted row x FK), i.e.
-- 313 x ~130 = ~40k probes, most of them sequential scans of multi-GB tables: measured at
-- >7 minutes without finishing the first pass, projected in hours. Step 2 above is
-- exhaustive over pg_constraint, so by the time this runs no child row can still hold an
-- old id -- referential integrity is established by construction, not by the trigger. The
-- assertion below re-proves that on the tables step 2 actually touched before anything is
-- deleted, and the suppression is SET LOCAL (transaction-scoped, reset immediately after).
DO $$
DECLARE c record; n bigint; bad bigint; touched int := 0;
BEGIN
  FOR c IN
    SELECT ct.conrelid::regclass AS tbl, a.attname AS col
    FROM pg_constraint ct
    JOIN pg_attribute a ON a.attrelid = ct.conrelid AND a.attnum = ANY (ct.conkey)
    WHERE ct.confrelid = 'provenance.runs'::regclass AND ct.contype = 'f'
  LOOP
    EXECUTE format('SELECT count(*) FROM %s t JOIN _mig m ON t.%I = m.old_id',
                   c.tbl, c.col) INTO bad;
    IF bad > 0 THEN
      RAISE EXCEPTION '%.% still holds % row(s) pointing at a pre-rescope run_id',
                      c.tbl, c.col, bad;
    END IF;
    touched := touched + 1;
  END LOOP;
  RAISE NOTICE '36_scope_comparator_frontier_runids: % FK child column(s) verified clean',
               touched;
END $$;

SET LOCAL session_replication_role = replica;
DELETE FROM provenance.runs r USING _mig m WHERE r.run_id = m.old_id;
SET LOCAL session_replication_role = DEFAULT;

COMMIT;
