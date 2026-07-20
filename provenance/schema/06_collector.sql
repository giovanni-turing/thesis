-- =========================================================================
-- 06_collector.sql  --  family "collector" (K21): AIC cost model vs real silicon
-- =========================================================================
-- Backs tex/aiconfigurator.tex (Ch.5). Source tree: /home/gio/tese/collector_artifacts/
-- (phase0..phase9 + phaseA..phaseE). Loader: provenance/loader/load_collector_silicon.py
--
-- The scientific question these tables answer: aiconfigurator (AIC) predicts ViT encoder
-- forward time f(N) analytically; how far is that from a real NVIDIA RTX 5090 running the
-- Qwen3-VL-8B vision tower, and what does the gap do to the provisioned worker count C*?
--
-- Engine vocabulary (normalized by the loader, use these spellings everywhere):
--   'aic'                -- aiconfigurator analytic prediction (not measured)
--   'vllm'               -- vLLM ViT path on this silicon (FLASH_ATTN backend)
--   'eager'              -- HuggingFace eager/sdpa ViT forward, no torch.compile
--   'compiled'           -- same model under torch.compile   (source files spell this
--                           'compile' in anchor_master.json and 'compiled' in
--                           burst_anchor_all.json -- NORMALIZED TO 'compiled' here)
--   'sdpa','flash_attention_2'  -- attention-backend-specific anchor benchmarks
--
-- Apply:  psql -h localhost -p 5433 -U goku -d postgres -v ON_ERROR_STOP=1 -f 06_collector.sql
-- Idempotent (CREATE TABLE IF NOT EXISTS).

CREATE SCHEMA IF NOT EXISTS provenance;
SET search_path = provenance, public;


-- ---------------------------------------------------------------- bench run
-- One row per measurement artifact file: the physical conditions under which the
-- numbers in that file were produced. Join any other collector_* table to this on
-- source_path to find out whether the GPU clocks were locked, which torch/CUDA built
-- it, and whether the run is a valid anchor.
CREATE TABLE IF NOT EXISTS provenance.collector_bench_run (
    source_path        text PRIMARY KEY,
    family             text,   -- anchor | fn | vllm | compile | opprofile | replay | closedloop | multiworker | burst_anchor | sim_stats | aiperf | collector_summary
    phase              text,   -- collector_artifacts phase dir (phaseB, phaseC, phaseE, phase9_two_pool, ...)
    experiment         text,   -- self-declared experiment label inside the file, when present
    attn_requested     text,   -- attention impl asked for (sdpa | flash_attention_2 | ...)
    attn_used          text,   -- attention impl actually selected by the framework
    engine             text,   -- dominant engine of this artifact (see vocabulary above); NULL if multi-engine
    model_dir          text,
    n_params           bigint, -- vision-tower parameter count (576,388,336 for Qwen3-VL-8B ViT)
    load_s             double precision,
    nruns              int,    -- protocol: independent replications
    iters              int,    -- protocol: timed iterations per replication
    warmup             int,    -- protocol: discarded warm-up iterations
    image_px           int,    -- protocol: input image edge in pixels
    grid_n             int,    -- protocol: ViT patch grid edge (28 => 784 patches at 448px)
    aic_reference_csv  text,   -- which AIC f(N) CSV the ratio_meas_over_pred column was computed against
    clocks_locked      boolean,-- as recorded by the bench harness (may be false even when externally locked -- see clock_lock_note)
    clock_lock_note    text,
    gpu_name           text,
    sm_clock_mhz       int,    -- nominal/target SM clock for the run
    sm_clock_before    int,
    sm_clock_after     int,
    max_sm_clock_mhz   int,
    power_w_before     double precision,
    power_w_after      double precision,
    temp_c_before      int,
    temp_c_after       int,
    throttle_hex_after text,   -- nvidia-smi throttle reason bitmask AFTER the run; '0x...0' == no throttling
    mem_used_mib_after int,
    torch_version      text,
    cuda_version       text,
    python_version     text,
    ratio_min          double precision,  -- ratio_summary: measured/AIC across all N in this file
    ratio_max          double precision,
    ratio_mean         double precision,
    ratio_spread_pct   double precision,
    ts                 timestamptz,       -- timestamp_utc declared inside the artifact
    is_valid           boolean NOT NULL DEFAULT true,  -- false => superseded/contended measurement, NEVER quote as an anchor
    invalid_reason     text,
    raw                jsonb              -- full file header (everything except the bulk rows)
);

