-- =====================================================================
-- 23_stage_conditional.sql
--
-- ADJUDICATION.md §2.6 -- the STAGE-CONDITIONAL vision grid.
--
-- READ THIS BEFORE QUERYING ANYTHING BELOW.
--
-- This file does NOT correct grid_window.c_star.  The stage-conditional
-- optimum is a DIFFERENT METRIC over the same simulation, not a better
-- estimate of the published one:
--
--   published  C*  (grid_window.c_star, tab:base-grid)
--       = smallest encoder-worker count whose encoder-delay p99 over
--         ALL requests is <= the 1,000 ms bound.  ~50 % of requests in
--         the trace are text-only, never enter the encoder, and enter
--         that percentile with delay 0.  They pull the p99 down.
--
--   stage-conditional C*  (rerun_b1_window.corrected_image_cstar)
--       = the same quantity computed over IMAGE-BEARING requests only.
--         Strictly the harder bound, so it is >= the published C* in
--         every window.
--
-- Both are correct under their own definition.  The thesis prints the
-- published C* in tab:base-grid and states the stage-conditional optima
-- in the prose that follows it (baselines.tex:92, 93).  Nothing here is
-- a defect in either.
--
-- The §2.6 ingest itself was ALREADY DONE by loader K28
-- (load_residual.load_rerun_b1 -> rerun_b1_run / rerun_b1_window /
-- rerun_b1_curve_point, 7 windows, 140 curve points, all from
-- verification/rerun_b1_results.json).  Verified 2026-07-20:
--   burst1 6->7, burst3 7->8, burst4 7->8, burst6 6->8, with GPU-hours
--   49.9->58.2, 3.1->3.6, 22.1->25.2, 8.2->10.9 -- an exact match to
--   the four deltas ADJUDICATION §2.6 names.
--
-- What was OUTSTANDING, and is what this file applies:
--
--   A. burst5's stage-conditional row is itself derived from the
--      PRE-CORRECTION C* = 16.  rerun_b1_results.json was generated
--      before the §2.1 supersession, so burst5 carries
--      grid_cstar_reported = current_mixed_cstar =
--      corrected_image_cstar = 16 and reports a 0-worker delta against
--      a baseline that no longer stands.  Superseded here, visibly.
--
--   B. only burst1 had a provenance.grid_correction row recording the
--      stage-conditional difference.  burst3 / burst4 / burst6 have the
--      same kind of difference and had no row at all, so a reader of
--      grid_correction saw one of four.  The three missing rows are
--      added, as correction_type = 'alternative_metric' -- the same
--      NOT-a-supersession class burst1 already uses.
--
-- INVARIANTS (identical to 22_corrections.sql):
--   1. No archived measurement is destroyed.  Every value K28 ingested
--      stays exactly where it was ingested.  Corrections are sibling
--      `_corrected` columns + a provenance.grid_correction row +
--      an `_effective` view.
--   2. Every statement is idempotent.  Safe to run repeatedly.
--
-- Depends on: 01_schema.sql, 05_grid.sql, 20_semantic.sql, 22_corrections.sql.
--
-- NOTE ON 21_checks.sql: it begins with DELETE FROM check_definition,
-- so it wipes the probes registered at the bottom of this file.  Run
-- order is always 21 -> 22 -> 23 -> 24.
-- =====================================================================
\set ON_ERROR_STOP on
SET search_path = provenance, public;


-- =====================================================================
-- PART A -- burst5's stage-conditional row: visible supersession
-- =====================================================================
-- Evidence, read off provenance.rerun_b1_curve_point (the dense C=1..20
-- curve K28 ingested from the same artifact):
--
--   burst5  C=7   mixed 925.2 ms   image 1037.5 ms   -> image INFEASIBLE
--   burst5  C=8   mixed 759.5 ms   image  852.4 ms   -> image FEASIBLE
--
-- 852.4 ms at C=8 is exactly the figure ADJUDICATION §2.6 states for
-- burst5 under the corrected baseline.  So the stage-conditional
-- optimum for burst5 is 8, equal to its own corrected published C* of 8
-- (22_corrections.sql PART A) -- i.e. a genuine 0-worker delta, but
-- against 8, not against the stale 16.
--
-- WHY THE INGESTED FEASIBILITY FLAGS SAY FALSE AT EVERY C: burst5's
-- curve points all carry divergent = true.  That is the queue-divergence
-- endpoint artifact §2.1 dismissed -- a backlog present at the window
-- boundary that in fact drains in a fraction of a second.  The flags are
-- left exactly as ingested; the corrected columns below apply the
-- p99-only gate the thesis's tab:base-grid actually uses.

