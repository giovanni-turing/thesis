-- =====================================================================
-- 24_config_column_checks.sql -- regression probes for ADJUDICATION §2.12
--
-- Registered into provenance.check_definition, so they run under
-- check_all(). Contract (from 21_checks.sql): sql_text returns exactly
-- one row of (passed boolean, detail text).
--
-- These guard the property that makes the §2.12 columns worth having:
-- every value is TRACEABLE. A configuration column that quietly acquires
-- a value with no evidence behind it is worse than the NULL it replaced,
-- because a later audit will condition on it and believe it.
-- =====================================================================
\set ON_ERROR_STOP on
SET search_path = provenance, public;

-- ---------------------------------------------------------------------
-- C410 -- no orphan provenance tags
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C410',
 'every config_provenance key names a column that is actually populated',
 'error',
 $q$
 WITH k AS (
   SELECT r.run_id, e.key, to_jsonb(r) ->> e.key AS val
     FROM provenance.runs r,
          LATERAL jsonb_each_text(coalesce(r.config_provenance, '{}'::jsonb)) e
 )
 SELECT count(*) = 0 AS passed,
        coalesce(string_agg(format('%s.%s tagged but NULL', run_id, key), '; '),
                 format('OK: %s provenance tags, all naming a populated column',
                        (SELECT count(*) FROM k))) AS detail
   FROM k WHERE val IS NULL
 $q$,
 'passed = true',
 'cheap',
 'A config_provenance entry claims "this column of this run was backfilled, here is the '
 'evidence". If the column is NULL the claim is false and the evidence map is lying about '
 'what it covers -- which would silently corrupt v_config_coverage''s by-evidence counts. '
 'Fires if a backfilled value is later cleared without clearing its tag.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C411 -- the two runtime_build writers cannot disagree
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C411',
 'runtime_build and runtime_version agree, and the vocabulary is closed',
 'error',
 $q$
 SELECT count(*) = 0 AS passed,
        coalesce(string_agg(format('%s: build=%s version=%s', run_id,
                                   coalesce(runtime_build,'NULL'),
                                   coalesce(runtime_version,'NULL')), '; '),
                 format('OK: source=%s wheel=%s null=%s',
                    (SELECT count(*) FROM provenance.runs WHERE runtime_build='source'),
                    (SELECT count(*) FROM provenance.runs WHERE runtime_build='wheel'),
                    (SELECT count(*) FROM provenance.runs WHERE runtime_build IS NULL))
                ) AS detail
   FROM provenance.runs
  WHERE (runtime_build IS NOT NULL AND runtime_build NOT IN ('source','wheel'))
     OR (runtime_build = 'source' AND runtime_version IS DISTINCT FROM '1.3.0')
     OR (runtime_build = 'wheel'  AND runtime_version IS DISTINCT FROM '1.2.1')
     OR (runtime_build IS NULL AND runtime_version IS NOT NULL)
 $q$,
 'passed = true',
 'cheap',
 'TWO loaders write runtime_build: K34 (load_config_backfill, §2.12) and K41 '
 '(load_runtime_build, §2.2). That is safe only while they read the SAME log marker '
 '("Using Lineage inactive backend (Tick)" = 1.3.0 source build, the bare line = 1.2.1 '
 'wheel), write the SAME vocabulary, and both COALESCE instead of overwriting. This check '
 'is what makes that invariant enforced rather than merely intended: if either pass is '
 'edited to use a different probe or a different token, the mapping breaks here. Backs '
 'related.tex:168, tese.tex:256, apendice_ecosystem.tex:125 and apendice.tex tab:ap-env.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C412 -- model_checkpoint is never confused with the forecast model
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C412',
 'model_checkpoint holds served checkpoints only, never a forecast model name',
 'error',
 $q$
 -- The OK detail must be counted over ALL runs, not over the (empty) offending
 -- set, or a passing check reports "0 runs carry a checkpoint" and misleads.
 SELECT count(*) = 0 AS passed,
        coalesce(string_agg(format('%s: model_checkpoint=%s', run_id, model_checkpoint), '; '),
                 format('OK: %s runs carry a checkpoint, %s distinct, none a forecast name',
                        (SELECT count(*) FROM provenance.runs
                          WHERE model_checkpoint IS NOT NULL),
                        (SELECT count(DISTINCT model_checkpoint) FROM provenance.runs
                          WHERE model_checkpoint IS NOT NULL))) AS detail
   FROM provenance.runs
  WHERE model_checkpoint IS NOT NULL
    AND (model_checkpoint IN ('chronos','toto','timesfm','ewma','naive','holt_winters',
                              'prophet','arima','kalman')
         OR position('/' in model_checkpoint) = 0)
 $q$,
 'passed = true',
 'cheap',
 'runs.model names the FORECAST model; runs.model_checkpoint names the SERVED LLM. The '
 'overload is exactly why no query could previously select the 32B arm, so the separation '
 'is worth enforcing. A served checkpoint is a HuggingFace id and always contains "/"; a '
 'forecast model name never does. Fires if a loader ever writes one into the other.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C414 -- run-level arrival_speedup never contradicts the summary copy
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C414',
 'runs.arrival_speedup agrees with encoder_run_summary.arrival_speedup',
 'error',
 $q$
 SELECT count(*) FILTER (WHERE bad) = 0 AS passed,
        coalesce(string_agg(format('%s: runs=%s summary=%s', run_id, a, b), '; ')
                   FILTER (WHERE bad),
                 format('OK: %s runs carry a speedup, %s also have an encoder summary, '
                        'all matching', (SELECT count(*) FROM provenance.runs
                                          WHERE arrival_speedup IS NOT NULL),
                        count(*))) AS detail
   FROM (SELECT r.run_id, r.arrival_speedup a, e.arrival_speedup b,
                r.arrival_speedup IS DISTINCT FROM e.arrival_speedup AS bad
           FROM provenance.runs r
           JOIN provenance.encoder_run_summary e USING (run_id)
          WHERE r.arrival_speedup IS NOT NULL AND e.arrival_speedup IS NOT NULL) q
 $q$,
 'passed = true',
 'cheap',
 'The offered-rate multiplier now lives in two places: runs.arrival_speedup (added so the '
 'language-only g3_32b defence track can be conditioned on load at all) and '
 'encoder_run_summary.arrival_speedup (ingested per encoder stats file). Duplication is '
 'only safe while it is checked. If these ever diverge, every load-conditioned comparison '
 'that mixes the two tracks is quietly comparing different offered rates. '
 'CURRENTLY VACUOUS, AND SAID SO IN THE DETAIL: the 232 runs carrying runs.arrival_speedup '
 'are all language-pool g3_32b runs, which have no encoder_run_summary row, so the join is '
 'empty and the check passes on zero rows. It is a FORWARD guard, armed the moment a run '
 'carries both. Read its detail, not its boolean -- "0 also have an encoder summary" is the '
 'honest statement of what it has verified so far, which is nothing.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;