COMMENT ON TABLE provenance.collector_bench_run IS
 'Per-artifact provenance for the collector/AIC-silicon family (K21): GPU state before/after, clock lock, toolchain versions, protocol, and the file-level measured/AIC ratio summary. is_valid=false marks measurements that must never be quoted as anchors (e.g. the CONTENDED run).';
COMMENT ON COLUMN provenance.collector_bench_run.clocks_locked IS 'Flag as written by the bench harness. anchor_*.json record true but their clock_lock_note explains the SM clock was pinned externally via nvidia-smi -lgc; fn_silicon_CONTENDED_INVALID.json records false and is genuinely unlocked.';
COMMENT ON COLUMN provenance.collector_bench_run.throttle_hex_after IS 'nvidia-smi clocks-throttle-reasons bitmask sampled after the run. All-zero means the measurement was not clock-throttled; 0x...4 indicates SW power cap engaged.';
COMMENT ON COLUMN provenance.collector_bench_run.is_valid IS 'false => the run is explicitly disowned by its own artifact (contended GPU, superseded). Filter is_valid on every query that quotes an absolute latency.';
COMMENT ON COLUMN provenance.collector_bench_run.ratio_mean IS 'Mean of measured_ms/aic_pred_ms over the N grid in this file: the headline "AIC under-models the ViT by Nx" number.';


-- ------------------------------------------------------------- encoder f(N)
-- THE unified long table: encoder forward time as a function of batch size N, across
-- every engine, attention backend and image resolution measured on this silicon, PLUS
-- the AIC analytic prediction as just another engine ('aic'). One row = one (file, engine,
-- resolution, N) point. Query "silicon vs model" by self-joining on (image_px, n_images).
CREATE TABLE IF NOT EXISTS provenance.collector_encoder_fn (
    source_path        text,
    engine             text,   -- aic | vllm | eager | compiled | sdpa | flash_attention_2
    attn               text,   -- attention backend when the artifact distinguishes it
    image_px           int,    -- input image edge (224 | 336 | 448 | 672)
    n_images           int,    -- batch size N: images in one encoder forward
    patches            int,    -- ViT patches for this shape
    post_merge_tokens  int,    -- LLM-visible vision tokens after the patch merger
    mean_ms            double precision,  -- primary measurement: mean forward latency
    ci95_ms            double precision,  -- 95% CI half-width over the replication means
    p50_ms             double precision,
    p99_ms             double precision,
    min_ms             double precision,
    ms_per_img         double precision,  -- mean_ms / n_images
    peak_mem_gb        double precision,
    sm_clock_mhz       int,    -- SM clock observed for THIS point (clocks differ per file)
    aic_pred_ms        double precision,  -- AIC prediction for the same shape, as carried in the artifact
    ratio_meas_over_aic double precision, -- mean_ms / aic_pred_ms
    speedup_over_eager double precision,  -- torch.compile speedup, where the artifact reports it
    is_valid           boolean NOT NULL DEFAULT true,  -- false => point comes from a disowned measurement
    note               text,
    raw                jsonb,  -- untruncated source record (keeps e.g. sm_clock_all per-replication clocks)
    PRIMARY KEY (source_path, engine, image_px, n_images)
);
COMMENT ON TABLE provenance.collector_encoder_fn IS
 'Unified long-form encoder forward-time curve f(N) for the Qwen3-VL ViT: silicon measurements (vllm/eager/compiled/sdpa/flash_attention_2) AND the AIC analytic prediction (engine=''aic'') in one table, keyed by source artifact so each point keeps its own clock and protocol. Join to collector_bench_run on source_path for GPU state. Distinct from provenance.collector_fn (K12), which holds only the four phaseB CSV curves.';
COMMENT ON COLUMN provenance.collector_encoder_fn.engine IS 'aic = analytic prediction, not a measurement. All other values are wall-clock measurements on an RTX 5090. Note ''compiled'' is the normalized spelling of what anchor_master.json calls ''compile''.';
COMMENT ON COLUMN provenance.collector_encoder_fn.n_images IS 'Batch size N of the encoder forward. The thesis headline anchor is N=64 (a full encoder batch).';
COMMENT ON COLUMN provenance.collector_encoder_fn.ratio_meas_over_aic IS 'measured mean_ms divided by the AIC prediction for the same shape. >1 means AIC is optimistic (under-models the encoder).';
COMMENT ON COLUMN provenance.collector_encoder_fn.is_valid IS 'false only for rows from fn_silicon_CONTENDED_INVALID.json, a GPU-contended run its own artifact disowns. Always filter is_valid to quote a clean anchor.';


