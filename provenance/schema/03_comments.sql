-- Data dictionary: COMMENT ON every table + non-obvious column, so an LLM writing SQL over
-- this schema has the semantics inline (readable via \d+, pg_description, or information_schema).
SET search_path = provenance, public;

COMMENT ON SCHEMA provenance IS
  'Thesis execution results: raw traces (source of truth) + derived projections, sharing the runs spine. Query the current_* views to exclude retracted results.';

-- ---- spine + dims
COMMENT ON TABLE provenance.runs IS
  'Dimension/provenance spine: one row per execution. All comparison dimensions are denormalized here; projection and raw tables reference run_id. supersedes/is_current mark retracted results.';
COMMENT ON COLUMN provenance.runs.run_id IS 'Primary key: "<experiment>:<filename-stem>" (or a factorial cell key). Join everything on this.';
COMMENT ON COLUMN provenance.runs.experiment IS 'Experiment family: a2/a6 (encoder fleet), a11/a12 (language, composed), a13 (full 1M-trace), a14 (per-model max span), grid, factorial, sweeps, reactive, ctmatrix, riders, live, predictors, eda, phasee, ewma.';
COMMENT ON COLUMN provenance.runs.pool IS 'encoder (vision/ViT on RTX 5090) | language (LLM on H100) | both (composed E2E).';
COMMENT ON COLUMN provenance.runs.window_name IS 'Episode/window: burst1..6, steady24h (calm day), aggregate/week, fulltrace (7d,1M req), e7..e18 (extra episodes), span_{chronos,toto,timesfm}. See table windows.';
COMMENT ON COLUMN provenance.runs.policy IS 'Provisioning policy: forecast | reactive | static.';
COMMENT ON COLUMN provenance.runs.model IS 'Forecaster: chronos, toto, timesfm, ewma, holt_winters, naive, arima, kalman, prophet, constant.';
COMMENT ON COLUMN provenance.runs.mode IS 'Forecast conditioning: uni (own history) | cov (covariate-conditioned).';
COMMENT ON COLUMN provenance.runs.lead_s IS 'Forecast lead L in seconds (also the cold-start provisioning budget).';
COMMENT ON COLUMN provenance.runs.rho IS 'Utilization target (percent) for provisioning: 10/15/20/25.';
COMMENT ON COLUMN provenance.runs.config_c IS 'Static encoder worker count C* (e.g. C2, C8).';
COMMENT ON COLUMN provenance.runs.tp IS 'LLM tensor-parallel degree.';
COMMENT ON COLUMN provenance.runs.n_replicas IS 'LLM replica count N.';
COMMENT ON COLUMN provenance.runs.converter IS 'Cost model: aic (aiconfigurator) | poly (polynomial fit).';
COMMENT ON COLUMN provenance.runs.actuation IS 'Scaling actuation timing: issue-time (load-bearing) | target-time (exploratory/superseded).';
COMMENT ON COLUMN provenance.runs.is_current IS 'FALSE = retracted/superseded; the current_* views filter on this. Default TRUE.';
COMMENT ON COLUMN provenance.runs.supersedes IS 'run_id this run replaces (soft reference).';
COMMENT ON COLUMN provenance.runs.config IS 'Run-level attributes as jsonb (freq_s, arrival_speedup, image_px, parquet metadata, ...).';

COMMENT ON TABLE provenance.windows IS 'Episode/window registry (from windows_ext.json): the temporal slices of the 1M-request Azure trace under study.';
COMMENT ON COLUMN provenance.windows.trace_offset IS 'Request-index offset into the 1M-request trace where this window starts.';
COMMENT ON COLUMN provenance.windows.peak_1min_img_per_s IS 'Peak 1-minute image arrival rate (img/s) — the burst intensity.';
COMMENT ON COLUMN provenance.windows.onset_min IS 'Minutes from window start to the burst peak.';
COMMENT ON COLUMN provenance.windows.in_coverage IS 'Whether this episode falls inside the forecast-covered span.';

-- ---- projections
COMMENT ON TABLE provenance.llm_run_summary IS 'K1: per-run language-pool KPI summary (from *.report.json). Hot metrics typed; full report in metrics jsonb. Recomputable from llm_request (see v_llm_drift).';
COMMENT ON COLUMN provenance.llm_run_summary.p99_ttft_ms IS 'p99 time-to-first-token (ms). The primary language-pool SLA metric.';
COMMENT ON COLUMN provenance.llm_run_summary.p99_itl_ms IS 'p99 inter-token latency (ms).';
COMMENT ON COLUMN provenance.llm_run_summary.gpu_hours IS 'GPU-hours consumed by the decode fleet for this run (74-key reports only; NULL for 68-key grid reports).';
COMMENT ON COLUMN provenance.llm_run_summary.metrics IS 'Full report.json as jsonb (all ~70 fields, incl. any not promoted to a typed column).';

COMMENT ON TABLE provenance.encoder_run_summary IS 'K3: per-run vision/encoder-pool summary (from *.jsonl.stats.json). Nested percentiles flattened; full stats in metrics jsonb.';
COMMENT ON COLUMN provenance.encoder_run_summary.encoder_delay_p99_ms IS 'p99 encoder queueing+service delay (ms) — the vision-pool SLA metric.';
COMMENT ON COLUMN provenance.encoder_run_summary.provisioned_worker_seconds IS 'Integral of provisioned encoder workers over time (worker-seconds) — the cost metric for the cost-ratio-vs-static claim.';
COMMENT ON COLUMN provenance.encoder_run_summary.busy_worker_seconds IS 'Worker-seconds actually doing work (utilization numerator).';
COMMENT ON COLUMN provenance.encoder_run_summary.queue_divergent IS 'TRUE if the encoder queue diverged (under-provisioned / unstable).';