ALTER TABLE provenance.rerun_b1_window
  ADD COLUMN IF NOT EXISTS grid_cstar_reported_corrected   integer,
  ADD COLUMN IF NOT EXISTS corrected_image_cstar_corrected integer,
  ADD COLUMN IF NOT EXISTS corrected_image_p99_corrected   double precision,
  ADD COLUMN IF NOT EXISTS delta_workers_corrected         integer,
  ADD COLUMN IF NOT EXISTS is_superseded                   boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS correction_source               text;

COMMENT ON COLUMN provenance.rerun_b1_window.grid_cstar_reported_corrected IS
  'Sibling of grid_cstar_reported carrying the POST-§2.1 published C* for this window. '
  'Populated only where the as-ingested baseline is stale (burst5: 16 -> 8). '
  'NULL means the as-ingested value already stands. Read via rerun_b1_window_effective.';
COMMENT ON COLUMN provenance.rerun_b1_window.corrected_image_cstar_corrected IS
  'Sibling of corrected_image_cstar: the stage-conditional (image-bearing requests only) '
  'optimum recomputed under the p99-only gate tab:base-grid uses, i.e. with the burst5 '
  'queue-divergence endpoint artifact dropped. NULL where the as-ingested value stands.';
COMMENT ON COLUMN provenance.rerun_b1_window.corrected_image_p99_corrected IS
  'Image-bearing-request encoder-delay p99 at corrected_image_cstar_corrected, read from '
  'provenance.rerun_b1_curve_point (burst5: 852.4 ms at C=8).';
COMMENT ON COLUMN provenance.rerun_b1_window.delta_workers_corrected IS
  'corrected_image_cstar_corrected - grid_cstar_reported_corrected: the stage-conditional '
  'worker delta measured against the window''s CORRECTED published C*. burst5 = 0 (8 vs 8).';
COMMENT ON COLUMN provenance.rerun_b1_window.is_superseded IS
  'True iff this window''s as-ingested stage-conditional row was computed against a '
  'published C* that has since been superseded. Only burst5.';
COMMENT ON COLUMN provenance.rerun_b1_window.correction_source IS
  'Artifact establishing the supersession. See provenance.grid_correction for the rationale.';

-- A.1  burst5 only. Driven off the ingested curve so the values are
--      derived, never typed in: smallest C whose IMAGE p99 <= sla_ms.
UPDATE provenance.rerun_b1_window w
   SET grid_cstar_reported_corrected   = 8,
       corrected_image_cstar_corrected = c.c_star,
       corrected_image_p99_corrected   = c.p99,
       delta_workers_corrected         = c.c_star - 8,
       is_superseded                   = true,
       correction_source               = '/home/gio/tese/verification/rerun-stability-e2e.md'
  FROM (SELECT DISTINCT ON (p.window_name)
               p.window_name, p.encoder_c AS c_star, p.image_p99_ms AS p99
          FROM provenance.rerun_b1_curve_point p
          JOIN provenance.rerun_b1_window ww USING (rerun_id, window_name)
         WHERE p.window_name = 'burst5'
           AND p.image_p99_ms <= ww.sla_ms
         ORDER BY p.window_name, p.encoder_c) c
 WHERE w.window_name = 'burst5'
   AND w.window_name = c.window_name
   AND (w.corrected_image_cstar_corrected IS DISTINCT FROM c.c_star
        OR w.is_superseded IS DISTINCT FROM true);


