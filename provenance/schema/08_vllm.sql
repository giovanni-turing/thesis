-- =========================================================================
-- FAMILY 4 (K23): MEASURED vLLM ETL DETAIL  --  THE ONLY SILICON GROUND TRUTH
-- =========================================================================
-- Source: /mnt/9d1dd233-5327-4660-a734-36a12ae92abd/vllm_trace_analysis/out/
--   One real H100-SXM vLLM run (model gemma4-E4B-it, multimodal), 7,817 requests,
--   5,252.114 s wall clock, 1,354,025 generated tokens, 35,219 images encoded.
--   Everything in this file shares ONE run_id: 'measured:vllm_h100_trace'.
--   Per-request rows for the same run are already in provenance.measured_request
--   (loaded by K11 under run_id 'measured:vllm_per_request' -- same physical run).
--
-- Table glosses below are taken from out/DATA_DICTIONARY.md.
-- Apply: psql -v ON_ERROR_STOP=1 -h localhost -p 5433 -U goku -d postgres -f 08_vllm.sql
-- Idempotent (IF NOT EXISTS / OR REPLACE).
--
-- DELIBERATELY NOT INGESTED (derivable; see the views at the bottom of this file):
--   prometheus_wide.parquet     -- pure PIVOT of prometheus_tidy + mechanical _delta/_rate/_mean
--   vision_cost_by_n.parquet    -- 8-row GROUP BY over vision.parquet
--   global_buckets' 11 hardware columns -- an as-of join against sys.parquet
SET search_path = provenance, public;

-- ---------------------------------------------------------------- raw series

CREATE TABLE IF NOT EXISTS provenance.vllm_token_itl (
    run_id     text NOT NULL,
    request_id text NOT NULL,
    token_idx  int  NOT NULL,
    offset_ms  double precision,
    itl_ms     double precision,
    abs_ts     double precision
);
CREATE INDEX IF NOT EXISTS vllm_token_itl_req_idx ON provenance.vllm_token_itl (request_id, token_idx);
CREATE INDEX IF NOT EXISTS vllm_token_itl_ts_idx  ON provenance.vllm_token_itl (abs_ts);

COMMENT ON TABLE provenance.vllm_token_itl IS
  'K23 raw: one row per GENERATED TOKEN of the measured H100 vLLM run (1,354,025 rows). DATA_DICTIONARY gloss: "One row/generated token: request_id, token_idx, offset_ms (client ms from send; token_idx 0 offset == client TTFT), itl_ms (successive diff; NaN at idx 0), abs_ts (unix epoch)." Client-side stream timing, so it includes network/frontend jitter; join request_id to provenance.measured_request for server-side truth.';
COMMENT ON COLUMN provenance.vllm_token_itl.token_idx IS '0-based index of the token within its request. token_idx=0 is the FIRST token, so its offset_ms equals the client-observed TTFT and its itl_ms is NULL by construction.';
COMMENT ON COLUMN provenance.vllm_token_itl.offset_ms IS 'Milliseconds from client send_ts to receipt of this token (client clock).';
COMMENT ON COLUMN provenance.vllm_token_itl.itl_ms IS 'Inter-token latency = offset_ms(i) - offset_ms(i-1). NULL at token_idx=0 (NaN in the parquet). 1,346,208 of 1,354,025 rows are non-NULL.';
COMMENT ON COLUMN provenance.vllm_token_itl.abs_ts IS 'Absolute unix epoch seconds when the client received this token. Same clock as vllm_vision_encode.ts / vllm_sys_sample.ts / vllm_bucket_1s.t (NOT the same clock as vllm_engine_step.ts_local).';

CREATE TABLE IF NOT EXISTS provenance.vllm_prom_sample (
    run_id text NOT NULL,
    ts     double precision NOT NULL,
    metric text NOT NULL,
    labels text,
    value  double precision
);
CREATE INDEX IF NOT EXISTS vllm_prom_metric_ts_idx ON provenance.vllm_prom_sample (metric, ts);

COMMENT ON TABLE provenance.vllm_prom_sample IS
  'K23 raw: the vLLM Prometheus /metrics scrape in LONG form (2,237,955 rows, ~1 Hz, 5,330 scrapes, 122 distinct series). DATA_DICTIONARY gloss: "Full long frame: ts, metric, labels, value for EVERY vllm:* series." This is the FULL-PRECISION source; prometheus_wide.parquet was NOT ingested because it is a pure pivot of this table plus mechanically derived _delta/_rate/_mean columns -- reconstruct it with the views v_vllm_prom_gauge / v_vllm_prom_wide below.';
COMMENT ON COLUMN provenance.vllm_prom_sample.ts IS 'Scrape timestamp, unix epoch seconds. Scrapes start ~57 s BEFORE the first request (engine startup is covered).';
COMMENT ON COLUMN provenance.vllm_prom_sample.metric IS 'Prometheus series name, e.g. vllm:num_requests_running, vllm:generation_tokens_total, vllm:time_to_first_token_seconds_bucket. *_total are monotone COUNTERS (de-cumulate them); *_bucket/_sum/_count are histogram families; *_created are process-start constants and carry no information.';
COMMENT ON COLUMN provenance.vllm_prom_sample.labels IS 'Raw Prometheus label set as text, e.g. {engine="0",model_name="gemma4-E4B-it"} or {engine="0",le="1.0",model_name="gemma4-E4B-it"}. Histogram rows carry le="..."; filter labels NOT LIKE ''%le=%'' to get scalar series only.';
COMMENT ON COLUMN provenance.vllm_prom_sample.value IS 'Sample value in the metric''s native unit (seconds for *_seconds_*, tokens, requests, or a 0..1 fraction for kv_cache_usage_perc).';

