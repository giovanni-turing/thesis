-- Query surface for the AI/NL->SQL layer.
--   current_* : DEFAULT surface — excludes retracted runs (runs.is_current = false).
--   v_*       : canned analytical views for the recurring thesis questions.
SET search_path = provenance, public;

-- ---- current_* (retraction-filtered) ------------------------------------
CREATE OR REPLACE VIEW provenance.current_runs AS
    SELECT * FROM provenance.runs WHERE is_current;

CREATE OR REPLACE VIEW provenance.current_llm_summary AS
    SELECT r.experiment, r.pool, r.window_name, r.policy, r.model, r.quantile, r.lead_s,
           r.config_c, r.tp, r.n_replicas, r.converter, r.actuation, s.*
    FROM provenance.llm_run_summary s JOIN provenance.runs r USING (run_id)
    WHERE r.is_current;

CREATE OR REPLACE VIEW provenance.current_encoder_summary AS
    SELECT r.experiment, r.pool, r.window_name, r.policy, r.model, r.quantile, r.lead_s,
           r.config_c, r.actuation, s.*
    FROM provenance.encoder_run_summary s JOIN provenance.runs r USING (run_id)
    WHERE r.is_current;

CREATE OR REPLACE VIEW provenance.current_factorial AS
    SELECT fc.* FROM provenance.factorial_cell fc JOIN provenance.runs r USING (run_id)
    WHERE r.is_current;

-- ---- analytical helpers -------------------------------------------------

-- Best (min-WAPE) forecaster per signal x resolution x mode  (RQ: which model wins where)
CREATE OR REPLACE VIEW provenance.v_forecast_best AS
    SELECT DISTINCT ON (variate, resolution, mode)
           variate, resolution, mode, model, candidate, wape, mae, rmse
    FROM provenance.forecast_metrics
    ORDER BY variate, resolution, mode, wape ASC;

-- Infeasible factorial cells  (RQ: which cells fail the 1000 ms SLA, and on which window)
CREATE OR REPLACE VIEW provenance.v_infeasible AS
    SELECT run_id, window_name, policy, model, quantile, rho, cold_start_s, lead_s, readiness,
           p99_ms, max_ms, provisioned_ws, actuation
    FROM provenance.current_factorial
    WHERE feasible IS FALSE;

-- Encoder provisioning cost per run  (RQ: forecast vs reactive vs static worker-seconds)
CREATE OR REPLACE VIEW provenance.v_encoder_cost AS
    SELECT r.experiment, r.window_name, r.policy, r.model, r.lead_s, r.config_c, r.actuation,
           s.provisioned_worker_seconds, s.busy_worker_seconds,
           s.encoder_delay_p99_ms, s.queue_divergent
    FROM provenance.encoder_run_summary s JOIN provenance.runs r USING (run_id)
    WHERE r.is_current;

-- Full-trace coverage guarantee rows  (RQ: is every request simulated per pool)
CREATE OR REPLACE VIEW provenance.v_coverage AS
    SELECT fleet, run, pool, requests, expect, is_full, ok FROM provenance.coverage;

-- Dual cost accounting (family 8): forecast vs reactive, billed both ways per window x lead.
-- order_ratio < readiness_ratio => order-billing widens the forecast advantage; reactive_fails
-- flags where reactive also breaks the 1000 ms SLA (e.g. burst5 L165 = the cost-order flip).
CREATE OR REPLACE VIEW provenance.v_cost_frontier_dual AS
    SELECT f.window_name, f.lead_s,
           f.provisioned_ws      AS forecast_readiness_ws,
           r.provisioned_ws      AS reactive_readiness_ws,
           f.total_from_order_ws AS forecast_order_ws,
           r.total_from_order_ws AS reactive_order_ws,
           round((f.total_from_order_ws / nullif(r.total_from_order_ws, 0))::numeric, 3) AS order_ratio,
           round((f.provisioned_ws      / nullif(r.provisioned_ws, 0))::numeric, 3)      AS readiness_ratio,
           r.p99_ms AS reactive_p99_ms, (r.p99_ms > 1000) AS reactive_fails
    FROM provenance.cost_accounting f
    JOIN provenance.cost_accounting r USING (window_name, lead_s)
    WHERE f.policy = 'forecast' AND r.policy = 'reactive';

-- Per-window closed-loop cost frontier: forecast provisioning by rho x quantile x model
CREATE OR REPLACE VIEW provenance.v_closedloop_frontier AS
    SELECT window_name, model, quantile, rho, cold_start_s, lead_s, readiness,
           bool_and(feasible) AS all_feasible,
           min(provisioned_ws) AS min_provisioned_ws,
           max(p99_ms) AS worst_p99_ms
    FROM provenance.current_factorial
    WHERE policy = 'forecast'
    GROUP BY window_name, model, quantile, rho, cold_start_s, lead_s, readiness;
