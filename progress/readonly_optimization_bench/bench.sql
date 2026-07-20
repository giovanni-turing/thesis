-- Representative thesis-verification workload.
-- Each query is named Qn; the runner wraps each in EXPLAIN (ANALYZE, BUFFERS).

-- Q1: runs joined to a projection, filtered by window/policy/model.
-- The shape behind every comparison matrix in the results chapter.
SELECT d.window_name, d.policy, d.forecast_model, d.quantile, d.lead_s,
       count(*) AS n, avg(s.provisioned_worker_seconds) AS ws,
       avg(l.p99_ttft_ms) AS p99
  FROM provenance.runs d
  JOIN provenance.encoder_run_summary s ON s.run_id = d.run_id
  LEFT JOIN provenance.llm_run_summary l ON l.run_id = d.run_id
 WHERE d.window_name IN ('burst1','burst3','week')
   AND d.policy IN ('forecast','reactive')
   AND d.model IS NOT NULL
 GROUP BY 1,2,3,4,5
 ORDER BY 1,2,3;

-- Q2: per-window cost ratio (the headline savings table).
SELECT * FROM provenance.v_window_cost_ratio ORDER BY window_name;

-- Q3: p99 recompute from raw llm_request. The evidence layer under every
-- published latency number (check C002/C003).
SELECT run_id,
       count(*) AS n,
       percentile_cont(0.99) WITHIN GROUP (ORDER BY ttft_ms) AS p99_ttft_ms,
       percentile_cont(0.99) WITHIN GROUP (ORDER BY e2e_latency_ms) AS p99_e2e_ms,
       max(ttft_ms) AS max_ttft_ms
  FROM provenance.llm_request
 GROUP BY run_id;

-- Q4a: forecast accuracy leaderboard from the projection.
SELECT * FROM provenance.v_forecast_best ORDER BY variate, resolution, mode;

-- Q4b: forecast accuracy recomputed from the 22M raw rows (check C006/C007).
SELECT model, mode, variate, resolution, h,
       count(*) AS n,
       sum(abs(point - y_true)) / nullif(sum(abs(y_true)),0) AS wape
  FROM provenance.forecast
 WHERE y_true IS NOT NULL AND point IS NOT NULL
 GROUP BY 1,2,3,4,5;

-- Q5: eda_metric path lookup.
SELECT script, metric_path, value_num
  FROM provenance.eda_metric
 WHERE metric_path LIKE 'burst%' OR signal = 'rps'
 ORDER BY 1,2;

-- Q6: vllm_token_itl aggregation (measured-vs-simulated chapter).
SELECT run_id,
       count(*) AS tokens,
       count(DISTINCT request_id) AS reqs,
       avg(itl_ms) AS mean_itl,
       percentile_cont(0.99) WITHIN GROUP (ORDER BY itl_ms) AS p99_itl
  FROM provenance.vllm_token_itl
 GROUP BY run_id;

-- Q7: the infraction view -- per-run LATERAL over llm_request. The most
-- expensive routinely-read object in the store.
SELECT run_id, window_name, policy, is_violation, n_requests_raw,
       fraction_requests_over_bound
  FROM provenance.v_infraction
 WHERE window_name IS NOT NULL;

-- Q8: single-run time-ordered raw scan (what check_run() and every
-- per-run time-series plot does).
SELECT run_id, arrival_time_ms, ttft_ms
  FROM provenance.llm_request
 WHERE run_id = :'ONERUN'
 ORDER BY arrival_time_ms;
