-- 37_composed_fill_partitions_and_scope.sql -- land the composed-coverage fill campaign
-- (2026-07-26, "no economy" directive; 9 request-linked composed cells for the static
-- arms, the calm day and the full trace) as a first-class experiment family.
--
-- WHAT WENT WRONG AND WHY THIS FILE EXISTS. The campaign's encoder-side artifacts were
-- ingested at 2026-07-27 01:13 UTC, two minutes BEFORE loader/runid.py gained
-- ("/composed_fill/", "composed_fill", True). Ten runs therefore landed as 'misc:<stem>'
-- and their raw rows in the *_default partitions; the two planner cells ingested at 01:27
-- carried the correct 'composed_fill:' ids but still landed in *_default because no
-- partition existed. Post-ingest the store reported two regressions against the a2854e0
-- snapshot: C306 (10 runs under experiment = misc) and C601 (default-partition rows --
-- composed=190779 llm=367299 encoder_series=134156).
--
-- Structure follows 36_scope_comparator_frontier_runids.sql (copy -> repoint FK children
-- -> fix ingest_log -> delete old), with one addition it did not need: comparator_frontier
-- has no rows in the partitioned raw tables, this family has ~692k. A partition cannot be
-- attached while the DEFAULT partition holds rows that would belong to it, so part 5
-- drains, attaches, and refills, in that order.
--
-- Idempotent: the JOIN on the old ids matches nothing on a second run, the partition
-- creations are IF NOT EXISTS, and the drain/refill selects an empty set once done.
--
-- New id derivation (verified against loader/runid.run_id_of over all 31 files):
--   old run_id  = 'misc:' || <stem>;  files sit directly under composed_fill/ (depth 0,
--   no artifact-by-kind segment), so the scoped mapping yields
--   new run_id  = 'composed_fill:' || <stem>            (10 old ids -> 10 distinct new ids)
BEGIN;

DROP TABLE IF EXISTS pg_temp._mig;
CREATE TEMP TABLE _mig(old_id text PRIMARY KEY, new_id text, new_exp text) ON COMMIT DROP;

INSERT INTO _mig(old_id, new_id, new_exp)
SELECT r.run_id, 'composed_fill:' || substr(r.run_id, 6), 'composed_fill'
FROM provenance.runs r
WHERE r.experiment = 'misc'
  AND r.run_id LIKE 'misc:%'
  AND r.source_path LIKE '%/composed_fill/%';

-- fail closed rather than half-migrate: every misc row must be a composed_fill row, and
-- the derived ids must stay injective and not collide with ids already present.
DO $$
DECLARE n_mig bigint; n_misc bigint; n_new bigint; n_clash bigint;
BEGIN
  SELECT count(*) INTO n_mig FROM _mig;
  SELECT count(*) INTO n_misc FROM provenance.runs WHERE experiment = 'misc';
  SELECT count(DISTINCT new_id) INTO n_new FROM _mig;
  SELECT count(*) INTO n_clash FROM _mig m JOIN provenance.runs r ON r.run_id = m.new_id;
  IF n_mig <> n_misc THEN
    RAISE EXCEPTION 'misc partition holds % rows but only % are composed_fill; '
                    'register the remaining families in loader/runid.py first',
                    n_misc, n_mig;
  END IF;
  IF n_new <> n_mig THEN
    RAISE EXCEPTION 'derived run_ids are not injective: % rows -> % ids', n_mig, n_new;
  END IF;
  IF n_clash > 0 THEN
    RAISE EXCEPTION '% derived run_id(s) already exist in provenance.runs', n_clash;
  END IF;
  RAISE NOTICE '37_composed_fill: rescoping % run(s)', n_mig;
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
UPDATE provenance.runs t SET supersedes    = m.new_id FROM _mig m WHERE t.supersedes    = m.old_id;
UPDATE provenance.runs t SET superseded_by = m.new_id FROM _mig m WHERE t.superseded_by = m.old_id;

-- 4. prove no child still points at a pre-rescope id, then drop the old rows.
--    RI triggers are suppressed for the same reason as in 36: step 2 is exhaustive over
--    pg_constraint, so integrity holds by construction, and a plain DELETE would fire
--    10 x 125 RI probes across ~30 GB of unindexed children.
DO $$
DECLARE c record; bad bigint; touched int := 0;
BEGIN
  FOR c IN
    SELECT ct.conrelid::regclass AS tbl, a.attname AS col
    FROM pg_constraint ct
    JOIN pg_attribute a ON a.attrelid = ct.conrelid AND a.attnum = ANY (ct.conkey)
    WHERE ct.confrelid = 'provenance.runs'::regclass AND ct.contype = 'f'
  LOOP
    EXECUTE format('SELECT count(*) FROM %s t JOIN _mig m ON t.%I = m.old_id', c.tbl, c.col)
      INTO bad;
    IF bad > 0 THEN
      RAISE EXCEPTION '%.% still holds % row(s) pointing at a pre-rescope run_id',
                      c.tbl, c.col, bad;
    END IF;
    touched := touched + 1;
  END LOOP;
  RAISE NOTICE '37_composed_fill: % FK child column(s) verified clean', touched;
