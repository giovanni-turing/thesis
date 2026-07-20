-- =========================================================================
-- 05_grid.sql -- family "grid": the STATIC-OPTIMAL GRID (ingest kind K20)
-- Engine: PostgreSQL 16.  Apply:
--   psql -h localhost -p 5433 -U goku -d postgres -v ON_ERROR_STOP=1 -f 05_grid.sql
-- Idempotent (CREATE TABLE IF NOT EXISTS / CREATE OR REPLACE VIEW).
--
-- WHAT THIS IS
--   Source: /home/gio/tese/simulation/results/grid/ (exhaustive brute-force sweep,
--   generated 2026-07-08, timing model "aic").  For each of 7 trace windows
--   (burst1..burst6, steady24h) the sweep walks encoder worker counts C and LLM
--   (TP, N) configurations, replays the window, and marks each point feasible or not
--   against a fixed SLA (vision p99 <= 1000 ms, LLM TTFT p99 <= 1000 ms,
--   LLM ITL p99 <= 100 ms).  The cheapest feasible point per window is that window's
--   PER-WINDOW OPTIMUM (c_star / tp_star / n_star).  The single config that is feasible
--   on EVERY window is the STATIC-OPTIMAL config (see grid_run_summary.static_*).
--
--   This family supplies the SLA-MINIMAL static denominator for cost-vs-static claims:
--   static_encoder_workers * window span_s = the worker-seconds a static fleet must buy
--   to pass every window.  See v_grid_static_vs_optimal below.
--
--   CAVEAT, verified against the loaded data -- do NOT conflate two different
--   denominators.  The thesis "0.62x cost vs static" headline is a WEEK-SCALE number:
--   provenance.encoder_run_summary for window_name='week' gives the autoscaled run
--   (e.g. a12:week_encoder_timesfm, 2,335,019.6 provisioned worker-seconds) over
--   misc:week_static_C8 (3,869,278.8 ws) = 0.603.  That denominator is a hand-chosen
--   C=8 static fleet, NOT this grid's C=16.  Against THIS grid's SLA-minimal static
--   config the burst windows come out ABOVE 1.0 (burst1 1.12x, burst4 1.29x) because
--   the autoscaler is tuned to a much tighter p99 (~588 ms) than the 1000 ms gate the
--   grid solves for; the saving is concentrated in calm traffic (steady24h 0.117x,
--   overprovision_vision_x 8.0).  Quote the grid as the feasibility-grounded static
--   baseline, and say which denominator you mean.
--
-- WHAT IS NOT HERE (deliberately -- would duplicate rows already in the schema)
--   * grid/reports/*.report.json (58) and grid/closeout/reports/*.report.json (35)
--     are already ingested by kind K1 into provenance.llm_run_summary (full ~68-key
--     report in .metrics jsonb).  grid_llm_point.report_run_id / grid_closeout_variant
--     .report_run_id are soft references into provenance.runs(run_id) for that detail.
--   * grid/traces/*.jsonl.stats.json (49) are already ingested by kind K3 into
--     provenance.encoder_run_summary.  grid_vision_point.stats_run_id points there.
--     (No grid_trace_stats table exists for exactly this reason.)
--   * grid/traces/*.jsonl (49 x ~14 MB) are simulator INPUT, never ingested; the path
--     is recorded in grid_vision_point.trace_path / grid_llm_point.trace_path.
--   * grid/closeout/{router,binding}_*.json (35) are byte-identical duplicates of the
--     corresponding entries in closeout_summary.json -> grid_closeout_variant.
--
-- FK POLICY: *_run_id columns are SOFT references (plain text, no FK constraint) so
-- this loader is order-independent w.r.t. the K1/K3 loaders.  Join on runs.run_id.
-- =========================================================================

CREATE SCHEMA IF NOT EXISTS provenance;
SET search_path = provenance, public;

-- -------------------------------------------------------------------------
-- 1. grid_run_summary -- the sweep header (one row per grid_summary.json)
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.grid_run_summary (
    grid_run_id                 text PRIMARY KEY,
    generated_utc               timestamptz,
    timing                      text,
    sla_vision_p99_ms           double precision,
    sla_llm_ttft_p99_ms         double precision,
    sla_llm_itl_p99_ms          double precision,
    n_windows                   int,
    n_vision_points             int,
    n_llm_points                int,
    n_failures                  int,
    failures                    jsonb,
    static_encoder_workers      int,
    static_llm_tp               int,
    static_llm_workers          int,
    static_llm_gpus             int,
    static_binding_window       text,
    static_note                 text,
    headline_note               text,
    is_valid                    boolean NOT NULL DEFAULT true,
    source_path                 text,
    raw                         jsonb
);

COMMENT ON TABLE provenance.grid_run_summary IS
 'K20: header of one static-optimal grid sweep (grid/grid_summary.json). Carries the SLA thresholds the whole family is judged against and the STATIC-OPTIMAL configuration -- the denominator of the "0.62x cost vs static" headline.';
COMMENT ON COLUMN provenance.grid_run_summary.grid_run_id IS 'Synthetic run id, ''grid:grid_summary'' (matches provenance.runs.run_id).';
COMMENT ON COLUMN provenance.grid_run_summary.timing IS 'Latency/cost model driving the replay: ''aic'' = aiconfigurator analytical model (vs a measured/poly converter elsewhere in the schema).';
COMMENT ON COLUMN provenance.grid_run_summary.sla_vision_p99_ms IS 'Vision-pool SLA: encoder delay p99 must be <= this (ms). 1000 in the shipped sweep.';
COMMENT ON COLUMN provenance.grid_run_summary.sla_llm_ttft_p99_ms IS 'Language-pool SLA: TTFT p99 must be <= this (ms). 1000 in the shipped sweep.';
COMMENT ON COLUMN provenance.grid_run_summary.sla_llm_itl_p99_ms IS 'Language-pool SLA: inter-token-latency p99 must be <= this (ms). 100 in the shipped sweep.';
COMMENT ON COLUMN provenance.grid_run_summary.n_failures IS 'Count of sweep cells that errored out (NOT infeasible cells -- infeasible is a valid result). 0 = clean sweep.';
COMMENT ON COLUMN provenance.grid_run_summary.failures IS 'Raw failures[] array from the summary; [] when the sweep completed cleanly.';
COMMENT ON COLUMN provenance.grid_run_summary.static_encoder_workers IS 'STATIC-OPTIMAL encoder worker count C: the single C feasible on ALL 7 windows (= max over windows of c_star). This times the window span is the static encoder cost denominator.';
COMMENT ON COLUMN provenance.grid_run_summary.static_llm_gpus IS 'GPUs held by the static LLM fleet = static_llm_tp * static_llm_workers. The static language-pool cost denominator per hour.';
COMMENT ON COLUMN provenance.grid_run_summary.static_binding_window IS 'The window whose per-window LLM optimum sets the all-windows static LLM config (the most expensive / binding window).';
COMMENT ON COLUMN provenance.grid_run_summary.static_note IS 'Author caveat shipped with the headline (feasibility is monotone in N at fixed TP but not across TP).';
COMMENT ON COLUMN provenance.grid_run_summary.is_valid IS 'FALSE marks a superseded/retracted sweep; never quote a FALSE row. All shipped rows are TRUE.';
COMMENT ON COLUMN provenance.grid_run_summary.raw IS 'grid_summary.json minus the per_window curves (which are exploded into grid_vision_point / grid_llm_point) -- lossless for the header.';

-- -------------------------------------------------------------------------
-- 2. grid_window -- per-window trace shape + per-window optimum + overprovision
--    (merges grid_summary.windows{} + per_window{} + headline.overprovision{})
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.grid_window (
    grid_run_id             text NOT NULL,
    window_name             text NOT NULL,
    trace_offset            bigint,
    max_requests            bigint,
    requests                bigint,
    span_s                  double precision,
    span_h                  double precision,
    mean_req_per_s          double precision,
    mean_img_per_s          double precision,
    peak_1min_img_per_s     double precision,
    text_only_fraction      double precision,
    c_star                  int,
    tp_star                 int,
    n_star                  int,
    llm_gpus                int,
    gpu_hours_rtx5090       double precision,
    gpu_hours_h100          double precision,
    overprovision_vision_x  double precision,
    overprovision_llm_x     double precision,
    n_vision_points         int,
    n_llm_points            int,
    note                    text,
    is_valid                boolean NOT NULL DEFAULT true,
    source_path             text,
    PRIMARY KEY (grid_run_id, window_name)
);
CREATE INDEX IF NOT EXISTS grid_window_name_idx ON provenance.grid_window (window_name);

COMMENT ON TABLE provenance.grid_window IS
 'K20: one row per trace window in the grid sweep. Merges three blocks of grid_summary.json (windows{} = trace shape, per_window{} = the per-window optimum and its GPU-hours, headline.overprovision_vs_per_window{} = static/optimum ratio). This is the per-window OPTIMUM side of the cost comparison; the STATIC side lives in grid_run_summary.static_*.';
COMMENT ON COLUMN provenance.grid_window.window_name IS 'burst1..burst6 (top-6 bursts by peak img/s, +/-10 min pad) or steady24h (a calm 24 h slice). Same vocabulary as provenance.windows / provenance.runs.window_name.';
COMMENT ON COLUMN provenance.grid_window.trace_offset IS 'Request-index offset into the 1M-request Azure trace where this window starts (named trace_offset, not the reserved word offset).';
COMMENT ON COLUMN provenance.grid_window.requests IS 'Requests actually replayed for this window (equals max_requests in every shipped row).';
COMMENT ON COLUMN provenance.grid_window.span_s IS 'Wall-clock span of the window in trace time (seconds).';
COMMENT ON COLUMN provenance.grid_window.span_h IS 'span_s in hours, as rounded by the sweep. The cost multiplier: GPU-hours = span_h * GPUs.';
COMMENT ON COLUMN provenance.grid_window.c_star IS 'PER-WINDOW OPTIMUM encoder worker count: the smallest C whose vision p99 meets the SLA on this window.';
COMMENT ON COLUMN provenance.grid_window.tp_star IS 'Per-window optimum LLM tensor-parallel degree.';
COMMENT ON COLUMN provenance.grid_window.n_star IS 'Per-window optimum LLM replica count N.';
COMMENT ON COLUMN provenance.grid_window.llm_gpus IS 'GPUs held by the per-window optimum LLM fleet = tp_star * n_star.';
COMMENT ON COLUMN provenance.grid_window.gpu_hours_rtx5090 IS 'ENCODER (vision-pool) GPU-hours of the per-window optimum = span_h * c_star; the encoder pool is priced on RTX 5090 in the thesis.';
COMMENT ON COLUMN provenance.grid_window.gpu_hours_h100 IS 'LANGUAGE-pool GPU-hours of the per-window optimum = span_h * llm_gpus; the LLM pool is priced on H100.';
COMMENT ON COLUMN provenance.grid_window.overprovision_vision_x IS 'Static-over-optimum encoder ratio for this window = static_encoder_workers / c_star. steady24h (8.0x) is the calm-traffic headline.';
COMMENT ON COLUMN provenance.grid_window.overprovision_llm_x IS 'Static-over-optimum language ratio for this window = static_llm_gpus / llm_gpus.';
COMMENT ON COLUMN provenance.grid_window.n_vision_points IS 'How many C values grid_summary''s vision_curve reports for this window (the per-file table grid_vision_point may hold a few more probes).';
COMMENT ON COLUMN provenance.grid_window.n_llm_points IS 'How many (C,TP,N) cells grid_summary''s llm_curve reports for this window.';
COMMENT ON COLUMN provenance.grid_window.note IS 'Free-text provenance of the slice (calendar span, peak img/s and its timestamp, burst onset minute).';

-- -------------------------------------------------------------------------
-- 3. grid_vision_point -- the encoder (vision pool) feasibility curve
--    one row per (window, C).  Source: vision_<w>_C<C>.json (superset, 48)
--    UNION grid_summary.per_window.<w>.vision_curve (43, strict subset).
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.grid_vision_point (
    grid_run_id             text NOT NULL,
    window_name             text NOT NULL,
    encoder_workers         int  NOT NULL,
    offered_img_per_s       double precision,
    horizon_s               double precision,
    delay_p50_ms            double precision,
    delay_p90_ms            double precision,
    delay_p99_ms            double precision,
    delay_max_ms            double precision,
    encoder_utilization     double precision,
    queue_divergent         boolean,
    feasible                boolean,
    is_c_star               boolean,
    in_summary_curve        boolean,
    curve_p99_ms            double precision,
    stats_run_id            text,
    trace_path              text,
    stats_path              text,
    is_valid                boolean NOT NULL DEFAULT true,
    source_path             text,
    PRIMARY KEY (grid_run_id, window_name, encoder_workers)
);
CREATE INDEX IF NOT EXISTS grid_vision_point_win_idx  ON provenance.grid_vision_point (window_name, encoder_workers);
CREATE INDEX IF NOT EXISTS grid_vision_point_feas_idx ON provenance.grid_vision_point (feasible);

COMMENT ON TABLE provenance.grid_vision_point IS
 'K20: encoder/vision-pool feasibility curve of the grid sweep -- one row per (window, encoder worker count C). feasible = delay_p99_ms <= grid_run_summary.sla_vision_p99_ms AND NOT queue_divergent. min(encoder_workers) WHERE feasible = that window''s c_star; max over windows of c_star = the static-optimal C.';
COMMENT ON COLUMN provenance.grid_vision_point.encoder_workers IS 'Encoder worker count C for this sweep point (the provisioning knob).';
COMMENT ON COLUMN provenance.grid_vision_point.offered_img_per_s IS 'Offered image load (img/s) over the window -- identical across C for a given window; the demand side.';
COMMENT ON COLUMN provenance.grid_vision_point.horizon_s IS 'Simulated horizon (s) for this point; matches grid_window.span_s.';
COMMENT ON COLUMN provenance.grid_vision_point.delay_p99_ms IS 'p99 encoder queueing+service delay (ms) -- THE vision-pool SLA metric. Rounded to 3 dp at source; the identical value at full source precision is in provenance.encoder_run_summary via stats_run_id.';
COMMENT ON COLUMN provenance.grid_vision_point.encoder_utilization IS 'Busy worker-seconds / provisioned worker-seconds over the window (0..1). Low values at feasible C are the overprovisioning the autoscaler attacks.';
COMMENT ON COLUMN provenance.grid_vision_point.queue_divergent IS 'TRUE if the encoder queue grew without bound (point is under-provisioned/unstable); such a point is never feasible.';
COMMENT ON COLUMN provenance.grid_vision_point.feasible IS 'Sweep''s own verdict for this point against the vision SLA. Authoritative.';
COMMENT ON COLUMN provenance.grid_vision_point.is_c_star IS 'TRUE if this C is the window''s per-window optimum (grid_window.c_star).';
COMMENT ON COLUMN provenance.grid_vision_point.in_summary_curve IS 'TRUE if grid_summary.json''s vision_curve also lists this point. FALSE for the 5 extra C=16 probes that exist only as vision_*.json files (they probe the static config on windows whose curve stopped earlier).';
COMMENT ON COLUMN provenance.grid_vision_point.curve_p99_ms IS 'The p99 as reported by grid_summary''s vision_curve; NULL when in_summary_curve is FALSE. Cross-check column -- equals delay_p99_ms in every shipped row.';
COMMENT ON COLUMN provenance.grid_vision_point.stats_run_id IS 'SOFT ref to provenance.runs(run_id) (= ''grid:grid_<window>_C<C>'') for the full 35-key encoder stats already loaded by kind K3 into provenance.encoder_run_summary. Join, do not duplicate.';
COMMENT ON COLUMN provenance.grid_vision_point.trace_path IS 'Path of the ~14 MB simulator INPUT trace (.jsonl). Recorded, never ingested.';
COMMENT ON COLUMN provenance.grid_vision_point.is_valid IS 'FALSE marks a superseded/retracted measurement; all shipped rows are TRUE.';

-- -------------------------------------------------------------------------
-- 4. grid_llm_point -- the language-pool feasibility curve
--    one row per (window, C, TP, N).  Source: llm_<w>_C<C>_N<N>[_TP<tp>]_aic.json
--    (58, full precision) joined to grid_summary.per_window.<w>.llm_curve (same 58).
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.grid_llm_point (
    grid_run_id             text NOT NULL,
    window_name             text NOT NULL,
    encoder_workers         int  NOT NULL,
    tp                      int  NOT NULL,
    llm_workers             int  NOT NULL,
    gpus                    int,
    timing                  text,
    ttft_mean_ms            double precision,
    ttft_median_ms          double precision,
    ttft_p90_ms             double precision,
    ttft_p99_ms             double precision,
    ttft_max_ms             double precision,
    itl_mean_ms             double precision,
    itl_median_ms           double precision,
    itl_p90_ms              double precision,
    itl_p99_ms              double precision,
    itl_max_ms              double precision,
    tpot_mean_ms            double precision,
    tpot_median_ms          double precision,
    tpot_p90_ms             double precision,
    tpot_p99_ms             double precision,
    tpot_max_ms             double precision,
    completed_requests      bigint,
    driver_wall_s           double precision,
    feasible                boolean,
    is_optimal              boolean,
    is_static_config        boolean,
    in_summary_curve        boolean,
    curve_ttft_p99_ms       double precision,
    curve_itl_p99_ms        double precision,
    report_run_id           text,
    report_path             text,
    trace_path              text,
    is_valid                boolean NOT NULL DEFAULT true,
    source_path             text,
    PRIMARY KEY (grid_run_id, window_name, encoder_workers, tp, llm_workers)
);
CREATE INDEX IF NOT EXISTS grid_llm_point_win_idx  ON provenance.grid_llm_point (window_name, tp, llm_workers);
CREATE INDEX IF NOT EXISTS grid_llm_point_feas_idx ON provenance.grid_llm_point (feasible);
CREATE INDEX IF NOT EXISTS grid_llm_point_run_idx  ON provenance.grid_llm_point (report_run_id);

COMMENT ON TABLE provenance.grid_llm_point IS
 'K20: language-pool feasibility curve of the grid sweep -- one row per (window, encoder C, tensor-parallel TP, replicas N). feasible = ttft_p99_ms <= sla_llm_ttft_p99_ms AND itl_p99_ms <= sla_llm_itl_p99_ms. Numbers are the FULL-PRECISION values from llm_*.json (identical to the ~68-key report reachable via report_run_id, which is NOT duplicated here).';
COMMENT ON COLUMN provenance.grid_llm_point.encoder_workers IS 'Encoder worker count C the composed trace was generated with -- the LLM point inherits the vision pool''s handoff timing, so C is part of the key.';
COMMENT ON COLUMN provenance.grid_llm_point.tp IS 'Tensor-parallel degree of one LLM worker (1 or 2) = GPUs per worker. TP1 source files omit the field entirely; the loader normalizes the implicit default to 1 (grid_summary''s llm_curve key spells it out as C<c>_TP1_N<n>).';
COMMENT ON COLUMN provenance.grid_llm_point.llm_workers IS 'LLM replica count N (named llm_workers; the sweep''s "N"). 1,2,4,8,16.';
COMMENT ON COLUMN provenance.grid_llm_point.gpus IS 'Total language-pool GPUs held = tp * llm_workers. The language-pool cost knob. Derived by the loader for TP1 rows, where the source file omits it.';
COMMENT ON COLUMN provenance.grid_llm_point.timing IS 'Latency model used for the replay: ''aic'' throughout this family.';
COMMENT ON COLUMN provenance.grid_llm_point.ttft_p99_ms IS 'p99 time-to-first-token (ms) -- primary language SLA metric (threshold 1000 ms).';
COMMENT ON COLUMN provenance.grid_llm_point.itl_p99_ms IS 'p99 inter-token latency (ms) -- second language SLA metric (threshold 100 ms).';
COMMENT ON COLUMN provenance.grid_llm_point.tpot_p99_ms IS 'p99 time-per-output-token (ms). Reported, not part of the feasibility gate.';
COMMENT ON COLUMN provenance.grid_llm_point.driver_wall_s IS 'Wall-clock seconds the replay driver took (harness cost, NOT a modeled result).';
COMMENT ON COLUMN provenance.grid_llm_point.feasible IS 'Sweep''s own verdict for this point against both language SLAs. Authoritative.';
COMMENT ON COLUMN provenance.grid_llm_point.is_optimal IS 'TRUE if (tp, llm_workers) equals this window''s per-window optimum (grid_window.tp_star/n_star) at its c_star.';
COMMENT ON COLUMN provenance.grid_llm_point.is_static_config IS 'TRUE if (tp, llm_workers) equals the all-windows STATIC-OPTIMAL LLM config (grid_run_summary.static_llm_tp / static_llm_workers), regardless of C.';
COMMENT ON COLUMN provenance.grid_llm_point.in_summary_curve IS 'TRUE if grid_summary''s llm_curve also lists this cell (TRUE for all 58 shipped rows).';
COMMENT ON COLUMN provenance.grid_llm_point.curve_ttft_p99_ms IS 'TTFT p99 as reported by grid_summary''s llm_curve. Cross-check column -- equals ttft_p99_ms in every shipped row.';
COMMENT ON COLUMN provenance.grid_llm_point.report_run_id IS 'SOFT ref to provenance.runs(run_id) (= ''grid:grid_llm_<window>_C<C>_N<N>[_TP<tp>]_aic'') for the full ~68-key aiperf-style report already loaded by kind K1 into provenance.llm_run_summary. Join, do not duplicate.';
COMMENT ON COLUMN provenance.grid_llm_point.is_valid IS 'FALSE marks a superseded/retracted measurement; all shipped rows are TRUE.';

-- -------------------------------------------------------------------------
-- 5. grid_closeout_run / grid_closeout_variant -- robustness closeout
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.grid_closeout_run (
    closeout_run_id         text PRIMARY KEY,
    generated_utc           timestamptz,
    binding_c               int,
    binding_tp              int,
    binding_n               int,
    n_variants              int,
    n_results               int,
    n_verdict_flips         int,
    n_binding_infeasible    int,
    n_failures              int,
    conclusion              text,
    router_variants         jsonb,
    router_verdict_flips    jsonb,
    binding_infeasible      jsonb,
    failures                jsonb,
    is_valid                boolean NOT NULL DEFAULT true,
    source_path             text
);

COMMENT ON TABLE provenance.grid_closeout_run IS
 'K20: header of the grid CLOSEOUT (grid/closeout/closeout_summary.json) -- the robustness check on the static-optimal result. It re-replays each window under perturbed router knobs, and re-replays the static ("binding") config on every window, asserting that no feasibility verdict flips. conclusion carries the PASS/FAIL sentence.';
COMMENT ON COLUMN provenance.grid_closeout_run.binding_c IS 'Encoder worker count of the binding/static config re-verified on every window (16).';
COMMENT ON COLUMN provenance.grid_closeout_run.binding_tp IS 'Tensor-parallel degree of the binding/static LLM config (2).';
COMMENT ON COLUMN provenance.grid_closeout_run.binding_n IS 'Replica count of the binding/static LLM config (2).';
COMMENT ON COLUMN provenance.grid_closeout_run.n_verdict_flips IS 'Number of (window, config) pairs whose feasible verdict changed under a router-knob perturbation. 0 = the static-optimal conclusion is robust to router tuning.';
COMMENT ON COLUMN provenance.grid_closeout_run.n_binding_infeasible IS 'Number of windows on which the static/binding config was NOT feasible. Must be 0 for the static config to be a legitimate cost denominator.';
COMMENT ON COLUMN provenance.grid_closeout_run.router_variants IS 'Knob settings probed, as {variant_name: {knob: value}} (overlap_score_credit 0.25/0.5, prefill_load_scale 0.5/2.0).';

CREATE TABLE IF NOT EXISTS provenance.grid_closeout_variant (
    closeout_run_id     text NOT NULL,
    tag                 text NOT NULL,
    family              text,
    window_name         text,
    encoder_workers     int,
    tp                  int,
    llm_workers         int,
    variant             text,
    variant_knob        text,
    variant_value       double precision,
    ttft_p99_ms         double precision,
    itl_p99_ms          double precision,
    feasible            boolean,
    wall_s              double precision,
    report_run_id       text,
    is_valid            boolean NOT NULL DEFAULT true,
    source_path         text,
    PRIMARY KEY (closeout_run_id, tag)
);
CREATE INDEX IF NOT EXISTS grid_closeout_variant_win_idx ON provenance.grid_closeout_variant (window_name, family);

COMMENT ON TABLE provenance.grid_closeout_variant IS
 'K20: one row per closeout replay (35 = 28 router-knob perturbations + 7 binding-config re-verifications), exploded from closeout_summary.json results{}. The 35 standalone closeout/{router,binding}_*.json files are byte-identical duplicates of these rows and are deliberately NOT ingested.';
COMMENT ON COLUMN provenance.grid_closeout_variant.tag IS 'Full run tag as emitted, e.g. router_burst1_C6_TP2_N2_credit0.25 or binding_burst1_C16_TP2_N2. Parsed into the columns beside it.';
COMMENT ON COLUMN provenance.grid_closeout_variant.family IS '''router'' = router-knob sensitivity replay at the window''s own optimum; ''binding'' = the static/binding config replayed on this window.';
COMMENT ON COLUMN provenance.grid_closeout_variant.variant IS 'Router-knob variant label (credit0.25, credit0.5, pls0.5, pls2.0); NULL for the binding family.';
COMMENT ON COLUMN provenance.grid_closeout_variant.variant_knob IS 'Which router knob the variant moved: overlap_score_credit or prefill_load_scale.';
COMMENT ON COLUMN provenance.grid_closeout_variant.variant_value IS 'Numeric value the knob was set to.';
COMMENT ON COLUMN provenance.grid_closeout_variant.feasible IS 'Verdict against the same SLA triple. Compare to grid_llm_point.feasible at the same (window, C, tp, N) to detect a verdict flip.';
COMMENT ON COLUMN provenance.grid_closeout_variant.wall_s IS 'Wall-clock seconds of the replay (harness cost, not a modeled result).';
COMMENT ON COLUMN provenance.grid_closeout_variant.report_run_id IS 'SOFT ref to provenance.runs(run_id) (= ''grid:'' || tag) for the full report already loaded by kind K1 into provenance.llm_run_summary.';

-- -------------------------------------------------------------------------
-- 6. grid_command -- reproduction provenance harvested from the .log headers
-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS provenance.grid_command (
    log_path        text PRIMARY KEY,
    grid_run_id     text,
    stage           text,
    artifact_stem   text,
    window_name     text,
    encoder_workers int,
    tp              int,
    llm_workers     int,
    variant         text,
    cmd             text,
    cwd             text,
    log_bytes       bigint
);
CREATE INDEX IF NOT EXISTS grid_command_stem_idx ON provenance.grid_command (artifact_stem);

COMMENT ON TABLE provenance.grid_command IS
 'K20: reproduction provenance for the grid family. Only the ''# cmd:'' / ''# cwd:'' header of each grid/logs/*.log and grid/closeout/logs/*.log is kept (149 files); the log bodies are simulator noise and are NOT ingested. This is the exact command line that produced each artifact.';
COMMENT ON COLUMN provenance.grid_command.stage IS '''trace'' = trace_to_two_pool.py generating the composed .jsonl (vision stage); ''llm'' = run_replay.sh replaying it through the LLM sim; ''closeout_router'' / ''closeout_binding'' = the closeout replays.';
COMMENT ON COLUMN provenance.grid_command.artifact_stem IS 'Log basename without .log; equals the stem of the artifact it produced, so it joins to runs.run_id as ''grid:'' || artifact_stem.';
COMMENT ON COLUMN provenance.grid_command.cmd IS 'Verbatim command line (includes --offset / --max-requests for trace stage, AIC_TP and --router-config for replay stage).';
COMMENT ON COLUMN provenance.grid_command.cwd IS 'Working directory the command was run from.';

-- =========================================================================
-- VIEWS -- the cost comparison the family exists to support
-- =========================================================================

CREATE OR REPLACE VIEW provenance.v_grid_static_vs_optimal AS
SELECT w.grid_run_id,
       w.window_name,
       w.span_h,
       -- encoder / vision pool
       w.c_star                                            AS optimal_encoder_workers,
       s.static_encoder_workers,
       w.gpu_hours_rtx5090                                 AS optimal_encoder_gpu_hours,
       w.span_h * s.static_encoder_workers                 AS static_encoder_gpu_hours,
       w.gpu_hours_rtx5090
         / NULLIF(w.span_h * s.static_encoder_workers, 0)  AS encoder_cost_ratio_vs_static,
       w.overprovision_vision_x,
       -- language pool
       w.llm_gpus                                          AS optimal_llm_gpus,
       s.static_llm_gpus,
       w.gpu_hours_h100                                    AS optimal_llm_gpu_hours,
       w.span_h * s.static_llm_gpus                        AS static_llm_gpu_hours,
       w.gpu_hours_h100
         / NULLIF(w.span_h * s.static_llm_gpus, 0)         AS llm_cost_ratio_vs_static,
       w.overprovision_llm_x
FROM provenance.grid_window w
JOIN provenance.grid_run_summary s ON s.grid_run_id = w.grid_run_id
WHERE w.is_valid AND s.is_valid;

COMMENT ON VIEW provenance.v_grid_static_vs_optimal IS
 'Per window: GPU-hours of the per-window optimum vs GPU-hours of the all-windows STATIC-OPTIMAL config, both pools, plus the cost ratio (optimal/static; <1 means the static config overpays). This is the pure-SQL denominator for the thesis "cost vs static" claims -- the autoscaled numerator lives in provenance.cost_accounting / encoder_run_summary.';

CREATE OR REPLACE VIEW provenance.v_grid_cheapest_feasible AS
SELECT v.grid_run_id,
       v.window_name,
       MIN(v.encoder_workers) FILTER (WHERE v.feasible)      AS cheapest_feasible_c,
       MIN(l.gpus)            FILTER (WHERE l.feasible)      AS cheapest_feasible_llm_gpus,
       w.c_star,
       w.llm_gpus                                            AS recorded_optimal_llm_gpus
FROM provenance.grid_vision_point v
JOIN provenance.grid_window w
  ON w.grid_run_id = v.grid_run_id AND w.window_name = v.window_name
LEFT JOIN provenance.grid_llm_point l
  ON l.grid_run_id = v.grid_run_id AND l.window_name = v.window_name AND l.is_valid
WHERE v.is_valid
GROUP BY v.grid_run_id, v.window_name, w.c_star, w.llm_gpus;

COMMENT ON VIEW provenance.v_grid_cheapest_feasible IS
 'Recomputes each window''s optimum straight from the feasibility curves (cheapest feasible C, cheapest feasible LLM GPU count) and puts it beside the value grid_summary.json recorded. A mismatch means the shipped headline disagrees with its own grid -- an audit view.';

-- =========================================================================
-- Remaining column comments (shared/repeated columns + the closeout tables)
-- =========================================================================

-- shared identity / provenance columns
COMMENT ON COLUMN provenance.grid_window.grid_run_id       IS 'FK-by-convention to grid_run_summary.grid_run_id -- which sweep this row belongs to.';
COMMENT ON COLUMN provenance.grid_vision_point.grid_run_id IS 'FK-by-convention to grid_run_summary.grid_run_id -- which sweep this row belongs to.';
COMMENT ON COLUMN provenance.grid_llm_point.grid_run_id    IS 'FK-by-convention to grid_run_summary.grid_run_id -- which sweep this row belongs to.';
COMMENT ON COLUMN provenance.grid_command.grid_run_id      IS 'FK-by-convention to grid_run_summary.grid_run_id.';
COMMENT ON COLUMN provenance.grid_window.source_path            IS 'Absolute path of the JSON file this row was parsed from.';
COMMENT ON COLUMN provenance.grid_vision_point.source_path      IS 'Absolute path of the JSON file this row was parsed from.';
COMMENT ON COLUMN provenance.grid_llm_point.source_path         IS 'Absolute path of the JSON file this row was parsed from.';
COMMENT ON COLUMN provenance.grid_run_summary.source_path       IS 'Absolute path of the JSON file this row was parsed from.';
COMMENT ON COLUMN provenance.grid_closeout_run.source_path      IS 'Absolute path of the JSON file this row was parsed from.';
COMMENT ON COLUMN provenance.grid_closeout_variant.source_path  IS 'Absolute path of the JSON file this row was parsed from (all 35 rows come from closeout_summary.json).';
COMMENT ON COLUMN provenance.grid_llm_point.window_name         IS 'Trace window replayed; joins grid_window.window_name / runs.window_name.';
COMMENT ON COLUMN provenance.grid_vision_point.window_name      IS 'Trace window replayed; joins grid_window.window_name / runs.window_name.';
COMMENT ON COLUMN provenance.grid_closeout_variant.window_name  IS 'Trace window replayed, parsed out of tag; joins grid_window.window_name.';
COMMENT ON COLUMN provenance.grid_command.window_name           IS 'Trace window, parsed out of the log filename.';
COMMENT ON COLUMN provenance.grid_run_summary.generated_utc     IS 'UTC timestamp the sweep summary was written (sweep completion time).';
COMMENT ON COLUMN provenance.grid_closeout_run.generated_utc    IS 'UTC timestamp the closeout summary was written.';
COMMENT ON COLUMN provenance.grid_closeout_run.closeout_run_id  IS 'Synthetic run id, ''grid:closeout_summary''.';
COMMENT ON COLUMN provenance.grid_closeout_variant.closeout_run_id IS 'FK-by-convention to grid_closeout_run.closeout_run_id.';

-- distribution columns: same metric at other points of the latency distribution.
-- p99 is the SLA gate; mean/median/p90/max are context only.
COMMENT ON COLUMN provenance.grid_llm_point.ttft_mean_ms   IS 'Mean time-to-first-token (ms). Context only -- feasibility is decided on ttft_p99_ms.';
COMMENT ON COLUMN provenance.grid_llm_point.ttft_median_ms IS 'Median (p50) time-to-first-token (ms). Context only.';
COMMENT ON COLUMN provenance.grid_llm_point.ttft_p90_ms    IS 'p90 time-to-first-token (ms). Context only.';
COMMENT ON COLUMN provenance.grid_llm_point.ttft_max_ms    IS 'Worst-case time-to-first-token (ms) over the window. Context only.';
COMMENT ON COLUMN provenance.grid_llm_point.itl_mean_ms    IS 'Mean inter-token latency (ms). Context only -- feasibility is decided on itl_p99_ms.';
COMMENT ON COLUMN provenance.grid_llm_point.itl_median_ms  IS 'Median (p50) inter-token latency (ms). Context only.';
COMMENT ON COLUMN provenance.grid_llm_point.itl_p90_ms     IS 'p90 inter-token latency (ms). Context only.';
COMMENT ON COLUMN provenance.grid_llm_point.itl_max_ms     IS 'Worst-case inter-token latency (ms). Context only.';
COMMENT ON COLUMN provenance.grid_llm_point.tpot_mean_ms   IS 'Mean time-per-output-token (ms). Not part of the feasibility gate.';
COMMENT ON COLUMN provenance.grid_llm_point.tpot_median_ms IS 'Median time-per-output-token (ms). Not part of the feasibility gate.';
COMMENT ON COLUMN provenance.grid_llm_point.tpot_p90_ms    IS 'p90 time-per-output-token (ms). Not part of the feasibility gate.';
COMMENT ON COLUMN provenance.grid_llm_point.tpot_max_ms    IS 'Worst-case time-per-output-token (ms). Not part of the feasibility gate.';
COMMENT ON COLUMN provenance.grid_llm_point.completed_requests IS 'Requests that finished in the replay; should equal grid_window.requests for a healthy point.';
COMMENT ON COLUMN provenance.grid_llm_point.curve_itl_p99_ms   IS 'ITL p99 as reported by grid_summary''s llm_curve. Cross-check column -- equals itl_p99_ms in every shipped row.';
COMMENT ON COLUMN provenance.grid_llm_point.report_path        IS 'Path of the full ~68-key report.json. NOT ingested here (already loaded by kind K1); use report_run_id to join provenance.llm_run_summary.';
COMMENT ON COLUMN provenance.grid_llm_point.trace_path         IS 'Path of the ~14 MB simulator INPUT trace (.jsonl). Recorded, never ingested.';
COMMENT ON COLUMN provenance.grid_vision_point.stats_path      IS 'Path of the 35-key encoder stats JSON. NOT ingested here (already loaded by kind K3); use stats_run_id to join provenance.encoder_run_summary.';
COMMENT ON COLUMN provenance.grid_vision_point.delay_p50_ms    IS 'p50 encoder delay (ms). Context only -- feasibility is decided on delay_p99_ms.';
COMMENT ON COLUMN provenance.grid_vision_point.delay_p90_ms    IS 'p90 encoder delay (ms). Context only.';
COMMENT ON COLUMN provenance.grid_vision_point.delay_max_ms    IS 'Worst-case encoder delay (ms) over the window. Context only.';

-- closeout detail
COMMENT ON COLUMN provenance.grid_closeout_run.n_variants IS 'Number of distinct router-knob settings probed (4).';
COMMENT ON COLUMN provenance.grid_closeout_run.n_results  IS 'Total closeout replays recorded = 28 router + 7 binding = 35.';
COMMENT ON COLUMN provenance.grid_closeout_run.n_failures IS 'Replays that errored out. 0 = clean closeout.';
COMMENT ON COLUMN provenance.grid_closeout_run.conclusion IS 'Verbatim PASS/FAIL sentence the closeout emitted. Quote this when asked whether the static-optimal result is robust.';
COMMENT ON COLUMN provenance.grid_closeout_run.router_verdict_flips IS 'Raw list of (window, config) pairs whose feasibility verdict changed under a router perturbation; [] on a PASS.';
COMMENT ON COLUMN provenance.grid_closeout_run.binding_infeasible   IS 'Raw list of windows on which the static/binding config failed the SLA; [] on a PASS.';
COMMENT ON COLUMN provenance.grid_closeout_run.failures  IS 'Raw failures[] array from the closeout summary; [] when clean.';
COMMENT ON COLUMN provenance.grid_closeout_run.is_valid  IS 'FALSE marks a superseded/retracted closeout; the shipped row is TRUE.';
COMMENT ON COLUMN provenance.grid_closeout_variant.encoder_workers IS 'Encoder worker count C of the replayed config, parsed out of tag.';
COMMENT ON COLUMN provenance.grid_closeout_variant.tp              IS 'Tensor-parallel degree of the replayed LLM config, parsed out of tag.';
COMMENT ON COLUMN provenance.grid_closeout_variant.llm_workers     IS 'LLM replica count N of the replayed config, parsed out of tag.';
COMMENT ON COLUMN provenance.grid_closeout_variant.ttft_p99_ms     IS 'p99 time-to-first-token (ms) of this closeout replay; compare to grid_llm_point.ttft_p99_ms at the same key.';
COMMENT ON COLUMN provenance.grid_closeout_variant.itl_p99_ms      IS 'p99 inter-token latency (ms) of this closeout replay.';
COMMENT ON COLUMN provenance.grid_closeout_variant.is_valid        IS 'FALSE marks a superseded/retracted replay; all shipped rows are TRUE.';

-- command log detail
COMMENT ON COLUMN provenance.grid_command.log_path        IS 'Absolute path of the .log file the header was harvested from (primary key). The log BODY is not ingested.';
COMMENT ON COLUMN provenance.grid_command.log_bytes       IS 'Size of the (un-ingested) log file in bytes.';
COMMENT ON COLUMN provenance.grid_command.encoder_workers IS 'Encoder worker count C, parsed out of the log filename.';
COMMENT ON COLUMN provenance.grid_command.tp              IS 'Tensor-parallel degree, parsed out of the log filename; NULL for trace-stage logs, defaulted to 1 for llm-stage logs with no TP token.';
COMMENT ON COLUMN provenance.grid_command.llm_workers     IS 'LLM replica count N, parsed out of the log filename; NULL for trace-stage logs.';
COMMENT ON COLUMN provenance.grid_command.variant         IS 'Router-knob variant label for closeout logs; NULL otherwise.';

COMMENT ON COLUMN provenance.grid_run_summary.n_windows      IS 'Number of trace windows in the sweep (7: burst1..burst6 + steady24h).';
COMMENT ON COLUMN provenance.grid_run_summary.n_vision_points IS 'Number of (window, C) points in grid_summary''s vision_curve blocks (43). grid_vision_point holds 48 -- the extra 5 are C=16 probes that exist only as vision_*.json files.';
COMMENT ON COLUMN provenance.grid_run_summary.n_llm_points   IS 'Number of (window, C, TP, N) cells in grid_summary''s llm_curve blocks (58 = exactly the grid_llm_point row count).';
COMMENT ON COLUMN provenance.grid_run_summary.static_llm_tp      IS 'STATIC-OPTIMAL LLM tensor-parallel degree (GPUs per worker) held on every window.';
COMMENT ON COLUMN provenance.grid_run_summary.static_llm_workers IS 'STATIC-OPTIMAL LLM replica count N held on every window.';
COMMENT ON COLUMN provenance.grid_run_summary.headline_note  IS 'Author note shipped with the overprovisioning headline (points at steady24h as the calm-traffic row).';

COMMENT ON COLUMN provenance.grid_window.max_requests        IS 'Request cap applied when slicing the window out of the trace; equals requests in every shipped row.';
COMMENT ON COLUMN provenance.grid_window.mean_req_per_s      IS 'Mean request arrival rate over the window (req/s).';
COMMENT ON COLUMN provenance.grid_window.mean_img_per_s      IS 'Mean image arrival rate over the window (img/s) -- the vision pool''s demand.';
COMMENT ON COLUMN provenance.grid_window.peak_1min_img_per_s IS 'Peak 1-minute image arrival rate (img/s) -- the burst intensity that forces the static config up.';
COMMENT ON COLUMN provenance.grid_window.text_only_fraction  IS 'Fraction of requests with no image (they skip the encoder pool entirely).';
COMMENT ON COLUMN provenance.grid_window.is_valid            IS 'FALSE marks a superseded/retracted window result; all shipped rows are TRUE.';