CREATE TABLE IF NOT EXISTS provenance.vllm_vision_encode (
    run_id       text NOT NULL,
    ts           double precision NOT NULL,
    num_images   int,
    encode_ms    double precision,
    ms_per_image double precision
);
CREATE INDEX IF NOT EXISTS vllm_vision_ts_idx ON provenance.vllm_vision_encode (ts);

COMMENT ON TABLE provenance.vllm_vision_encode IS
  'K23 raw: one row per VISION ENCODE CALL (10,683 rows, 35,219 images total), GPU-event timed inside the engine. DATA_DICTIONARY gloss: "Per encode CALL (GPU-event timed): ts, num_images (1..8 batch), encode_ms, ms_per_image." This is the measured basis of the vision cost model encode_ms = 0.7108 + 13.7036*num_images (R2 = 0.999861, OLS over all 10,683 calls). A call is a BATCH of images, not a request: one request with img=64 fans out over several calls.';
COMMENT ON COLUMN provenance.vllm_vision_encode.num_images IS 'Images in this encode batch, 1..8 (8 is the engine batch cap). 5,384 of the 10,683 calls are single-image.';
COMMENT ON COLUMN provenance.vllm_vision_encode.encode_ms IS 'Wall-clock ms of the ViT encode call, measured with CUDA events (not host timers). Range 14.03..121.7 ms.';
COMMENT ON COLUMN provenance.vllm_vision_encode.ms_per_image IS 'encode_ms / num_images. Falls 16.8 -> ~13.8 ms as the batch grows: the only batching economy the encoder shows.';

CREATE TABLE IF NOT EXISTS provenance.vllm_detok (
    run_id                text NOT NULL,
    ts                    double precision NOT NULL,
    calls                 bigint,
    tokens                bigint,
    sec                   double precision,
    d_calls               double precision,
    d_tokens              double precision,
    d_sec                 double precision,
    us_per_token_interval double precision
);
CREATE INDEX IF NOT EXISTS vllm_detok_ts_idx ON provenance.vllm_detok (ts);

COMMENT ON TABLE provenance.vllm_detok IS
  'K23 raw: detokenizer cost, flushed every 100 update() calls (13,542 rows). DATA_DICTIONARY gloss: "Cumulative detok timing flushed every 100 update() calls; de-cumulated d_calls/d_tokens/d_sec/us_per_token_interval." Establishes that detokenization is negligible (~8.7 us/token) versus the 14 ms ITL floor.';
COMMENT ON COLUMN provenance.vllm_detok.calls IS 'CUMULATIVE detokenizer update() calls since process start (100 .. 1,354,000). Do NOT treat as an interval count -- use d_calls.';
COMMENT ON COLUMN provenance.vllm_detok.tokens IS 'CUMULATIVE tokens detokenized since process start. Use d_tokens for the interval.';
COMMENT ON COLUMN provenance.vllm_detok.sec IS 'CUMULATIVE seconds spent in detokenization since process start (max 23.82 s over the whole run). Use d_sec for the interval.';
COMMENT ON COLUMN provenance.vllm_detok.d_calls IS 'Interval delta of calls: always exactly 100 (the flush period). NULL on the first row.';
COMMENT ON COLUMN provenance.vllm_detok.d_tokens IS 'Interval delta of tokens (100). NULL on the first row.';
COMMENT ON COLUMN provenance.vllm_detok.d_sec IS 'Interval delta of sec: seconds spent detokenizing the last 100 tokens. NULL on the first row.';
COMMENT ON COLUMN provenance.vllm_detok.us_per_token_interval IS 'Microseconds per token over the interval = d_sec/d_tokens*1e6. Range 3.1..268.7 us; the run-level figure quoted in the analysis is ~8.7 us/token.';

CREATE TABLE IF NOT EXISTS provenance.vllm_sys_sample (
    run_id           text NOT NULL,
    ts               double precision NOT NULL,
    gpu_util_pct     int,
    gpu_mem_util_pct int,
    gpu_mem_used_mib bigint,
    gpu_power_w      double precision,
    gpu_temp_c       int,
    gpu_sm_clock_mhz int,
    cpu_pct          double precision,
    cpu_pct_max_core double precision,
    load1            double precision,
    ram_used_mib     bigint,
    ram_pct          double precision
);
CREATE INDEX IF NOT EXISTS vllm_sys_ts_idx ON provenance.vllm_sys_sample (ts);

COMMENT ON TABLE provenance.vllm_sys_sample IS
  'K23 raw: 1 Hz host/GPU hardware sampler for the measured run (5,410 rows, covers startup + the 5,252 s workload). DATA_DICTIONARY gloss: "1Hz host sampler: gpu_util_pct, gpu_mem_used_mib, gpu_power_w, gpu_temp_c, gpu_sm_clock_mhz, cpu_pct, cpu_pct_max_core, load1, ram_used_mib, ram_pct." This is the SOLE copy of the hardware telemetry: the 11 identical columns inside global_buckets.parquet were an as-of join against this table and were deliberately not duplicated -- join vllm_bucket_1s to this table on sys_join_ts (exact) or on nearest ts.';
