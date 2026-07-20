-- =====================================================================
-- 23_forecast_covariate.sql
--
-- ADJUDICATION.md §2.9 (covariate-mode forecast ingest) and §2.8 (EWMA
-- calibration coverage), applied 2026-07-20.
--
-- WHAT §2.9 ACTUALLY WAS.  The ledger described the gap as "the
-- covariate-mode POINT partitions at 1s/30s/45s/1min were never
-- ingested", implying cov-mode 15 s rows were present.  That reading was
-- stale.  At the time of this pass provenance.forecast held
-- ZERO rows with mode = 'cov' at ANY resolution:
--
--     select count(*) from provenance.forecast where mode='cov';  -- 0
--
-- The rows the ledger mistook for cov-mode 15 s data are the NULL-mode
-- rows, which are two entirely different post-manuscript families:
-- the 12 *_expctx.parquet expanding-context reforecasts (40,308 each)
-- and the 3 ewma_cal_*.parquet calibration variants (38,388 each).
--
-- ROOT CAUSE.  Nothing was wrong with load_forecast.  The two covariate
-- parquets are the only forecast artifacts stored SPLIT AND GZIPPED --
-- {chronos,toto}_covariates.parquet.gz.part{00,01} -- by commit 925b399
-- ("compress large result artifacts to keep the repo LFS-free"), and the
-- loader globs '*.parquet', which cannot match '*.parquet.gz.part00'.
-- The archive was complete; only the reassembly step was missing.  The
-- reassembled files are gitignored (.gitignore:85-86), i.e. reassembly
-- on demand is the intended workflow, mirroring _ensure_covariates() in
-- figuras_new/predictors.py:78-85.
--
-- No loader change was required and none was made.  Reassembling the two
-- files at their canonical paths and re-running `main.py --only K10`
-- ingested exactly 5,269,200 rows and touched no other file; a second
-- run loaded 0 rows (idempotent, sha256 in ingest_log).
--
-- RECONCILIATION.  provenance.forecast now holds 22,003,500 rows and
-- reconciles to the on-disk archive FILE BY FILE: 41 forecast parquets on
-- disk, 41 source_tag groups in the DB, zero count mismatches, both sides
-- totalling 22,003,500.
--
-- CONSEQUENCE FOR intro.tex:431 ("21.4 million archived rows"), the
-- question R29 left open as Q1.  The thesis-run forecast corpus is
-- mode IN ('uni','cov') -- that is, every row this thesis reports on,
-- excluding the two families that postdate the manuscript (the _expctx
-- reforecasts and the ewma_cal_* variants, both written 2026-07-19):
--
--     all files                          22,003,500
--     excl ewma_cal_*                    21,888,336
--     excl ewma_cal_* and *_expctx       21,404,640
--     mode in ('uni','cov')              21,404,640   <-- 21.4 M, exact
--
-- The last two rules coincide, and they land on 21,404,640 = "21.4
-- million" exactly, not by rounding slack.  intro.tex:431 is CONFIRMED
-- in-store for the first time and needs no weakening.  Note this refutes
-- the ledger's own 21,565,872 figure for the same exclusion rule.
--
-- WHY THIS WAS NOT A COSMETIC GAP.  Check C006 recomputes
-- forecast_metrics WAPE/MAE/RMSE from raw forecast rows and joins on
-- rc.md = coalesce(m.mode,'~') -- it is mode-aware.  With no cov rows in
-- forecast, all 360 cov-mode metric cells at span='full', h IN (1,4,12)
-- failed to join and were silently dropped: C006 verified 1,080 cells
-- while reporting as a full check.  It now verifies all 1,440, and all
-- 1,440 pass.  A vacuously-passing check has been made honest WITHOUT
-- touching its tolerance or its population predicate.
--
-- §2.8 REQUIRED NO INGEST.  provenance.ewma_cal_coverage already carries
-- all four schemes x both splits, matching ewma_cal_manifest.json to full
-- stored precision (eval: add 0.9012529, mult 0.8783340, wsc 0.8765972,
-- native 0.9288860), and the table and all five columns are already
-- COMMENTed.  The ledger's "the coverage artifact does not [exist]" is
-- stale.  What was NOT recorded anywhere is the fact that makes coverage
-- the ONLY discriminator among the arms; C010 below records it.
--
-- Depends on: 01_schema.sql, 09_predictors_ewma.sql, 21_checks.sql.
-- Every statement is idempotent.
-- =====================================================================