-- =====================================================================
-- PART B -- the effective view
-- =====================================================================
CREATE OR REPLACE VIEW provenance.rerun_b1_window_effective AS
SELECT w.rerun_id,
       w.window_name,
       w.sla_ms,
       w.total_reqs,
       w.n_image_reqs,
       round((w.n_image_reqs::numeric / NULLIF(w.total_reqs, 0)), 4) AS image_bearing_fraction,
       coalesce(w.grid_cstar_reported_corrected,   w.grid_cstar_reported)   AS published_cstar_effective,
       coalesce(w.corrected_image_cstar_corrected, w.corrected_image_cstar) AS stage_conditional_cstar_effective,
       coalesce(w.corrected_image_p99_corrected,   w.corrected_image_p99)   AS stage_conditional_p99_effective,
       coalesce(w.delta_workers_corrected,         w.delta_workers)         AS delta_workers_effective,
       w.grid_cstar_reported   AS published_cstar_as_ingested,
       w.corrected_image_cstar AS stage_conditional_cstar_as_ingested,
       w.delta_workers         AS delta_workers_as_ingested,
       w.is_superseded,
       w.correction_source,
       w.gpuh_5090_old,
       w.gpuh_5090_new,
       w.gpuh_h100,
       w.reproduces_grid_mixed_cstar,
       w.source_path
  FROM provenance.rerun_b1_window w;

COMMENT ON VIEW provenance.rerun_b1_window_effective IS
  'ADJUDICATION §2.6. Resolved read of the STAGE-CONDITIONAL vision grid: encoder C* '
  'computed over IMAGE-BEARING requests only, versus the published all-request C* of '
  'tab:base-grid. THIS IS A DIFFERENT METRIC, NOT A CORRECTION OF grid_window.c_star -- '
  'do not substitute stage_conditional_cstar_effective for a published C* anywhere. '
  'The published grid is right under its own (all-request) definition and an independent '
  'rerun reproduced it exactly in all seven windows (reproduces_grid_mixed_cstar). '
  'The four windows where the metrics differ are burst1 6->7, burst3 7->8, burst4 7->8, '
  'burst6 6->8; burst2 and steady24h are unchanged, and burst5 is 0-delta once its own '
  'published C* is taken post-§2.1 (8, not the stale 16) -- see is_superseded. '
  'The *_as_ingested columns preserve the artifact exactly as K28 loaded it.';


-- =====================================================================
-- PART C -- grid_correction rows for the three unrecorded windows
-- =====================================================================
-- burst1 already has 'burst1:c_star:alternative_metric'. These three are
-- the same class of statement for the other three differing windows, so
-- grid_correction stops showing one of four.

INSERT INTO provenance.grid_correction
    (correction_id, window_name, field, correction_type,
     original_value, corrected_value, original_source, corrected_source,
     thesis_location, published_value, affects_headline, rationale)