-- ---------------------------------------------------------------------
-- C413 -- artifact_commit_sha is never mistaken for commit_sha
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
    (check_id, title, severity, sql_text, expected, est_cost, note)
VALUES (
 'C413',
 'runs.commit_sha stays empty; the archival sha lives in its own column',
 'warn',
 $q$
 -- Counted over ALL runs; the WHERE clause below selects only the offending rows,
 -- so counting inside it would report "0 of 0" on a pass.
 SELECT (SELECT count(*) FROM provenance.runs
          WHERE commit_sha IS NOT NULL AND commit_sha = artifact_commit_sha) = 0 AS passed,
        format('commit_sha populated on %s runs; artifact_commit_sha on %s of %s',
               count(*) FILTER (WHERE commit_sha IS NOT NULL),
               count(*) FILTER (WHERE artifact_commit_sha IS NOT NULL),
               count(*)) AS detail
   FROM provenance.runs
 $q$,
 'passed = true',
 'cheap',
 'commit_sha means "the code commit that PRODUCED this run" and is unrecoverable -- no '
 'artifact records it, so it is NULL on every row and §2.12 leaves it that way. '
 'artifact_commit_sha means "the commit at which this run''s artifact is ARCHIVED", '
 'recovered by git log. They answer different questions and only the first supports a '
 'reproduction claim. This check fires if a future pass papers over the unrecoverable gap '
 'by copying the archival sha across -- which would make 1,674 runs look reproducible '
 'when none of them are.'
) ON CONFLICT (check_id) DO UPDATE SET
    title=excluded.title, severity=excluded.severity, sql_text=excluded.sql_text,
    expected=excluded.expected, est_cost=excluded.est_cost, note=excluded.note;