END $$;

SET LOCAL session_replication_role = replica;
DELETE FROM provenance.runs r USING _mig m WHERE r.run_id = m.old_id;
SET LOCAL session_replication_role = DEFAULT;

-- 5. partitions. Drain the default partition of every composed_fill row, attach the
--    dedicated partition, refill through the parent so the rows route to it. Draining
--    FIRST is not optional: ATTACH/CREATE ... FOR VALUES IN ('composed_fill') is rejected
--    while the DEFAULT partition still holds a row that would belong to the new one.
--    The experiment column is rewritten in the temp copy, not in place, so no row is ever
--    updated across a partition boundary.
-- D27 FIX (reviewer 2026-07-26, thread D27): the original delete went through the
-- partitioned PARENT, so a second run -- with the default already drained -- would
-- have deleted every row in the dedicated partition and restored nothing (692,234
-- rows). The delete is now scoped to the *_default* child, the whole step is a
-- guarded no-op when the default holds no composed_fill rows, and the
-- post-condition asserts dedicated-partition preservation.
DO $$
-- D33 (2026-07-27): clean-start order restored -- DRAIN the default child BEFORE
-- attaching the dedicated partition (attach is rejected while the default holds
-- rows belonging to the new partition, SQLSTATE 23514); delete stays scoped to
-- the default child (D27); pre/post preservation asserted in every branch.
DECLARE t text; n bigint; pre_dedicated bigint; post_dedicated bigint; part_exists boolean;
        parts text[] := ARRAY['composed_request','llm_request','encoder_series'];
BEGIN
  FOREACH t IN ARRAY parts LOOP
    EXECUTE format('SELECT count(*) FROM provenance.%I WHERE run_id LIKE %L',
                   t||'_default', 'composed_fill:%') INTO n;
    EXECUTE format('SELECT to_regclass(%L) IS NOT NULL', 'provenance.'||t||'_composed_fill')
      INTO part_exists;
    IF part_exists THEN
      EXECUTE format('SELECT count(*) FROM provenance.%I', t||'_composed_fill') INTO pre_dedicated;
    ELSE
      pre_dedicated := 0;
    END IF;
    IF n = 0 THEN
      IF NOT part_exists THEN
        EXECUTE format('CREATE TABLE provenance.%I PARTITION OF provenance.%I '
                       'FOR VALUES IN (%L)', t||'_composed_fill', t, 'composed_fill');
      END IF;
      -- D37: a same-named relation is NOT the required partition; assert the exact
      -- pg_inherits edge to THIS parent and the intended list bound, in this branch too.
      PERFORM 1 FROM pg_inherits i
        WHERE i.inhrelid = ('provenance.'||t||'_composed_fill')::regclass
          AND i.inhparent = ('provenance.'||t)::regclass;
      IF NOT FOUND THEN
        RAISE EXCEPTION '37/D37: provenance.%_composed_fill exists but is NOT a partition of provenance.%', t, t;
      END IF;
      IF pg_get_expr(c.relpartbound, c.oid) IS DISTINCT FROM 'FOR VALUES IN (''composed_fill'')' FROM pg_class c
         WHERE c.oid = ('provenance.'||t||'_composed_fill')::regclass THEN
        RAISE EXCEPTION '37/D37: provenance.%_composed_fill partition bound is not exactly FOR VALUES IN (composed_fill)', t;
      END IF;
      RAISE NOTICE '37_composed_fill: %_default holds no composed_fill rows -- step is a no-op (partition %, edge+bound verified)',
        t, CASE WHEN part_exists THEN 'existed' ELSE 'created' END;
      CONTINUE;
    END IF;
    EXECUTE format('CREATE TEMP TABLE pg_temp._cf37 AS SELECT * FROM provenance.%I WHERE run_id LIKE %L',
                   t||'_default', 'composed_fill:%');
    EXECUTE 'UPDATE pg_temp._cf37 SET experiment = ''composed_fill''';
    -- drain FIRST, scoped to the DEFAULT CHILD only (D27)
    EXECUTE format('DELETE FROM provenance.%I WHERE run_id LIKE %L', t||'_default', 'composed_fill:%');
    IF NOT part_exists THEN
      EXECUTE format('CREATE TABLE provenance.%I PARTITION OF provenance.%I '
                     'FOR VALUES IN (%L)', t||'_composed_fill', t, 'composed_fill');
    END IF;
    -- D37: same exact-edge + bound assertion on the relocation branch
    PERFORM 1 FROM pg_inherits i
      WHERE i.inhrelid = ('provenance.'||t||'_composed_fill')::regclass
        AND i.inhparent = ('provenance.'||t)::regclass;
    IF NOT FOUND THEN
      RAISE EXCEPTION '37/D37: provenance.%_composed_fill is NOT a partition of provenance.%', t, t;
    END IF;
    IF pg_get_expr(c.relpartbound, c.oid) IS DISTINCT FROM 'FOR VALUES IN (''composed_fill'')' FROM pg_class c
       WHERE c.oid = ('provenance.'||t||'_composed_fill')::regclass THEN
      RAISE EXCEPTION '37/D37: %_composed_fill relocation-branch bound is not exactly FOR VALUES IN (composed_fill)', t;
    END IF;
    EXECUTE format('INSERT INTO provenance.%I SELECT * FROM pg_temp._cf37', t);
    EXECUTE format('SELECT count(*) FROM provenance.%I', t||'_composed_fill') INTO post_dedicated;
    IF post_dedicated <> pre_dedicated + n THEN
      RAISE EXCEPTION '37_composed_fill: %_composed_fill preservation violated (pre=% moved=% post=%)',
        t, pre_dedicated, n, post_dedicated;
    END IF;
    RAISE NOTICE '37_composed_fill: % row(s) relocated into %_composed_fill (now %)', n, t, post_dedicated;
    EXECUTE 'DROP TABLE pg_temp._cf37';
  END LOOP;