-- ---------------------------------------------------------------------
-- PART A — refresh comments that the ingest made stale
-- ---------------------------------------------------------------------

COMMENT ON TABLE provenance.forecast IS
'K10 RAW: rolling-origin forecast outputs, LIST-partitioned by model. '
'22,003,500 rows as of the 2026-07-20 covariate ingest (was ~16.7 M; the '
'5,269,200 mode=''cov'' rows arrived then -- see schema/23_forecast_covariate.sql). '
'y_true vs point + 9 quantile heads p10..p90; forecast_metrics is the scored summary. '
'mode: ''uni'' (each variate from its own history) and ''cov'' (chronos: other 3 '
'variates as past-only covariates; toto: all 4 jointly via variate-axis attention) '
'together form the 21,404,640-row thesis-run corpus quoted at intro.tex:431. '
'mode IS NULL marks the two post-manuscript families -- *_expctx expanding-context '
'reforecasts and ewma_cal_* calibration variants -- which are NOT thesis-run data.';

-- The NULL-source_tag rows the old comment warned about are gone: every
-- one of the 22,003,500 rows is now attributable to its source parquet.
COMMENT ON COLUMN provenance.forecast.source_tag IS
'Absolute path of the source parquet these rows were loaded from. provenance.forecast '
'has no run_id/source_path, so this is the ONLY identity of a load unit: it distinguishes '
'parquets that share (model, mode, variate) -- notably the EWMA calibration variants -- '
'and it is the scope of load_forecast''s idempotent delete. As of 2026-07-20 it is '
'non-NULL on every row (41 distinct source files), so it is a total key: the DB '
'reconciles to the on-disk archive file by file through this column.';

COMMENT ON COLUMN provenance.forecast.mode IS
'Forecast conditioning: ''uni'' univariate, ''cov'' covariate-conditioned, NULL for the '
'post-manuscript *_expctx and ewma_cal_* families. Filter mode IN (''uni'',''cov'') to get '
'the thesis-run corpus; do NOT use count(*) over the whole table as the archived-row figure.';


-- ---------------------------------------------------------------------
-- PART B — new checks
-- ---------------------------------------------------------------------

-- C009: the cov-mode ingest matches the archived parquets exactly.
-- These 10 counts are read from the two reassembled parquets with pyarrow
-- (chronos 2,593,680 + toto 2,675,520 = 5,269,200) and are the same
-- numbers ADJUDICATION §2.9 quotes from the on-disk archive. If a future
-- reload drops or double-loads a partition this fails loudly.
INSERT INTO provenance.check_definition
  (check_id, title, severity, est_cost, sql_text, expected, note)
VALUES ('C009',
 'covariate-mode forecast ingest matches the on-disk archive partition by partition',
 'error', 'cheap',
 $chk$
 WITH want(model, resolution, n) AS (VALUES
     ('chronos','1s',2386896),('chronos','15s',128976),('chronos','30s',48336),
     ('chronos','45s',21456),('chronos','1min',8016),
     ('toto','1s',2403264),('toto','15s',145344),('toto','30s',64704),
     ('toto','45s',37824),('toto','1min',24384)),
      got AS (SELECT model, resolution, count(*)::int n
                FROM provenance.forecast WHERE mode='cov' GROUP BY 1,2)
 SELECT count(*) FILTER (WHERE w.n IS DISTINCT FROM g.n) = 0,
        format('%s of %s cov-mode (model,resolution) partitions disagree with the archive; total %s of expected 5269200',
               count(*) FILTER (WHERE w.n IS DISTINCT FROM g.n), count(*),
               coalesce(sum(g.n),0))
   FROM want w FULL JOIN got g USING (model, resolution)
 $chk$,
 'All 10 cov-mode partitions match the archived parquet counts; total 5,269,200.',
 'Added 2026-07-20 with the ADJUDICATION §2.9 ingest. Guards the gap that made C006 '
 'vacuous: with cov rows absent, C006''s mode-aware join silently dropped 360 of its '
 '1,440 metric cells while still reporting as a full check.')
