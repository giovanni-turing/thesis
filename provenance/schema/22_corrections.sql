-- =====================================================================
-- 22_corrections.sql
--
-- ADJUDICATION.md §2 DB corrections + WINDOW_ALIAS.md §3.2 normalisation.
--
-- Applies the cases where the THESIS is right and the DATABASE was stale
-- or incomplete.  Two invariants govern every statement here:
--
--   1. NO ARCHIVED MEASUREMENT IS DESTROYED.  Every value that came out
--      of an ingested artifact stays exactly where it was ingested.  A
--      correction is expressed as a SIBLING `_corrected` column plus a
--      row in provenance.grid_correction, and is resolved for readers by
--      an `_effective` view.  An auditor can always see both sides and
--      the supersession that connects them.
--   2. EVERY STATEMENT IS IDEMPOTENT.  Safe to run repeatedly.
--
-- Depends on: 01_schema.sql, 05_grid.sql, 20_semantic.sql.
-- Run 21_checks.sql's check_all() afterwards.
-- =====================================================================


-- =====================================================================
-- PART A — ADJUDICATION §2.1: the burst5 C* supersession, derived columns
-- =====================================================================
-- The supersession itself (grid_window.c_star_corrected = 8,
-- is_superseded = t, gpu_hours_rtx5090_corrected) was already ingested.
-- What was NOT propagated is everything ARITHMETICALLY DERIVED from the
-- stale C* = 16:
--
--   * grid_run_summary.static_encoder_workers = 16
--       = max over the per-window C* set.  With burst5 corrected the set
--         is {b1 6, b2 8, b3 7, b4 7, b5 8, b6 6, steady 2} -> max 8,
--         attained at burst2 AND burst5.
--         (verification/rerun-stability-e2e.md:137)
--   * grid_window.overprovision_vision_x, all seven windows
--       = static_encoder_workers / c_star.  Every published value was
--         computed with 16 in the numerator.
--
-- Sources: /home/gio/tese/verification/rerun-stability-e2e.md
--          /home/gio/tese/verification/rerun_b1_results.json
--
-- NOT TOUCHED (R40): grid_window.c_star, grid_window.overprovision_*,
-- grid_vision_point.feasible, grid_run_summary.static_encoder_workers,
-- grid_run_summary.raw.  Those are the raw pre-correction record of the
-- untouched grid_summary.json ingest and must stay readable as ingested.

ALTER TABLE provenance.grid_window
  ADD COLUMN IF NOT EXISTS overprovision_vision_x_corrected double precision,
  ADD COLUMN IF NOT EXISTS overprovision_correction_source  text;

ALTER TABLE provenance.grid_run_summary
  ADD COLUMN IF NOT EXISTS static_encoder_workers_corrected     integer,
  ADD COLUMN IF NOT EXISTS static_encoder_workers_is_superseded boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS static_correction_source             text;

-- A.1  Fleet-wide deployable static encoder count: 16 -> 8.
UPDATE provenance.grid_run_summary s
   SET static_encoder_workers_corrected = m.c_star_fleet,
       static_encoder_workers_is_superseded = (m.c_star_fleet IS DISTINCT FROM s.static_encoder_workers),
       static_correction_source = '/home/gio/tese/verification/rerun-stability-e2e.md'
  FROM (SELECT grid_run_id, max(c_star_effective) AS c_star_fleet
          FROM provenance.grid_window_effective
         GROUP BY grid_run_id) m
 WHERE m.grid_run_id = s.grid_run_id
   AND (s.static_encoder_workers_corrected IS DISTINCT FROM m.c_star_fleet
        OR s.static_correction_source IS DISTINCT FROM '/home/gio/tese/verification/rerun-stability-e2e.md');