VALUES
 ('burst3:c_star:alternative_metric', 'burst3', 'c_star', 'alternative_metric',
  7, 8,
  '/home/gio/tese/simulation/results/grid/grid_summary.json',
  '/home/gio/tese/verification/rerun_b1_results.json',
  'tex/baselines.tex:92', 7, false,
  'NOT a supersession. C*=7 is correct under the all-request encoder-delay p99 that '
  'tab:base-grid uses, and the rerun reproduced it exactly. Under the stage-conditional '
  'metric -- image-bearing requests only, excluding the text-only requests that never '
  'enter the encoder -- burst3 needs C=8 (image-only p99 852.9 ms at C=8). GPU-hours on '
  'RTX 5090 move 3.1 -> 3.6. The thesis prints 7 in the table and states the '
  'stage-conditional optimum in the prose following it. Both are correct under their own '
  'definition; grid_window.c_star is NOT marked superseded for burst3. Full curve in '
  'provenance.rerun_b1_curve_point; resolved read in provenance.rerun_b1_window_effective.'),

 ('burst4:c_star:alternative_metric', 'burst4', 'c_star', 'alternative_metric',
  7, 8,
  '/home/gio/tese/simulation/results/grid/grid_summary.json',
  '/home/gio/tese/verification/rerun_b1_results.json',
  'tex/baselines.tex:92', 7, false,
  'NOT a supersession. C*=7 is correct under the all-request encoder-delay p99 that '
  'tab:base-grid uses, and the rerun reproduced it exactly. Under the stage-conditional '
  'metric burst4 needs C=8 (image-only p99 875.8 ms at C=8). GPU-hours on RTX 5090 move '
  '22.1 -> 25.2. Both numbers are correct under their own definition; grid_window.c_star '
  'is NOT marked superseded for burst4. Full curve in provenance.rerun_b1_curve_point; '
  'resolved read in provenance.rerun_b1_window_effective.'),

 ('burst6:c_star:alternative_metric', 'burst6', 'c_star', 'alternative_metric',
  6, 8,
  '/home/gio/tese/simulation/results/grid/grid_summary.json',
  '/home/gio/tese/verification/rerun_b1_results.json',
  'tex/baselines.tex:92', 6, false,
  'NOT a supersession, and the largest of the four stage-conditional steps: +2 workers. '
  'C*=6 is correct under the all-request p99 of tab:base-grid. Under the stage-conditional '
  'metric burst6 needs C=8, NOT C=7 -- at C=7 the image-bearing p99 is 1049.1 ms, still '
  'over the 1,000 ms bound, so the curve skips 7 entirely (894.8 ms at C=8). GPU-hours on '
  'RTX 5090 move 8.2 -> 10.9. Both numbers are correct under their own definition; '
  'grid_window.c_star is NOT marked superseded for burst6. Full curve in '
  'provenance.rerun_b1_curve_point; resolved read in provenance.rerun_b1_window_effective.'),

 ('burst5:stage_conditional_baseline:supersession', 'burst5',
  'stage_conditional_baseline', 'supersession',
  16, 8,
  '/home/gio/tese/verification/rerun_b1_results.json',
  '/home/gio/tese/verification/rerun-stability-e2e.md',
  'tex/baselines.tex:92', 8, false,
  'The stage-conditional artifact predates the §2.1 burst5 supersession, so burst5''s row '
  'in it compares against the stale published C*=16 and reports a 0-worker delta that is '
  'right for the wrong reason. Recomputed against the corrected published C*=8: the '
  'smallest C whose IMAGE-BEARING p99 clears 1,000 ms is C=8 at 852.4 ms (C=7 is 1037.5 ms), '
  'so the delta really is 0 -- but 0 against 8, not against 16. The ingested curve''s '
  'feasibility flags read false at every C for burst5 because every burst5 curve point '
  'carries divergent=true, which is the same queue-divergence endpoint artifact §2.1 '
  'dismissed; the corrected columns apply the p99-only gate tab:base-grid actually uses. '
  'rerun_b1_window.corrected_image_cstar and .delta_workers are preserved unmodified; read '
  'the *_corrected siblings or provenance.rerun_b1_window_effective.')
ON CONFLICT (correction_id) DO UPDATE SET
    window_name      = excluded.window_name,
    field            = excluded.field,
    correction_type  = excluded.correction_type,
    original_value   = excluded.original_value,
    corrected_value  = excluded.corrected_value,
    original_source  = excluded.original_source,
    corrected_source = excluded.corrected_source,
    thesis_location  = excluded.thesis_location,
    published_value  = excluded.published_value,
    affects_headline = excluded.affects_headline,
    rationale        = excluded.rationale;


-- =====================================================================
-- PART D -- checks
-- =====================================================================
INSERT INTO provenance.check_definition
    (check_id, title, severity, est_cost, expected, note, sql_text)
VALUES

('C210', 'stage-conditional C* is recomputable from the ingested curve', 'error', 'cheap',
 'For every window, corrected_image_cstar (as ingested) must equal the smallest encoder_c '
 'in rerun_b1_curve_point whose image_p99_ms <= sla_ms -- EXCEPT burst5, whose as-ingested '
 'value is superseded and whose corrected sibling must satisfy the identity instead.',
 'This is the probe that makes §2.6 self-checking: the summary row and the dense curve come '
 'from the same artifact, so they must agree. burst5 is not excluded from the population, it '
 'is evaluated against its effective value, which is the point of the _effective view.',
 $$
 WITH recomputed AS (
     SELECT DISTINCT ON (p.window_name) p.window_name, p.encoder_c AS c_star
       FROM provenance.rerun_b1_curve_point p
       JOIN provenance.rerun_b1_window w USING (rerun_id, window_name)
      WHERE p.image_p99_ms <= w.sla_ms
      ORDER BY p.window_name, p.encoder_c
 ), cmp AS (
     SELECT e.window_name, e.stage_conditional_cstar_effective AS stored, r.c_star AS recomputed
       FROM provenance.rerun_b1_window_effective e
       JOIN recomputed r USING (window_name)
 )
 SELECT count(*) FILTER (WHERE stored IS DISTINCT FROM recomputed) = 0,
        'windows=' || count(*) || ' mismatched=' ||
        coalesce(string_agg(window_name || '(' || stored || '<>' || recomputed || ')', ', ')
                 FILTER (WHERE stored IS DISTINCT FROM recomputed), 'none')
   FROM cmp
 $$),

