-- =====================================================================
-- 25_week_surface_coverage.sql
--
-- ADJUDICATION §2.7 follow-up: the WEEK-SURFACE cells.
--
-- Two gaps, both now closed in provenance.factorial_cell:
--
--   (a) week_matrix (112 target-time cells). sweep_manifest_coverage read
--       cells_week 112 requested / 0 returned. The cells were on disk and
--       their 112 spine rows were loaded (K3+K4, repair3_week_matrix.py);
--       what was missing was the FACTORIAL projection. week_matrix is the
--       only factorial family with no *_results.json -- run_week_matrix.sh
--       deletes the per-request jsonl and keeps only <tag>.jsonl.stats.json
--       -- so loaders.load_factorial, which globs results files, never saw
--       it. Projected by loader/load_week_matrix_cells.py (kind K7w).
--
--   (b) week_surface_issuetime (96 issue-time cells, BOTH the p90 and the
--       p50 half). This file WAS ingested, as K7 with n_rows = 0: its
--       records are flat and carry no "window" key, so loaders._norm_cell
--       rejected every one of the 96 and the loader recorded a clean zero.
--       _norm_cell now understands that shape and takes the window from the
--       explicit _FAMILY_DIMS identity table.
--
-- ACTUATION was resolved by loaders.actuation_of() in both cases -- the
-- explicit artifact-identity table, never a path substring. The substring
-- heuristic is what mislabelled 572 cells (see 24_actuation_correction.sql).
--   week_matrix             -> target-time  (run_week_matrix.sh:5 uses
--                              simulation/forecast_schedule.py; leads
--                              {15,30,45,300}). SUPERSEDED, is_current=false.
--   week_surface_issuetime  -> issue-time   (run_44_week_surface_issuetime.py
--                              uses verification/scripts/forecast_schedule_issuetime.py;
--                              leads {15,30,45,165}). CURRENT.
-- The successor's own docstring states it: "the archived run_week_matrix.sh
-- was target-time at L=300" (run_44_week_surface_issuetime.py:6-7).
--
-- C507 (the two actuations are never pooled) is preserved: the 112
-- target-time runs are demoted to is_current=false, so current_factorial
-- still contains exactly one actuation.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- A  a manifest may point at a DIRECTORY of per-cell artifacts
-- ---------------------------------------------------------------------
-- sweep_manifest.results_path assumed one results file per sweep. week_matrix
-- has 112 -- one stats file per cell -- so cells_week could never carry a
-- results_path and its coverage row was structurally stuck at 0 returned.
-- Recording the directory (and keeping factorial_cell.source_path pointing at
-- the individual stats file, which is the true provenance) fixes that without
-- loosening the exact-path match every other manifest still uses.

ALTER TABLE provenance.sweep_manifest
  ADD COLUMN IF NOT EXISTS results_is_dir boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN provenance.sweep_manifest.results_is_dir IS
  'true when results_path is a DIRECTORY of per-cell artifacts rather than a single '
  'results file (week_matrix writes one <tag>.jsonl.stats.json per cell). Coverage then '
  'matches factorial_cell.source_path by directory prefix instead of by equality. false '
  'for every single-file manifest, which keeps their match exact.';

UPDATE provenance.sweep_manifest
   SET results_path   = '/home/gio/tese/simulation/results/week_matrix',
       results_is_dir = true,
       note = note || ' RESOLVED 2026-07-20: the shortfall was a missing factorial '
                   || 'PROJECTION, not missing data -- week_matrix keeps only per-cell '
                   || '*.jsonl.stats.json (run_week_matrix.sh deletes the jsonl), which '
                   || 'the results-file glob in loaders.load_factorial never matched. All '
                   || '112 cells are now in factorial_cell via loader/'
                   || 'load_week_matrix_cells.py (K7w), actuation=target-time, '
                   || 'is_current=false (superseded by week_surface_issuetime).'
 WHERE manifest_id = 'cells_week';