-- A.2  Per-window vision overprovisioning factor, recomputed from the
--      corrected fleet count over the corrected per-window C*.
--      Rounded to 2 dp, matching the precision of the archived block.
--      steady24h: 16/2 = 8.0  ->  8/2 = 4.0   (the headline figure)
--      bursts:    2.67/2.0/2.29/2.29/1.0/2.67 -> 1.33/1.0/1.14/1.14/1.0/1.33
UPDATE provenance.grid_window w
   SET overprovision_vision_x_corrected = round((f.c_star_fleet::numeric / e.c_star_effective), 2)::double precision,
       overprovision_correction_source  = '/home/gio/tese/verification/rerun-stability-e2e.md'
  FROM provenance.grid_window_effective e,
       (SELECT grid_run_id, max(c_star_effective) AS c_star_fleet
          FROM provenance.grid_window_effective GROUP BY grid_run_id) f
 WHERE e.grid_run_id = w.grid_run_id AND e.window_name = w.window_name
   AND f.grid_run_id = w.grid_run_id
   AND e.c_star_effective > 0
   AND (w.overprovision_vision_x_corrected IS DISTINCT FROM round((f.c_star_fleet::numeric / e.c_star_effective), 2)::double precision
        OR w.overprovision_correction_source IS DISTINCT FROM '/home/gio/tese/verification/rerun-stability-e2e.md');

-- A.3  Record each derived correction in the supersession ledger, so the
--      change is discoverable without reading this file.
INSERT INTO provenance.grid_correction
  (correction_id, window_name, field, correction_type,
   original_value, corrected_value, original_source, corrected_source,
   thesis_location, published_value, affects_headline, rationale)
VALUES
  ('grid:static_encoder_workers:supersession', 'ALL', 'static_encoder_workers', 'supersession',
   16, 8,
   '/home/gio/tese/simulation/results/grid/grid_summary.json',
   '/home/gio/tese/verification/rerun-stability-e2e.md',
   'tex/baselines.tex', 8, true,
   'Derived, not measured: the deployable static encoder fleet is max over windows of the per-window C*. '
   'The archived 16 was the max over the STALE per-window set, in which burst5 carried C*=16 from the '
   'queue-divergence heuristic later shown to be an endpoint artifact. With burst5 corrected to 8 the set is '
   '{burst1 6, burst2 8, burst3 7, burst4 7, burst5 8, burst6 6, steady24h 2} and the max is 8, attained at '
   'burst2 AND burst5 (rerun-stability-e2e.md:137). grid_run_summary.static_encoder_workers and .raw are '
   'preserved unmodified as the pre-correction artifact; read static_encoder_workers_corrected, or the view '
   'provenance.grid_run_summary_effective. NOTE: the SILICON fleet C*=16 in silicon_multiworker.json is a '
   'DIFFERENT quantity and is NOT superseded -- under silicon timings the fleet is bound by burst2''s genuine '
   '2.0x p99 knee (rerun-stability-e2e.md, "Important wrinkle"), so 16 stands there.')
ON CONFLICT (correction_id) DO UPDATE
  SET corrected_value = EXCLUDED.corrected_value,
      corrected_source = EXCLUDED.corrected_source,
      rationale = EXCLUDED.rationale,
      affects_headline = EXCLUDED.affects_headline;

INSERT INTO provenance.grid_correction
  (correction_id, window_name, field, correction_type,
   original_value, corrected_value, original_source, corrected_source,
   thesis_location, published_value, affects_headline, rationale)
SELECT 'grid:' || w.window_name || ':overprovision_vision_x:supersession',
       w.window_name, 'overprovision_vision_x', 'supersession',
       w.overprovision_vision_x, w.overprovision_vision_x_corrected,
       '/home/gio/tese/simulation/results/grid/grid_summary.json',
       '/home/gio/tese/verification/rerun-stability-e2e.md',
       CASE WHEN w.window_name = 'steady24h' THEN 'tex/baselines.tex (calm-day overprovisioning headline)' ELSE NULL END,
       CASE WHEN w.window_name = 'steady24h' THEN 4.0 ELSE NULL END,
       (w.window_name = 'steady24h'),
       'Derived, not measured: overprovision_vision_x = deployable static encoder workers / this window''s C*. '
       'The archived value used the stale fleet count 16; the corrected fleet count is 8 (see '
       'grid:static_encoder_workers:supersession). ' ||
       CASE WHEN w.window_name = 'burst5'
            THEN 'burst5''s own C* also moves 16 -> 8, so the ratio stays 1.0 for a different reason. '
            ELSE '' END ||
       'grid_window.overprovision_vision_x is preserved unmodified; read overprovision_vision_x_corrected or '
       'provenance.grid_window_effective. overprovision_llm_x is unaffected (TP2x2 = 4 GPUs on the bursts vs '
       'TP1x2 = 2 on the calm day, ratio 2 at steady24h and 1 elsewhere).'
  FROM provenance.grid_window w
 WHERE w.overprovision_vision_x_corrected IS DISTINCT FROM w.overprovision_vision_x