-- ------------------------------------------------ anchor master: engine level
-- File-level aggregate of anchor_master.json: the f(N=64) anchor per engine and its
-- inflation over AIC, plus the geometric means across windows.
CREATE TABLE IF NOT EXISTS provenance.collector_anchor_engine (
    source_path      text,
    engine           text,   -- aic | vllm | eager | compiled
    clock_mhz        int,    -- locked SM clock for the whole anchor study (2400 MHz)
    sla_ms           double precision, -- encoder-delay p99 SLA the C* gate is evaluated against
    f64_ms           double precision, -- encoder forward time at N=64 for this engine
    f64_over_aic     double precision, -- f64_ms / f64_ms(aic); 1.0 by definition for engine='aic'
    geo_w1_ratio     double precision, -- geometric mean over windows of the W=1 p99 ratio vs AIC
    geo_inflation    double precision, -- geometric mean over windows of the C* worker inflation vs AIC
    PRIMARY KEY (source_path, engine)
);
COMMENT ON TABLE provenance.collector_anchor_engine IS
 'Engine-level summary from anchor_master.json: the N=64 encoder anchor f64_ms per engine, its ratio over the AIC prediction, and the across-window geometric means of the single-worker p99 ratio and of the C* worker inflation.';
COMMENT ON COLUMN provenance.collector_anchor_engine.f64_ms IS 'Encoder forward time for a full 64-image batch at 448px, SM locked to clock_mhz. AIC predicts 316.369 ms; vLLM measures 333.611 ms; HF eager 511.573 ms; torch.compile 370.645 ms.';
COMMENT ON COLUMN provenance.collector_anchor_engine.geo_inflation IS 'Geometric mean over the six burst windows of C*(engine)/C*(aic): how many more encoder workers the real silicon needs than AIC says. NULL for engines the artifact does not aggregate.';


-- ------------------------------------------- anchor master: window x engine
CREATE TABLE IF NOT EXISTS provenance.collector_anchor_window_engine (
    source_path        text,
    window_name        text,   -- burst1..burst6 (trace windows shared with the simulation family)
    engine             text,   -- aic | vllm | eager | compiled
    images             bigint, -- total images offered in the window
    n_image_reqs       bigint, -- requests carrying at least one image
    w1_p99_ms          double precision, -- encoder-delay p99 with a SINGLE encoder worker (saturation regime)
    cstar              int,    -- smallest worker count C meeting the p99 SLA under this engine's f(N)
    gate               text,   -- feasibility gate used to pick C* ('p99_only')
    p99_at_aic_cstar   double precision, -- encoder-delay p99 this engine actually achieves at AIC's C*
    w1_ratio_over_aic  double precision, -- w1_p99_ms / w1_p99_ms(aic) for this window
    inflation_over_aic double precision, -- cstar / cstar(aic) for this window
    PRIMARY KEY (source_path, window_name, engine)
);
COMMENT ON TABLE provenance.collector_anchor_window_engine IS
 'anchor_master.json windows[*]: per trace window and per engine, the single-worker p99, the SLA-feasible worker count C*, and what p99 you actually get if you provision AIC''s C* but run on real silicon (p99_at_aic_cstar) -- the central "the cost model under-provisions" evidence.';
COMMENT ON COLUMN provenance.collector_anchor_window_engine.p99_at_aic_cstar IS 'Encoder-delay p99 of THIS engine when provisioned at the worker count AIC deemed sufficient. Exceeding the 1000 ms SLA here means AIC-sized fleets miss SLA on real hardware.';
COMMENT ON COLUMN provenance.collector_anchor_window_engine.inflation_over_aic IS 'C*(engine)/C*(aic): extra encoder workers needed once the real f(N) is used. Only populated for the engines the artifact reports it for (vllm, eager).';


