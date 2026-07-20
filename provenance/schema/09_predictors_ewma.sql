-- provenance family 5: DYNAMO PREDICTORS + EWMA ABLATION  (ingest_log kind K24)
-- Apply:  psql -h localhost -p 5433 -U goku -d postgres -v ON_ERROR_STOP=1 -f 09_predictors_ewma.sql
-- Idempotent (IF NOT EXISTS). Loader: provenance/loader/load_pred_ewma.py
--
-- Backs two claims:
--   (a) "do the shipped Dynamo load predictors reach the foundation-model frontier?"
--       -> forecast_eval: one WAPE row per (family, predictor, resolution) at h=1 on the
--          image-rate signal, over the SAME common origin span as the FM benchmark.
--   (b) the EWMA cheap-forecaster ablation
--       -> ewma_ablation_cell: the 4 models x 6 windows x lead x rho x quantile x readiness
--          feasibility/cost sweep against the static C=8 baseline.
--
-- Naming follows provenance.runs: window_name / lead_s / rho / quantile / resolution / model.
-- Reserved-word avoidance: context_window (not "window"), n_rows-free, no "offset"/"full".

CREATE SCHEMA IF NOT EXISTS provenance;
SET search_path = provenance, public;

-- =========================================================================
-- (a) FORECAST ACCURACY LEADERBOARD
-- =========================================================================

CREATE TABLE IF NOT EXISTS provenance.forecast_eval (
    family                   text NOT NULL,
    predictor                text NOT NULL,
    resolution               text NOT NULL,
    signal                   text,
    horizon_h                int,
    metric                   text,
    context_window           int,
    n_origins_available      int,
    n_origins_used           int,
    common_span_first_origin bigint,
    common_span_last_origin  bigint,
    wape                     double precision,
    mae                      double precision,
    n_fail                   int,
    n_nonfinite              int,
    fail_examples            text[],
    seconds                  double precision,
    orig_per_s               double precision,
    is_best_fm               boolean NOT NULL DEFAULT false,
    precision_src            text,
    is_valid                 boolean NOT NULL DEFAULT true,
    source_path              text,
    PRIMARY KEY (family, predictor, resolution)
);
CREATE INDEX IF NOT EXISTS forecast_eval_res_idx  ON provenance.forecast_eval (resolution, wape);
CREATE INDEX IF NOT EXISTS forecast_eval_fam_idx  ON provenance.forecast_eval (family);

COMMENT ON TABLE provenance.forecast_eval IS
  'Head-to-head forecast accuracy at horizon h=1 on the image-rate demand signal, all rows evaluated on the SAME common origin span (origin >= 8076) so WAPE is directly comparable across families. Sources: predictors/results_dynamo/<predictor>_<resolution>.json (Dynamo rows, full precision) and predictors/results_dynamo/consolidated.json -> fm_baseline_reference_h1 (foundation-model and cheap-baseline reference rows). Answers "do the shipped Dynamo predictors reach the FM frontier?" - compare min(wape) per resolution across family.';
COMMENT ON COLUMN provenance.forecast_eval.family IS
  'Predictor family: dynamo (shipped NVIDIA Dynamo planner predictors: arima/kalman/prophet/constant) | fm (foundation model: toto/uni, chronos/cov, toto/cov) | baseline (cheap statistical: naive, ewma, holt_winters).';
COMMENT ON COLUMN provenance.forecast_eval.predictor IS
  'Predictor name. Dynamo rows: arima|kalman|prophet|constant. FM rows use "<model>/<mode>" (toto/uni, toto/cov, chronos/cov). Baseline rows: naive|ewma|holt_winters. NOTE the dynamo "constant" predictor and the "naive" baseline are the same last-value rule and agree to 4dp (0.618 at 1min, 0.7638 at 15s) - they are two independent implementations, not a duplicated row.';