ON CONFLICT (correction_id) DO UPDATE
  SET original_value = EXCLUDED.original_value,
      corrected_value = EXCLUDED.corrected_value,
      corrected_source = EXCLUDED.corrected_source,
      published_value = EXCLUDED.published_value,
      affects_headline = EXCLUDED.affects_headline,
      rationale = EXCLUDED.rationale;


-- ---------------------------------------------------------------------
-- A.4  The documented query surfaces.
-- ---------------------------------------------------------------------
-- grid_window_effective gains the overprovisioning columns, so a naive
-- reader of the view can never see a value derived from the stale C*.

-- Column order/names change, so a plain CREATE OR REPLACE is rejected.
DROP VIEW IF EXISTS provenance.grid_window_effective;
CREATE VIEW provenance.grid_window_effective AS
SELECT
    w.grid_run_id,
    w.window_name,
    w.span_h,
    w.c_star                                                  AS c_star_as_ingested,
    COALESCE(w.c_star_corrected, w.c_star)                    AS c_star_effective,
    w.is_superseded,
    COALESCE(w.gpu_hours_rtx5090_corrected, w.gpu_hours_rtx5090) AS gpu_hours_rtx5090_effective,
    w.gpu_hours_h100,
    w.tp_star,
    w.n_star,
    w.overprovision_vision_x                                  AS overprovision_vision_x_as_ingested,
    COALESCE(w.overprovision_vision_x_corrected, w.overprovision_vision_x) AS overprovision_vision_x_effective,
    (w.overprovision_vision_x_corrected IS DISTINCT FROM w.overprovision_vision_x) AS overprovision_vision_x_is_superseded,
    w.overprovision_llm_x,
    COALESCE(w.correction_source, w.overprovision_correction_source) AS correction_source
FROM provenance.grid_window w;

COMMENT ON VIEW provenance.grid_window_effective IS
$$THE query surface for the per-window static-optimal grid. Always read this, never grid_window directly.

grid_window holds the raw, untouched ingest of simulation/results/grid/grid_summary.json, including values
later shown to be wrong. This view resolves every recorded supersession while keeping the pre-correction
value visible beside it (*_as_ingested) and naming the evidence (correction_source).

Live supersessions (see provenance.grid_correction for the full rationale of each):
  * burst5 c_star            16 -> 8   (queue-divergence heuristic was an endpoint artifact)
  * burst5 gpu_hours_rtx5090 21.59 -> 10.79
  * overprovision_vision_x, ALL SEVEN windows: recomputed against the corrected fleet count 8 (was 16).
    steady24h 8.0 -> 4.0 is the calm-day overprovisioning headline.

NOT superseded: burst1 c_star = 6 is correct under the all-request encoder-delay p99 that tab:base-grid
uses; the stage-conditional (image-bearing only) optimum of 7 is a different metric, filed in
grid_correction as correction_type = 'alternative_metric'.$$;

COMMENT ON COLUMN provenance.grid_window.c_star IS
  'RAW AS-INGESTED, may be superseded. Do not read directly -- use grid_window_effective.c_star_effective. Preserved unmodified so the pre-correction record survives (burst5 = 16 here, corrected to 8).';
COMMENT ON COLUMN provenance.grid_window.overprovision_vision_x IS
  'RAW AS-INGESTED, superseded on ALL SEVEN windows. Derived as (fleet static encoder workers)/(this window C*) with the stale fleet count 16. Use grid_window_effective.overprovision_vision_x_effective.';
