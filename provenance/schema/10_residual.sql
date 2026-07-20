-- =========================================================================
-- 10_residual.sql -- the last ingest gaps: artifacts that each back a
-- PUBLISHED thesis number and were not reachable by any earlier loader.
--
--   K25  simulation/results/sweeps/      -> sweep_*         (tab:sim-knees, fig:sim-knees)
--   K26  simulation/results/{srcbuild,}  -> cost_model_*    (tab:sim-poly-aic)
--   K27  predictors/results/ewma_cal_manifest.json -> ewma_cal_*
--   K28  verification/rerun_b1_results.json        -> rerun_b1_*
--   K29  analysis/trace_eda/series/rates_*.parquet -> eda_rate_series
--
-- Plus a schema change that is not an ingest at all (see the bottom of this
-- file): an explicit, queryable representation of the burst5 C* correction,
-- which until now existed only as prose in tex/apendice.tex.
--
-- Convention note: every table here carries source_path so a row can be
-- traced back to the exact file, and provenance.ingest_log holds that file's
-- sha256. Nothing in this file re-loads data another kind already owns; where
-- a richer artifact already lives in another table it is soft-referenced by
-- run_id rather than copied.
-- =========================================================================

-- =========================================================================
-- K25 -- the saturation-knee load sweep (simulation/results/sweeps/)
-- =========================================================================
-- The sweep asks one question per (pool, window, timing): as the arrival
-- speedup s rises, at what s does the pool's SLA metric first cross its
-- bound? The per-point JSONs and summary.json carry the same 30 points;
-- summary.json additionally carries the derived curves and the knees, which
-- is what the thesis table actually prints.
--
-- NOT re-ingested here (already owned by earlier kinds, soft-ref'd by run_id):
--   sweeps/reports/*.report.json      (19) -> K1 llm_run_summary
--   sweeps/series/*.series.json       (12) -> K5 encoder_series
--   sweeps/traces/*.jsonl.stats.json  (14) -> K3 encoder_run_summary
--   sweeps/traces/*.jsonl             (14) -> K6 composed_request
--   sweeps/logs/*.log                 (32) -- driver stdout, no unique facts
-- -------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS provenance.sweep_run (
    sweep_run_id                text PRIMARY KEY,
    generated_utc               timestamptz,
    thr_encoder_delay_p99_ms    double precision,
    thr_ttft_p99_ms             double precision,
    thr_itl_p99_ms              double precision,
    threshold_note              text,
    mech_llm                    text,
    mech_vision                 text,
    n_points                    int,
    n_curves                    int,
    all_exit_codes_zero         boolean,
    n_offered_scaling_issues    int,
    n_nonmonotonic_curves       int,
    source_path                 text
);

COMMENT ON TABLE provenance.sweep_run IS
 'K25: one row -- the load-sweep campaign behind tab:sim-knees / fig:sim-knees, parsed from simulation/results/sweeps/summary.json. Holds the SLA thresholds the knees are defined against, the two arrival-speedup mechanisms, and the sweep''s own self-check (sanity{}). Generator: simulation/sweep_load.py; figure: simulation/sweep_fig.py.';
COMMENT ON COLUMN provenance.sweep_run.sweep_run_id IS 'Stable id of the sweep campaign (''sweeps:summary''). Parent of sweep_window / sweep_point / sweep_curve / sweep_decoupling.';
COMMENT ON COLUMN provenance.sweep_run.generated_utc IS 'summary.json generated_utc: when the aggregation was rebuilt from the per-point files.';
COMMENT ON COLUMN provenance.sweep_run.thr_encoder_delay_p99_ms IS 'Evaluation-SLA bound on VISION encoder-delay p99 (1000 ms). The bound whose first crossing defines a vision-pool knee.';
COMMENT ON COLUMN provenance.sweep_run.thr_ttft_p99_ms IS 'Evaluation-SLA bound on LANGUAGE TTFT p99 (1000 ms).';
COMMENT ON COLUMN provenance.sweep_run.thr_itl_p99_ms IS 'Evaluation-SLA bound on LANGUAGE inter-token-latency p99 (100 ms). Distinct from the TTFT bound and frequently the FIRST to break: the thesis calls such knees "ITL-bound".';
COMMENT ON COLUMN provenance.sweep_run.threshold_note IS 'Verbatim note from summary.json recording that these are tail-based evaluation targets, while the SLA-Planner baseline runs its own window-mean targets (ttft 500 / itl 50) as policy config. Kept because the two target sets are easy to confuse.';
COMMENT ON COLUMN provenance.sweep_run.mech_llm IS 'How arrival speedup s is applied to the language pool: native dynamo.replay --arrival-speedup-ratio on the s=1 isolation trace (timestamps divided by s).';
COMMENT ON COLUMN provenance.sweep_run.mech_vision IS 'How arrival speedup s is applied to the vision pool: the converter rescales inter-arrival gaps by 1/s and re-runs the FIFO encoder sim, emitting a separate trace per point.';
COMMENT ON COLUMN provenance.sweep_run.n_points IS 'Number of swept points in summary.json points[] (30).';
COMMENT ON COLUMN provenance.sweep_run.n_curves IS 'Number of (pool,window,timing) curves in summary.json curves{} (6).';
COMMENT ON COLUMN provenance.sweep_run.all_exit_codes_zero IS 'sanity.all_exit_codes_zero: TRUE if every swept point''s simulator exited 0. A FALSE here invalidates the knees.';
COMMENT ON COLUMN provenance.sweep_run.n_offered_scaling_issues IS 'Count of sanity.offered_scaling_issues: points where offered load did not scale as s*base (0 = clean). Guards against the speedup mechanism silently not applying.';
COMMENT ON COLUMN provenance.sweep_run.n_nonmonotonic_curves IS 'Count of sanity.nonmonotonic_curves: curves whose SLA metric fell as s rose (0 = clean). Non-monotonicity would make "first crossing" ill-defined.';
COMMENT ON COLUMN provenance.sweep_run.source_path IS 'Absolute path of summary.json.';


CREATE TABLE IF NOT EXISTS provenance.sweep_window (
    sweep_run_id  text NOT NULL,
    window_name   text NOT NULL,
    trace_offset  bigint,
    max_requests  bigint,
    note          text,
    source_path   text,
    PRIMARY KEY (sweep_run_id, window_name)
);

COMMENT ON TABLE provenance.sweep_window IS
 'K25: the two trace windows swept, from summary.json windows{}. Vocabulary is NARROWER than provenance.grid_window / provenance.windows: the sweep uses head2k (the steady 2000-request trace head) and burst1 (the week''s largest burst episode, +/-10 min pad), not the full burst1..burst6 grid.';
COMMENT ON COLUMN provenance.sweep_window.sweep_run_id IS 'Parent sweep campaign; joins sweep_run.sweep_run_id.';
COMMENT ON COLUMN provenance.sweep_window.window_name IS 'head2k or burst1. burst1 denotes the SAME trace slice as grid_window.window_name=''burst1'' (offset 843072, 64804 requests), so the two tables join on it; head2k has no grid counterpart.';
COMMENT ON COLUMN provenance.sweep_window.trace_offset IS 'Request-index offset into the 1M-request Azure trace where the window starts.';
COMMENT ON COLUMN provenance.sweep_window.max_requests IS 'Requests replayed from that offset.';
COMMENT ON COLUMN provenance.sweep_window.note IS 'Free-text shape of the slice (calendar span, mean req/s and img/s, peak img/s and its timestamp) -- the provenance of the "2.77 req/s / 8.0 img/s" and "2.17 req/s / 116 img/s" figures quoted in the tab:sim-knees caption.';
COMMENT ON COLUMN provenance.sweep_window.source_path IS 'Absolute path of summary.json.';


CREATE TABLE IF NOT EXISTS provenance.sweep_point (
    sweep_run_id            text NOT NULL,
    pool                    text NOT NULL,
    window_name             text NOT NULL,
    timing                  text NOT NULL,
    speedup                 double precision NOT NULL,
    -- topology
    llm_workers             int,
    encoder_workers         int,
    image_px                int,
    encoder_batch_images    int,
    mechanism               text,
    -- offered load (base = the window's own recorded rate; offered = base * s)
    base_req_per_s          double precision,
    base_img_per_s          double precision,
    base_input_tok_per_s    double precision,
    base_output_tok_per_s   double precision,
    offered_req_per_s       double precision,
    offered_img_per_s       double precision,
    offered_input_tok_per_s double precision,
    offered_output_tok_per_s double precision,
    offered_total_tok_per_s double precision,
    -- scale of the run
    requests                bigint,
    total_images            bigint,
    horizon_s               double precision,
    -- LANGUAGE-pool measured throughput
    measured_req_per_s      double precision,
    measured_output_tok_s   double precision,
    measured_total_tok_s    double precision,
    measured_duration_ms    double precision,
    completed_requests      bigint,
    sim_wall_time_ms        double precision,
    driver_wall_s           double precision,
    -- LANGUAGE-pool latency distributions
    ttft_mean_ms            double precision,
    ttft_median_ms          double precision,
    ttft_p90_ms             double precision,
    ttft_p99_ms             double precision,
    ttft_max_ms             double precision,
    tpot_mean_ms            double precision,
    tpot_median_ms          double precision,
    tpot_p90_ms             double precision,
    tpot_p99_ms             double precision,
    tpot_max_ms             double precision,
    itl_mean_ms             double precision,
    itl_median_ms           double precision,
    itl_p90_ms              double precision,
    itl_p99_ms              double precision,
    itl_max_ms              double precision,
    e2e_mean_ms             double precision,
    e2e_median_ms           double precision,
    e2e_p90_ms              double precision,
    e2e_p99_ms              double precision,
    e2e_max_ms              double precision,
    itl_ok                  boolean,
    -- VISION-pool encoder distributions
    enc_delay_p50_ms        double precision,
    enc_delay_p90_ms        double precision,
    enc_delay_p99_ms        double precision,
    enc_delay_max_ms        double precision,
    enc_service_p50_ms      double precision,
    enc_service_p90_ms      double precision,
    enc_service_p99_ms      double precision,
    enc_batch_service_p50_ms double precision,
    enc_batch_service_p90_ms double precision,
    enc_batch_service_p99_ms double precision,
    enc_batch_service_max_ms double precision,
    handoff_p50_ms          double precision,
    handoff_p90_ms          double precision,
    handoff_p99_ms          double precision,
    handoff_max_ms          double precision,
    encoder_utilization     double precision,
    queue_divergent         boolean,
    batches                 bigint,
    vision_sim_end_s        double precision,
    -- queue depth, derived from the per-second series (see column comments)
    queue_imgs_max          int,
    queue_imgs_mean         double precision,
    queue_imgs_final        int,
    busy_workers_max        int,
    -- the SLA view: one comparable number per point
    sla_metric              text,
    sla_metric_p99_ms       double precision,
    sla_threshold_ms        double precision,
    over_threshold          boolean,
    -- provenance / soft refs
    exit_code               int,
    trace_path              text,
    report_path             text,
    stats_path              text,
    series_path             text,
    report_run_id           text,
    series_run_id           text,
    source_path             text,
    PRIMARY KEY (sweep_run_id, pool, window_name, timing, speedup)
);
CREATE INDEX IF NOT EXISTS sweep_point_curve_idx ON provenance.sweep_point (pool, window_name, timing, speedup);

COMMENT ON TABLE provenance.sweep_point IS
 'K25: one row per swept point (pool x window x timing x arrival speedup s) -- 30 rows, the raw material of fig:sim-knees. Deliberately a SINGLE table spanning both pools rather than two: the whole point of the chapter is that the two pools saturate at different s on the same load axis, and that comparison should be one query, not a union. Columns are therefore sparse by construction -- language points leave every enc_*/handoff_*/queue_* column NULL and vision points leave every ttft_*/tpot_*/itl_*/e2e_* column NULL. Use sla_metric_p99_ms for the pool-agnostic comparison. Each row is parsed from its own per-point JSON (source_path); summary.json points[] carries byte-equivalent copies.';
COMMENT ON COLUMN provenance.sweep_point.sweep_run_id IS 'Parent sweep campaign; joins sweep_run.sweep_run_id.';
COMMENT ON COLUMN provenance.sweep_point.pool IS 'llm (language pool: prefill+decode of Qwen3-VL-8B at TP1, 2 workers) or vision (encoder pool: ViT at 448 px, batch 64, 2 workers). The two pools are simulated by different mechanisms -- see sweep_run.mech_llm / mech_vision.';
COMMENT ON COLUMN provenance.sweep_point.window_name IS 'head2k or burst1; joins sweep_window.window_name.';
COMMENT ON COLUMN provenance.sweep_point.timing IS 'Cost model pricing the pool: poly (the mocker''s default polynomial) or aic (aiconfigurator''s calibrated h100_sxm / vLLM 0.22.0 database). Vision points are aic-only -- there is no polynomial encoder model -- so a poly-vs-aic contrast exists for the language pool only.';
COMMENT ON COLUMN provenance.sweep_point.speedup IS 'Arrival speedup s: the multiplier applied to the window''s recorded arrival rate. s=1 replays the trace at its own recorded rate, so an SLA violation at s=1 means the pool cannot serve the real traffic.';
COMMENT ON COLUMN provenance.sweep_point.llm_workers IS 'Language-pool worker count (2 throughout; the topology is locked so that s is the only axis). NULL for vision points.';
COMMENT ON COLUMN provenance.sweep_point.encoder_workers IS 'Encoder-pool worker count (2 throughout). NULL for language points.';
COMMENT ON COLUMN provenance.sweep_point.image_px IS 'Encoder input resolution in pixels per side (448). NULL for language points.';
COMMENT ON COLUMN provenance.sweep_point.encoder_batch_images IS 'Encoder batch size in images (64). NULL for language points.';
COMMENT ON COLUMN provenance.sweep_point.mechanism IS 'Verbatim per-point record of how the speedup was applied; redundant with sweep_run.mech_* but kept per row because the two pools differ and a point should be self-describing.';
COMMENT ON COLUMN provenance.sweep_point.base_req_per_s IS 'The window''s OWN recorded request rate (independent of s). offered_req_per_s = base_req_per_s * speedup.';
COMMENT ON COLUMN provenance.sweep_point.base_img_per_s IS 'The window''s own recorded image rate. Vision points only. The burst1/head2k contrast lives here: 116 vs 8.0 img/s at nearly identical req/s -- images per request, not requests, is what bursts.';
COMMENT ON COLUMN provenance.sweep_point.base_input_tok_per_s IS 'Window''s own input-token rate. Language points only.';
COMMENT ON COLUMN provenance.sweep_point.base_output_tok_per_s IS 'Window''s own output-token rate. Language points only.';
COMMENT ON COLUMN provenance.sweep_point.offered_req_per_s IS 'OFFERED request load at this point = base * s. This is the x-axis of fig:sim-knees for language rows and the "Offered" column of tab:sim-knees.';
COMMENT ON COLUMN provenance.sweep_point.offered_img_per_s IS 'Offered image load = base_img_per_s * s. The x-axis for vision rows and the "Offered" column of tab:sim-knees vision rows.';
COMMENT ON COLUMN provenance.sweep_point.offered_input_tok_per_s IS 'Offered input-token load = base * s. Language points only.';
COMMENT ON COLUMN provenance.sweep_point.offered_output_tok_per_s IS 'Offered output-token load = base * s. Language points only.';
COMMENT ON COLUMN provenance.sweep_point.offered_total_tok_per_s IS 'Offered total (input+output) token load. Language points only.';
COMMENT ON COLUMN provenance.sweep_point.requests IS 'Requests in the replayed window (2000 for head2k, 64804 for burst1). Constant across s -- s compresses time, it does not add requests.';
COMMENT ON COLUMN provenance.sweep_point.total_images IS 'Images encoded over the window. Vision points only.';
COMMENT ON COLUMN provenance.sweep_point.horizon_s IS 'Simulated horizon in seconds AT s=1 (the window''s natural span); the actual simulated span at speedup s is horizon_s/s.';
COMMENT ON COLUMN provenance.sweep_point.measured_req_per_s IS 'Achieved request throughput from the simulator. Compare against offered_req_per_s: a gap means the pool could not keep up. Language points only.';
COMMENT ON COLUMN provenance.sweep_point.measured_output_tok_s IS 'Achieved output-token throughput. Language points only.';
COMMENT ON COLUMN provenance.sweep_point.measured_total_tok_s IS 'Achieved total-token throughput. Language points only.';
COMMENT ON COLUMN provenance.sweep_point.measured_duration_ms IS 'Simulated wall duration of the replay in ms. Language points only.';
COMMENT ON COLUMN provenance.sweep_point.completed_requests IS 'Requests that completed. Equals requests in every shipped point; a shortfall would invalidate the tail statistics. Language points only.';
COMMENT ON COLUMN provenance.sweep_point.sim_wall_time_ms IS 'The simulator''s own reported compute time. REAL time spent simulating, not simulated time -- an instrumentation cost, not a result.';
COMMENT ON COLUMN provenance.sweep_point.driver_wall_s IS 'Real seconds the driver process took end-to-end for this point.';
COMMENT ON COLUMN provenance.sweep_point.ttft_mean_ms IS 'Time-to-first-token, mean (ms). Language points only.';
COMMENT ON COLUMN provenance.sweep_point.ttft_median_ms IS 'TTFT median (ms).';
COMMENT ON COLUMN provenance.sweep_point.ttft_p90_ms IS 'TTFT p90 (ms).';
COMMENT ON COLUMN provenance.sweep_point.ttft_p99_ms IS 'TTFT p99 (ms) -- the language pool''s SLA metric, compared against sweep_run.thr_ttft_p99_ms. Printed in the last column of tab:sim-knees for language rows.';
COMMENT ON COLUMN provenance.sweep_point.ttft_max_ms IS 'TTFT maximum (ms). The extreme tail; sensitive to instrumentation overhead (see the wheel-vs-source-build note on cost_model_variant.runtime).';
COMMENT ON COLUMN provenance.sweep_point.tpot_mean_ms IS 'Time-per-output-token, mean (ms). Language points only.';
COMMENT ON COLUMN provenance.sweep_point.tpot_median_ms IS 'TPOT median (ms).';
COMMENT ON COLUMN provenance.sweep_point.tpot_p90_ms IS 'TPOT p90 (ms).';
COMMENT ON COLUMN provenance.sweep_point.tpot_p99_ms IS 'TPOT p99 (ms).';
COMMENT ON COLUMN provenance.sweep_point.tpot_max_ms IS 'TPOT maximum (ms).';
COMMENT ON COLUMN provenance.sweep_point.itl_mean_ms IS 'Inter-token latency, mean (ms). Language points only. Distinct from TPOT: ITL is the gap between consecutive tokens, TPOT amortizes over the whole decode.';
COMMENT ON COLUMN provenance.sweep_point.itl_median_ms IS 'ITL median (ms).';
COMMENT ON COLUMN provenance.sweep_point.itl_p90_ms IS 'ITL p90 (ms).';
COMMENT ON COLUMN provenance.sweep_point.itl_p99_ms IS 'ITL p99 (ms) -- compared against the 100 ms bound. This is what makes the steady-window language knees "ITL-bound": ITL p99 crosses 100 ms while TTFT p99 is still far under 1000 ms, so the knee sits below where the TTFT curve would put it.';
COMMENT ON COLUMN provenance.sweep_point.itl_max_ms IS 'ITL maximum (ms).';
COMMENT ON COLUMN provenance.sweep_point.e2e_mean_ms IS 'End-to-end request latency, mean (ms). Language points only.';
COMMENT ON COLUMN provenance.sweep_point.e2e_median_ms IS 'E2E median (ms).';
COMMENT ON COLUMN provenance.sweep_point.e2e_p90_ms IS 'E2E p90 (ms).';
COMMENT ON COLUMN provenance.sweep_point.e2e_p99_ms IS 'E2E p99 (ms).';
COMMENT ON COLUMN provenance.sweep_point.e2e_max_ms IS 'E2E maximum (ms).';
COMMENT ON COLUMN provenance.sweep_point.itl_ok IS 'Per-point _itl_ok flag from the sweep: TRUE if this point met the ITL p99 bound. Present on language points only; this is the flag that distinguishes an "ITL-bound" knee from a TTFT-bound one.';
COMMENT ON COLUMN provenance.sweep_point.enc_delay_p50_ms IS 'Encoder DELAY (queue wait + service, i.e. what a request experiences) p50 in ms. Vision points only.';
COMMENT ON COLUMN provenance.sweep_point.enc_delay_p90_ms IS 'Encoder delay p90 (ms).';
COMMENT ON COLUMN provenance.sweep_point.enc_delay_p99_ms IS 'Encoder delay p99 (ms) -- the vision pool''s SLA metric, compared against sweep_run.thr_encoder_delay_p99_ms. Printed in the last column of tab:sim-knees for vision rows.';
COMMENT ON COLUMN provenance.sweep_point.enc_delay_max_ms IS 'Encoder delay maximum (ms).';
COMMENT ON COLUMN provenance.sweep_point.enc_service_p50_ms IS 'Encoder SERVICE time p50 (ms) -- time on the GPU, excluding queue wait. delay minus service is queueing, which is what actually explodes under burst.';
COMMENT ON COLUMN provenance.sweep_point.enc_service_p90_ms IS 'Encoder service p90 (ms).';
COMMENT ON COLUMN provenance.sweep_point.enc_service_p99_ms IS 'Encoder service p99 (ms).';
COMMENT ON COLUMN provenance.sweep_point.enc_batch_service_p50_ms IS 'Per-BATCH encoder service time p50 (ms). A batch of up to encoder_batch_images images is the scheduling unit; at saturation every batch is full, so this collapses to a constant (316.369 ms at 448 px / 64 images) -- visible as p50=p90=p99=max in the burst1 rows.';
COMMENT ON COLUMN provenance.sweep_point.enc_batch_service_p90_ms IS 'Per-batch encoder service p90 (ms).';
COMMENT ON COLUMN provenance.sweep_point.enc_batch_service_p99_ms IS 'Per-batch encoder service p99 (ms).';
COMMENT ON COLUMN provenance.sweep_point.enc_batch_service_max_ms IS 'Per-batch encoder service maximum (ms) = the full-batch cost.';
COMMENT ON COLUMN provenance.sweep_point.handoff_p50_ms IS 'Encoder-to-language handoff time p50 (ms): moving the projector output between pools. Bounded and small even under saturation -- the thesis'' "handoff bound" claim.';
COMMENT ON COLUMN provenance.sweep_point.handoff_p90_ms IS 'Handoff p90 (ms).';
COMMENT ON COLUMN provenance.sweep_point.handoff_p99_ms IS 'Handoff p99 (ms).';
COMMENT ON COLUMN provenance.sweep_point.handoff_max_ms IS 'Handoff maximum (ms).';
COMMENT ON COLUMN provenance.sweep_point.encoder_utilization IS 'Fraction of encoder-GPU time busy over the window, 0..1. The decoupling evidence: at the calibrated language knee on the steady window the encoder sits at ~0.045, i.e. the language pool saturates while the encoder idles.';
COMMENT ON COLUMN provenance.sweep_point.queue_divergent IS 'Sweep''s own flag for an encoder queue that never drains within the horizon. FALSE at every shipped point -- note that a non-divergent queue can still blow the delay SLA by orders of magnitude, which is why the knee is defined on enc_delay_p99_ms and not on this flag. (The same divergence heuristic is what mis-set burst5''s C* in the grid sweep -- see provenance.grid_correction.)';
COMMENT ON COLUMN provenance.sweep_point.batches IS 'Encoder batches executed over the window. Vision points only.';
COMMENT ON COLUMN provenance.sweep_point.vision_sim_end_s IS 'Simulated end time of the encoder sim (s). Exceeding horizon_s means work outlived the arrival stream, i.e. a backlog at the end of the window.';
COMMENT ON COLUMN provenance.sweep_point.queue_imgs_max IS 'DERIVED (not in the JSON): peak encoder queue depth in images, computed by this loader from the point''s per-second series file (max of queue_imgs_end). The full per-second trajectory is NOT duplicated here -- it lives in provenance.encoder_series under series_run_id, already loaded by kind K5. Vision points only, and only where a series file exists.';
COMMENT ON COLUMN provenance.sweep_point.queue_imgs_mean IS 'DERIVED: mean encoder queue depth in images over the window (mean of queue_imgs_end across all seconds). Contrast with queue_imgs_max: a large max with a small mean is a transient spike, both large is genuine saturation.';
COMMENT ON COLUMN provenance.sweep_point.queue_imgs_final IS 'DERIVED: encoder queue depth in images at the LAST second of the series. Non-zero means the window ended with an undrained backlog -- the honest saturation signal, and the one the divergence heuristic tried and failed to capture.';
COMMENT ON COLUMN provenance.sweep_point.busy_workers_max IS 'DERIVED: peak simultaneously-busy encoder workers (max of busy_workers_end). Equals encoder_workers whenever the pool ever fully saturates.';
COMMENT ON COLUMN provenance.sweep_point.sla_metric IS 'Which metric governs this pool''s knee: ttft_p99 for language rows, encoder_delay_p99 for vision rows. Makes sla_metric_p99_ms self-describing across pools.';
COMMENT ON COLUMN provenance.sweep_point.sla_metric_p99_ms IS 'The pool-agnostic comparison column: ttft_p99_ms for language rows, enc_delay_p99_ms for vision rows. This is the "metric" array in summary.json curves{} and the y-axis of fig:sim-knees. NOTE it does NOT capture the ITL bound, so a language point can be under this value''s threshold and still be over SLA -- see itl_ok and sweep_curve.knee_is_itl_bound.';
COMMENT ON COLUMN provenance.sweep_point.sla_threshold_ms IS 'The threshold sla_metric_p99_ms is compared against (1000 ms for both pools'' primary metric), copied per row so the comparison is self-contained.';
COMMENT ON COLUMN provenance.sweep_point.over_threshold IS 'TRUE if sla_metric_p99_ms > sla_threshold_ms, i.e. this point violates its pool''s PRIMARY bound. The first TRUE along a curve is sweep_curve.first_over_speedup. Again: does not account for the ITL bound.';
COMMENT ON COLUMN provenance.sweep_point.exit_code IS 'Simulator exit code; 0 at every shipped point (aggregated as sweep_run.all_exit_codes_zero).';
COMMENT ON COLUMN provenance.sweep_point.trace_path IS 'Absolute path of the trace replayed at this point (simulator INPUT; content loaded by kind K6 for the composed traces).';
COMMENT ON COLUMN provenance.sweep_point.report_path IS 'Absolute path of the language-pool report JSON; its contents are loaded by kind K1, not duplicated here. Language points only.';
COMMENT ON COLUMN provenance.sweep_point.stats_path IS 'Absolute path of the encoder stats sidecar; contents loaded by kind K3. Vision points only.';
COMMENT ON COLUMN provenance.sweep_point.series_path IS 'Absolute path of the per-second encoder series JSON; contents loaded by kind K5. Vision points only.';
COMMENT ON COLUMN provenance.sweep_point.report_run_id IS 'Soft reference (no FK) to provenance.llm_run_summary.run_id / runs.run_id for report_path, so the full per-request detail is one join away.';
COMMENT ON COLUMN provenance.sweep_point.series_run_id IS 'Soft reference (no FK) to provenance.encoder_series.run_id for series_path -- join here to recover the full per-second queue trajectory that queue_imgs_* only summarizes.';
COMMENT ON COLUMN provenance.sweep_point.source_path IS 'Absolute path of the per-point JSON this row was parsed from (e.g. sweeps/llm_head2k_poly_s1.json). summary.json points[] holds an equivalent copy.';


CREATE TABLE IF NOT EXISTS provenance.sweep_curve (
    sweep_run_id            text NOT NULL,
    pool                    text NOT NULL,
    window_name             text NOT NULL,
    timing                  text NOT NULL,
    sla_metric              text,
    threshold_ms            double precision,
    n_points                int,
    speedups                double precision[],
    metric_ms               double precision[],
    offered                 double precision[],
    offered_unit            text,
    metric_at_s1_ms         double precision,
    offered_at_s1           double precision,
    knee_speedup            double precision,
    knee_offered            double precision,
    knee_metric_ms          double precision,
    first_over_speedup      double precision,
    first_over_metric_ms    double precision,
    knee_is_itl_bound       boolean,
    knee_censored           boolean,
    over_at_s1              boolean,
    saturated_in_range      boolean,
    monotonic_ok            boolean,
    monotonicity_violations text[],
    source_path             text,
    PRIMARY KEY (sweep_run_id, pool, window_name, timing)
);

-- Re-applying this file over an earlier version of the table: CREATE TABLE IF
-- NOT EXISTS is a no-op on an existing table and would silently skip columns
-- added after it was first created.
ALTER TABLE provenance.sweep_curve
    ADD COLUMN IF NOT EXISTS metric_at_s1_ms double precision,
    ADD COLUMN IF NOT EXISTS offered_at_s1   double precision;

COMMENT ON TABLE provenance.sweep_curve IS
 'K25: one row per (pool, window, timing) curve -- 6 rows, and THIS IS THE TABLE BEHIND tab:sim-knees: one published table row per curve row. Parsed from summary.json curves{}, whose keys are "pool|window|timing". The knee columns are the sweep''s own derivation, re-checkable against provenance.sweep_point (see the view-style query in the loader docstring). The parallel arrays speedups/metric_ms/offered are kept as arrays because they are exactly what fig:sim-knees plots; the same data is available row-wise in sweep_point.';
COMMENT ON COLUMN provenance.sweep_curve.sweep_run_id IS 'Parent sweep campaign; joins sweep_run.sweep_run_id.';
COMMENT ON COLUMN provenance.sweep_curve.pool IS 'llm or vision; joins sweep_point.pool.';
COMMENT ON COLUMN provenance.sweep_curve.window_name IS 'head2k or burst1; joins sweep_window.window_name.';
COMMENT ON COLUMN provenance.sweep_curve.timing IS 'poly or aic; joins sweep_point.timing. Vision curves are aic-only.';
COMMENT ON COLUMN provenance.sweep_curve.sla_metric IS 'Metric this curve is drawn on: ttft_p99 (language) or encoder_delay_p99 (vision).';
COMMENT ON COLUMN provenance.sweep_curve.threshold_ms IS 'The bound the metric is compared against (1000 ms). Copied from summary.json curves[].threshold.';
COMMENT ON COLUMN provenance.sweep_curve.n_points IS 'Number of swept speedups on this curve (2..7 -- the sweep is deliberately uneven, refining near each pool''s knee rather than gridding uniformly).';
COMMENT ON COLUMN provenance.sweep_curve.speedups IS 'Ascending array of swept arrival speedups s. Index-aligned with metric_ms and offered.';
COMMENT ON COLUMN provenance.sweep_curve.metric_ms IS 'Array of sla_metric values in ms, index-aligned with speedups. The y-axis of fig:sim-knees.';
COMMENT ON COLUMN provenance.sweep_curve.offered IS 'Array of offered load, index-aligned with speedups. The x-axis of fig:sim-knees. UNITS DIFFER BY POOL -- see offered_unit.';
COMMENT ON COLUMN provenance.sweep_curve.offered_unit IS 'Unit of the offered array: req_per_s for language curves, img_per_s for vision curves. Recorded explicitly because the two pools'' load axes are not comparable -- the chapter''s central claim ("no single load axis serves both pools").';
COMMENT ON COLUMN provenance.sweep_curve.metric_at_s1_ms IS 'DERIVED: sla_metric at s=1, i.e. the pool''s p99 under the window''s OWN recorded traffic with no speedup. This is the LEFT value of the "X -> Y" last column of tab:sim-knees (the right value is knee_metric_ms); where the knee is itself s=1, or there is no knee, the published table collapses to this single number. Kept as a column because "what does the pool do on the real trace" is the question most often asked of this table.';
COMMENT ON COLUMN provenance.sweep_curve.offered_at_s1 IS 'DERIVED: offered load at s=1 in offered_unit -- the window''s own recorded rate. Equals sweep_point.base_req_per_s / base_img_per_s for the same curve.';
COMMENT ON COLUMN provenance.sweep_curve.knee_speedup IS 'THE KNEE: the largest swept s meeting EVERY SLA bound (both TTFT and ITL for language curves). NULL means no swept point passed -- the pool is already over its bound at s=1 (see over_at_s1). This is the "Knee" column of tab:sim-knees.';
COMMENT ON COLUMN provenance.sweep_curve.knee_offered IS 'DERIVED: offered load at knee_speedup, in offered_unit. The "Offered" column of tab:sim-knees. NULL when there is no knee.';
COMMENT ON COLUMN provenance.sweep_curve.knee_metric_ms IS 'DERIVED: sla_metric value at the knee (ms) -- the left half of the "X -> Y" last column of tab:sim-knees.';
COMMENT ON COLUMN provenance.sweep_curve.first_over_speedup IS 'The smallest swept s whose PRIMARY metric exceeds threshold_ms. Note this is generally NOT knee_speedup + one step: for ITL-bound language curves the knee sits strictly below first_over, because ITL breaks while TTFT is still fine. Where first_over_speedup = 1.0 the pool fails at the trace''s own recorded rate.';
COMMENT ON COLUMN provenance.sweep_curve.first_over_metric_ms IS 'DERIVED: sla_metric value at first_over_speedup (ms) -- the right half of the "X -> Y" last column of tab:sim-knees, and the single quoted value for curves with no knee.';
COMMENT ON COLUMN provenance.sweep_curve.knee_is_itl_bound IS 'DERIVED: TRUE when the point immediately after the knee still meets the TTFT bound but fails the ITL bound -- i.e. decode saturates the SLA before prefill queueing does. Printed as "(ITL-bound)" in tab:sim-knees. Computed from sweep_point.itl_ok, not present in summary.json.';
COMMENT ON COLUMN provenance.sweep_curve.knee_censored IS 'DERIVED: TRUE when the metric never crossed threshold_ms anywhere in the swept range, so the knee is a LOWER BOUND (">= s=32", "cens." in tab:sim-knees) rather than a measurement. Only the vision/head2k curve is censored.';
COMMENT ON COLUMN provenance.sweep_curve.over_at_s1 IS 'DERIVED: TRUE when the curve is already over its bound at s=1, i.e. the pool cannot serve the window''s REAL recorded traffic. Printed as "none: over at s=1" in tab:sim-knees; true for both AIC-timed pools on the burst window.';
COMMENT ON COLUMN provenance.sweep_curve.saturated_in_range IS 'summary.json flag: TRUE if the curve crossed its threshold somewhere in the swept range. Its negation is knee_censored.';
COMMENT ON COLUMN provenance.sweep_curve.monotonic_ok IS 'summary.json flag: TRUE if the metric rose monotonically with s. Must be TRUE for "first crossing" to be well defined.';
COMMENT ON COLUMN provenance.sweep_curve.monotonicity_violations IS 'Any monotonicity violations found (empty in every shipped curve); kept as text so a violation is legible rather than merely counted.';
COMMENT ON COLUMN provenance.sweep_curve.source_path IS 'Absolute path of summary.json.';


CREATE TABLE IF NOT EXISTS provenance.sweep_decoupling (
    sweep_run_id                text NOT NULL,
    window_name                 text NOT NULL,
    llm_timing                  text NOT NULL,
    vision_knee_speedup         double precision,
    llm_knee_speedup            double precision,
    knees_differ                boolean,
    llm_over_vision_knee_ratio  double precision,
    source_path                 text,
    PRIMARY KEY (sweep_run_id, window_name, llm_timing)
);

COMMENT ON TABLE provenance.sweep_decoupling IS
 'K25: one row per (window, language timing) pairing the two pools'' knees -- the quantitative statement of the chapter''s decoupling claim, from summary.json decoupling{} (keys "window|llm-timing"). If the pools saturated together these ratios would be ~1; they are not, which is the argument for scaling the two pools independently.';
COMMENT ON COLUMN provenance.sweep_decoupling.sweep_run_id IS 'Parent sweep campaign; joins sweep_run.sweep_run_id.';
COMMENT ON COLUMN provenance.sweep_decoupling.window_name IS 'head2k or burst1; joins sweep_window.window_name.';
COMMENT ON COLUMN provenance.sweep_decoupling.llm_timing IS 'Which language-pool cost model is being compared against the (always AIC-timed) vision pool: poly or aic.';
COMMENT ON COLUMN provenance.sweep_decoupling.vision_knee_speedup IS 'The vision pool''s knee s on this window (from sweep_curve where pool=vision). NULL where vision has no knee (burst window: over at s=1). For the steady window this is a CENSORED lower bound of 32 -- see sweep_curve.knee_censored -- so head2k ratios understate the true decoupling.';
COMMENT ON COLUMN provenance.sweep_decoupling.llm_knee_speedup IS 'The language pool''s knee s on this window at llm_timing. NULL where the language pool has no knee.';
COMMENT ON COLUMN provenance.sweep_decoupling.knees_differ IS 'TRUE when the two pools'' knees are not equal -- i.e. one pool saturates before the other and a single fleet-wide load target would misprovision one of them.';
COMMENT ON COLUMN provenance.sweep_decoupling.llm_over_vision_knee_ratio IS 'llm_knee_speedup / vision_knee_speedup. Well under 1 (0.094 poly, 0.062 aic on the steady window) means the LANGUAGE pool is the earlier bottleneck by more than 10x in load terms, while the encoder still idles. NULL where either knee is NULL.';
COMMENT ON COLUMN provenance.sweep_decoupling.source_path IS 'Absolute path of summary.json.';


-- =========================================================================
-- K26 -- polynomial vs calibrated (AIC) cost model, same load and topology
-- =========================================================================
-- Three families of paired runs, each a {poly, aic} pair over an identical
-- window and topology, so the ONLY difference is how decode time is priced:
--   head2k_src  simulation/results/srcbuild/llm_head2k_{poly,aic}_src.json
--               -- the source-built runtime; the pair printed in tab:sim-poly-aic
--   two_pool    simulation/results/two_pool_{poly,aic}.json
--   llm_only    simulation/results/llm_only_{poly,aic}.json
-- The files are flat aiperf-style metric dicts with slightly different key
-- sets per family, so the complete payload is stored tall in
-- cost_model_metric and only the published metrics are promoted to columns.
-- -------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS provenance.cost_model_variant (
    variant_id                  text PRIMARY KEY,
    family                      text NOT NULL,
    converter                   text NOT NULL,
    window_name                 text,
    runtime                     text,
    topology                    text,
    is_published                boolean NOT NULL DEFAULT false,
    -- promoted headline metrics (exactly the rows of tab:sim-poly-aic)
    mean_ttft_ms                double precision,
    p99_ttft_ms                 double precision,
    max_ttft_ms                 double precision,
    mean_e2e_latency_ms         double precision,
    p99_e2e_latency_ms          double precision,
    mean_itl_ms                 double precision,
    max_itl_ms                  double precision,
    mean_output_tok_per_user    double precision,
    -- scale / cost context
    completed_requests          bigint,
    duration_ms                 double precision,
    request_throughput_rps      double precision,
    total_input_tokens          bigint,
    total_output_tokens         bigint,
    gpu_hours                   double precision,
    decode_worker_seconds       double precision,
    prefill_worker_seconds      double precision,
    n_metrics                   int,
    source_path                 text
);

COMMENT ON TABLE provenance.cost_model_variant IS
 'K26: one row per cost-model run -- 6 rows = 3 families x {poly, aic}. Backs tab:sim-poly-aic, which prints the head2k_src pair. The table exists to make the poly-vs-aic contrast a self-join on family: the two rows of a family are the SAME window, topology and trace, differing only in how decode time is priced, so any column difference between them is attributable to the cost model alone. Full untruncated payloads live in cost_model_metric.';
COMMENT ON COLUMN provenance.cost_model_variant.variant_id IS 'Stable id, "<family>:<converter>" (e.g. head2k_src:aic).';
COMMENT ON COLUMN provenance.cost_model_variant.family IS 'Which paired experiment: head2k_src (source-built runtime, the pair PUBLISHED in tab:sim-poly-aic), two_pool (encoder+language composed run), or llm_only (language pool in isolation). Rows are comparable WITHIN a family only.';
COMMENT ON COLUMN provenance.cost_model_variant.converter IS 'The decode cost model: poly = the mocker''s default polynomial; aic = aiconfigurator''s calibrated h100_sxm / vLLM 0.22.0 database. The single independent variable of this table.';
COMMENT ON COLUMN provenance.cost_model_variant.window_name IS 'Trace window replayed. head2k (the steady 2000-request head) for every shipped row; joins sweep_window.window_name.';
COMMENT ON COLUMN provenance.cost_model_variant.runtime IS 'Which runtime produced the numbers: srcbuild = source-built Dynamo with calibrated predictions running in-core (Rust, microseconds); wheel = the earlier wheel-based runtime whose per-request Python callbacks leaked wall-time into the simulated clock. The thesis reports that this inflated the EXTREME tail only (identical p99; max TTFT 7.6 vs 4.5 s on identical perf data), which is why the published pair is the srcbuild one. NULL where the artifact does not record it.';
COMMENT ON COLUMN provenance.cost_model_variant.topology IS 'Worker topology held fixed across the pair (2 language workers, offline KV router).';
COMMENT ON COLUMN provenance.cost_model_variant.is_published IS 'TRUE for the two head2k_src rows, which are the ones printed in tab:sim-poly-aic. The other four families are corroborating runs, not published numbers -- flagged so an auditor does not mistake them for the table.';
COMMENT ON COLUMN provenance.cost_model_variant.mean_ttft_ms IS 'Mean time-to-first-token (ms). tab:sim-poly-aic row 1, first value: 67.3 (poly) vs 68.2 (aic) -- averages barely move.';
COMMENT ON COLUMN provenance.cost_model_variant.p99_ttft_ms IS 'TTFT p99 (ms). tab:sim-poly-aic row 1, second value: 248 vs 307, the 1.24x tail growth the section headline is built on.';
COMMENT ON COLUMN provenance.cost_model_variant.max_ttft_ms IS 'Maximum TTFT (ms). tab:sim-poly-aic row 1, third value: 2540 vs 4518, ~1.8x.';
COMMENT ON COLUMN provenance.cost_model_variant.mean_e2e_latency_ms IS 'Mean end-to-end request latency (ms). tab:sim-poly-aic row 2, first value: 1413 vs 1590.';
COMMENT ON COLUMN provenance.cost_model_variant.p99_e2e_latency_ms IS 'End-to-end request latency p99 (ms). tab:sim-poly-aic row 2, second value: 6879 vs 8163.';
COMMENT ON COLUMN provenance.cost_model_variant.mean_itl_ms IS 'Mean inter-token latency (ms). tab:sim-poly-aic row 3, first value: 6.79 vs 7.67.';
COMMENT ON COLUMN provenance.cost_model_variant.max_itl_ms IS 'Maximum inter-token latency (ms). tab:sim-poly-aic row 3, second value: 181 vs 348, ~1.9x -- the decode tail the polynomial hides.';
COMMENT ON COLUMN provenance.cost_model_variant.mean_output_tok_per_user IS 'Mean per-user output token rate (tok/s). tab:sim-poly-aic row 4: 160.6 vs 142.0.';
COMMENT ON COLUMN provenance.cost_model_variant.completed_requests IS 'Requests completed (2000 in every row -- the pair is over an identical request set).';
COMMENT ON COLUMN provenance.cost_model_variant.duration_ms IS 'Simulated wall duration of the replay (ms). Identical within a pair because arrivals are trace-driven, not closed-loop: the cost model changes latencies, not the arrival process.';
COMMENT ON COLUMN provenance.cost_model_variant.request_throughput_rps IS 'Achieved request throughput (req/s).';
COMMENT ON COLUMN provenance.cost_model_variant.total_input_tokens IS 'Total prompt tokens over the run.';
COMMENT ON COLUMN provenance.cost_model_variant.total_output_tokens IS 'Total generated tokens over the run.';
COMMENT ON COLUMN provenance.cost_model_variant.gpu_hours IS 'GPU-hours attributed to the run. Present in the srcbuild artifacts only; NULL elsewhere.';
COMMENT ON COLUMN provenance.cost_model_variant.decode_worker_seconds IS 'Aggregate decode-worker busy seconds. srcbuild artifacts only.';
COMMENT ON COLUMN provenance.cost_model_variant.prefill_worker_seconds IS 'Aggregate prefill-worker busy seconds; 0.0 in the shipped rows (aggregated serving -- prefill is not disaggregated onto its own workers in this experiment). srcbuild artifacts only.';
COMMENT ON COLUMN provenance.cost_model_variant.n_metrics IS 'How many scalar metrics this artifact carried into cost_model_metric. Differs across families (the srcbuild files add gpu_hours / worker-seconds / prefix-cache keys), which is exactly why the full payload is stored tall.';
COMMENT ON COLUMN provenance.cost_model_variant.source_path IS 'Absolute path of the JSON this row was parsed from.';


CREATE TABLE IF NOT EXISTS provenance.cost_model_metric (
    variant_id  text NOT NULL,
    metric      text NOT NULL,
    value       double precision,
    PRIMARY KEY (variant_id, metric)
);

COMMENT ON TABLE provenance.cost_model_metric IS
 'K26: the COMPLETE flat metric payload of each cost-model artifact, stored tall (one row per scalar key) so nothing is dropped and the three families'' differing key sets coexist without schema drift. ~380 rows. cost_model_variant promotes only the published subset to columns; anything not promoted is still recoverable here. Pivot with filtered aggregates to compare poly against aic on any metric.';
COMMENT ON COLUMN provenance.cost_model_metric.variant_id IS 'Owning run; joins cost_model_variant.variant_id.';
COMMENT ON COLUMN provenance.cost_model_metric.metric IS 'Metric key verbatim from the JSON (e.g. p99_ttft_ms, mean_itl_ms, processed_tokens_per_s). Naming is the aiperf convention: <stat>_<quantity>_<unit>.';
COMMENT ON COLUMN provenance.cost_model_metric.value IS 'Metric value as double precision. Every key in the shipped artifacts is numeric; any non-numeric key would be skipped by the loader rather than coerced.';


-- =========================================================================
-- K27 -- EWMA conformal calibration manifest
-- =========================================================================
CREATE TABLE IF NOT EXISTS provenance.ewma_cal_manifest (
    manifest_id   text PRIMARY KEY,
    source_parquet text,
    t0_eval       timestamptz,
    nominal       double precision,
    resolution    text,
    n_calib       bigint,
    n_eval        bigint,
    wsc_k         double precision,
    source_path   text
);

COMMENT ON TABLE provenance.ewma_cal_manifest IS
 'K27: one row -- the calibration setup behind the EWMA predictor''s conformal prediction intervals (predictors/results/ewma_cal_manifest.json). Records the calib/eval split so the coverage numbers in ewma_cal_coverage are interpretable, and the fitted interval widths in ewma_cal_param so the intervals are reconstructable.';
COMMENT ON COLUMN provenance.ewma_cal_manifest.manifest_id IS 'Stable id of this calibration (''ewma:cal_manifest'').';
COMMENT ON COLUMN provenance.ewma_cal_manifest.source_parquet IS 'Absolute path of the EWMA forecast parquet the calibration was fitted on.';
COMMENT ON COLUMN provenance.ewma_cal_manifest.t0_eval IS 'Split instant: everything before is calibration, everything at or after is evaluation. A STRICTLY TEMPORAL split -- the calibration set never sees the future, which is what makes the eval coverage an honest out-of-sample number.';
COMMENT ON COLUMN provenance.ewma_cal_manifest.nominal IS 'Target coverage of the prediction intervals (0.9). The number every ewma_cal_coverage.coverage should be compared against.';
COMMENT ON COLUMN provenance.ewma_cal_manifest.resolution IS 'Time resolution of the underlying series (15s); joins eda_rate_series.resolution.';
COMMENT ON COLUMN provenance.ewma_cal_manifest.n_calib IS 'Number of calibration points (6144).';
COMMENT ON COLUMN provenance.ewma_cal_manifest.n_eval IS 'Number of evaluation points (32244) -- 5x the calibration set, so eval coverage is the better-powered estimate.';
COMMENT ON COLUMN provenance.ewma_cal_manifest.wsc_k IS 'Fitted k of the wsc (worst-slab-coverage) method: a single scalar multiplier, unlike the per-horizon add/mult quantiles in ewma_cal_param.';
COMMENT ON COLUMN provenance.ewma_cal_manifest.source_path IS 'Absolute path of ewma_cal_manifest.json.';


CREATE TABLE IF NOT EXISTS provenance.ewma_cal_coverage (
    manifest_id text NOT NULL,
    method      text NOT NULL,
    split       text NOT NULL,
    coverage    double precision,
    nominal     double precision,
    PRIMARY KEY (manifest_id, method, split)
);

COMMENT ON TABLE provenance.ewma_cal_coverage IS
 'K27: achieved empirical coverage per (interval method, data split) -- 8 rows. The point of the table is the calib-vs-eval gap: a method that hits nominal on calib but misses on eval has overfitted the calibration set.';
COMMENT ON COLUMN provenance.ewma_cal_coverage.manifest_id IS 'Owning calibration; joins ewma_cal_manifest.manifest_id.';
COMMENT ON COLUMN provenance.ewma_cal_coverage.method IS 'Interval construction: add (additive per-horizon conformal offset), mult (multiplicative per-horizon scaling), wsc (worst-slab-coverage, single k), or native (the model''s own uncalibrated intervals). native is the BASELINE -- it overcovers (0.94/0.93 against a 0.90 target), which is what motivates conformal calibration.';
COMMENT ON COLUMN provenance.ewma_cal_coverage.split IS 'calib (in-sample, fitted on) or eval (out-of-sample, held out after t0_eval). Only eval is evidence.';
COMMENT ON COLUMN provenance.ewma_cal_coverage.coverage IS 'Empirical fraction of true values falling inside the interval, 0..1. Compare against nominal: add holds up out-of-sample (0.898 -> 0.901) while mult and wsc degrade (to 0.878 / 0.877).';
COMMENT ON COLUMN provenance.ewma_cal_coverage.nominal IS 'Target coverage (0.9), denormalized from the manifest so a row reads standalone.';


CREATE TABLE IF NOT EXISTS provenance.ewma_cal_param (
    manifest_id text NOT NULL,
    param_kind  text NOT NULL,
    horizon     int  NOT NULL,
    value       double precision,
    PRIMARY KEY (manifest_id, param_kind, horizon)
);

COMMENT ON TABLE provenance.ewma_cal_param IS
 'K27: the fitted per-horizon conformal quantiles -- 24 rows (2 kinds x 12 horizons). These are the numbers needed to REBUILD the prediction intervals, not just to describe them.';
COMMENT ON COLUMN provenance.ewma_cal_param.manifest_id IS 'Owning calibration; joins ewma_cal_manifest.manifest_id.';
COMMENT ON COLUMN provenance.ewma_cal_param.param_kind IS 'add_qh (additive: interval = point +/- value, in images/s) or mult_qh (multiplicative: interval = point +/- value * scale, dimensionless). The two are alternative calibrations of the same forecasts, not components of one.';
COMMENT ON COLUMN provenance.ewma_cal_param.horizon IS 'Forecast horizon h in steps ahead (1..12). At the 15s resolution h=12 is 3 minutes.';
COMMENT ON COLUMN provenance.ewma_cal_param.value IS 'Fitted quantile at this horizon. Rises with h in both kinds (add: 264 -> 494 across h=1..12), the expected widening of intervals further into the future.';


-- =========================================================================
-- K28 -- burst1 C* recomputation under the stage-conditional metric
-- =========================================================================
CREATE TABLE IF NOT EXISTS provenance.rerun_b1_run (
    rerun_id                text PRIMARY KEY,
    sla_ms                  double precision,
    n_windows               int,
    deployable_static_old   int,
    deployable_static_new   int,
    burst5_c16_image_p99    double precision,
    burst5_c16_mixed_p99    double precision,
    deployable_is_stale     boolean,
    stale_reason            text,
    source_path             text
);

COMMENT ON TABLE provenance.rerun_b1_run IS
 'K28: one row -- the campaign-level facts of the stage-conditional recomputation (verification/rerun_b1_results.json). NOTE THE FILENAME UNDERSELLS THE FILE: despite being called rerun_b1, it recomputes ALL SEVEN windows, not just burst1. The per-window results are in rerun_b1_window.';
COMMENT ON COLUMN provenance.rerun_b1_run.rerun_id IS 'Stable id (''verify:rerun_b1'').';
COMMENT ON COLUMN provenance.rerun_b1_run.sla_ms IS 'Encoder-delay p99 bound applied to every window (1000 ms) -- the same evaluation SLA as the grid and load sweeps.';
COMMENT ON COLUMN provenance.rerun_b1_run.n_windows IS 'Windows recomputed (7: burst1..burst6 + steady).';
COMMENT ON COLUMN provenance.rerun_b1_run.deployable_static_old IS 'Fleet-wide deployable static encoder count under the ALL-REQUEST metric, as this artifact computed it (16). STALE -- see deployable_is_stale.';
COMMENT ON COLUMN provenance.rerun_b1_run.deployable_static_new IS 'Fleet-wide deployable static encoder count under the STAGE-CONDITIONAL metric, as this artifact computed it (16). Equal to the old value, which is this artifact''s actual finding: changing the metric moves per-window optima but NOT the deployable fleet. STALE in absolute value -- see deployable_is_stale.';
COMMENT ON COLUMN provenance.rerun_b1_run.burst5_c16_image_p99 IS 'burst5 stage-conditional encoder-delay p99 at C=16 (588.4 ms). Well under the 1000 ms bound -- an early hint that C=16 was far more than burst5 needed, later confirmed by the stability rerun that corrected burst5 to C=8.';
COMMENT ON COLUMN provenance.rerun_b1_run.burst5_c16_mixed_p99 IS 'burst5 all-request encoder-delay p99 at C=16 (588.4 ms). Identical to the image-only value here because at C=16 burst5''s queue is empty enough that the text-only requests do not move the percentile.';
COMMENT ON COLUMN provenance.rerun_b1_run.deployable_is_stale IS 'TRUE: the deployable_static_* values of 16 were computed while burst5''s C* was still the pre-correction 16, and burst5 was the window forcing the fleet-wide maximum. After the burst5 supersession (provenance.grid_correction, correction_id burst5:c_star:supersession) the deployable static fleet is C=8, which is what the thesis publishes. Do NOT quote deployable_static_old/new as current; they are preserved as the artifact recorded them.';
COMMENT ON COLUMN provenance.rerun_b1_run.stale_reason IS 'Why the deployable_static_* columns are stale, in one sentence.';
COMMENT ON COLUMN provenance.rerun_b1_run.source_path IS 'Absolute path of rerun_b1_results.json.';


CREATE TABLE IF NOT EXISTS provenance.rerun_b1_window (
    rerun_id                    text NOT NULL,
    window_name                 text NOT NULL,
    sla_ms                      double precision,
    trace_offset                bigint,
    max_requests                bigint,
    span_h                      double precision,
    total_reqs                  bigint,
    n_image_reqs                bigint,
    grid_cstar_reported         int,
    current_mixed_cstar         int,
    current_mixed_p99           double precision,
    image_p99_at_current_cstar  double precision,
    corrected_image_cstar       int,
    corrected_image_p99         double precision,
    delta_workers               int,
    gpuh_5090_old               double precision,
    gpuh_5090_new               double precision,
    gpuh_h100                   double precision,
    llm_gpus                    int,
    reproduces_grid_mixed_cstar boolean,
    source_path                 text,
    PRIMARY KEY (rerun_id, window_name)
);

COMMENT ON TABLE provenance.rerun_b1_window IS
 'K28: one row per window (7) -- the encoder-optimum recomputation (verification/rerun_b1_results.json, narrative in verification/rerun-b1.md). READ THIS CAREFULLY: it is NOT a correction of published numbers. The thesis publishes C* under the ALL-REQUEST encoder-delay p99 (tab:base-grid); this rerun recomputes each optimum under the STAGE-CONDITIONAL metric (image-bearing requests only, excluding the ~50% text-only requests that never touch the encoder). Both are reported: the thesis prose immediately after tab:base-grid states the stage-conditional optima explicitly (burst1 to 7, burst3/burst4 to 8, burst6 to 8; burst2/burst5/steady unchanged) -- which is exactly the delta_workers column here. So these rows record an ALTERNATIVE METRIC, registered in provenance.grid_correction with correction_type=''alternative_metric'' -- unlike burst5, which is a genuine supersession. CAVEAT: this artifact predates the burst5 stability correction, so its burst5 rows still carry the pre-correction C*=16; see rerun_b1_run.deployable_is_stale.';
COMMENT ON COLUMN provenance.rerun_b1_window.rerun_id IS 'Owning campaign; joins rerun_b1_run.rerun_id.';
COMMENT ON COLUMN provenance.rerun_b1_window.window_name IS 'burst1..burst6 or steady; joins grid_window.window_name. NOTE the vocabulary differs slightly from grid_window, which spells the calm slice steady24h while this artifact spells it steady.';
COMMENT ON COLUMN provenance.rerun_b1_window.sla_ms IS 'Encoder-delay p99 bound applied (1000 ms), denormalized from rerun_b1_run so a window row reads standalone.';
COMMENT ON COLUMN provenance.rerun_b1_window.trace_offset IS 'Request-index offset of this window into the 1M-request trace. Matches grid_window and (for burst1) sweep_window: the same slices.';
COMMENT ON COLUMN provenance.rerun_b1_window.max_requests IS 'Requests in the window.';
COMMENT ON COLUMN provenance.rerun_b1_window.span_h IS 'Window span in hours. The cost multiplier for the GPU-hour columns.';
COMMENT ON COLUMN provenance.rerun_b1_window.total_reqs IS 'All requests in the window.';
COMMENT ON COLUMN provenance.rerun_b1_window.n_image_reqs IS 'Image-bearing requests only (43768 of 64804 for burst1). The stage-conditional metric is computed over these; the difference between the two metrics is entirely the text-only remainder, which never enters the encoder queue but always enters the all-request percentile.';
COMMENT ON COLUMN provenance.rerun_b1_window.grid_cstar_reported IS 'C* as the original grid sweep reported it -- the value in grid_window.c_star. For burst5 this is the PRE-CORRECTION 16.';
COMMENT ON COLUMN provenance.rerun_b1_window.current_mixed_cstar IS 'C* recomputed by this rerun under the all-request ("mixed") metric. Equal to grid_cstar_reported in all seven windows, which is the reproduction check -- see reproduces_grid_mixed_cstar.';
COMMENT ON COLUMN provenance.rerun_b1_window.current_mixed_p99 IS 'All-request encoder-delay p99 at current_mixed_cstar (ms). For burst1: 995.9 -- feasible, but by only 4 ms of headroom.';
COMMENT ON COLUMN provenance.rerun_b1_window.image_p99_at_current_cstar IS 'Stage-conditional (image-only) p99 at that same C (ms). For burst1: 1118.0 -- INFEASIBLE. The 4 ms of headroom under the all-request metric was an artifact of averaging in text-only requests with zero encoder delay.';
COMMENT ON COLUMN provenance.rerun_b1_window.corrected_image_cstar IS 'Smallest C feasible under the stage-conditional metric. Rises above current_mixed_cstar for burst1 (7), burst3 (8), burst4 (8) and burst6 (8); unchanged for burst2, burst5 and steady.';
COMMENT ON COLUMN provenance.rerun_b1_window.corrected_image_p99 IS 'Stage-conditional p99 at corrected_image_cstar (ms) -- feasible by construction.';
COMMENT ON COLUMN provenance.rerun_b1_window.delta_workers IS 'corrected_image_cstar - current_mixed_cstar: how many extra encoder workers the stage-conditional metric demands. 0 for burst2/burst5/steady, +1 for burst1/burst3/burst4, +2 for burst6 -- precisely the list the thesis prose gives after tab:base-grid.';
COMMENT ON COLUMN provenance.rerun_b1_window.gpuh_5090_old IS 'Encoder GPU-hours at current_mixed_cstar = span_h * C. Matches grid_window.gpu_hours_rtx5090.';
COMMENT ON COLUMN provenance.rerun_b1_window.gpuh_5090_new IS 'Encoder GPU-hours at corrected_image_cstar = span_h * C. The 58.2 / 3.6 / 25.2 / 10.9 figures the thesis prose quotes for burst1 / burst3 / burst4 / burst6.';
COMMENT ON COLUMN provenance.rerun_b1_window.gpuh_h100 IS 'Language-pool GPU-hours over the window, unaffected by the encoder metric.';
COMMENT ON COLUMN provenance.rerun_b1_window.llm_gpus IS 'Language-pool GPUs at the window optimum (4 = TP2 x 2 replicas for the burst windows).';
COMMENT ON COLUMN provenance.rerun_b1_window.reproduces_grid_mixed_cstar IS 'TRUE if this independent rerun reproduced the original grid''s all-request C* for this window. TRUE in all seven. That is what licenses trusting its stage-conditional numbers: the difference is the metric, not a changed simulator.';
COMMENT ON COLUMN provenance.rerun_b1_window.source_path IS 'Absolute path of rerun_b1_results.json.';


CREATE TABLE IF NOT EXISTS provenance.rerun_b1_curve_point (
    rerun_id     text NOT NULL,
    window_name  text NOT NULL,
    encoder_c    int  NOT NULL,
    mixed_p99_ms double precision,
    image_p99_ms double precision,
    divergent    boolean,
    mixed_feasible boolean,
    image_feasible boolean,
    PRIMARY KEY (rerun_id, window_name, encoder_c)
);

COMMENT ON TABLE provenance.rerun_b1_curve_point IS
 'K28: the full C-sweep behind every window''s recomputation -- 140 rows (7 windows x C=1..20), both metrics side by side. Makes the metric choice auditable at every C rather than only at the two optima: for burst1 the two feasibility columns diverge at exactly one C (=6), which is the whole finding. window_name is part of the KEY -- an earlier revision of this table keyed on (rerun_id, encoder_c) alone and silently collapsed all seven windows onto one another.';
COMMENT ON COLUMN provenance.rerun_b1_curve_point.rerun_id IS 'Owning campaign; joins rerun_b1_run.rerun_id.';
COMMENT ON COLUMN provenance.rerun_b1_curve_point.window_name IS 'Which window this sweep point belongs to; joins rerun_b1_window.window_name.';
COMMENT ON COLUMN provenance.rerun_b1_curve_point.encoder_c IS 'Encoder worker count C swept (1..20).';
COMMENT ON COLUMN provenance.rerun_b1_curve_point.mixed_p99_ms IS 'Encoder-delay p99 over ALL requests at this C (ms), text-only requests included at zero delay.';
COMMENT ON COLUMN provenance.rerun_b1_curve_point.image_p99_ms IS 'Encoder-delay p99 over IMAGE-BEARING requests only at this C (ms). Always >= mixed_p99_ms, because dropping zero-delay requests shifts the percentile right.';
COMMENT ON COLUMN provenance.rerun_b1_curve_point.divergent IS 'Whether the encoder queue failed to drain at this C. FALSE at every swept C here.';
COMMENT ON COLUMN provenance.rerun_b1_curve_point.mixed_feasible IS 'mixed_p99_ms <= sla_ms. The smallest C with this TRUE is current_mixed_cstar.';
COMMENT ON COLUMN provenance.rerun_b1_curve_point.image_feasible IS 'image_p99_ms <= sla_ms. The smallest C with this TRUE is corrected_image_cstar.';


-- =========================================================================
-- K29 -- the raw arrival-rate series behind the EDA statistics
-- =========================================================================
CREATE TABLE IF NOT EXISTS provenance.eda_rate_series (
    resolution   text NOT NULL,
    ts           timestamptz NOT NULL,
    signal       text NOT NULL,
    value        double precision,
    PRIMARY KEY (resolution, signal, ts)
);
CREATE INDEX IF NOT EXISTS eda_rate_series_sig_idx ON provenance.eda_rate_series (signal, resolution);

COMMENT ON TABLE provenance.eda_rate_series IS
 'K29: the binned arrival-rate series of the Azure trace, long-format -- ~2.76M rows from analysis/trace_eda/series/rates_{1s,15s,30s,45s,1min}.parquet. These are the INPUTS from which the burstiness statistics in provenance.eda_metric (Hurst exponent, Fano factor, CV^2) are computed, so loading them makes those published statistics RECOMPUTABLE rather than merely recorded. Long rather than wide so that "which signal, at which resolution" is a filter instead of a column choice, and so a new signal would not require DDL. The multi-resolution stack is itself the point: Hurst and Fano are only meaningful as a function of aggregation scale, which is why the same week is binned five ways.';
COMMENT ON COLUMN provenance.eda_rate_series.resolution IS 'Bin width of the series: 1s, 15s, 30s, 45s, or 1min. Row counts are 604800 / 40320 / 20160 / 13440 / 10080 bins respectively -- all covering the SAME one-week span (604800 s), so the five are aggregations of one another, not different data.';
COMMENT ON COLUMN provenance.eda_rate_series.ts IS 'Start instant of the bin (the parquet''s window_start), UTC. The count in this row covers [ts, ts + resolution).';
COMMENT ON COLUMN provenance.eda_rate_series.signal IS 'Which counter: requests (arrivals per bin), images (images per bin -- the vision pool''s actual load, and the one that bursts), ctx (context/prompt tokens per bin), gen (generated tokens per bin). Kept as one series each because the thesis'' burstiness result is that requests and images have DIFFERENT burst structure -- images spike where requests do not.';
COMMENT ON COLUMN provenance.eda_rate_series.value IS 'Counter value in this bin, as double precision. Counts are integral; double is used so the column also accepts a rate should a future resolution store one.';


-- =========================================================================
-- A KNOWN CORRECTION, REPRESENTED AS DATA (not an ingest)
-- =========================================================================
-- Problem this solves: provenance.grid_window.c_star holds burst5 = 16,
-- faithfully parsed from results/grid/grid_summary.json. But the THESIS
-- publishes burst5 C* = 8 (tab:base-grid), because the grid's divergence
-- heuristic was later shown to be an endpoint artifact and the burst5 row was
-- superseded by verification/rerun-stability-e2e.md. Until now that fact
-- existed ONLY as prose in tex/apendice.tex:301, so the store silently
-- disagreed with the thesis and an auditor had no way to see why.
--
-- Design choice: c_star is NOT overwritten. grid_summary.json really does say
-- 16, and a provenance store that rewrites its sources destroys the evidence
-- that a correction happened. Instead both values are kept side by side, with
-- the superseding document named, so the supersession is itself a queryable
-- fact.
-- -------------------------------------------------------------------------

ALTER TABLE provenance.grid_window
    ADD COLUMN IF NOT EXISTS c_star_corrected           int,
    ADD COLUMN IF NOT EXISTS gpu_hours_rtx5090_corrected double precision,
    ADD COLUMN IF NOT EXISTS correction_source          text,
    ADD COLUMN IF NOT EXISTS is_superseded              boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN provenance.grid_window.c_star IS
 'PER-WINDOW OPTIMUM encoder worker count as recorded by grid_summary.json: the smallest C whose vision p99 meets the SLA on this window. THIS IS THE PRE-CORRECTION VALUE and for burst5 it disagrees with the thesis (16 here, 8 published in tab:base-grid) -- grid_summary.json is the pre-correction artifact and is preserved verbatim. Always check is_superseded / c_star_corrected before quoting this column; use provenance.grid_window_effective, which resolves it.';
COMMENT ON COLUMN provenance.grid_window.c_star_corrected IS
 'The corrected per-window optimum encoder worker count, NULL where no correction applies (6 of 7 windows). Populated for burst5 = 8, the value PUBLISHED in tab:base-grid. The original grid forced burst5 to 16 via a queue-divergence heuristic later shown to be an endpoint artifact (a backlog at the window edge that drains in a fraction of a second); once divergence is dropped, burst5 is p99-knee-limited and its honest AIC knee is 8. Full argument and the tiling test in verification/rerun-stability-e2e.md.';
COMMENT ON COLUMN provenance.grid_window.gpu_hours_rtx5090_corrected IS
 'Encoder GPU-hours recomputed at c_star_corrected = span_h * c_star_corrected. Populated for burst5 = 10.79 (vs 21.59 at the pre-correction C*=16), matching the 10.8 published in tab:base-grid. Carried explicitly because the correction halves this window''s encoder cost and any cost aggregate that sums the uncorrected column is wrong.';
COMMENT ON COLUMN provenance.grid_window.correction_source IS
 'Absolute path of the document that supersedes this row, NULL where none. For burst5: verification/rerun-stability-e2e.md.';
COMMENT ON COLUMN provenance.grid_window.is_superseded IS
 'TRUE if this row''s optimum has been superseded by a later verification. TRUE for burst5 only. A query that filters on the uncorrected c_star should either exclude these rows or use provenance.grid_window_effective.';


CREATE TABLE IF NOT EXISTS provenance.grid_correction (
    correction_id     text PRIMARY KEY,
    window_name       text NOT NULL,
    field             text NOT NULL,
    correction_type   text NOT NULL,
    original_value    double precision,
    corrected_value   double precision,
    original_source   text,
    corrected_source  text,
    thesis_location   text,
    published_value   double precision,
    affects_headline  boolean,
    rationale         text,
    recorded_utc      timestamptz DEFAULT now()
);

COMMENT ON TABLE provenance.grid_correction IS
 'The register of known discrepancies between an ingested artifact and the value the thesis publishes. Exists so that "the store says X but the thesis says Y" is never a silent inconsistency an auditor has to discover by reading prose. Two rows, and they are NOT the same kind of thing -- see correction_type: burst5 is a genuine SUPERSESSION (the artifact is wrong, the thesis is right), while burst1 is an ALTERNATIVE METRIC (both numbers are correct under their own definition, and the thesis reports both). Conflating the two would be its own provenance error. Populated by DML in this file, not by a loader: these are editorial facts about the thesis, not parsed from any artifact.';
COMMENT ON COLUMN provenance.grid_correction.correction_id IS 'Stable id, "<window>:<field>:<correction_type>".';
COMMENT ON COLUMN provenance.grid_correction.window_name IS 'Trace window the correction applies to; joins grid_window.window_name.';
COMMENT ON COLUMN provenance.grid_correction.field IS 'Which column of grid_window is affected (c_star).';
COMMENT ON COLUMN provenance.grid_correction.correction_type IS 'supersession = the ingested artifact is now known to be WRONG and the corrected value replaces it (burst5). alternative_metric = the artifact is correct under its own definition and the corrected value is what a DIFFERENT, equally valid metric yields; both are reported by the thesis and neither supersedes the other (burst1). Only supersession rows set grid_window.is_superseded.';
COMMENT ON COLUMN provenance.grid_correction.original_value IS 'The value as ingested from the artifact, still present in grid_window.c_star.';
COMMENT ON COLUMN provenance.grid_correction.corrected_value IS 'The value under the correction or the alternative metric.';
COMMENT ON COLUMN provenance.grid_correction.original_source IS 'Absolute path of the artifact carrying original_value.';
COMMENT ON COLUMN provenance.grid_correction.corrected_source IS 'Absolute path of the document or artifact carrying corrected_value.';
COMMENT ON COLUMN provenance.grid_correction.thesis_location IS 'Where in the thesis source the discrepancy is acknowledged, as file:line.';
COMMENT ON COLUMN provenance.grid_correction.published_value IS 'The value ACTUALLY PRINTED in the thesis table. For burst5 this equals corrected_value (8) -- the thesis prints the corrected number. For burst1 it equals original_value (6) -- the thesis prints the all-request number in the table and mentions the stage-conditional 7 in the surrounding prose. This column is the tiebreaker for "which number is the published one".';
COMMENT ON COLUMN provenance.grid_correction.affects_headline IS 'Whether the correction moves a headline result. FALSE for both: the deployable static fleet is C=8 under every variant here, so the 0.62x cost headline of the closed-loop chapter is untouched. Only the per-window table moves.';
COMMENT ON COLUMN provenance.grid_correction.rationale IS 'Why the original value is being corrected or supplemented, in one paragraph.';
COMMENT ON COLUMN provenance.grid_correction.recorded_utc IS 'When this correction was registered in the store.';


-- --- populate: burst5 supersession (16 -> 8) ------------------------------
UPDATE provenance.grid_window
   SET c_star_corrected            = 8,
       gpu_hours_rtx5090_corrected = round((span_h * 8)::numeric, 2)::double precision,
       correction_source           = '/home/gio/tese/verification/rerun-stability-e2e.md',
       is_superseded               = true
 WHERE window_name = 'burst5';

INSERT INTO provenance.grid_correction
    (correction_id, window_name, field, correction_type,
     original_value, corrected_value, original_source, corrected_source,
     thesis_location, published_value, affects_headline, rationale)
VALUES
    ('burst5:c_star:supersession', 'burst5', 'c_star', 'supersession',
     16, 8,
     '/home/gio/tese/simulation/results/grid/grid_summary.json',
     '/home/gio/tese/verification/rerun-stability-e2e.md',
     'tex/apendice.tex:301', 8, false,
     'The grid sweep rejected C<16 for burst5 on a queue-divergence heuristic. That heuristic was later shown to be an endpoint artifact: it flagged a backlog present at the window boundary that in fact drains in a fraction of a second, and a 3x back-to-back tiling of burst5''s arrivals confirmed the queue is stable at every C >= 8 under BOTH cost models. With divergence dropped, burst5 is p99-knee-limited like every other window and its honest AIC knee is C=8. The thesis publishes 8; grid_summary.json still says 16 and is preserved unmodified as the pre-correction artifact.'),
    ('burst1:c_star:alternative_metric', 'burst1', 'c_star', 'alternative_metric',
     6, 7,
     '/home/gio/tese/simulation/results/grid/grid_summary.json',
     '/home/gio/tese/verification/rerun_b1_results.json',
     'tex/baselines.tex:88', 6, false,
     'NOT a supersession. C*=6 is correct under the all-request encoder-delay p99 that tab:base-grid uses, and an independent rerun reproduced it exactly. Under the stage-conditional metric -- image-bearing requests only, excluding the ~50% of requests that are text-only and never enter the encoder -- the same window needs C=7 (image-only p99 is 1118 ms at C=6, 986 ms at C=7). The thesis prints 6 in the table and states the stage-conditional optima in the prose immediately following it. Both numbers are correct under their own definition; grid_window.c_star is NOT marked superseded for burst1. Full curve in provenance.rerun_b1_curve_point.')
ON CONFLICT (correction_id) DO UPDATE SET
    original_value   = excluded.original_value,
    corrected_value  = excluded.corrected_value,
    original_source  = excluded.original_source,
    corrected_source = excluded.corrected_source,
    thesis_location  = excluded.thesis_location,
    published_value  = excluded.published_value,
    affects_headline = excluded.affects_headline,
    rationale        = excluded.rationale;


-- A resolved view, so the common case ("give me the optimum the thesis
-- publishes") does not require every caller to remember the correction.
CREATE OR REPLACE VIEW provenance.grid_window_effective AS
SELECT w.grid_run_id,
       w.window_name,
       w.span_h,
       w.c_star                                        AS c_star_as_ingested,
       coalesce(w.c_star_corrected, w.c_star)          AS c_star_effective,
       w.is_superseded,
       coalesce(w.gpu_hours_rtx5090_corrected,
                w.gpu_hours_rtx5090)                   AS gpu_hours_rtx5090_effective,
       w.gpu_hours_h100,
       w.tp_star,
       w.n_star,
       w.correction_source
  FROM provenance.grid_window w;

COMMENT ON VIEW provenance.grid_window_effective IS
 'grid_window with the known corrections applied: c_star_effective is the value the THESIS publishes (tab:base-grid), while c_star_as_ingested preserves what grid_summary.json actually said. Differs for burst5 only (8 vs 16). Prefer this view over grid_window for any cost or fleet-sizing query; use grid_window directly only when the question is specifically about what the original artifact contained.';