-- ------------------------------------- burst replay latency (burst_anchor_all)
CREATE TABLE IF NOT EXISTS provenance.collector_burst_anchor_latency (
    source_path   text,
    window_name   text,   -- burst1..burst6
    engine        text,   -- aic | eager | compiled  (source spells the last one 'compiled')
    n_reqs        bigint,
    images        bigint,
    p50_ms        double precision, -- encoder delay percentiles over the replayed window
    p90_ms        double precision,
    p99_ms        double precision,
    max_ms        double precision,
    busy_s        double precision, -- encoder-worker busy seconds consumed by the window
    p99_over_aic  double precision, -- p99_ms / p99_ms(aic) for the same window
    sm_clock_mhz  int,
    PRIMARY KEY (source_path, window_name, engine)
);
COMMENT ON TABLE provenance.collector_burst_anchor_latency IS
 'burst_anchor_all.json: each burst window replayed through the simulator three times, once per encoder cost curve (AIC analytic, HF eager silicon, torch.compile silicon), reporting the resulting encoder-delay distribution and worker busy time.';
COMMENT ON COLUMN provenance.collector_burst_anchor_latency.busy_s IS 'Worker-seconds of actual encoder compute in the window. Ratio of busy_s across engines is the pure cost-model error, free of queueing amplification.';


-- ------------------------------------------ silicon in the closed loop (E2E)
CREATE TABLE IF NOT EXISTS provenance.collector_closedloop_window (
    source_path       text,
    window_name       text,
    policy            text,    -- forecast policy under test, e.g. 'p90/rho15/L30 (chronos)'
    sla_ms            double precision,
    static_c          int,     -- the static baseline worker count it is compared against
    fc_worker_s       double precision, -- worker-seconds spent by the forecast policy
    static_worker_s   double precision, -- worker-seconds spent by the static baseline
    ratio             double precision, -- fc_worker_s / static_worker_s (>1 = forecast costs more here)
    aic_p99_ms        double precision, -- p99 encoder delay with the AIC cost curve
    aic_feasible      boolean,          -- does the AIC curve meet sla_ms?
    silicon_p99_ms    double precision, -- p99 encoder delay with the measured silicon curve
    silicon_feasible  boolean,          -- does the real silicon still meet sla_ms?
    sched_peak        int,              -- peak worker count the schedule reaches
    PRIMARY KEY (source_path, window_name)
);
COMMENT ON TABLE provenance.collector_closedloop_window IS
 'silicon_closedloop.json: the forecast-driven autoscaling loop re-run with the MEASURED encoder cost curve substituted for the AIC one. silicon_feasible answers "does the policy still meet SLA on real hardware".';
COMMENT ON COLUMN provenance.collector_closedloop_window.ratio IS 'Cost of the forecast policy relative to the static-C baseline in worker-seconds, for this window.';


-- --------------------------------------- multiworker sweep (C* determination)
CREATE TABLE IF NOT EXISTS provenance.collector_multiworker_window (
    source_path             text,
    window_name             text,
    sla_ms                  double precision,
    trace_offset            bigint,  -- window start offset into the source trace
    max_requests            bigint,
    n_image_reqs            bigint,
    total_images            bigint,
    grid_cstar_reported     int,     -- C* as published in the thesis static-grid table
    aic_feasible_cstar      int,     -- C* recomputed here from the AIC curve
    silicon_feasible_cstar  int,     -- C* required once the measured curve is used
    aic_reproduces_grid     boolean, -- does aic_feasible_cstar == grid_cstar_reported? (sanity check)
    worker_inflation_x      double precision, -- silicon_feasible_cstar / aic_feasible_cstar
    silicon_p99_at_aic_cstar double precision, -- p99 on silicon if provisioned at AIC's C*
    canonical_fn_source     text,    -- which f(N) artifact supplied the measured curve
    PRIMARY KEY (source_path, window_name)
);
COMMENT ON TABLE provenance.collector_multiworker_window IS
 'silicon_multiworker.json windows[*]: independent re-derivation of the SLA-feasible encoder worker count C* under the AIC curve versus the measured silicon curve, including a reproduction check against the published static grid.';
COMMENT ON COLUMN provenance.collector_multiworker_window.aic_reproduces_grid IS 'true means this collector rerun reproduced the C* printed in the thesis static-grid table, validating the pipeline before the silicon substitution.';

CREATE TABLE IF NOT EXISTS provenance.collector_multiworker_p99 (
    source_path  text,
    window_name  text,
    arm          text,    -- 'aic' | 'silicon': which encoder cost curve drove the sweep
    n_workers    int,     -- W, encoder worker count
    p99_ms       double precision,
    divergent    boolean, -- true if the encoder queue never drained (unstable at this W)
    PRIMARY KEY (source_path, window_name, arm, n_workers)
);
COMMENT ON TABLE provenance.collector_multiworker_p99 IS
 'The full p99-vs-worker-count curve behind collector_multiworker_window: for each window and each cost curve (AIC vs silicon), the encoder-delay p99 at every swept worker count W. C* is the smallest W with p99_ms <= sla_ms and divergent = false.';