-- ---------------------------------------------------------------------
-- B  the issue-time week surface, as a manifest
-- ---------------------------------------------------------------------
-- Its design lives in the generator's own MODELS/QUANTILES/RHOS/LEADS lists
-- rather than in a cells_*.jsonl, so manifest_path is the script. cell_ix is
-- the generator's iteration order (run_44_week_surface_issuetime.py:77,
-- `for m in MODELS for q in QUANTILES for r in RHOS for l in LEADS`), which
-- keeps the column's documented meaning -- position in the design -- intact.

INSERT INTO provenance.sweep_manifest
  (manifest_id, manifest_path, actuation, n_cells, generator, results_path,
   results_is_dir, is_current, note)
VALUES
  ('cells_week_surface_issuetime',
   '/home/gio/tese/simulation/run_44_week_surface_issuetime.py',
   'issue-time', 96,
   'simulation/run_44_week_surface_issuetime.py -> verification/scripts/forecast_schedule_issuetime.py -> workload/trace_to_two_pool.py',
   '/home/gio/tese/simulation/results/week_surface_issuetime/week_surface_issuetime_results.json',
   false, true,
   'The issue-time week-scale surface that SUPERSEDES the target-time week_matrix '
   '(cells_week): 3 models x {p50,p90} x rho{10,15,20,25} x leads{15,30,45,165} = 96 '
   'warm-pool aggregate cells, continuous replay of the covered span. Denominator = '
   'static C8 over that span = 3,869,278 worker-s. Design is in the script, not a '
   'cells_*.jsonl, so manifest_path is the generator. Both quantile halves are present; '
   'all 96 returned.')
ON CONFLICT (manifest_id) DO UPDATE SET
  manifest_path = excluded.manifest_path, actuation = excluded.actuation,
  n_cells = excluded.n_cells, generator = excluded.generator,
  results_path = excluded.results_path, results_is_dir = excluded.results_is_dir,
  is_current = excluded.is_current, note = excluded.note;

INSERT INTO provenance.sweep_manifest_cell
  (manifest_id, cell_ix, window_name, resolution, rho, cold_start_s,
   hysteresis_min, policy, quantile, model, cell)
SELECT 'cells_week_surface_issuetime',
       (m.ix * 32) + (q.ix * 16) + (r.ix * 4) + l.ix,
       'aggregate',
       NULL,                       -- forecast_schedule_issuetime.py takes no --resolution
       r.rho,
       l.lead,
       NULL,                       -- ... and no --hysteresis-min
       'forecast', q.q, m.model,
       jsonb_build_object('window', 'aggregate', 'policy', 'forecast',
                          'model', m.model, 'quantile', q.q, 'rho', r.rho,
                          'cold_start_s', l.lead, 'readiness', 'warm')
  FROM (VALUES ('chronos', 0), ('toto', 1), ('timesfm', 2))       AS m(model, ix),
       (VALUES ('p90', 0), ('p50', 1))                            AS q(q, ix),
       (VALUES (10, 0), (15, 1), (20, 2), (25, 3))                AS r(rho, ix),
       (VALUES (15, 0), (30, 1), (45, 2), (165, 3))               AS l(lead, ix)
ON CONFLICT (manifest_id, cell_ix) DO UPDATE SET
  window_name = excluded.window_name, resolution = excluded.resolution,
  rho = excluded.rho, cold_start_s = excluded.cold_start_s,
  hysteresis_min = excluded.hysteresis_min, policy = excluded.policy,
  quantile = excluded.quantile, model = excluded.model, cell = excluded.cell;


-- ---------------------------------------------------------------------
-- C  coverage view: honour results_is_dir
-- ---------------------------------------------------------------------
-- Same dimension match as before. The ONLY change is how a cell's source is
-- tied to its manifest: exact path equality (unchanged for all four existing
-- single-file manifests) or, for a directory manifest, the cell's source_path
-- lying under that directory. This is a generalisation to a sweep shape the
-- view could not express, not a relaxation of the dimension match -- a cell
-- still has to agree on window, policy, quantile, model, rho and cold_start_s
-- to count as returned.