COMMENT ON COLUMN provenance.vllm_sys_sample.ts IS 'Sample timestamp, unix epoch seconds (same clock as vllm_bucket_1s.t and vllm_vision_encode.ts).';
COMMENT ON COLUMN provenance.vllm_sys_sample.gpu_util_pct IS 'NVML GPU utilization percent (0..100). >=50 is the "active" regime used by the hardware_regimes facet.';
COMMENT ON COLUMN provenance.vllm_sys_sample.gpu_mem_util_pct IS 'NVML memory-controller utilization percent (0..63), NOT memory occupancy -- that is gpu_mem_used_mib.';
COMMENT ON COLUMN provenance.vllm_sys_sample.gpu_mem_used_mib IS 'GPU memory in use (MiB). Pinned at ~31,001 MiB once the KV cache is allocated; 513 MiB before.';
COMMENT ON COLUMN provenance.vllm_sys_sample.gpu_power_w IS 'Board power draw (W), 8.2 idle .. 570.8 peak.';
COMMENT ON COLUMN provenance.vllm_sys_sample.gpu_sm_clock_mhz IS 'SM clock (MHz), 187 idle .. 2,932 boost. Active-regime mean 2,893.8 MHz (CV 0.6%) -- i.e. NO thermal/power throttling during the workload.';
COMMENT ON COLUMN provenance.vllm_sys_sample.cpu_pct IS 'Host-wide CPU utilization percent (all cores averaged).';
COMMENT ON COLUMN provenance.vllm_sys_sample.cpu_pct_max_core IS 'Utilization of the single busiest core. Frequently 100% while cpu_pct is ~10% -- one saturated core (the engine loop), not a host CPU bottleneck.';
COMMENT ON COLUMN provenance.vllm_sys_sample.load1 IS '1-minute load average.';

CREATE TABLE IF NOT EXISTS provenance.vllm_bucket_1s (
    run_id            text NOT NULL,
    t                 double precision NOT NULL,
    t_rel             double precision,
    arrivals          int,
    completions       int,
    gen_tokens        bigint,
    gen_tput_tok_s    double precision,
    prompt_tokens     bigint,
    prompt_tput_tok_s double precision,
    vision_encode_ms  double precision,
    vision_images     int,
    vision_busy_frac  double precision,
    inflight          int,
    sys_join_ts       double precision
);
CREATE INDEX IF NOT EXISTS vllm_bucket_trel_idx ON provenance.vllm_bucket_1s (t_rel);

COMMENT ON TABLE provenance.vllm_bucket_1s IS
  'K23 raw: 1-second time buckets over the measured run (5,253 rows = the 5,252 s wall clock). DATA_DICTIONARY gloss: "1s time buckets: arrivals, completions, gen_tokens, gen_tput_tok_s, prompt_tput_tok_s, vision_encode_ms, vision_images, vision_busy_frac, inflight, + nearest sys hardware sample." The 11 nearest-sys hardware columns of the parquet were DROPPED here (they are an as-of join, not a measurement): join provenance.vllm_sys_sample ON ts = sys_join_ts to reproduce the parquet exactly.';
COMMENT ON COLUMN provenance.vllm_bucket_1s.t IS 'Bucket centre, unix epoch seconds.';
COMMENT ON COLUMN provenance.vllm_bucket_1s.t_rel IS 'Seconds since the first request (0 .. 5252). Use this for plots and for joining to measured_request.t_rel.';
COMMENT ON COLUMN provenance.vllm_bucket_1s.arrivals IS 'Requests that arrived in this second (0..9).';
COMMENT ON COLUMN provenance.vllm_bucket_1s.completions IS 'Requests that finished in this second (0..9).';
COMMENT ON COLUMN provenance.vllm_bucket_1s.gen_tput_tok_s IS 'Generated tokens per second in this bucket (numerically equal to gen_tokens for 1 s buckets). Peak 1,088 tok/s.';
COMMENT ON COLUMN provenance.vllm_bucket_1s.prompt_tput_tok_s IS 'Prompt tokens processed per second in this bucket. Peak 47,180 tok/s.';
COMMENT ON COLUMN provenance.vllm_bucket_1s.vision_encode_ms IS 'Total ViT encode milliseconds attributed to this second (sum over encode calls).';
COMMENT ON COLUMN provenance.vllm_bucket_1s.vision_busy_frac IS 'vision_encode_ms/1000: the fraction of this second the vision encoder was busy. Max 0.509 -- the encoder never saturates in this run.';
COMMENT ON COLUMN provenance.vllm_bucket_1s.inflight IS 'Concurrent requests in the engine during this second (0..16). 16 is the CLOSED-LOOP CLIENT CAP, not a server limit -- every model fitted on this run is valid only for concurrency 0..16.';
COMMENT ON COLUMN provenance.vllm_bucket_1s.sys_join_ts IS 'The vllm_sys_sample.ts that the ETL as-of-joined to this bucket. Kept purely as an exact join key so the dropped hardware columns are reproducible; it is not itself a measurement of this bucket.';