ON CONFLICT (check_id) DO UPDATE
  SET title=EXCLUDED.title, severity=EXCLUDED.severity, est_cost=EXCLUDED.est_cost,
      sql_text=EXCLUDED.sql_text, expected=EXCLUDED.expected, note=EXCLUDED.note;


-- C010: ADJUDICATION §2.8 -- the three EWMA calibration arms are
-- POINT-IDENTICAL and differ ONLY in p90. This is why ewma_cal_coverage
-- is the only table that can discriminate them: every point-forecast
-- error metric (WAPE/MAE/RMSE) is identical across add/mult/wsc by
-- construction, since conformal calibration rescales the interval and
-- never touches the point forecast. Verified 38,388 rows, 0 point
-- differences, 38,388 p90 differences on both comparisons.
INSERT INTO provenance.check_definition
  (check_id, title, severity, est_cost, sql_text, expected, note)
VALUES ('C010',
 'EWMA calibration arms are point-identical and differ only in p90',
 'error', 'cheap',
 $chk$
 WITH a AS (SELECT origin,h,variate,point,p90 FROM provenance.forecast
             WHERE source_tag LIKE '%/ewma_cal_add_images.parquet'),
      m AS (SELECT origin,h,variate,point,p90 FROM provenance.forecast
             WHERE source_tag LIKE '%/ewma_cal_mult_images.parquet'),
      w AS (SELECT origin,h,variate,point,p90 FROM provenance.forecast
             WHERE source_tag LIKE '%/ewma_cal_wsc_images.parquet')
 SELECT count(*) > 0
        AND count(*) FILTER (WHERE a.point IS DISTINCT FROM m.point
                                OR a.point IS DISTINCT FROM w.point) = 0
        AND count(*) FILTER (WHERE a.p90 IS NOT DISTINCT FROM m.p90) = 0
        AND count(*) FILTER (WHERE a.p90 IS NOT DISTINCT FROM w.p90) = 0,
        format('%s aligned rows; point disagreements %s (want 0); p90 ties add~mult %s add~wsc %s (want 0)',
               count(*),
               count(*) FILTER (WHERE a.point IS DISTINCT FROM m.point
                                   OR a.point IS DISTINCT FROM w.point),
               count(*) FILTER (WHERE a.p90 IS NOT DISTINCT FROM m.p90),
               count(*) FILTER (WHERE a.p90 IS NOT DISTINCT FROM w.p90))
   FROM a JOIN m USING (origin,h,variate) JOIN w USING (origin,h,variate)
 $chk$,
 'All 38,388 aligned rows share an identical point forecast; every p90 differs across all three arms.',
 'Added 2026-07-20 for ADJUDICATION §2.8. The substantive content of §2.8: because the '
 'arms are point-identical, NO point-error metric can rank them, so ewma_cal_coverage is '
 'the only evidence that separates add (eval 0.9013, holds nominal) from mult (0.8783) and '
 'wsc (0.8766, both degrade out-of-sample). closedloop.tex:218''s 0.88-0.90 band is the '
 'mult/wsc/add eval spread at its own precision.')
ON CONFLICT (check_id) DO UPDATE
  SET title=EXCLUDED.title, severity=EXCLUDED.severity, est_cost=EXCLUDED.est_cost,
      sql_text=EXCLUDED.sql_text, expected=EXCLUDED.expected, note=EXCLUDED.note;


-- ---------------------------------------------------------------------
-- PART C — a named view for the thesis-run corpus, so intro.tex:431 has
-- a single canonical definition rather than an ad-hoc WHERE clause.
-- ---------------------------------------------------------------------

CREATE OR REPLACE VIEW provenance.v_forecast_thesis_corpus AS
  SELECT * FROM provenance.forecast WHERE mode IN ('uni','cov');

COMMENT ON VIEW provenance.v_forecast_thesis_corpus IS
'The forecast rows this thesis reports on: mode IN (''uni'',''cov''), i.e. provenance.forecast '
'minus the two post-manuscript families (*_expctx reforecasts, ewma_cal_* calibration variants). '
'count(*) = 21,404,640, which is exactly the "21.4 million archived rows" of intro.tex:431. '
'Use this view for any archived-row claim; count(*) over the base table (22,003,500) '
'over-counts by including artifacts written after the manuscript.';