-- ------------------------------------------------ ViT operator-level breakdown
CREATE TABLE IF NOT EXISTS provenance.collector_vit_op_breakdown (
    source_path  text,
    n_images     int,     -- batch size the profile was taken at (8, 32, 64)
    op_name      text,    -- matmul | elementwise | other | ffn_gemm | attn_gemm | merger | patch_embed | norm
    ms           double precision, -- time attributed to this operator class
    total_ms     double precision, -- the file's own total for this n_images (total_ms or sum_ops_ms)
    share        double precision, -- ms / total_ms
    profile_level text,   -- 'coarse' (vit_op_profile.json) | 'fine' (vit_op_profile2.json)
    PRIMARY KEY (source_path, n_images, op_name)
);
COMMENT ON TABLE provenance.collector_vit_op_breakdown IS
 'Operator-level attribution of the ViT forward pass (vit_op_profile.json coarse, vit_op_profile2.json fine-grained). Explains WHERE the AIC/silicon gap lives: AIC models GEMMs well but under-counts elementwise/normalization/merger work, whose share grows with batch size.';
COMMENT ON COLUMN provenance.collector_vit_op_breakdown.profile_level IS 'coarse = {matmul, elementwise, other}; fine = {ffn_gemm, attn_gemm, merger, patch_embed, norm}. The two profiles are separate runs, so their totals differ; do not mix them in one sum.';


-- ------------------------------------------------------ CUDA kernel ledger
CREATE TABLE IF NOT EXISTS provenance.collector_kernel_ledger (
    source_path      text,
    n_images         int,
    entry_kind       text,   -- 'category' (aggregated class) | 'kernel' (a single named CUDA kernel)
    entry_name       text,   -- category name, or the demangled CUDA kernel signature
    ms               double precision,
    total_kernel_ms  double precision, -- file total across all kernels at this n_images
    PRIMARY KEY (source_path, n_images, entry_kind, entry_name)
);
COMMENT ON TABLE provenance.collector_kernel_ledger IS
 'phaseB kernel_ledger_N{1,64}.json: nsys/torch-profiler CUDA kernel accounting for a single-image and a full-batch ViT forward, both as coarse categories and as the individual top kernels. Ground truth for which kernels the AIC cost model is missing.';
COMMENT ON COLUMN provenance.collector_kernel_ledger.entry_kind IS 'Rows with entry_kind=''category'' sum to total_kernel_ms; rows with entry_kind=''kernel'' are the top-K individual kernels and are a SUBSET of the categories -- never sum the two kinds together.';


-- ------------------------------------- raw AIC collector kernel-perf rows
CREATE TABLE IF NOT EXISTS provenance.collector_kernel_perf (
    source_path   text,
    row_idx       int,     -- position of the row within its source file (surrogate key: shape columns are nullable)
    framework     text,    -- VLLM
    version       text,    -- framework version the collector ran against (0.22.0)
    device        text,    -- GPU as reported by the collector
    op_name       text,    -- encoder_attention | gemm
    kernel_source text,    -- vllm_vit_flash_attn | vllm_default
    batch_size    int,
    isl           int,     -- input sequence length (patches) for attention ops
    num_heads     int,
    head_dim      int,
    attn_dtype    text,
    gemm_dtype    text,
    m             bigint,  -- GEMM dims (NULL for attention rows)
    n             bigint,
    k             bigint,
    latency_ms    double precision, -- collector-measured kernel latency in ms
    PRIMARY KEY (source_path, row_idx)
);
COMMENT ON TABLE provenance.collector_kernel_perf IS
 'Raw per-kernel timings emitted by the aiconfigurator collector on the RTX 5090 -- the data AIC''s own perf database is built from. Covers phaseC shape-infill outputs (encoder_attention_perf.txt, gemm_perf.txt), the phase4 smoke rows and the phase5 limit20 parquet.';
COMMENT ON COLUMN provenance.collector_kernel_perf.latency_ms IS 'Milliseconds, as written by the collector. These feed AIC''s interpolated encoder cost model; the residual gap in collector_encoder_fn is what survives even after this infill.';