COMMENT ON COLUMN provenance.grid_window.overprovision_vision_x_corrected IS
  'Recomputed against the corrected fleet count 8 and the corrected per-window C*. Populated for every window; equal to the ingested value only at burst5, whose own C* moved 16 -> 8 so the ratio stays 1.0.';
COMMENT ON COLUMN provenance.grid_window.overprovision_llm_x IS
  'Not superseded: (fleet LLM GPUs 4)/(this window LLM GPUs). 2.0 at steady24h (TP1x2 = 2 GPUs), 1.0 on the bursts (TP2x2 = 4 GPUs).';

CREATE OR REPLACE VIEW provenance.grid_run_summary_effective AS
SELECT
    s.grid_run_id,
    s.generated_utc,
    s.timing,
    s.sla_vision_p99_ms,
    s.sla_llm_ttft_p99_ms,
    s.sla_llm_itl_p99_ms,
    s.n_windows,
    s.static_encoder_workers                                       AS static_encoder_workers_as_ingested,
    COALESCE(s.static_encoder_workers_corrected, s.static_encoder_workers) AS static_encoder_workers_effective,
    s.static_encoder_workers_is_superseded,
    s.static_llm_tp,
    s.static_llm_workers,
    s.static_llm_gpus,
    s.static_binding_window,
    s.static_correction_source                                     AS correction_source,
    s.static_note,
    s.headline_note,
    s.is_valid,
    s.source_path
FROM provenance.grid_run_summary s;

COMMENT ON VIEW provenance.grid_run_summary_effective IS
$$THE query surface for the fleet-wide static configuration. Always read this, never grid_run_summary directly.

static_encoder_workers_as_ingested = 16 is the archived grid_summary.json value, computed as the max over a
per-window C* set in which burst5 was wrongly 16. static_encoder_workers_effective = 8 is the corrected max,
attained at burst2 and burst5 (verification/rerun-stability-e2e.md:137). The LLM side is unchanged: TP2, 2
workers, 4 GPUs, binding window burst1.

grid_run_summary.raw is the byte-faithful JSON of the pre-correction artifact, INCLUDING its
headline.overprovision_vs_per_window block, whose vision_x values are all stale. Read
grid_window_effective.overprovision_vision_x_effective instead.$$;

COMMENT ON COLUMN provenance.grid_run_summary.static_encoder_workers IS
  'RAW AS-INGESTED = 16, SUPERSEDED. Use grid_run_summary_effective.static_encoder_workers_effective (= 8).';
COMMENT ON COLUMN provenance.grid_run_summary.raw IS
  'Byte-faithful pre-correction JSON of grid_summary.json. Its headline.overprovision_vs_per_window.*.vision_x values are ALL stale (computed from static encoder workers = 16). Never quote them; use grid_window_effective.';


-- =====================================================================
-- PART B — WINDOW_ALIAS.md §3.2: normalise the window-name spellings
-- =====================================================================
-- 'week' == 'aggregate' == 'span_chronos' is ONE span (5.60 d, 749,601
-- requests, 483,659.8 s, trace_offset 250,399), proven on four axes in
-- WINDOW_ALIAS.md §1.2/§1.3.  'steady' == 'steady24h' is CONFIRMED
-- (identical trace_offset 627,019 / 88,260 requests / 23.999 h).
--
-- FIXED AT THE BASE TABLES, which is the defective side.  The tradeoff:
--
--   + a filter on the canonical name now returns the full population from
--     ANY relation, so the silent-undercount failure mode is structurally
--     gone rather than merely documented (today
--     `runs WHERE window_name='aggregate'` returns 6 of 135);
--   + C209/C210 go green, and windows() becomes a usable dimension;
--   - the as-ingested spelling would be lost, which is why every affected
--     table gains window_name_as_ingested, backfilled for EVERY row (not
--     just the renamed ones).  Nothing is destroyed: the original spelling
--     of every row remains queryable, and the rename is reconstructable
--     exactly by `WHERE window_name <> window_name_as_ingested`.
--
-- A window_name spelling is a LABEL, not a measurement, so normalising it
-- does not engage the never-destroy-a-measurement rule; the sibling column
-- is kept anyway so the ingest record stays auditable.
--
-- NOT folded: 'head2k' (genuinely distinct), 'fulltrace' (7 d / 1,000,000
-- requests, NOT the 5.60 d aggregate span).

