-- ===========================================================================
-- REPAIR 3 -- spine completeness, per-request provenance, retraction machinery
-- Applied 2026-07-19. Companion to 11_repair2.sql.
--
-- (a) week_matrix spine: 112 runs rows were missing, orphaning 118,861
--     worker_schedule rows. Fixed by re-running the real K3/K4 loaders scoped to
--     /home/gio/tese/simulation/results/week_matrix (see the loader; no DDL here).
--     Those runs carry experiment='factorial' (runid._DIR_EXP_LEGACY maps
--     "week_matrix" -> "factorial") and window_name='week'.
--     week_matrix ships NO *.report.json and NO *.requests.jsonl, so
--     llm_run_summary/llm_request correctly stay empty for them; only
--     encoder_run_summary (112 rows) applies.
-- ===========================================================================
SET search_path = provenance, public;

-- ---------------------------------------------------------------------------
-- (b) per-request backing: make "not recomputable" explicit
-- ---------------------------------------------------------------------------
ALTER TABLE provenance.llm_run_summary
    ADD COLUMN IF NOT EXISTS has_raw_records boolean;

COMMENT ON COLUMN provenance.llm_run_summary.has_raw_records IS
  'Tri-state provenance flag for the per-request layer. TRUE = provenance.llm_request holds this run''s rows, so every summary percentile is recomputable from raw (see v_llm_drift). FALSE = VERIFIED NOT RECOMPUTABLE: the run''s *.requests.jsonl does not exist anywhere under /home/gio/tese/{simulation/results,defense/anim/data}; the run genuinely never persisted per-request records and no amount of re-ingest will produce them. NULL = NOT YET CHECKED (default for newly inserted rows) -- do not read NULL as FALSE. Verified by exhaustive disk scan on 2026-07-19: every *.requests.jsonl on disk was mapped through runid.run_id_of and intersected with this table; the 394 FALSE rows had zero candidate files, the split was 394 absent / 0 present-but-unloaded. Re-verify with v_llm_raw_backing after any K2 ingest.';

-- One-time classification from the 2026-07-19 disk scan.
UPDATE provenance.llm_run_summary s
   SET has_raw_records = EXISTS (SELECT 1 FROM provenance.llm_request q
                                 WHERE q.run_id = s.run_id);

-- Guard: catches (i) rows never classified, and (ii) a row marked "verified absent"
-- that has since acquired raw rows (i.e. the FALSE verdict went stale).
CREATE OR REPLACE VIEW provenance.v_llm_raw_backing AS
    SELECT s.run_id,
           r.experiment,
           s.has_raw_records,
           EXISTS (SELECT 1 FROM provenance.llm_request q WHERE q.run_id = s.run_id)
               AS raw_rows_present_now,
           CASE
             WHEN s.has_raw_records IS NULL THEN 'UNCHECKED'
             WHEN s.has_raw_records = EXISTS (SELECT 1 FROM provenance.llm_request q
                                              WHERE q.run_id = s.run_id) THEN 'OK'
             ELSE 'STALE_FLAG'
           END AS status
    FROM provenance.llm_run_summary s
    JOIN provenance.runs r USING (run_id);

COMMENT ON VIEW provenance.v_llm_raw_backing IS
  'Freshness guard for llm_run_summary.has_raw_records. status=OK: flag agrees with the live llm_request contents. status=STALE_FLAG: the flag disagrees -- re-run the disk scan and re-classify. status=UNCHECKED: has_raw_records IS NULL, nobody has established whether per-request data exists. Expect zero STALE_FLAG and zero UNCHECKED rows; any other result means an ingest ran without re-classifying.';

-- ---------------------------------------------------------------------------
-- (c) retraction machinery -- populated ONLY from documented evidence
-- ---------------------------------------------------------------------------
-- Evidence: progress/results-ledger.md, entry "forecast_file predictor: sub-minute
-- feed fixes (2026-07-09)", commit a3cd122:
--   "Pre-fix burst4 fc results (fc_scale{6.22,8}_burst4.report.json) are INVALID
--    -- superseded by _v2"
--   "supersedes: fc_scale6.22_burst4/fc_scale8_burst4 (buggy feed; retained as the
--    bug record)"
-- Two compounding sub-minute feed bugs (per-BIN vs per-60s quantile units; predictor
-- tick clock) made these two runs' inputs wrong. They are retained as the bug record,
-- which is exactly what is_current=false means here: the rows stay, the default query
-- surface stops returning them.
UPDATE provenance.runs SET is_current = false,
       superseded_by = 'riders:fc_scale6.22_burst4_v2'
 WHERE run_id = 'riders:fc_scale6.22_burst4';
UPDATE provenance.runs SET supersedes = 'riders:fc_scale6.22_burst4'
 WHERE run_id = 'riders:fc_scale6.22_burst4_v2';

UPDATE provenance.runs SET is_current = false,
       superseded_by = 'riders:fc_scale8.0_burst4_v2'
 WHERE run_id = 'riders:fc_scale8_burst4';
UPDATE provenance.runs SET supersedes = 'riders:fc_scale8_burst4'
 WHERE run_id = 'riders:fc_scale8.0_burst4_v2';

COMMENT ON COLUMN provenance.runs.is_current IS
  'FALSE = this run is RETRACTED: its inputs or method are documented as wrong and its numbers must not be quoted. The row and all its child rows are deliberately retained as the bug record. TRUE = not retracted. TRUE IS NOT A CERTIFICATE OF CORRECTNESS -- it is the default, and a run only leaves it when written evidence of supersession exists. As of 2026-07-19 exactly 2 of 2318 runs are FALSE (riders:fc_scale6.22_burst4, riders:fc_scale8_burst4), both on progress/results-ledger.md:155-156 (commit a3cd122). See v_retractions.';