-- --------------------------------------------------------- cold start trials
CREATE TABLE IF NOT EXISTS provenance.collector_cold_start_trial (
    source_path       text,
    trial_idx         int,
    total_s_to_ready  double precision, -- wall seconds from process start to a warm second forward
    imports_s         double precision,
    cuda_ctx_s        double precision,
    load_ckpt_s       double precision,
    to_gpu_s          double precision,
    first_forward_s   double precision, -- includes lazy CUDA kernel autotuning
    second_forward_s  double precision, -- steady-state forward
    ckpt_bytes        bigint,
    gpu               text,
    torch_version     text,
    pid               bigint,
    PRIMARY KEY (source_path, trial_idx)
);
COMMENT ON TABLE provenance.collector_cold_start_trial IS
 'phaseD_cold_start/trials.jsonl: measured encoder-worker cold-start time on this node, broken into phases. This is the empirical basis for the cold-start / lead-time budget L used by the forecasting policies.';


-- --------------------------------------------- single-window silicon replay
CREATE TABLE IF NOT EXISTS provenance.collector_replay_window (
    source_path        text,
    window_name        text,
    arm                text,   -- 'aic' | 'measured' | 'silicon' | 'sim_reference'
    n_image_reqs       bigint,
    total_images       bigint,
    horizon_s          double precision,
    n_workers          int,
    cap                int,    -- encoder batch cap (images per forward)
    attn               text,
    sm_clock_mhz       int,
    f64_ms             double precision, -- the N=64 encoder cost this arm was driven with
    p50_ms             double precision, -- resulting encoder delay distribution
    p90_ms             double precision,
    p99_ms             double precision,
    max_ms             double precision,
    busy_s             double precision,
    p99_ratio_over_aic double precision,
    verdict            text,   -- PASS | FAIL against the SLA, as recorded by the artifact
    PRIMARY KEY (source_path, window_name, arm)
);
COMMENT ON TABLE provenance.collector_replay_window IS
 'Single-worker FIFO replays of one burst window under alternative encoder cost curves (burst3_fifo_replay.json and oneworker_artifact/silicon_burst{3,5}.json). arm=''sim_reference'' is the independent simulator cross-check that the replay harness reproduces the main simulation.';
COMMENT ON COLUMN provenance.collector_replay_window.arm IS 'aic = analytic curve; measured/silicon = the real f(N) from this GPU; sim_reference = the main simulator''s own output for the same window, present only in burst3_fifo_replay.json as a harness-agreement check.';


-- ------------------------------------------- encoder sim stats (phaseE arms)
CREATE TABLE IF NOT EXISTS provenance.collector_encoder_stats (
    source_path                text PRIMARY KEY,
    arm                        text,   -- ctrl_aic | treatment_vllm
    scenario                   text,   -- static_c8 | winsched
    requests                   bigint,
    requests_with_images       bigint,
    total_images               bigint,
    image_px                   int,
    encoder_workers            int,    -- static worker count, or the base count when a schedule is used
    encoder_batch_images       int,
    text_only_fraction         double precision,
    encoder_delay_p50_ms       double precision,
    encoder_delay_p90_ms       double precision,
    encoder_delay_p99_ms       double precision,
    encoder_delay_max_ms       double precision,
    encoder_service_p99_ms     double precision,
    handoff_p99_ms             double precision,
    provisioned_worker_seconds double precision, -- billed worker-seconds (worker count integrated over the horizon)
    busy_worker_seconds        double precision, -- worker-seconds actually computing
    encoder_utilization        double precision, -- busy / provisioned
    sim_horizon_s              double precision,
    mean_images_per_s          double precision,
    offered_img_per_s          double precision,
    batches                    bigint,
    encoder_forwards           bigint,
    requests_chunked           bigint,
    service_memo_hits          bigint,
    distinct_service_sizes_costed int,  -- how many distinct batch sizes the cost curve was evaluated at
    queue_divergent            boolean,
    has_worker_schedule        boolean, -- true when the arm drove a time-varying worker schedule
    metrics                    jsonb    -- the complete 35-key stats object, nothing dropped
);
COMMENT ON TABLE provenance.collector_encoder_stats IS
 'phaseE control/treatment encoder simulation summaries: the SAME full trace simulated with the AIC cost curve (ctrl_aic) and with the measured vLLM silicon curve (treatment_vllm), under a static C=8 fleet and under a windowed schedule. The busy_worker_seconds delta is the pure cost-model error at full-trace scale.';
