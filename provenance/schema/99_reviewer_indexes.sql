-- =====================================================================
-- 99_reviewer_indexes.sql -- schema `provenance`, PostgreSQL 16
--
-- COMPREHENSIVE ad-hoc query indexing for a READ-ONLY reviewer database.
--
-- Rationale (differs deliberately from 99_readonly_optimization_applied.sql,
-- which measured indexes as no-ops on a FIXED 9-query benchmark):
--   * The store is now READ-ONLY (roles picolo/provenance_ro; goku rotated).
--     No more writes -> zero write amplification -> an index is a one-time
--     build cost, never an ongoing tax.
--   * The REVIEWER workload is UNKNOWN. The matviews (mv_llm_percentiles,
--     mv_infraction, ...) only accelerate queries that USE them; an ad-hoc
--     reviewer query (WHERE ttft_ms > x, ORDER BY t, GROUP BY input_length,
--     JOIN on session_id) would otherwise seq-scan tens of millions of rows.
-- So we index every plausible filter / sort / group / join column.
-- Zero-selectivity columns are skipped (terminal_status is 100% 'completed').
--
-- Build cost is one-time; safe to re-run (IF NOT EXISTS). Reads are NOT
-- blocked during CREATE INDEX (SHARE lock allows concurrent SELECT).
-- =====================================================================
\set ON_ERROR_STOP on
SET search_path = provenance, public;
SET maintenance_work_mem = '2GB';
SET max_parallel_maintenance_workers = 4;
\timing on

-- ---- llm_request (18.9M rows, partitioned by experiment) -------------
CREATE INDEX IF NOT EXISTS llm_request_run_cover_idx  ON provenance.llm_request (run_id)
       INCLUDE (arrival_time_ms, ttft_ms, itl_ms, e2e_latency_ms, input_length, output_length);
CREATE INDEX IF NOT EXISTS llm_request_run_arrival_idx ON provenance.llm_request (run_id, arrival_time_ms);
CREATE INDEX IF NOT EXISTS llm_request_session_idx     ON provenance.llm_request (session_id, turn_index);
CREATE INDEX IF NOT EXISTS llm_request_ttft_idx        ON provenance.llm_request (ttft_ms);
CREATE INDEX IF NOT EXISTS llm_request_e2e_idx         ON provenance.llm_request (e2e_latency_ms);
CREATE INDEX IF NOT EXISTS llm_request_itl_idx         ON provenance.llm_request (itl_ms);
CREATE INDEX IF NOT EXISTS llm_request_inlen_idx       ON provenance.llm_request (input_length);
CREATE INDEX IF NOT EXISTS llm_request_outlen_idx      ON provenance.llm_request (output_length);
CREATE INDEX IF NOT EXISTS llm_request_arrival_brin    ON provenance.llm_request USING brin (arrival_time_ms);

-- ---- composed_request (35M rows, partitioned by experiment) ----------
CREATE INDEX IF NOT EXISTS composed_request_run_line_idx ON provenance.composed_request (run_id, line_index)
       INCLUDE (ts, input_length, output_length);
CREATE INDEX IF NOT EXISTS composed_request_inlen_idx  ON provenance.composed_request (input_length);
CREATE INDEX IF NOT EXISTS composed_request_outlen_idx ON provenance.composed_request (output_length);
CREATE INDEX IF NOT EXISTS composed_request_ts_brin    ON provenance.composed_request USING brin (ts);

-- ---- encoder_series (30M rows, partitioned by experiment) ------------
CREATE INDEX IF NOT EXISTS encoder_series_run_t_idx ON provenance.encoder_series (run_id, t)
       INCLUDE (img_arrived, img_completed, queue_imgs_end, busy_workers_end);

-- ---- forecast (22M rows, partitioned by model) ----------------------
CREATE INDEX IF NOT EXISTS forecast_var_res_h_idx ON provenance.forecast (variate, resolution, h);
CREATE INDEX IF NOT EXISTS forecast_res_var_h_idx ON provenance.forecast (resolution, variate, h);
CREATE INDEX IF NOT EXISTS forecast_mode_idx      ON provenance.forecast (mode);
CREATE INDEX IF NOT EXISTS forecast_origin_idx    ON provenance.forecast (origin);
CREATE INDEX IF NOT EXISTS forecast_ts_brin       ON provenance.forecast USING brin (ts);

-- ---- vllm_prom_sample (2.2M) : run+metric time series, index-only ----
CREATE INDEX IF NOT EXISTS vllm_prom_run_metric_ts_idx ON provenance.vllm_prom_sample (run_id, metric, ts)
       INCLUDE (value);

-- ---- vllm_token_itl (1.36M) : per-run ITL, index-only ----------------
CREATE INDEX IF NOT EXISTS vllm_token_itl_run_cover_idx ON provenance.vllm_token_itl (run_id)
       INCLUDE (itl_ms, offset_ms, token_idx);

-- ---- eda_rate_series (2.77M) : signal-first series, index-only -------
CREATE INDEX IF NOT EXISTS eda_rate_signal_res_ts_idx ON provenance.eda_rate_series (signal, resolution, ts)
       INCLUDE (value);

-- ---- worker_schedule (236K) : ordered per-run schedule ---------------
CREATE INDEX IF NOT EXISTS worker_schedule_run_step_idx ON provenance.worker_schedule (run_id, step_index)
       INCLUDE (t_s, worker_count);

-- ---- measured_request (7.8K, small) ---------------------------------
CREATE INDEX IF NOT EXISTS measured_request_status_idx ON provenance.measured_request (status);
CREATE INDEX IF NOT EXISTS measured_request_ts_idx     ON provenance.measured_request (ts_ms);

-- ---- runs spine (3.1K) : cheap dim filters reviewers slice by --------
CREATE INDEX IF NOT EXISTS runs_rho_idx        ON provenance.runs (rho);
CREATE INDEX IF NOT EXISTS runs_config_c_idx   ON provenance.runs (config_c);
CREATE INDEX IF NOT EXISTS runs_tp_idx         ON provenance.runs (tp);
CREATE INDEX IF NOT EXISTS runs_gpu_idx        ON provenance.runs (gpu);
CREATE INDEX IF NOT EXISTS runs_lead_s_idx     ON provenance.runs (lead_s);
CREATE INDEX IF NOT EXISTS runs_actuation_idx  ON provenance.runs (actuation);
CREATE INDEX IF NOT EXISTS runs_quantile_idx   ON provenance.runs (quantile);
CREATE INDEX IF NOT EXISTS runs_resolution_idx ON provenance.runs (resolution);
CREATE INDEX IF NOT EXISTS runs_kind_idx       ON provenance.runs (kind);

-- ---- refresh planner statistics for the new indexes -----------------
ANALYZE provenance.llm_request;
ANALYZE provenance.composed_request;
ANALYZE provenance.encoder_series;
ANALYZE provenance.forecast;
ANALYZE provenance.vllm_prom_sample;
ANALYZE provenance.vllm_token_itl;
ANALYZE provenance.eda_rate_series;
ANALYZE provenance.worker_schedule;
ANALYZE provenance.measured_request;
ANALYZE provenance.runs;