('C211', 'stage-conditional C* never undercuts the published C*', 'error', 'cheap',
 'The stage-conditional optimum is computed over a strict subset of the requests that carry '
 'all the encoder delay, so it can only be >= the published all-request C*, never below it.',
 'The one-directional half of the metric relationship, and the invariant that would break '
 'first if the two metrics were ever accidentally swapped at a call site.',
 $$
 SELECT count(*) FILTER (WHERE stage_conditional_cstar_effective < published_cstar_effective) = 0,
        'windows=' || count(*) || ' violations=' ||
        coalesce(string_agg(window_name, ', ')
                 FILTER (WHERE stage_conditional_cstar_effective < published_cstar_effective), 'none')
   FROM provenance.rerun_b1_window_effective
 $$),

('C212', 'dense mixed-metric C* bounds the published grid C*', 'error', 'cheap',
 'For every window the smallest encoder_c with mixed_p99_ms <= sla_ms on the dense C=1..20 '
 'rerun curve must be <= the published grid C*.',
 'Deliberately stated as an INEQUALITY, not an equality. The published grid samples C in '
 '{1,2,4,8,16} only, while the rerun curve is dense over 1..20, so a window whose true knee '
 'is a non-grid value is published at the next grid point up. That is exactly burst5: dense '
 'mixed knee 7 (925.2 ms), published 8. Six of seven windows are equal; asserting equality '
 'would fail honestly on burst5 for a reason that is a property of the grid resolution and '
 'not a defect, so the invariant is written at the strength that is actually true. See C213 '
 'for the census of where the two differ.',
 $$
 WITH dense AS (
     SELECT DISTINCT ON (p.window_name) p.window_name, p.encoder_c AS c_star
       FROM provenance.rerun_b1_curve_point p
       JOIN provenance.rerun_b1_window w USING (rerun_id, window_name)
      WHERE p.mixed_p99_ms <= w.sla_ms
      ORDER BY p.window_name, p.encoder_c
 )
 SELECT count(*) FILTER (WHERE d.c_star > e.published_cstar_effective) = 0,
        'windows=' || count(*) || ' violations=' ||
        coalesce(string_agg(d.window_name, ', ')
                 FILTER (WHERE d.c_star > e.published_cstar_effective), 'none')
   FROM dense d JOIN provenance.rerun_b1_window_effective e USING (window_name)
 $$),

('C213', 'census: dense mixed knee vs published grid C*', 'info', 'cheap',
 'Descriptive. Reports, per window, the dense-curve mixed knee alongside the published C*, '
 'so the grid-resolution gap C212 tolerates stays visible instead of being tolerated silently.',
 'Never fails. Expected content as of 2026-07-20: six windows equal, burst5 dense 7 vs '
 'published 8.',
 $$
 WITH dense AS (
     SELECT DISTINCT ON (p.window_name) p.window_name, p.encoder_c AS c_star
       FROM provenance.rerun_b1_curve_point p
       JOIN provenance.rerun_b1_window w USING (rerun_id, window_name)
      WHERE p.mixed_p99_ms <= w.sla_ms
      ORDER BY p.window_name, p.encoder_c
 )
 SELECT true,
        string_agg(d.window_name || ' dense=' || d.c_star || ' published=' ||
                   e.published_cstar_effective, ', ' ORDER BY d.window_name)
   FROM dense d JOIN provenance.rerun_b1_window_effective e USING (window_name)
 $$)

ON CONFLICT (check_id) DO UPDATE SET
    title = excluded.title, severity = excluded.severity, est_cost = excluded.est_cost,
    expected = excluded.expected, note = excluded.note, sql_text = excluded.sql_text;