CREATE TABLE IF NOT EXISTS provenance.vllm_engine_step (
    run_id         text NOT NULL,
    ts_local       double precision NOT NULL,
    prompt_tput    double precision,
    gen_tput       double precision,
    running        int,
    waiting        int,
    kv_usage_pct   double precision,
    prefix_hit_pct double precision
);

COMMENT ON TABLE provenance.vllm_engine_step IS
  'K23 raw: vLLM engine step log lines parsed from stdout, ~1 per 10 s (527 rows). DATA_DICTIONARY gloss: "vLLM engine step lines (~10s): prompt_tput, gen_tput, running, waiting, kv_usage_pct, prefix_hit_pct. ts_local may need offset alignment." *** CLOCK CAVEAT: ts_local is on a DIFFERENT CLOCK from every other table in this family. Do NOT join or align it to ts / abs_ts / t without first establishing the offset. It is deliberately named ts_local, not ts, for that reason. Use it for distributions and for corroborating vllm_prom_sample, not for per-second alignment.';
COMMENT ON COLUMN provenance.vllm_engine_step.ts_local IS 'Engine-local log timestamp, unix epoch seconds. DIFFERENT CLOCK from the other tables -- may need an offset alignment before any temporal join (see the table comment).';
COMMENT ON COLUMN provenance.vllm_engine_step.prompt_tput IS 'Engine-reported prompt throughput (tokens/s) over the step window, 0..9,757.';
COMMENT ON COLUMN provenance.vllm_engine_step.gen_tput IS 'Engine-reported generation throughput (tokens/s) over the step window, 0..850.2.';
COMMENT ON COLUMN provenance.vllm_engine_step.running IS 'Requests running in the engine at the log line (0..16 -- the closed-loop client cap).';
COMMENT ON COLUMN provenance.vllm_engine_step.waiting IS 'Requests queued waiting for admission (0..4).';
COMMENT ON COLUMN provenance.vllm_engine_step.kv_usage_pct IS 'KV-cache occupancy percent (0..13.9). The KV cache is never close to full in this run: no preemption pressure.';
COMMENT ON COLUMN provenance.vllm_engine_step.prefix_hit_pct IS 'Prefix-cache hit rate percent. IDENTICALLY ZERO for all 527 rows -- prefix caching delivered no benefit in this run.';

CREATE TABLE IF NOT EXISTS provenance.vllm_otlp_startup (
    run_id       text NOT NULL,
    span_name    text NOT NULL,
    start_ts     double precision,
    end_ts       double precision,
    duration_ms  double precision,
    process_kind text,
    module       text,
    PRIMARY KEY (run_id, span_name, start_ts)
);

COMMENT ON TABLE provenance.vllm_otlp_startup IS
  'K23 raw: engine initialisation spans from OpenTelemetry (14 rows). DATA_DICTIONARY gloss: "Engine init spans (Worker init, Load weights, Allocate KV cache, Warmup, ...): name, start_ts, end_ts, duration_ms." This is the measured COLD-START budget of a vLLM worker on H100 -- the empirical anchor for the cold_start_s / lead_s provisioning parameters used elsewhere in the thesis.';
COMMENT ON COLUMN provenance.vllm_otlp_startup.span_name IS 'Span label as emitted by vLLM (e.g. "Worker init", "Load weights", "Allocate KV cache", "Warmup"). Renamed from the parquet column "name" for clarity.';
COMMENT ON COLUMN provenance.vllm_otlp_startup.duration_ms IS 'Span duration in ms, 52.1 .. 23,730. Sum over the top-level spans is the worker cold-start time.';
COMMENT ON COLUMN provenance.vllm_otlp_startup.process_kind IS 'Emitting process role, e.g. engine_core. NULL for 2 of the 14 spans.';

-- ---------------------------------------------------- reconciliation + stats

CREATE TABLE IF NOT EXISTS provenance.vllm_reconcile_check (
    run_id     text NOT NULL,
    check_name text NOT NULL,
    level      text,
    passed     boolean,
    detail     text,
    PRIMARY KEY (run_id, check_name)
);

COMMENT ON TABLE provenance.vllm_reconcile_check IS
  'K23: the 13 ETL self-consistency checks from out/reconcile.json -- the audit gate on the whole measured dataset. hard_fail was FALSE for this run: every "hard" check passed; exactly one "soft" check failed (client_gen_tokens_eq_gen, 24/7817 rows, a known logprob edge where server truth was used). Query this table before citing any number from the vllm_* tables.';
COMMENT ON COLUMN provenance.vllm_reconcile_check.check_name IS 'Check identifier, e.g. join_1to1, phase_identity, token_itl_total, vision_image_count.';
COMMENT ON COLUMN provenance.vllm_reconcile_check.level IS 'hard = a failure invalidates the dataset (the ETL aborts); soft = advisory, recorded but tolerated.';
COMMENT ON COLUMN provenance.vllm_reconcile_check.passed IS 'TRUE if the check passed. Exactly one row is FALSE for this run (client_gen_tokens_eq_gen, level=soft).';
COMMENT ON COLUMN provenance.vllm_reconcile_check.detail IS 'Free-text evidence string, e.g. "client=7817 otlp=7817 fe=7817 merged=7817 unique=True".';