COMMENT ON COLUMN provenance.forecast_eval.resolution IS 'Demand-series sampling resolution the forecast is made at: 15s or 1min. WAPE is only comparable WITHIN a resolution.';
COMMENT ON COLUMN provenance.forecast_eval.signal IS 'Forecast target signal; "images" (image arrival rate) for every row in this table.';
COMMENT ON COLUMN provenance.forecast_eval.horizon_h IS 'Forecast horizon in steps ahead; 1 for every row here (one resolution-step ahead).';
COMMENT ON COLUMN provenance.forecast_eval.metric IS 'Metric definition string, verbatim from the artifact: "WAPE = sum|y-yhat|/sum|y|".';
COMMENT ON COLUMN provenance.forecast_eval.context_window IS 'Rolling context length in samples fed to the predictor at each origin (512 for the Dynamo predictors). Named context_window because "window" is reserved; unrelated to runs.window_name (the trace episode).';
COMMENT ON COLUMN provenance.forecast_eval.n_origins_available IS 'Forecast origins available in the common span. NULL for reference rows (not recorded in the archived FM benchmark summary).';
COMMENT ON COLUMN provenance.forecast_eval.n_origins_used IS 'Origins actually evaluated. IMPORTANT: < n_origins_available means the run was subsampled for cost (arima/prophet at 15s used 300 of 2687 origins, ~11%), so their WAPE carries more sampling noise than kalman/constant which used all 2687.';
COMMENT ON COLUMN provenance.forecast_eval.common_span_first_origin IS 'First origin index of the common evaluation span (8076), chosen to match the FM benchmark span.';
COMMENT ON COLUMN provenance.forecast_eval.common_span_last_origin IS 'Last origin index of the common evaluation span.';
COMMENT ON COLUMN provenance.forecast_eval.wape IS 'Weighted absolute percentage error, sum|y-yhat|/sum|y|. LOWER IS BETTER. Dynamo rows carry full float precision from the per-predictor JSON; reference rows are 4dp as archived. This is the headline number.';
COMMENT ON COLUMN provenance.forecast_eval.mae IS 'Mean absolute error in images per resolution-step. Recorded only for Dynamo rows (the FM reference summary kept WAPE only).';
COMMENT ON COLUMN provenance.forecast_eval.n_fail IS 'Origins where the predictor raised/failed to produce a forecast (0 everywhere in this load).';
COMMENT ON COLUMN provenance.forecast_eval.n_nonfinite IS 'Origins whose forecast was NaN/Inf (0 everywhere in this load).';
COMMENT ON COLUMN provenance.forecast_eval.fail_examples IS 'Sample of failing-origin diagnostics from the artifact; empty array when n_fail=0.';
COMMENT ON COLUMN provenance.forecast_eval.seconds IS 'Wall-clock seconds to evaluate all used origins (compute cost of the predictor). Dynamo rows only.';
COMMENT ON COLUMN provenance.forecast_eval.orig_per_s IS 'Evaluation throughput, origins per second = n_origins_used/seconds. Dynamo rows only.';
COMMENT ON COLUMN provenance.forecast_eval.is_best_fm IS 'TRUE on the single foundation-model row that was the best FM at that resolution (the frontier the Dynamo predictors are measured against): toto/uni at 1min, toto/cov at 15s.';
COMMENT ON COLUMN provenance.forecast_eval.precision_src IS 'Provenance of the wape value: json_full = full-precision float from the per-predictor JSON; json_ref_4dp = 4-decimal value as archived in consolidated.json fm_baseline_reference_h1. No value here came from the rounded comparison_table.csv.';
COMMENT ON COLUMN provenance.forecast_eval.is_valid IS 'FALSE would mark a superseded/invalid measurement; TRUE for every row currently loaded.';
COMMENT ON COLUMN provenance.forecast_eval.source_path IS 'Absolute path of the artifact the row was read from.';

CREATE TABLE IF NOT EXISTS provenance.forecast_eval_meta (
    source_path text PRIMARY KEY,
    description text,
    metric      text,
    horizon_h   int,
    signal      text,
    span        text,
    payload     jsonb
);
COMMENT ON TABLE provenance.forecast_eval_meta IS
  'Header/prose metadata of the forecast_eval source artifact (consolidated.json): what the comparison is, the metric definition, and the exact evaluation span. Kept separately so forecast_eval stays one-row-per-measurement.';
COMMENT ON COLUMN provenance.forecast_eval_meta.description IS 'Verbatim free-text description of the comparison from the artifact.';
COMMENT ON COLUMN provenance.forecast_eval_meta.span IS 'Evaluation span description, e.g. "common (origin >= 8076, same as FM benchmark)" - the reason WAPEs are cross-comparable.';
COMMENT ON COLUMN provenance.forecast_eval_meta.payload IS 'Full artifact JSON minus the dynamo_predictors block (that block is loaded row-wise into forecast_eval; kept out to avoid storing it twice).';

-- =========================================================================
-- (b) EWMA CHEAP-FORECASTER ABLATION SWEEP
-- =========================================================================