COMMENT ON COLUMN provenance.collector_encoder_stats.provisioned_worker_seconds IS 'Worker count integrated over the simulated horizon -- the billing basis. Identical between ctrl and treatment within a scenario by construction (same fleet), so only busy_worker_seconds and the delay percentiles differ.';
COMMENT ON COLUMN provenance.collector_encoder_stats.metrics IS 'Full original stats JSON including the nested percentile objects (encoder_service_ms, encoder_batch_service_ms, encoder_delay_ms, handoff_ms, images_per_batch, input_length, context_minus_aic_vision_tokens) that are not flattened into columns.';


-- ------------------------------------------------------ aiperf smoke report
CREATE TABLE IF NOT EXISTS provenance.collector_aiperf_report (
    source_path              text PRIMARY KEY,
    label                    text,   -- what was benchmarked (two_pool)
    completed_requests       bigint,
    duration_ms              double precision,
    mean_ttft_ms             double precision,
    p99_ttft_ms              double precision,
    mean_itl_ms              double precision,
    p99_itl_ms               double precision,
    mean_tpot_ms             double precision,
    p99_tpot_ms              double precision,
    mean_e2e_latency_ms      double precision,
    p99_e2e_latency_ms       double precision,
    max_e2e_latency_ms       double precision,
    request_throughput_rps   double precision,
    output_throughput_tok_s  double precision,
    is_smoke                 boolean NOT NULL DEFAULT true, -- true => tiny run, NOT a load-test result
    metrics                  jsonb   -- the complete 72-key aiperf report
);
COMMENT ON TABLE provenance.collector_aiperf_report IS
 'phase9_two_pool/two_pool_report.json: a 50-request aiperf SMOKE test proving the two-pool (encoder + language) deployment serves end to end. is_smoke=true -- these latencies are not a capacity result and must not be quoted as one.';


-- --------------------------------------------- AIC system spec (rtx_5090.yaml)
CREATE TABLE IF NOT EXISTS provenance.collector_system_spec (
    source_path text,
    key_path    text,   -- dotted path into the YAML, e.g. 'gpu.bfloat16_tc_flops'
    value_num   double precision, -- numeric value when the leaf is a number
    value_text  text,             -- raw textual value (always populated)
    PRIMARY KEY (source_path, key_path)
);
COMMENT ON TABLE provenance.collector_system_spec IS
 'phase2_system_metadata/rtx_5090.yaml flattened: the hardware constants aiconfigurator uses to PREDICT performance on this GPU (memory bandwidth, tensor-core FLOPS, SM count, power). When AIC mis-predicts, these are the inputs to interrogate.';
COMMENT ON COLUMN provenance.collector_system_spec.key_path IS 'Dotted YAML path. Key entries: gpu.bfloat16_tc_flops (419 TFLOPS dense, derived from 170 SM at the 2407 MHz boost clock), gpu.mem_bw (1.792 TB/s), gpu.sm_version (120).';


-- ------------------------------------------------------------ loose scalars
CREATE TABLE IF NOT EXISTS provenance.collector_scalar (
    source_path text,
    scope       text,   -- what the metric is about: 'file', a window name, an engine, ...
    metric      text,   -- metric name as it appears in the artifact
    value_num   double precision,
    value_text  text,
    PRIMARY KEY (source_path, scope, metric)
);
COMMENT ON TABLE provenance.collector_scalar IS
 'Catch-all for file-level scalars in the collector family that do not belong to any wide table (geometric means, aggregate ratios, feasibility flags, contended-run ratio bounds, collector error counts). Nothing from an ingested artifact is dropped: if it is not in a wide table it is here.';
COMMENT ON COLUMN provenance.collector_scalar.scope IS '''file'' for artifact-wide scalars; otherwise the window or engine the scalar belongs to.';

-- Multiple artifacts carry an engine='aic' curve (aic_multires.json, and the aic_fn block
-- inside oneworker_artifact/silicon_burst{3,5}.json). When self-joining silicon against AIC,
-- ALWAYS constrain the AIC side by source_path or the join fans out.
COMMENT ON COLUMN provenance.collector_encoder_fn.source_path IS
 'Artifact the point came from. More than one artifact carries an engine=''aic'' curve, so a silicon-vs-AIC self-join must pin the AIC side to one source_path (aic_multires.json is the canonical multi-resolution AIC curve).';