CREATE TABLE IF NOT EXISTS provenance.vllm_stat (
    run_id      text NOT NULL,
    source_file text NOT NULL,
    facet       text,
    metric_path text NOT NULL,
    value_num   double precision,
    value_text  text,
    value_json  jsonb,
    is_valid    boolean NOT NULL DEFAULT true,
    PRIMARY KEY (run_id, source_file, metric_path)
);
CREATE INDEX IF NOT EXISTS vllm_stat_path_idx  ON provenance.vllm_stat (metric_path);
CREATE INDEX IF NOT EXISTS vllm_stat_facet_idx ON provenance.vllm_stat (facet);

COMMENT ON TABLE provenance.vllm_stat IS
  'K23: TALL (entity-attribute-value) flattening of every analysis stats JSON of the measured run -- out/stats/*.json (15 files) plus the summary block of out/reconcile.json. Each nested JSON leaf becomes one row keyed by a dotted metric_path. This is the full-precision numeric record behind the narrative claims in vllm_facet_claim; when a claim and a stat disagree, the stat wins. Typical use: SELECT value_num FROM vllm_stat WHERE source_file=''prefill_ttft.json'' AND metric_path LIKE ''decomp%%''.';
COMMENT ON COLUMN provenance.vllm_stat.source_file IS 'Basename of the JSON the row came from: prefill_ttft.json, decode_tpot.json, queue_arrival.json, vision_encoder.json, hardware_regimes.json, prometheus_dynamics.json, waterfall_overhead.json, regimes_degradation.json, trace_inputs.json, model_knn.json, model_mlp.json, xgb_ensemble.json, physical_mechanistic.json, supplementary.json, verify_decode_tpot_check.json, reconcile.json.';
COMMENT ON COLUMN provenance.vllm_stat.facet IS 'source_file without the .json extension -- joins to vllm_facet.facet for the 9 narrative facets (the model_*/xgb_*/physical_*/supplementary/verify_* files have no narrative facet).';
COMMENT ON COLUMN provenance.vllm_stat.metric_path IS 'Dot-separated path to the leaf inside the JSON, with list elements as [i], e.g. "decomp.agg_share_prefill" or "operating_regimes[2].gpu_util_mean". Reconstructs the original nesting exactly.';
COMMENT ON COLUMN provenance.vllm_stat.value_num IS 'The leaf value when it is numeric (booleans are also stored here as 1/0). NULL for string/array leaves.';
COMMENT ON COLUMN provenance.vllm_stat.value_text IS 'The leaf value when it is a string (or "true"/"false" for booleans). Holds the prose caveats and free-text notes embedded in the stats files.';
COMMENT ON COLUMN provenance.vllm_stat.value_json IS 'The leaf value when it is a homogeneous array of scalars (e.g. a histogram bin list) -- stored whole rather than exploded.';
COMMENT ON COLUMN provenance.vllm_stat.is_valid IS 'FALSE marks a stat the project itself disowned. All rows are TRUE for this run: no stats file was superseded. Kept so a retraction can be recorded without deleting the evidence.';

-- ------------------------------------------------------------ fitted models

CREATE TABLE IF NOT EXISTS provenance.vllm_model_fit (
    run_id       text NOT NULL,
    model        text NOT NULL,
    target       text NOT NULL,
    variant      text NOT NULL,
    mape         double precision,
    median_ape   double precision,
    rmse         double precision,
    r2           double precision,
    p90_abs_err  double precision,
    mean_abs_err double precision,
    n_test       bigint,
    is_best      boolean NOT NULL DEFAULT false,
    top_features text[],
    source_file  text,
    PRIMARY KEY (run_id, model, target, variant)
);

COMMENT ON TABLE provenance.vllm_model_fit IS
  'K23: held-out accuracy of every latency model fitted on the measured run (4 model families x 2 targets x 2 variants = 16 rows). Numbers are the FULL-PRECISION values from out/stats/{model_mlp,model_knn,xgb_ensemble,physical_mechanistic}.json; the rounded duplicates in out/findings/model_bundle.json "fits" were deliberately NOT ingested (only its best_models flags were, into is_best). Split: time-ordered, last 20% = test (n=1564); target transform log1p. VALIDITY ENVELOPE: concurrency 0..16 only (closed-loop client cap); tpot models exclude gen<=1.';
COMMENT ON COLUMN provenance.vllm_model_fit.model IS 'Model family: xgboost (GPU hist ensemble), torch_mlp, cuml_knn, physical (mechanistic closed form).';
COMMENT ON COLUMN provenance.vllm_model_fit.target IS 'Predicted quantity: ttft_server_ms or tpot_decode_ms (server-side ground truth from measured_request).';
COMMENT ON COLUMN provenance.vllm_model_fit.variant IS 'marginal = features are request INPUTS only (img,txt,gen,...) -- this is the feed-forward predictor t(); contextual = adds runtime load features. CONTEXTUAL IS NOT A FEED-FORWARD PREDICTOR: its experienced-context features are time-averages over the request''s own service window and are only resolvable inside a closed-loop simulator (leakage_notes in xgb_ensemble.json).';
COMMENT ON COLUMN provenance.vllm_model_fit.mape IS 'Test mean absolute percentage error (percent). Headline: ttft torch_mlp contextual 21.11%, tpot xgboost contextual 7.17%.';
COMMENT ON COLUMN provenance.vllm_model_fit.r2 IS 'Test R^2. NEGATIVE for the tpot marginal variants: request inputs genuinely cannot predict TPOT, because the dominant driver is chunked-prefill interference, which inputs cannot see.';
COMMENT ON COLUMN provenance.vllm_model_fit.n_test IS 'Held-out test rows (1,564 = last 20% of 7,817, time-ordered).';
COMMENT ON COLUMN provenance.vllm_model_fit.is_best IS 'TRUE for the per-target winner declared in out/findings/model_bundle.json best_models: torch_mlp for ttft_server_ms, xgboost for tpot_decode_ms (both contextual).';
COMMENT ON COLUMN provenance.vllm_model_fit.top_features IS 'Ranked feature list as reported by the fit (gain or permutation importance, per family).';
COMMENT ON COLUMN provenance.vllm_model_fit.source_file IS 'Which stats JSON this row was read from -- the full-precision source, not model_bundle.json.';