END $$;

-- 6. record the rescope the way IC003 recorded its own (32/36 skipped this; there is no
--    reason to, and run_id_alias is what makes an old id in a notebook still resolvable).
INSERT INTO provenance.ingest_correction
  (correction_id, table_name, field, original_value, corrected_value, n_rows, source_path,
   evidence, rationale)
VALUES ('IC037', 'runs', 'experiment/run_id', 'misc:<stem>', 'composed_fill:<stem>', 10,
        '/home/gio/tese/simulation/results/composed_fill/',
        'loader/selftest.py test B reported these files under experiment misc; check C306 '
        'reported 10 runs under misc and C601 reported 692,234 rows in the *_default '
        'partitions, both regressions against the a2854e0 snapshot.',
        'The composed-coverage fill campaign (2026-07-26 "no economy" directive: 9 '
        'request-linked composed cells -- static C=8 on burst1/3/4/5 and the calm day, '
        'forecast-p90 and reactive on the calm day, and the full-trace static C=8 / '
        'reactive pair) was ingested at 01:13 UTC, before loader/runid.py mapped '
        '/composed_fill/. Ten runs fell through to the misc catch-all. This correction '
        'renames them, attaches composed_request/llm_request/encoder_series partitions for '
        'the family, and relocates the raw rows out of the default partitions.')
ON CONFLICT (correction_id) DO NOTHING;

INSERT INTO provenance.run_id_alias (old_run_id, new_run_id, correction_id)
SELECT old_id, new_id, 'IC037' FROM _mig
ON CONFLICT (old_run_id) DO NOTHING;

-- 7. post-conditions: the two regressions this file exists to close.
DO $$
DECLARE n_misc bigint; a bigint; b bigint; c bigint;
BEGIN
  SELECT count(*) INTO n_misc FROM provenance.runs WHERE experiment = 'misc';
  SELECT count(*) INTO a FROM provenance.composed_request_default;
  SELECT count(*) INTO b FROM provenance.llm_request_default;
  SELECT count(*) INTO c FROM provenance.encoder_series_default;
  IF n_misc <> 0 THEN RAISE EXCEPTION 'C306 would still fail: % runs under misc', n_misc; END IF;
  IF (a+b+c) <> 0 THEN
    RAISE EXCEPTION 'C601 would still fail: default rows composed=% llm=% encoder_series=%', a, b, c;
  END IF;
  -- D27: dedicated partitions must be POPULATED (a rerun that emptied them must abort)
  SELECT count(*) INTO a FROM provenance.composed_request_composed_fill;
  SELECT count(*) INTO b FROM provenance.llm_request_composed_fill;
  SELECT count(*) INTO c FROM provenance.encoder_series_composed_fill;
  IF a = 0 OR b = 0 OR c = 0 THEN
    RAISE EXCEPTION 'D27 preservation post-condition: dedicated partition empty (composed=% llm=% enc=%)', a, b, c;
  END IF;
  -- D37 final: the populated relations must be TRUE partitions of their parents
  IF (SELECT count(*) FROM pg_inherits i
      WHERE (i.inhrelid, i.inhparent) IN (
        (('provenance.composed_request_composed_fill')::regclass, ('provenance.composed_request')::regclass),
        (('provenance.llm_request_composed_fill')::regclass,      ('provenance.llm_request')::regclass),
        (('provenance.encoder_series_composed_fill')::regclass,   ('provenance.encoder_series')::regclass))) <> 3 THEN
    RAISE EXCEPTION 'D37 post-condition: composed_fill relations are not all true partitions';
  END IF;
  IF (SELECT count(*) FROM pg_class c
      WHERE c.oid IN (('provenance.composed_request_composed_fill')::regclass,
                      ('provenance.llm_request_composed_fill')::regclass,
                      ('provenance.encoder_series_composed_fill')::regclass)
        AND pg_get_expr(c.relpartbound, c.oid) = 'FOR VALUES IN (''composed_fill'')') <> 3 THEN
    RAISE EXCEPTION 'D40/D37 post-condition: a composed_fill child has a non-exact partition bound';
  END IF;
  RAISE NOTICE '37_composed_fill: C306, C601 and D27-preservation post-conditions hold (%/%/% rows)', a, b, c;
END $$;

COMMIT;