CREATE OR REPLACE VIEW provenance.sweep_manifest_coverage AS
SELECT m.manifest_id,
       m.actuation,
       m.n_cells                                   AS requested,
       count(f.run_id)                             AS returned,
       m.n_cells - count(f.run_id)                 AS missing,
       m.results_path
  FROM provenance.sweep_manifest m
  LEFT JOIN provenance.sweep_manifest_cell c ON c.manifest_id = m.manifest_id
  LEFT JOIN provenance.factorial_cell f
         ON (CASE WHEN m.results_is_dir
                  THEN f.source_path LIKE m.results_path || '/%'
                  ELSE f.source_path = m.results_path END)
        AND f.actuation    IS NOT DISTINCT FROM m.actuation
        AND f.window_name  IS NOT DISTINCT FROM c.window_name
        AND f.policy       IS NOT DISTINCT FROM c.policy
        AND f.quantile     IS NOT DISTINCT FROM c.quantile
        AND f.model        IS NOT DISTINCT FROM c.model
        AND f.rho          IS NOT DISTINCT FROM c.rho
        AND f.cold_start_s IS NOT DISTINCT FROM c.cold_start_s
 GROUP BY m.manifest_id, m.actuation, m.n_cells, m.results_path;

COMMENT ON VIEW provenance.sweep_manifest_coverage IS
  'Requested (manifest) vs returned (factorial_cell) per sweep. A non-zero `missing` '
  'is a real gap — cells that were designed and launched but produced no graded '
  'result (converter errors, aborted waves). Cells are tied to their manifest by '
  'source_path (exact, or by directory prefix when sweep_manifest.results_is_dir) AND '
  'by actuation AND by the six sweep dimensions, so a cell can never be counted '
  'against a manifest of the other actuation.';


-- ---------------------------------------------------------------------
-- D  new invariant: the week surface must not silently empty again
-- ---------------------------------------------------------------------
INSERT INTO provenance.check_definition
  (check_id, title, severity, est_cost, expected, note, sql_text)
VALUES
('C510', 'every ingested factorial RESULTS file yielded cells', 'error', 'cheap',
 'No ingest_log row of kind K7/K7w whose file_path names a results file has n_rows = 0, '
 'except the known converter-error file results_week_canary.jsonl (3 requested cells, 3 '
 'converter errors).',
 'week_surface_issuetime_results.json sat in ingest_log as K7 with n_rows=0 for the '
 'whole of §2.7: loaders._norm_cell did not recognise its flat, window-less record '
 'shape and rejected all 96 cells without raising. A silent zero from a file that is on '
 'disk and non-empty is indistinguishable from a real absence, which is exactly how the '
 '96-cell issue-time week surface went missing. '
 'SCOPE, stated honestly: load_factorial globs whole directories, so K7 also registers '
 '13 files that are NOT cell files and legitimately yield zero -- the four '
 'aggregate44/fc_p90_L*_issuetime.ledger.json and six rerun_verify/*_issue_L*.ledger.json '
 'scale-up ledgers (arrays of {target_ts, level, ready_ts}), plus '
 'rerun_verify/{burst5_stability, e2e_ingress_to_first_token, onset_audit_issuetime}.json '
 '(analysis artifacts). Each was opened and confirmed to contain no cell records. Rather '
 'than allowlist thirteen paths, the check is scoped to files whose name says results, '
 'which is the naming every real factorial sweep uses. LIMITATION: a future factorial '
 'sweep whose output is NOT named *results* and which silently empties would not fire '
 'here -- name new sweep outputs *_results.json to stay covered.',
 $$SELECT count(*) = 0,
          format('%s factorial results file(s) ingested with 0 cells: %s', count(*),
                 coalesce(string_agg(file_path, ', '), 'none'))
     FROM provenance.ingest_log
    WHERE kind IN ('K7', 'K7w') AND n_rows = 0
      -- basename, not the whole path: every one of these lives under a
      -- directory literally called "results", so a LIKE on file_path matches
      -- everything and the check would never discriminate.
      AND split_part(file_path, '/', -1) LIKE '%results%'
      AND file_path <> '/home/gio/tese/simulation/results/results_week_canary.jsonl'$$)
ON CONFLICT (check_id) DO UPDATE SET
  title = excluded.title, severity = excluded.severity, est_cost = excluded.est_cost,
  expected = excluded.expected, note = excluded.note, sql_text = excluded.sql_text;

COMMIT;