CREATE TABLE IF NOT EXISTS provenance.vllm_sim_validation (
    run_id              text NOT NULL,
    metric              text NOT NULL,
    median_actual       double precision,
    median_sim          double precision,
    median_ape_pct      double precision,
    p95_actual          double precision,
    p95_sim             double precision,
    p95_ape_pct         double precision,
    per_request_mape_pct double precision,
    ks_stat             double precision,
    PRIMARY KEY (run_id, metric)
);

COMMENT ON TABLE provenance.vllm_sim_validation IS
  'K23: replay-validation of the closed-loop simulator built from the measured run (out/findings/model_bundle.json simulator.validation_metrics). The simulator replays the trace and its output distribution is compared to the measured one. This is the accuracy claim any thesis statement about the simulator must cite.';
COMMENT ON COLUMN provenance.vllm_sim_validation.metric IS 'Validated quantity: ttft_ms, tpot_ms, or e2e_ms.';
COMMENT ON COLUMN provenance.vllm_sim_validation.median_ape_pct IS 'Absolute percentage error of the SIMULATED median vs the ACTUAL median (distributional accuracy). ttft 38.2%, tpot 3.4%, e2e 14.2%.';
COMMENT ON COLUMN provenance.vllm_sim_validation.per_request_mape_pct IS 'Per-request paired MAPE. USE WITH CARE: for tpot_ms it is 1.5e7 percent, an artefact of near-zero denominators (gen=1 requests), not a meaningful error. Prefer the distributional median/p95/ks columns.';
COMMENT ON COLUMN provenance.vllm_sim_validation.ks_stat IS 'Two-sample Kolmogorov-Smirnov statistic between simulated and actual distributions (0 = identical). e2e 0.074, ttft 0.129, tpot 0.247.';

-- ---------------------------------------------------- narrative + adversarial

CREATE TABLE IF NOT EXISTS provenance.vllm_facet (
    run_id       text NOT NULL,
    facet        text NOT NULL,
    script_path  text,
    stats_json   text,
    figures      text[],
    n_claims     int,
    n_confirmed  int,
    n_partly     int,
    analysis     jsonb,
    verification jsonb,
    PRIMARY KEY (run_id, facet)
);

COMMENT ON TABLE provenance.vllm_facet IS
  'K23: the 9 analysis FACETS of the measured run (out/findings/analysis_bundle.json). Each facet is one analyst pass over the ETL output plus an INDEPENDENT verifier pass that re-derived every claim from the parquets. The per-claim rows are in vllm_facet_claim; the full untruncated analyst and verifier objects (caveats, surprises, model_hints, additional_issues, verifier script) are kept verbatim in the analysis / verification jsonb columns.';
COMMENT ON COLUMN provenance.vllm_facet.facet IS 'Facet name: prefill_ttft, decode_tpot, queue_arrival, vision_encoder, hardware_regimes, prometheus_dynamics, waterfall_overhead, regimes_degradation, trace_inputs.';
COMMENT ON COLUMN provenance.vllm_facet.stats_json IS 'Path of the stats JSON this facet produced -- its rows are in vllm_stat with the matching source_file.';
COMMENT ON COLUMN provenance.vllm_facet.n_confirmed IS 'Claims the independent verifier reproduced exactly (verdict = confirmed). Run totals: 40 confirmed, 14 partly, 0 fully refuted.';
COMMENT ON COLUMN provenance.vllm_facet.n_partly IS 'Claims the verifier only partly reproduced (numbers right, mechanism or framing off). Read the claim''s verdict_note before citing any of these.';
COMMENT ON COLUMN provenance.vllm_facet.analysis IS 'Full analyst object as jsonb: headline_findings, quantitative_summary, caveats, surprises, model_hints, evidence, figures, script_path.';
COMMENT ON COLUMN provenance.vllm_facet.verification IS 'Full verifier object as jsonb: verdicts, additional_issues, verifier_check_script (the script text that re-derived the numbers).';

CREATE TABLE IF NOT EXISTS provenance.vllm_facet_claim (
    run_id       text NOT NULL,
    facet        text NOT NULL,
    claim_index  int  NOT NULL,
    claim        text,
    evidence     text,
    confidence   text,
    verdict      text,
    verdict_note text,
    recomputed   text,
    is_valid     boolean NOT NULL DEFAULT true,
    PRIMARY KEY (run_id, facet, claim_index)
);
CREATE INDEX IF NOT EXISTS vllm_claim_valid_idx ON provenance.vllm_facet_claim (is_valid, verdict);

