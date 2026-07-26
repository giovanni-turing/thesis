-- 32_scope_misc_runids.sql -- rename the 5 pre-mapping 'misc:*' runs to their scoped
-- family run_ids (2026-07-26). Companion to loader/runid.py gaining the scoped families
-- encoder_hybrid + lang_qsweep (reframe-thread dirs; loader selftest B unmapped-dir /
-- C run_id-injectivity failures). Copy -> repoint FK children -> fix ingest_log ->
-- delete old, in one transaction. Idempotent: the JOIN on the old ids matches nothing
-- on a second run.
BEGIN;

CREATE TEMP TABLE _mig(old_id text PRIMARY KEY, new_id text, new_exp text) ON COMMIT DROP;
INSERT INTO _mig VALUES
  ('misc:fc_chronos_p50_s8', 'lang_qsweep:perreq:fc_chronos_p50_s8', 'lang_qsweep'),
  ('misc:F6_fc',      'encoder_hybrid:F6_fc',         'encoder_hybrid'),
  ('misc:F6_hybrid',  'encoder_hybrid:F6_hybrid',     'encoder_hybrid'),
  ('misc:F6_re',      'encoder_hybrid:F6_re',         'encoder_hybrid'),
  ('misc:fc_p50',     'encoder_hybrid:combos:fc_p50', 'encoder_hybrid');

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

-- 4. drop the old rows (children already repointed; CASCADE finds none)
DELETE FROM provenance.runs r USING _mig m WHERE r.run_id = m.old_id;

COMMIT;