ALTER TABLE provenance.runs                 ADD COLUMN IF NOT EXISTS window_name_as_ingested text;
ALTER TABLE provenance.composed_e2e         ADD COLUMN IF NOT EXISTS window_name_as_ingested text;
ALTER TABLE provenance.rerun_b1_window      ADD COLUMN IF NOT EXISTS window_name_as_ingested text;
ALTER TABLE provenance.rerun_b1_curve_point ADD COLUMN IF NOT EXISTS window_name_as_ingested text;

UPDATE provenance.runs                 SET window_name_as_ingested = window_name WHERE window_name_as_ingested IS NULL AND window_name IS NOT NULL;
UPDATE provenance.composed_e2e         SET window_name_as_ingested = window_name WHERE window_name_as_ingested IS NULL AND window_name IS NOT NULL;
UPDATE provenance.rerun_b1_window      SET window_name_as_ingested = window_name WHERE window_name_as_ingested IS NULL AND window_name IS NOT NULL;
UPDATE provenance.rerun_b1_curve_point SET window_name_as_ingested = window_name WHERE window_name_as_ingested IS NULL AND window_name IS NOT NULL;

UPDATE provenance.runs                 SET window_name = 'aggregate' WHERE window_name = 'week';    -- 129
UPDATE provenance.composed_e2e         SET window_name = 'aggregate' WHERE window_name = 'week';    --   4
UPDATE provenance.rerun_b1_window      SET window_name = 'steady24h' WHERE window_name = 'steady';  --   1
UPDATE provenance.rerun_b1_curve_point SET window_name = 'steady24h' WHERE window_name = 'steady';  --  20

COMMENT ON COLUMN provenance.runs.window_name_as_ingested IS
  'The spelling this row was ingested with, before window-name normalisation (WINDOW_ALIAS.md 3.2). Differs from window_name only for rows renamed by that pass: `WHERE window_name <> window_name_as_ingested` reconstructs the rename exactly (129 runs, week -> aggregate).';
COMMENT ON COLUMN provenance.composed_e2e.window_name_as_ingested IS
  'As-ingested spelling before window-name normalisation (WINDOW_ALIAS.md 3.2). 4 rows renamed week -> aggregate.';
COMMENT ON COLUMN provenance.rerun_b1_window.window_name_as_ingested IS
  'As-ingested spelling before window-name normalisation (WINDOW_ALIAS.md 3.2). 1 row renamed steady -> steady24h.';
COMMENT ON COLUMN provenance.rerun_b1_curve_point.window_name_as_ingested IS
  'As-ingested spelling before window-name normalisation (WINDOW_ALIAS.md 3.2). 20 rows renamed steady -> steady24h.';


-- ---------------------------------------------------------------------
-- B.1  Register head2k in the windows dimension.
-- ---------------------------------------------------------------------
-- head2k is referenced by sweep_window/sweep_point/sweep_curve/
-- sweep_decoupling/cost_model_variant but had no windows row, so
-- v_dim.window_span_s was NULL for it and no sweep_* cost ratio was
-- computable.  Facts from the archived trace stats, not invented:
--   simulation/results/sweeps/traces/llm_head2k.jsonl.stats.json
--     requests 2000, sim_horizon_s 721.072, mean_requests_per_s 2.774,
--     mean_images_per_s 7.985, text_only_fraction 0.3685
--   simulation/results/sweeps/summary.json -> windows.head2k.offset = 0

INSERT INTO provenance.windows
  (window_name, trace_offset, max_requests, requests, span_s,
   mean_req_per_s, mean_img_per_s, text_only_fraction, in_coverage, t0, note)