COMMENT ON TABLE provenance.vllm_facet_claim IS
  'K23: one row per HEADLINE CLAIM about the measured run (54 rows across 9 facets), each paired with the independent verifier''s verdict and re-derivation. This is the claim-level audit trail for the silicon chapter: any thesis sentence about the measured vLLM run should be traceable to a row here whose is_valid is TRUE.';
COMMENT ON COLUMN provenance.vllm_facet_claim.claim_index IS '1-based index of the claim within its facet, matching the verifier''s claim_index and the critic''s "<facet> CLAIM <n>" references.';
COMMENT ON COLUMN provenance.vllm_facet_claim.claim IS 'The analyst''s claim, verbatim.';
COMMENT ON COLUMN provenance.vllm_facet_claim.evidence IS 'The analyst''s supporting numbers, verbatim.';
COMMENT ON COLUMN provenance.vllm_facet_claim.confidence IS 'Analyst self-assessed confidence: high / medium / low. NOT the verifier''s opinion -- use verdict for that.';
COMMENT ON COLUMN provenance.vllm_facet_claim.verdict IS 'Independent verifier verdict: confirmed (40 rows) or partly (14 rows). No claim was fully refuted at verification time; the refutation of prefill_ttft claim 6 came later, from the critic pass (see vllm_critic_note and is_valid).';
COMMENT ON COLUMN provenance.vllm_facet_claim.verdict_note IS 'The verifier''s prose: what reproduced, what did not, and any framing correction. Mandatory reading for verdict = partly.';
COMMENT ON COLUMN provenance.vllm_facet_claim.recomputed IS 'The verifier''s independently recomputed numbers for this claim.';
COMMENT ON COLUMN provenance.vllm_facet_claim.is_valid IS 'FALSE = the critic pass explicitly REFUTED or demanded a rewrite of this claim (a vllm_critic_note row of category redo_needed names it). DO NOT CITE is_valid = FALSE claims. Join vllm_critic_note on (facet, claim_index) for the reason. For this run THREE claims are FALSE: prefill_ttft claim 6 (its mechanism, "busy-server inflation is queueing/co-scheduling", is contradicted by the data and by regimes_degradation), prefill_ttft claim 5 (vision-share trend whose numerator is a MODELLED, not measured, split), and decode_tpot claim 2 (the "they carry essentially all the tail" flourish is an overstatement). Their NUMBERS may still be correct -- it is the stated mechanism/framing that was disowned.';

CREATE TABLE IF NOT EXISTS provenance.vllm_critic_note (
    run_id      text NOT NULL,
    category    text NOT NULL,
    note_index  int  NOT NULL,
    facet       text,
    claim_index int,
    note        text,
    PRIMARY KEY (run_id, category, note_index)
);

COMMENT ON TABLE provenance.vllm_critic_note IS
  'K23: the adversarial CRITIC pass over all 9 facets (out/findings/analysis_bundle.json critic) -- 29 notes. This is where the measured-run analysis argues with itself: unmeasured gaps, claims needing rewrite, cross-facet contradictions, and the surviving headline results. Read the redo_needed and inconsistencies rows before quoting any facet claim.';
COMMENT ON COLUMN provenance.vllm_critic_note.category IS 'gap (8: decision-relevant quantity no facet computed, e.g. SLO attainment, phase co-occupancy) | redo_needed (4: a claim that must be rewritten before it can be headlined) | inconsistency (5: two facets reaching opposite conclusions from the same data) | headline_result (12: the results the critic endorses after adjudication).';
COMMENT ON COLUMN provenance.vllm_critic_note.note_index IS '1-based position within the category, preserving the critic''s own ordering (roughly severity-ranked).';
COMMENT ON COLUMN provenance.vllm_critic_note.facet IS 'Facet the note targets, parsed best-effort from a leading "<facet> CLAIM <n>" reference. NULL when the note is cross-cutting.';
COMMENT ON COLUMN provenance.vllm_critic_note.claim_index IS 'Claim the note targets, parsed best-effort from the note text. Joins to vllm_facet_claim (facet, claim_index). NULL when not claim-specific.';
COMMENT ON COLUMN provenance.vllm_critic_note.note IS 'The critic''s full text, verbatim and untruncated. These carry the run''s most important caveats (e.g. 100% of requests hit max_tokens: no natural EOS, so all decode-length conclusions are conditioned on synthetic fixed-length generation).';

-- ---------------------------------------------------------------- views that
-- replace the artifacts we deliberately did not ingest

-- Replaces vision_cost_by_n.parquet (an 8-row GROUP BY over vision.parquet).
CREATE OR REPLACE VIEW provenance.v_vllm_vision_cost_by_n AS
    SELECT run_id, num_images,
           avg(encode_ms)                                                    AS mean_encode_ms,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY encode_ms)            AS median_encode_ms,
           stddev_samp(encode_ms)                                            AS std_encode_ms,
           count(*)                                                          AS n_calls,
           avg(ms_per_image)                                                 AS mean_ms_per_image
    FROM provenance.vllm_vision_encode
    GROUP BY run_id, num_images;

COMMENT ON VIEW provenance.v_vllm_vision_cost_by_n IS
  'Reconstructs vision_cost_by_n.parquet (deliberately not ingested: it is a GROUP BY over vision.parquet). Encode cost per batch size: mean 14.42 ms at num_images=1 rising to 110.3 ms at 8, i.e. ~13.7 ms marginal per image with a 0.71 ms fixed cost.';

