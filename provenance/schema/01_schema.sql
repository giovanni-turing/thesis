-- provenance schema: thesis execution results (raw traces + derived projections)
-- Engine: PostgreSQL 16 (ssd2 stack). Apply:  psql -h localhost -p 5433 -U goku -d postgres -f 01_schema.sql
-- Idempotent (IF NOT EXISTS). Reset:  DROP SCHEMA provenance CASCADE;
--
-- Design: star schema. `runs` is the dimension/provenance spine (one row per execution,
-- all comparison dimensions denormalized wide for easy NL->SQL). Projection tables hold
-- derived summaries; raw fact tables hold everything-as-rows. Both reference runs.run_id,
-- so every projected number is recomputable from that run's raw rows (see 04_lineage.sql).
-- supersedes/is_current mark retracted results so the AI never returns disowned numbers.

CREATE SCHEMA IF NOT EXISTS provenance;
SET search_path = provenance, public;

-- =========================================================================
-- SPINE + DIMENSIONS
-- =========================================================================

CREATE TABLE IF NOT EXISTS provenance.runs (
    run_id          text PRIMARY KEY,
    experiment      text NOT NULL DEFAULT 'misc',   -- a2 a6 a11 a12 a13 a14 grid factorial sweeps reactive ctmatrix riders live predictors eda phasee ewma ...
    pool            text,                            -- encoder | language | both
    window_name     text,                            -- burst1..6 steady24h aggregate fulltrace e7..e18 span_* ...
    policy          text,                            -- forecast | reactive | static
    model           text,                            -- chronos toto timesfm ewma holt_winters naive arima kalman prophet constant ...
    mode            text,                            -- uni | cov
    quantile        text,                            -- p50 p90 ...
    resolution      text,                            -- 1s 15s 30s 45s 1min
    horizon_h       int,
    lead_s          int,                             -- forecast lead L (== cold_start budget in some sweeps)
    cold_start_s    int,
    rho             numeric,                         -- utilization target
    hysteresis_min  int,
    config_c        int,                             -- encoder worker count C*
    tp              int,                             -- LLM tensor parallel
    n_replicas      int,                             -- LLM replicas N
    converter       text,                            -- aic | poly
    gpu             text,                             -- rtx_5090 | h100_sxm ...
    engine          text,                            -- AIC vLLM-FA HF-SDPA HF-FA2 torch.compile ...
    actuation       text,                            -- issue-time | target-time
    kind            text,                            -- source K-kind label (K1..K13)
    source_path     text,                            -- primary artifact path
    artifact_paths  text[],
    command         text,
    commit_sha      text,
    run_utc         timestamptz,
    feeds           text,                            -- tex section / table / figure this feeds
    supersedes      text,                            -- run_id this replaces (soft ref)
    superseded_by   text,                            -- run_id that replaces this (soft ref)
    is_current      boolean NOT NULL DEFAULT true,
    config          jsonb,                           -- run-level attributes (freq_s, arrival_speedup, image_px, encoder_workers, parquet metadata, ...)
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS runs_experiment_idx ON provenance.runs (experiment);
CREATE INDEX IF NOT EXISTS runs_dims_idx       ON provenance.runs (pool, window_name, policy, model);
CREATE INDEX IF NOT EXISTS runs_current_idx    ON provenance.runs (is_current);
CREATE INDEX IF NOT EXISTS runs_supersedes_idx ON provenance.runs (supersedes);

CREATE TABLE IF NOT EXISTS provenance.windows (
    window_name         text PRIMARY KEY,
    trace_offset        bigint,
    max_requests        bigint,
    requests            bigint,
    span_s              double precision,
    mean_req_per_s      double precision,
    mean_img_per_s      double precision,
    peak_1min_img_per_s double precision,
    text_only_fraction  double precision,
    onset_min           int,
    in_coverage         boolean,
    t0                  timestamptz,
    note                text
);

-- =========================================================================
-- PROJECTIONS (derived summaries)
-- =========================================================================

-- K1  *.report.json  (language pool KPIs; hot columns typed, full dict in metrics jsonb)
CREATE TABLE IF NOT EXISTS provenance.llm_run_summary (
    run_id                   text PRIMARY KEY REFERENCES provenance.runs(run_id) ON DELETE CASCADE,
    completed_requests       bigint,
    num_requests             bigint,
    mean_ttft_ms             double precision,
    median_ttft_ms           double precision,
    p90_ttft_ms              double precision,
    p95_ttft_ms              double precision,
    p99_ttft_ms              double precision,
    max_ttft_ms              double precision,
    mean_itl_ms              double precision,
    p99_itl_ms               double precision,
    mean_tpot_ms             double precision,
    p99_tpot_ms              double precision,
    mean_e2e_latency_ms      double precision,
    p90_e2e_latency_ms       double precision,
    p99_e2e_latency_ms       double precision,
    max_e2e_latency_ms       double precision,
    p99_ttst_ms              double precision,
    request_throughput_rps   double precision,
    output_throughput_tok_s  double precision,
    total_throughput_tok_s   double precision,
    gpu_hours                double precision,
    decode_worker_seconds    double precision,
    prefill_worker_seconds   double precision,
    prefix_cache_reused_ratio double precision,
    metrics                  jsonb        -- full report.json dict (lossless)
);

-- K3  *.jsonl.stats.json  (vision/encoder pool)
CREATE TABLE IF NOT EXISTS provenance.encoder_run_summary (
    run_id                     text PRIMARY KEY REFERENCES provenance.runs(run_id) ON DELETE CASCADE,
    requests                   bigint,
    requests_with_images       bigint,
    total_images               bigint,
    image_px                   int,
    encoder_workers            int,
    encoder_batch_images       int,
    text_only_fraction         double precision,
    encoder_delay_p50_ms       double precision,
    encoder_delay_p90_ms       double precision,
    encoder_delay_p99_ms       double precision,
    encoder_delay_max_ms       double precision,
    encoder_service_p99_ms     double precision,
    handoff_p99_ms             double precision,
    provisioned_worker_seconds double precision,
    busy_worker_seconds        double precision,
    encoder_utilization        double precision,
    arrival_speedup            double precision,
    mean_images_per_s          double precision,
    offered_img_per_s          double precision,
    queue_divergent            boolean,
    chunk_dispatch             text,
    batches                    bigint,
    encoder_forwards           bigint,
    metrics                    jsonb       -- full stats.json dict (lossless)
);

-- K7  factorial cell rows (the canonical results table)
CREATE TABLE IF NOT EXISTS provenance.factorial_cell (
    run_id            text PRIMARY KEY REFERENCES provenance.runs(run_id) ON DELETE CASCADE,
    window_name       text,
    resolution        text,
    rho               numeric,
    cold_start_s      int,
    hysteresis_min    int,
    policy            text,
    quantile          text,
    model             text,
    actuation         text,
    readiness         text,      -- strict-rewarm | warm-pool (issue-time factorial)
    lead_s            int,       -- forecast lead L
    p99_ms            double precision,
    max_ms            double precision,
    feasible          boolean,
    provisioned_ws    double precision,
    busy_ws           double precision,
    sched_steps       int,
    sched_min_workers int,
    sched_max_workers int,
    source_path       text
);
CREATE INDEX IF NOT EXISTS factorial_feasible_idx ON provenance.factorial_cell (feasible);
CREATE INDEX IF NOT EXISTS factorial_dims_idx     ON provenance.factorial_cell (window_name, policy, model, quantile);

-- K8  coverage_manifest.json rows + meta
CREATE TABLE IF NOT EXISTS provenance.coverage (
    manifest_path text,
    fleet         text,
    run           text,
    pool          text,
    requests      bigint,
    expect        bigint,
    is_full       boolean,
    ok            boolean,
    PRIMARY KEY (manifest_path, fleet, run, pool)
);
CREATE TABLE IF NOT EXISTS provenance.coverage_meta (
    manifest_path          text PRIMARY KEY,
    trace_requests         bigint,
    forecast_span_requests bigint,
    context_days_requests  bigint,
    complete               boolean,
    per_model_maxspan      jsonb,
    coverage               jsonb,
    guarantee              jsonb
);

-- K8b  verification.json (per-run self-checks)
CREATE TABLE IF NOT EXISTS provenance.verification (
    source_path     text,
    run_id          text,
    stage           text,        -- encoder | language
    requests        bigint,
    completed       bigint,
    enc_p99         double precision,
    enc_max         double precision,
    ttft_p99        double precision,
    itl_p99         double precision,
    provisioned_ws  double precision,
    gpu_h           double precision,
    queue_divergent boolean,
    PRIMARY KEY (source_path, run_id)
);

-- K10  forecast accuracy metrics
CREATE TABLE IF NOT EXISTS provenance.forecast_metrics (
    model      text,
    mode       text,
    span       text,
    resolution text,
    variate    text,
    candidate  text,
    h          int NOT NULL DEFAULT -1,  -- forecast horizon step 1..12; -1 = aggregated over horizons
    mae        double precision,
    rmse       double precision,
    wape       double precision,
    PRIMARY KEY (model, mode, span, resolution, variate, candidate, h)
);

-- one-off structured analyses kept lossless as jsonb (e.g. additive structural ablation)
CREATE TABLE IF NOT EXISTS provenance.analysis_artifact (
    name        text PRIMARY KEY,
    source_path text,
    payload     jsonb
);
CREATE TABLE IF NOT EXISTS provenance.quantile_coverage (
    model   text,
    signal  text,      -- images | requests | ctx | gen
    detail  jsonb,
    PRIMARY KEY (model, signal)
);

-- K12  collector f(N) micro-benchmarks (measured vs AIC vs engine variants)
CREATE TABLE IF NOT EXISTS provenance.collector_fn (
    source_path    text,
    engine         text,       -- measured | aic | fa2 | sdpa | ...
    gpu            text,
    image_px       int,
    n_images       int,
    patches        int,
    mean_ms        double precision,
    p50_ms         double precision,
    min_ms         double precision,
    aic_ms         double precision,
    aic_ms_per_img double precision,
    iters          int,
    sm_clock_mhz   int,
    PRIMARY KEY (source_path, engine, image_px, n_images)
);

-- dual cost accounting: each policy costed bill-from-readiness (ledgered) AND bill-from-order
-- (each up-step pays its warm-up). a2_cost_accounting.csv. Confirms 0.62x is conservative.
CREATE TABLE IF NOT EXISTS provenance.cost_accounting (
    window_name         text,
    policy              text,
    lead_s              int,
    p99_ms              double precision,
    provisioned_ws      double precision,   -- bill-from-readiness (ledgered basis)
    warmup_ws           double precision,
    total_from_order_ws double precision,   -- bill-from-order (readiness + all warm-ups)
    warmup_frac         double precision,
    source_path         text,
    PRIMARY KEY (source_path, window_name, policy, lead_s)
);

-- A12 request-linked composed E2E (ingress->first-token): each request's own encoder delay
-- (recovered from the seam) + its own replayed TTFT, then the percentile of that per-request
-- SUM. NOTE e2e_p99_ms is NOT enc_p99_ms + ttft_p99_ms -- the worst encoder delays and worst
-- TTFTs land on different requests (equal only when encoder delay is flat, i.e. forecast).
CREATE TABLE IF NOT EXISTS provenance.composed_e2e (
    window_name    text,
    arm            text,          -- fc_chronos | fc_toto | fc_timesfm | reactive
    model          text,
    policy         text,
    requests       bigint,
    enc_p99_ms     double precision,
    ttft_p99_ms    double precision,
    e2e_p99_ms     double precision,
    e2e_max_ms     double precision,
    itl_p99_ms     double precision,
    gpu_hours      double precision,
    composed_trace text,
    source_path    text,
    PRIMARY KEY (source_path, window_name, arm)
);

-- =========================================================================
-- RAW FACT TABLES (everything-as-rows; big ones LIST-partitioned by experiment)
-- =========================================================================

-- K2  *.requests.jsonl  (per-request language-pool trace)
CREATE TABLE IF NOT EXISTS provenance.llm_request (
    experiment              text NOT NULL,
    run_id                  text NOT NULL,
    uuid                    text,
    session_id              text,
    turn_index              int,
    arrival_time_ms         double precision,
    first_admit_ms          double precision,
    first_token_ms          double precision,
    last_token_ms           double precision,
    ttft_ms                 double precision,
    ttst_ms                 double precision,
    e2e_latency_ms          double precision,
    itl_ms                  double precision,
    input_length            int,
    requested_output_length int,
    output_length           int,
    reused_input_tokens     bigint,
    prefill_worker_idx      int,
    decode_worker_idx       int,
    prefill_admit_ms        double precision,
    source_held_ms          double precision,
    destination_reserved_ms double precision,
    destination_activated_ms double precision,
    decode_admit_ms         double precision,
    source_released_ms      double precision,
    decode_reused_input_tokens    bigint,
    prefill_route_overlap_tokens  bigint,
    decode_route_overlap_tokens   bigint,
    terminal_status         text
) PARTITION BY LIST (experiment);

-- K5  *.series.json  (per-second encoder trajectory)
CREATE TABLE IF NOT EXISTS provenance.encoder_series (
    experiment       text NOT NULL,
    run_id           text NOT NULL,
    t                int,
    img_arrived      int,
    img_completed    int,
    queue_imgs_end   int,
    busy_workers_end int
) PARTITION BY LIST (experiment);

-- K6  composed *.jsonl  (encoder-stage output feeding the LLM sim)
CREATE TABLE IF NOT EXISTS provenance.composed_request (
    experiment    text NOT NULL,
    run_id        text NOT NULL,
    line_index    int,
    ts            double precision,
    input_length  int,
    output_length int,
    hash_ids      bigint[]
) PARTITION BY LIST (experiment);

-- create per-experiment partitions + a DEFAULT for each partitioned raw table
DO $$
DECLARE e text; t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['llm_request','encoder_series','composed_request'] LOOP
    FOREACH e IN ARRAY ARRAY['a2','a2x','a2t','a2tf','a15','a6','a11','a12','a13','a14',
                             'g1',
                             'grid','factorial','sweeps','reactive','ctmatrix','riders',
                             'live','predictors','eda','phasee','ewma','episode','planner'] LOOP
      EXECUTE format('CREATE TABLE IF NOT EXISTS provenance.%I PARTITION OF provenance.%I FOR VALUES IN (%L)',
                     t||'_'||e, t, e);
    END LOOP;
    EXECUTE format('CREATE TABLE IF NOT EXISTS provenance.%I PARTITION OF provenance.%I DEFAULT', t||'_default', t);
  END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS llm_request_run_idx      ON provenance.llm_request (run_id);
CREATE INDEX IF NOT EXISTS encoder_series_run_idx   ON provenance.encoder_series (run_id);
CREATE INDEX IF NOT EXISTS composed_request_run_idx ON provenance.composed_request (run_id);

-- K4  *.sched.json  (autoscaler worker-count timeline; small, not partitioned)
CREATE TABLE IF NOT EXISTS provenance.worker_schedule (
    run_id       text NOT NULL,
    source_path  text NOT NULL,
    step_index   int,
    t_s          double precision,
    worker_count int,
    PRIMARY KEY (source_path, step_index)
);
CREATE INDEX IF NOT EXISTS worker_schedule_run_idx ON provenance.worker_schedule (run_id);

-- K10  forecast outputs (~21M rows; partitioned by model)
CREATE TABLE IF NOT EXISTS provenance.forecast (
    source_tag text,   -- source parquet path: the only per-load identity this table has
    model      text NOT NULL,
    mode       text,
    variate    text,
    resolution text,
    origin     int,
    h          int,
    step       int,
    ts         timestamptz,
    y_true     double precision,
    point      double precision,
    p10 double precision, p20 double precision, p30 double precision,
    p40 double precision, p50 double precision, p60 double precision,
    p70 double precision, p80 double precision, p90 double precision
) PARTITION BY LIST (model);
DO $$
DECLARE m text;
BEGIN
  FOREACH m IN ARRAY ARRAY['chronos','toto','timesfm','ewma','holt_winters','naive','moirai','arima'] LOOP
    EXECUTE format('CREATE TABLE IF NOT EXISTS provenance.%I PARTITION OF provenance.forecast FOR VALUES IN (%L)', 'forecast_'||m, m);
  END LOOP;
  EXECUTE 'CREATE TABLE IF NOT EXISTS provenance.forecast_default PARTITION OF provenance.forecast DEFAULT';
END $$;
-- retro-fit for databases created before source_tag existed (instantaneous in PG16)
ALTER TABLE provenance.forecast ADD COLUMN IF NOT EXISTS source_tag text;
CREATE INDEX IF NOT EXISTS forecast_key_idx ON provenance.forecast (model, variate, resolution, h);

-- K11  measured vLLM per-request (GROUND TRUTH; see vllm_trace_analysis/out/DATA_DICTIONARY.md)
CREATE TABLE IF NOT EXISTS provenance.measured_request (
    request_id text PRIMARY KEY,
    ts_ms bigint, send_ts double precision, img bigint, txt bigint, gen bigint, status bigint,
    client_ttft double precision, client_e2e double precision, stream_chunks bigint,
    gen_tokens bigint, prompt_tokens bigint, completion_tokens bigint, finish_reason text, error text,
    n_tok_offsets bigint, otlp_recv_ts double precision, otlp_start_ts double precision,
    otlp_end_ts double precision, otlp_duration_ms double precision, ttft_server double precision,
    e2e_server double precision, queue_s double precision, prefill_s double precision,
    decode_s double precision, inference_s double precision, engine_other_s double precision,
    prompt_tokens_otlp bigint, completion_tokens_otlp bigint, max_tokens bigint, top_p double precision,
    n bigint, status_code bigint, fe_recv_ts double precision, fe_resp_start_ts double precision,
    fe_resp_end_ts double precision, fe_to_resp_s double precision, fe_server_e2e_s double precision,
    fe_status bigint, resp_len_chars bigint, resp_head text, conv_error text, soft_img_tokens bigint,
    prompt_pred bigint, template_tokens bigint, seq_len_total bigint, tpot_decode_ms double precision,
    tpot_e2e_ms double precision, ttft_server_ms double precision, ttft_client_ms double precision,
    prefill_ms double precision, decode_ms double precision, queue_ms double precision,
    net_send_to_fe_ms double precision, fe_to_engine_ms double precision, engine_to_respend_ms double precision,
    itl_median double precision, itl_mean double precision, itl_p95 double precision, itl_std double precision,
    itl_max double precision, conc_inflight double precision, prefill_inflight double precision,
    decode_inflight double precision, kv_tokens_inflight double precision, gen_tokens_inflight double precision,
    arr_rate_1s double precision, arr_rate_5s double precision, arr_rate_10s double precision,
    vision_expected_ms double precision, prefill_nonvision_ms double precision, t_rel double precision
);

-- =========================================================================
-- PROVENANCE LEDGER + INGEST BOOKKEEPING
-- =========================================================================

-- K13  results-ledger.md (best-effort normalized)
CREATE TABLE IF NOT EXISTS provenance.ledger_entry (
    id             bigserial PRIMARY KEY,
    section        text,
    name           text,
    entry_date     date,
    artifact_paths text[],
    command        text,
    feeds          text,
    supersedes     text,
    result_note    text,
    commit_sha     text,
    run_id         text,
    raw            text
);

CREATE TABLE IF NOT EXISTS provenance.ingest_log (
    file_path  text PRIMARY KEY,
    sha256     text NOT NULL,
    kind       text,
    n_rows     bigint,
    run_id     text,
    bytes      bigint,
    loaded_at  timestamptz NOT NULL DEFAULT now()
);