COMMENT ON COLUMN provenance.runs.superseded_by IS
  'run_id of the run that replaced this one, set together with is_current=false. NULL for every non-retracted run.';
COMMENT ON COLUMN provenance.runs.supersedes IS
  'run_id this run replaced. NULL unless this run is the replacement in a documented supersession.';

CREATE OR REPLACE VIEW provenance.v_retractions AS
    SELECT r.run_id, r.experiment, r.source_path, r.superseded_by,
           n.source_path AS superseding_source_path
    FROM provenance.runs r
    LEFT JOIN provenance.runs n ON n.run_id = r.superseded_by
    WHERE NOT r.is_current
    ORDER BY r.run_id;

COMMENT ON VIEW provenance.v_retractions IS
  'The complete retraction set: every run with is_current=false and what replaced it. Currently 2 rows (the pre-feed-fix burst4 fc_scale runs). Row-level corrections that do NOT retract a whole run live elsewhere: grid_correction (burst5 c_star supersession -> grid_window.is_superseded; burst1 alternative_metric, not a supersession) and artifact_quarantine.';

-- ---- honest comments on the current_* surface -----------------------------
-- These views DO filter runs.is_current. Before repair 3 the filter was a no-op
-- because nothing was ever marked; the comments must not let a reader infer a
-- broader cleanliness guarantee than the flag actually carries.
COMMENT ON VIEW provenance.current_runs IS
  'runs with is_current = true. The filter is REAL but NARROW: is_current=false is set only where a written supersession exists (progress/results-ledger.md / tex/apendice.tex / grid_correction). As of 2026-07-19 it excludes exactly 2 of 2318 runs. Rows surviving this view are "not known to be retracted", NOT "verified correct" -- validity questions belong to verification, coverage and artifact_quarantine. See v_retractions for the full excluded set.';

COMMENT ON VIEW provenance.current_llm_summary IS
  'llm_run_summary joined to runs dims, retracted runs excluded. The filter is LIVE HERE: as of 2026-07-19 it drops 2 of 495 rows (riders:fc_scale6.22_burst4, riders:fc_scale8_burst4 -- the pre-feed-fix burst4 runs, see v_retractions). Default surface for language-pool KPI questions. Exclusion means "documented as superseded", not "all remaining rows verified correct". Pair with has_raw_records to know whether a row is recomputable from provenance.llm_request -- 394 of 495 are not.';

COMMENT ON VIEW provenance.current_encoder_summary IS
  'encoder_run_summary joined to runs dims, retracted runs excluded. NOTE: as of 2026-07-19 the filter removes NOTHING here -- neither retracted run carries an encoder_run_summary row, so this view is row-identical to the unfiltered join (569 rows). Do not read it as a cleaned or validated subset. Default surface for vision-pool cost/latency questions.';

COMMENT ON VIEW provenance.current_factorial IS
  'factorial_cell with retracted runs excluded. NOTE: as of 2026-07-19 the filter removes NOTHING here -- neither retracted run is a factorial cell, so this view is row-identical to factorial_cell (1172 rows). Do not read it as a cleaned or validated subset; feasibility verdicts are judged by factorial_cell.feasible, not by this filter. Default surface for feasibility/cost-frontier questions.';

-- ---------------------------------------------------------------------------
-- (d) mv_llm_p99_check freshness
-- ---------------------------------------------------------------------------
REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;

CREATE OR REPLACE VIEW provenance.v_llm_p99_check_freshness AS
    SELECT (SELECT count(*) FROM provenance.mv_llm_p99_check)      AS matview_runs,
           (SELECT count(DISTINCT run_id) FROM provenance.llm_request
             WHERE run_id IN (SELECT run_id FROM provenance.llm_run_summary))
                                                                    AS live_joinable_runs,
           (SELECT count(*) FROM provenance.llm_run_summary)        AS summary_runs,
           (SELECT count(DISTINCT run_id) FROM provenance.llm_request)
                                                                    AS raw_runs,
           ((SELECT count(*) FROM provenance.mv_llm_p99_check) =
            (SELECT count(DISTINCT run_id) FROM provenance.llm_request
              WHERE run_id IN (SELECT run_id FROM provenance.llm_run_summary)))
                                                                    AS is_fresh;

COMMENT ON VIEW provenance.v_llm_p99_check_freshness IS
  'Staleness guard for the mv_llm_p99_check materialized view. is_fresh=false means the matview was built before the current contents of llm_request/llm_run_summary: RUN "REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;" AFTER EVERY K1 OR K2 INGEST (main.py --only K1 / --only K2), otherwise v_llm_drift silently audits an old snapshot and can report "no drift" for runs it never saw. matview_runs counts runs in the matview; live_joinable_runs counts runs that have BOTH a raw llm_request row and a summary row (the matview''s own join condition). summary_runs minus live_joinable_runs is the population with no raw backing -- see llm_run_summary.has_raw_records for whether that is verified-absent or merely unchecked.';

COMMENT ON MATERIALIZED VIEW provenance.mv_llm_p99_check IS
  'SNAPSHOT, not a live view: p99 TTFT/ITL recomputed from raw llm_request vs the stored llm_run_summary projection. Refresh after any K1/K2 ingest -- "REFRESH MATERIALIZED VIEW provenance.mv_llm_p99_check;". Check provenance.v_llm_p99_check_freshness before trusting v_llm_drift.';