COMMENT ON TABLE provenance.factorial_cell IS 'K7: the canonical results table — one row per factorial experiment cell (encoder provisioning). feasible = passes the 1000 ms p99 SLA.';
COMMENT ON COLUMN provenance.factorial_cell.feasible IS 'TRUE if the cell meets the 1000 ms p99 encoder-delay SLA.';
COMMENT ON COLUMN provenance.factorial_cell.provisioned_ws IS 'Provisioned encoder worker-seconds for the cell (cost).';
COMMENT ON COLUMN provenance.factorial_cell.readiness IS 'Worker readiness model: strict (rewarm each time) | warm(-pool). Only set for issue-time readiness sweep (factorial_issuetime).';
COMMENT ON COLUMN provenance.factorial_cell.rho IS 'Utilization target (percent): 10/15/20/25 — the tunable cost frontier.';

COMMENT ON TABLE provenance.forecast_metrics IS 'K10: forecast accuracy per (model, mode, span, resolution, variate, candidate). Lower WAPE/MAE = better.';
COMMENT ON COLUMN provenance.forecast_metrics.variate IS 'Forecast signal: images, requests, ctx (context tokens), gen (generated tokens).';
COMMENT ON COLUMN provenance.forecast_metrics.wape IS 'Weighted absolute percentage error (primary accuracy metric).';
COMMENT ON COLUMN provenance.forecast_metrics.candidate IS 'Point-forecast source: the point head, or a below/above-median quantile used as the operating point.';

COMMENT ON TABLE provenance.quantile_coverage IS 'K10: empirical vs nominal quantile-band coverage per (model, signal), as jsonb detail.';
COMMENT ON TABLE provenance.coverage IS 'K8: full-trace coverage guarantee — one row per (fleet, run, pool): requests simulated vs expected, is_full = all covered.';
COMMENT ON TABLE provenance.coverage_meta IS 'K8: coverage_manifest.json header (trace_requests, per-model max span, guarantee block).';
COMMENT ON TABLE provenance.verification IS 'K8b: per-run self-check endpoints (enc_p99 / ttft_p99 / provisioned_ws) asserted by the animation builders.';
COMMENT ON TABLE provenance.collector_fn IS 'K12: encoder f(N) micro-benchmarks — measured vs AIC latency per image batch size N (aiconfigurator cost-model validation).';
COMMENT ON COLUMN provenance.collector_fn.aic_ms_per_img IS 'AIC-modeled per-image encoder latency at batch N (ms); compare to measured mean_ms/N for the AIC-vs-silicon ratio.';
COMMENT ON TABLE provenance.ledger_entry IS 'K13: normalized results-ledger.md — the hand-maintained artifact->manuscript provenance log (artifact/command/feeds/supersedes/commit).';
COMMENT ON TABLE provenance.cost_accounting IS 'K14: dual cost accounting (a2_cost_accounting.csv) — each policy billed two ways: provisioned_ws (bill-from-readiness, ledgered) and total_from_order_ws (bill-from-order = readiness + every scale-up warm-up). Order-billing widens the forecast advantage; confirms the 0.62x cost claim is conservative.';

-- ---- raw facts
COMMENT ON TABLE provenance.llm_request IS 'K2 RAW: per-request language-pool trace (one row per request), LIST-partitioned by experiment. llm_run_summary is the p-summary of this.';
COMMENT ON COLUMN provenance.llm_request.ttft_ms IS 'Time-to-first-token for this request (ms).';
COMMENT ON COLUMN provenance.llm_request.itl_ms IS 'Mean inter-token latency for this request (ms).';
COMMENT ON TABLE provenance.encoder_series IS 'K5 RAW: per-second encoder trajectory (t, img arrived/completed, queue depth, busy workers), LIST-partitioned by experiment.';
COMMENT ON TABLE provenance.composed_request IS 'K6 RAW: composed request trace (encoder-stage output feeding the LLM sim): timestamp, input/output length, prefix-cache hash_ids.';
COMMENT ON TABLE provenance.worker_schedule IS 'K4 RAW: autoscaler worker-count timeline — (step_index, t_s, worker_count) per run.';
COMMENT ON TABLE provenance.forecast IS 'K10 RAW: rolling-origin forecast outputs (~17M rows), LIST-partitioned by model. y_true vs point + 9 quantile heads p10..p90; forecast_metrics is the scored summary.';
COMMENT ON COLUMN provenance.forecast.origin IS 'Rolling-origin index (forecast issue point).';
COMMENT ON COLUMN provenance.forecast.h IS 'Horizon step 1..12 ahead of the origin.';
COMMENT ON TABLE provenance.measured_request IS 'K11 RAW: MEASURED vLLM per-request ground truth (real H100 run) — what the simulator is validated against. See vllm_trace_analysis/out/DATA_DICTIONARY.md.';

COMMENT ON TABLE provenance.ingest_log IS 'Loader bookkeeping: file_path -> sha256 + row count + kind. Idempotency: unchanged sha = skip on reload.';

-- ---- views
COMMENT ON VIEW provenance.current_llm_summary IS 'llm_run_summary joined to runs dims, retracted runs excluded. Default surface for language-pool KPI questions.';
COMMENT ON VIEW provenance.current_encoder_summary IS 'encoder_run_summary joined to runs dims, retracted excluded. Default surface for vision-pool cost/latency questions.';
COMMENT ON VIEW provenance.current_factorial IS 'factorial_cell with retracted runs excluded. Default surface for feasibility/cost-frontier questions.';
COMMENT ON VIEW provenance.v_forecast_best IS 'Min-WAPE forecaster per (variate, resolution, mode).';
-- NOTE: COMMENT ON VIEW v_llm_drift lives in 04_lineage.sql (where the view is defined).