-- Scalar (non-histogram) Prometheus series only.
CREATE OR REPLACE VIEW provenance.v_vllm_prom_gauge AS
    SELECT run_id, ts, metric, value
    FROM provenance.vllm_prom_sample
    WHERE labels NOT LIKE '%le=%' AND metric NOT LIKE '%_created';

COMMENT ON VIEW provenance.v_vllm_prom_gauge IS
  'vllm_prom_sample with histogram bucket rows (labels containing le=) and constant *_created rows removed: the ~1 Hz scalar gauge/counter series only. Building block for v_vllm_prom_wide.';

-- Replaces the interesting part of prometheus_wide.parquet (a pure pivot + derived cols).
CREATE OR REPLACE VIEW provenance.v_vllm_prom_wide AS
    SELECT run_id, ts,
           max(value) FILTER (WHERE metric = 'vllm:num_requests_running')        AS num_requests_running,
           max(value) FILTER (WHERE metric = 'vllm:num_requests_waiting')        AS num_requests_waiting,
           max(value) FILTER (WHERE metric = 'vllm:kv_cache_usage_perc')         AS kv_cache_usage_perc,
           max(value) FILTER (WHERE metric = 'vllm:prompt_tokens_total')         AS prompt_tokens_total,
           max(value) FILTER (WHERE metric = 'vllm:generation_tokens_total')     AS generation_tokens_total,
           max(value) FILTER (WHERE metric = 'vllm:prefix_cache_queries_total')  AS prefix_cache_queries_total,
           max(value) FILTER (WHERE metric = 'vllm:prefix_cache_hits_total')     AS prefix_cache_hits_total,
           max(value) FILTER (WHERE metric = 'vllm:num_preemptions_total')       AS num_preemptions_total,
           sum(value) FILTER (WHERE metric = 'vllm:request_success_total')       AS request_success_total,
           max(value) FILTER (WHERE metric = 'vllm:time_to_first_token_seconds_sum')   AS ttft_seconds_sum,
           max(value) FILTER (WHERE metric = 'vllm:time_to_first_token_seconds_count') AS ttft_seconds_count,
           max(value) FILTER (WHERE metric = 'vllm:inter_token_latency_seconds_sum')   AS itl_seconds_sum,
           max(value) FILTER (WHERE metric = 'vllm:inter_token_latency_seconds_count') AS itl_seconds_count,
           max(value) FILTER (WHERE metric = 'vllm:e2e_request_latency_seconds_sum')   AS e2e_seconds_sum,
           max(value) FILTER (WHERE metric = 'vllm:request_queue_time_seconds_sum')    AS queue_seconds_sum,
           max(value) FILTER (WHERE metric = 'vllm:request_prefill_time_seconds_sum')  AS prefill_seconds_sum,
           max(value) FILTER (WHERE metric = 'vllm:request_decode_time_seconds_sum')   AS decode_seconds_sum
    FROM provenance.v_vllm_prom_gauge
    GROUP BY run_id, ts;

COMMENT ON VIEW provenance.v_vllm_prom_wide IS
  'Reconstructs the load-bearing columns of prometheus_wide.parquet (deliberately not ingested: it is a pure pivot of prometheus_tidy plus mechanically derived _delta/_rate/_mean). *_total columns are MONOTONE COUNTERS -- de-cumulate with value - lag(value) OVER (ORDER BY ts) to get the _delta/_rate columns of the original parquet. request_success_total is summed because it is label-split by finish reason.';

-- Every K23 table carries the same single run_id: there is exactly one measured run.
DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['vllm_token_itl','vllm_prom_sample','vllm_vision_encode','vllm_detok',
                           'vllm_sys_sample','vllm_bucket_1s','vllm_engine_step','vllm_otlp_startup',
                           'vllm_reconcile_check','vllm_stat','vllm_model_fit','vllm_sim_validation',
                           'vllm_facet','vllm_facet_claim','vllm_critic_note']
  LOOP
    EXECUTE format($f$COMMENT ON COLUMN provenance.%I.run_id IS
      'Always ''measured:vllm_h100_trace'' -- this family is ONE physical H100 vLLM run. Joins to provenance.runs. The per-request rows of the same run live in provenance.measured_request under run_id ''measured:vllm_per_request''.'$f$, t);
  END LOOP;
END $$;

COMMENT ON COLUMN provenance.vllm_otlp_startup.module IS 'Emitting vLLM module, e.g. vllm.engine_core.';
COMMENT ON COLUMN provenance.vllm_facet.script_path IS 'Path of the analysis script that produced this facet (in the vllm_trace_analysis workspace, outside this repo).';
COMMENT ON COLUMN provenance.vllm_facet.figures IS 'Absolute paths of the PNG figures this facet produced (in vllm_trace_analysis/viz/), not stored in the DB.';
COMMENT ON COLUMN provenance.vllm_model_fit.median_ape IS 'Test median absolute percentage error -- more robust than mape, which the long TTFT tail inflates.';
COMMENT ON COLUMN provenance.vllm_model_fit.p90_abs_err IS 'Test 90th-percentile absolute error, in the target''s own unit (ms).';
COMMENT ON COLUMN provenance.vllm_sim_validation.p95_ape_pct IS 'Absolute percentage error of the SIMULATED p95 vs the ACTUAL p95 -- the tail-accuracy figure.';