VALUES
  ('head2k', 0, 2000, 2000, 721.072, 2.774, 7.985, 0.3685, false,
   (SELECT t0 FROM provenance.windows WHERE window_name = 'fulltrace'),
   'trace head slice: the first 2000 requests of the 7-day trace, from its very start '
   '(2024-10-15 12:00:00.269 UTC), span 721.072 s. Used by the sweep_* family and by '
   'cost_model_variant. GENUINELY DISTINCT -- NOT an alias of aggregate or of anything else; '
   'do not fold it. in_coverage = false: it starts at trace offset 0, before every '
   'foundation-model forecastable span. Facts from '
   'simulation/results/sweeps/traces/llm_head2k.jsonl.stats.json and sweeps/summary.json.')
ON CONFLICT (window_name) DO UPDATE
  SET trace_offset = EXCLUDED.trace_offset,
      max_requests = EXCLUDED.max_requests,
      requests = EXCLUDED.requests,
      span_s = EXCLUDED.span_s,
      mean_req_per_s = EXCLUDED.mean_req_per_s,
      mean_img_per_s = EXCLUDED.mean_img_per_s,
      text_only_fraction = EXCLUDED.text_only_fraction,
      in_coverage = EXCLUDED.in_coverage,
      t0 = EXCLUDED.t0,
      note = EXCLUDED.note;


-- ---------------------------------------------------------------------
-- B.2  The alias dictionary, updated to the proven state.
-- ---------------------------------------------------------------------
-- After B, the week/steady folds are defensive no-ops -- kept so that a
-- future ingest writing the old spelling is still resolved by v_dim, and
-- so C210 keeps probing for it.  span_chronos is now registered (it is a
-- byte-identical duplicate row in windows(), kept as a separate name only
-- for the forecast-coverage narrative), which turns C211 green.

CREATE OR REPLACE VIEW provenance.v_window_alias AS
SELECT * FROM (VALUES
  ('week', 'aggregate',
   'CONFIRMED: requests=749601, total_images=11408002, completed_requests=749601 and '
   'max(worker_schedule.t_s)=483644.9 all identical to the aggregate window. Base tables NORMALISED '
   '2026-07-20 (runs 129, composed_e2e 4); this fold is now a defensive no-op guarding future ingests.'),
  ('steady', 'steady24h',
   'CONFIRMED (upgraded from PROBABLE): rerun_b1_window.steady had trace_offset=627019, total_reqs=88260, '
   'span_h=23.999 == windows.steady24h exactly. Base tables NORMALISED 2026-07-20 (rerun_b1_window 1, '
   'rerun_b1_curve_point 20); defensive no-op thereafter.'),
  ('span_chronos', 'aggregate',
   'CONFIRMED: byte-identical windows row (trace_offset=250399, requests=749601, span_s=483659.8). Kept as '
   'a separate windows() name only for the forecast-coverage narrative, where it is the chronos '
   'forecastable span alongside span_timesfm/span_toto/span_expctx. No base table outside windows() uses it.'),
  ('head2k', NULL,
   'GENUINELY DISTINCT: 2000-request, 721.072 s head slice used by the sweeps. DO NOT FOLD. Registered in '
   'windows() 2026-07-20, so sweep_* cost ratios are now computable.'),
  ('fulltrace', NULL,
   'GENUINELY DISTINCT: the whole 7-day trace, 1000000 requests / 604799.7 s. NOT the 5.60-day aggregate '
   'span (749601 req / 483659.8 s). DO NOT FOLD into aggregate.')
) t(alias, canonical_window, note);

COMMENT ON VIEW provenance.v_window_alias IS
$$Window-name synonym dictionary, as data.

canonical_window IS NULL means "this name is genuinely its own span -- folding it would be an error", and
the note says why. canonical_window NOT NULL means the two names provably denote the identical span.

As of the 2026-07-20 normalisation the two folding entries are defensive no-ops: no base table carries an
alias spelling any more (guard: check C210). They are retained so a future ingest that reintroduces the old
spelling is still resolved by v_dim and still trips C210.$$;