CREATE TABLE IF NOT EXISTS provenance.ewma_ablation_cell (
    model              text NOT NULL,
    window_name        text NOT NULL,
    lead_s             int  NOT NULL,
    rho                numeric NOT NULL,
    quantile           text NOT NULL,
    readiness          text NOT NULL,
    p99_ms             double precision,
    max_ms             double precision,
    divergent          boolean,
    ws                 double precision,
    ratio_vs_static    double precision,
    feasible           boolean,
    denom_static_c8_ws double precision,
    is_valid           boolean NOT NULL DEFAULT true,
    source_path        text,
    PRIMARY KEY (model, window_name, lead_s, rho, quantile, readiness)
);
CREATE INDEX IF NOT EXISTS ewma_cell_model_idx    ON provenance.ewma_ablation_cell (model);
CREATE INDEX IF NOT EXISTS ewma_cell_window_idx   ON provenance.ewma_ablation_cell (window_name);
CREATE INDEX IF NOT EXISTS ewma_cell_feasible_idx ON provenance.ewma_ablation_cell (feasible);

COMMENT ON TABLE provenance.ewma_ablation_cell IS
  'EWMA cheap-forecaster ablation: one row per swept configuration cell, from verification/results/ewma_sweep.json (208 cells). Asks whether a trivially cheap EWMA forecaster can substitute for the chronos foundation model in the encoder autoscaling loop - compare feasible/ws between model=chronos and the three ewma-* variants at the same (window_name, lead_s, rho, quantile, readiness). The six verification/results/ewma_baseline_<scope>.json files were verified to be an exact subset of these cells (36 of 208, identical on every value column) and were deliberately NOT loaded.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.model IS
  'Forecaster under test: chronos (foundation model, the reference arm) | ewma-add (additive EWMA) | ewma-mult (multiplicative EWMA) | ewma-wsc (EWMA with worst-case/safety correction).';
COMMENT ON COLUMN provenance.ewma_ablation_cell.window_name IS 'Trace episode this cell was simulated on: burst1/burst3/burst4/burst5 (spike episodes), steady24h (calm day), aggregate (the full week). Joins provenance.windows.window_name.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.lead_s IS 'Forecast lead / cold-start provisioning budget in seconds: 15, 30, 45 or 165. Named lead_s to match runs.lead_s (the artifact field is "lead").';
COMMENT ON COLUMN provenance.ewma_ablation_cell.rho IS 'Utilization target in percent (10/15/20/25): lower rho provisions more headroom.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.quantile IS 'Forecast quantile used to size the fleet: p50 (median) or p90 (conservative). Artifact field is "q"; named quantile to match runs.quantile.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.readiness IS 'Worker readiness accounting: strict (a worker counts only after full cold start) | warm (already-warm workers count immediately). strict is the pessimistic/honest arm.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.p99_ms IS 'p99 encoder queueing+service latency (ms) under this policy. The SLO gate that drives feasible.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.max_ms IS 'Worst observed encoder latency (ms) in the episode.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.divergent IS 'TRUE if the request queue diverged (unbounded backlog) - the cell never provisioned enough capacity and its latency numbers are floor values, not converged results.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.ws IS 'Provisioned worker-seconds consumed over the episode: the cost axis. Only comparable between cells sharing the same window_name (episodes differ in length).';
COMMENT ON COLUMN provenance.ewma_ablation_cell.ratio_vs_static IS
  'Cost relative to the static C=8 baseline, ws/denom_static_c8_ws (<1 = cheaper than static). Artifact field is "ratio" in ewma_sweep.json and "ratio_vs_static" in the ewma_baseline_* files - NORMALIZED to this one name. NULL for every window_name other than aggregate, because the denominator is a full-week static-C8 figure and the ratio is only meaningful over the same full-week span.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.feasible IS 'TRUE if the cell met the p99 latency SLO gate. The primary filter: an ewma variant only substitutes for chronos where feasible is TRUE and ws is no worse.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.denom_static_c8_ws IS
  'Denominator of ratio_vs_static: provisioned worker-seconds of the static C=8 control over the full week, 3869278.4 as recorded in ewma_sweep.json. CAVEAT: collector_artifacts/phaseE_physical_anchor/static_c8_ctrl_aic.stats.json records provisioned_worker_seconds = 3869278.8 for what should be the same control - a 0.4 ws (1.0e-7 relative) discrepancy, verified and deliberately NOT reconciled here. Either value gives the same ratio to 4dp.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.is_valid IS 'FALSE would mark a superseded/invalid measurement; TRUE for every row currently loaded.';
COMMENT ON COLUMN provenance.ewma_ablation_cell.source_path IS 'Absolute path of the artifact the cell was read from (verification/results/ewma_sweep.json for all rows).';