-- =====================================================================
-- PART C — ADJUDICATION §2.1 item 4 / Q8: silicon_multiworker burst5
-- =====================================================================
-- Q8 asked whether silicon_multiworker.json's burst5 C*=16 is an
-- INDEPENDENT confirmation of 16 or the SAME endpoint artifact.
-- Answered by verification/rerun-stability-e2e.md:116-129: it is the SAME
-- artifact. Both cost models flag burst5 non-divergent at every C >= 8;
-- the divergence flag is shared, not corroborating. burst5's real knees
-- are C=8 (AIC: cond p99 852 ms at C=8, 1038 at C=7) and C=15 (silicon:
-- 898 at C=15, 1045 at C=14).  Neither is 16.
--
-- CRITICAL DISTINCTION, and the reason the FLEET silicon number does NOT
-- move: the silicon-deployable fleet C* = max over windows = 16 STILL
-- STANDS -- it is now bound by burst2's genuine measured silicon p99 knee
-- (conditional p99 crosses 1000 between C=15 (1141) and C=16 (916)), not
-- by burst5's artifact (rerun-stability-e2e.md:131-147). Only the
-- PROVENANCE of the 16 moves. The AIC-costed fleet is 8 (Part A).

ALTER TABLE provenance.collector_multiworker_window
  ADD COLUMN IF NOT EXISTS aic_feasible_cstar_corrected       integer,
  ADD COLUMN IF NOT EXISTS silicon_feasible_cstar_corrected   integer,
  ADD COLUMN IF NOT EXISTS worker_inflation_x_corrected       double precision,
  ADD COLUMN IF NOT EXISTS silicon_p99_at_aic_cstar_corrected double precision,
  ADD COLUMN IF NOT EXISTS is_superseded                      boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS correction_source                  text;

UPDATE provenance.collector_multiworker_window
   SET aic_feasible_cstar_corrected       = 8,
       silicon_feasible_cstar_corrected   = 15,
       worker_inflation_x_corrected       = 1.88,   -- 15/8 = 1.875, 2 dp as in the archived column
       silicon_p99_at_aic_cstar_corrected = 1257.1, -- silicon all-request p99 at the corrected AIC C*=8
       is_superseded                      = true,
       correction_source                  = '/home/gio/tese/verification/rerun-stability-e2e.md'
 WHERE window_name = 'burst5'
   AND source_path LIKE '%silicon_multiworker.json'
   AND (aic_feasible_cstar_corrected IS DISTINCT FROM 8
        OR silicon_feasible_cstar_corrected IS DISTINCT FROM 15
        OR is_superseded IS DISTINCT FROM true);

DROP VIEW IF EXISTS provenance.collector_multiworker_window_effective;
CREATE VIEW provenance.collector_multiworker_window_effective AS
SELECT
    m.source_path,
    m.window_name,
    m.sla_ms,
    m.trace_offset,
    m.max_requests,
    m.n_image_reqs,
    m.total_images,
    m.grid_cstar_reported,
    m.aic_feasible_cstar                                                   AS aic_feasible_cstar_as_ingested,
    COALESCE(m.aic_feasible_cstar_corrected, m.aic_feasible_cstar)         AS aic_feasible_cstar_effective,
    m.silicon_feasible_cstar                                               AS silicon_feasible_cstar_as_ingested,
    COALESCE(m.silicon_feasible_cstar_corrected, m.silicon_feasible_cstar) AS silicon_feasible_cstar_effective,
    m.worker_inflation_x                                                   AS worker_inflation_x_as_ingested,
    COALESCE(m.worker_inflation_x_corrected, m.worker_inflation_x)         AS worker_inflation_x_effective,
    m.silicon_p99_at_aic_cstar                                             AS silicon_p99_at_aic_cstar_as_ingested,
    COALESCE(m.silicon_p99_at_aic_cstar_corrected, m.silicon_p99_at_aic_cstar) AS silicon_p99_at_aic_cstar_effective,
    m.aic_reproduces_grid,
    m.is_superseded,
    m.correction_source,
    m.canonical_fn_source
FROM provenance.collector_multiworker_window m;

COMMENT ON VIEW provenance.collector_multiworker_window_effective IS
$$THE query surface for the phase-E multiworker silicon-vs-AIC comparison. Read this, not the base table.

One supersession, burst5 (see provenance.grid_correction, correction_id 'silicon:burst5:*'):
  aic_feasible_cstar 16 -> 8, silicon_feasible_cstar 16 -> 15, worker_inflation_x 1.0 -> 1.88,
  silicon_p99_at_aic_cstar 783.6 -> 1257.1.
The ingested burst5 row inherited the grid's queue-divergence flag, later shown to be an endpoint artifact
under BOTH cost models. With it dropped, burst5 is p99-knee-limited exactly like the other five windows and
its 1.0x "no inflation" reading -- the one window that appeared to contradict the ~2x silicon underprice --
becomes 1.88x, in line with burst1 2.17, burst2 2.0, burst3 1.86, burst4 2.0, burst6 2.0.

The fleet-wide silicon-deployable C* = max over windows = 16 is UNCHANGED; it is now attained at burst2
(genuine measured knee, conditional p99 1141 at C=15 -> 916 at C=16) instead of at burst5's artifact.
The AIC-costed fleet C* is 8: see provenance.grid_run_summary_effective.$$;

COMMENT ON COLUMN provenance.collector_multiworker_window.aic_feasible_cstar IS
  'RAW AS-INGESTED from silicon_multiworker.json; SUPERSEDED at burst5 (16 -> 8). Use collector_multiworker_window_effective.';
COMMENT ON COLUMN provenance.collector_multiworker_window.silicon_feasible_cstar IS
  'RAW AS-INGESTED; SUPERSEDED at burst5 (16 -> 15). Use collector_multiworker_window_effective. NOTE the fleet max over windows stays 16, attained at burst2.';

INSERT INTO provenance.grid_correction
  (correction_id, window_name, field, correction_type,
   original_value, corrected_value, original_source, corrected_source,
   thesis_location, published_value, affects_headline, rationale)
VALUES
  ('silicon:burst5:aic_feasible_cstar:supersession', 'burst5', 'aic_feasible_cstar', 'supersession',
   16, 8,
   '/home/gio/tese/collector_artifacts/phaseE_physical_anchor/silicon_multiworker.json',
   '/home/gio/tese/verification/rerun-stability-e2e.md',
   'tex/aiconfigurator.tex:336-348', 8, false,
   'ANSWERS Q8. silicon_multiworker.json''s burst5 C*=16 is NOT an independent confirmation of the grid''s 16 '
   '-- it is the SAME endpoint artifact, inherited. Both cost models find burst5 non-divergent at every C >= 8. '
   'Dropping the flag leaves burst5 p99-knee-limited: AIC conditional p99 852 ms at C=8 vs 1038 ms at C=7, so '
   'the honest AIC knee is 8.'),
  ('silicon:burst5:silicon_feasible_cstar:supersession', 'burst5', 'silicon_feasible_cstar', 'supersession',
   16, 15,
   '/home/gio/tese/collector_artifacts/phaseE_physical_anchor/silicon_multiworker.json',
   '/home/gio/tese/verification/rerun-stability-e2e.md',
   'tex/aiconfigurator.tex:336-348', NULL, false,
   'Same artifact, silicon side: burst5''s measured-silicon knee is C=15 (conditional p99 898 ms at C=15 vs '
   '1045 ms at C=14), not 16. The knee ratio 15/8 = 1.9x restores burst5 to the ~2x silicon-underprice pattern '
   'of the other five windows instead of appearing as a 1.0x outlier. THE FLEET-WIDE SILICON C* = 16 IS '
   'UNCHANGED and must not be edited: it is the max over windows and is now attained at burst2, whose knee is '
   'genuine (conditional p99 1141 at C=15 -> 916 at C=16). Only its provenance moves from burst5 to burst2.')
ON CONFLICT (correction_id) DO UPDATE
  SET original_value = EXCLUDED.original_value,
      corrected_value = EXCLUDED.corrected_value,
      corrected_source = EXCLUDED.corrected_source,
      rationale = EXCLUDED.rationale;
