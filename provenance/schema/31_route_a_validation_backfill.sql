-- 31_route_a_validation_backfill.sql
-- Idempotent. Applied to the live store 2026-07-22.
--
-- Fixes two verification findings from the multi-agent claim audit:
--
-- (0264 / aiconfigurator tab:aic-validation) The Route-A HF reference validation
--   (collector_artifacts/phaseA_validation/result.txt: 11.360/36.421/103.824 ms
--   measured vs 7.822/31.973/89.347 ms raw-slice AIC prediction, locked clocks) was
--   never ingested, so the table's numbers were not re-derivable from the DB. Ingest
--   them into collector_encoder_fn as engine='hf', n_images=1, one row per resolution.
--   This is the "raw slice" AIC prediction the table caption already discloses; it is a
--   distinct source_path from the composed phaseE anchors (aic_pred_ms=8.162), so it does
--   not disturb them.
--
-- (0436 / closedloop headline 0.62x) NOT a data gap. The headline Chronos p90 rho=15 L30
--   warm-pool ratio 0.6231 is CURRENT and VALID in v_ewma_ablation_ratio; v_cost_ratio's
--   factorial:forecast_p90_chronos_rho15_L30 row (0.6140) is the older cold-start
--   accounting and is correctly superseded (is_current=false). No row change -- only
--   discoverability COMMENTs so an auditor queries the right view.

SET search_path=provenance,public;

BEGIN;

-- (0264) Route-A HF reference validation -> collector_encoder_fn
DELETE FROM collector_encoder_fn
 WHERE source_path = '/home/gio/tese/collector_artifacts/phaseA_validation/result.txt';

INSERT INTO collector_encoder_fn
  (source_path, engine, attn, image_px, n_images, patches, post_merge_tokens,
   mean_ms, ci95_ms, ms_per_img, sm_clock_mhz, aic_pred_ms, ratio_meas_over_aic, is_valid, note)
VALUES
  ('/home/gio/tese/collector_artifacts/phaseA_validation/result.txt','hf',NULL,448,1,784,196,
   11.360,0.006,11.360, 2385, 7.822, 11.360/7.822,  true,
   'Route-A HF Qwen3VLVisionModel bf16 reference validation (5x50 iters, CUDA events, 95% CI, locked clocks); AIC=raw-slice prediction. Backs tab:aic-validation 448^2 row.'),
  ('/home/gio/tese/collector_artifacts/phaseA_validation/result.txt','hf',NULL,896,1,3136,784,
   36.421,0.010,36.421, 2392,31.973, 36.421/31.973, true,
   'Route-A HF reference validation; raw-slice AIC prediction. Backs tab:aic-validation 896^2 row.'),
  ('/home/gio/tese/collector_artifacts/phaseA_validation/result.txt','hf',NULL,1344,1,7056,1764,
   103.824,0.022,103.824,2392,89.347,103.824/89.347, true,
   'Route-A HF reference validation; raw-slice AIC prediction. Backs tab:aic-validation 1344^2 row.');

-- (0436) discoverability comments (no data change)
COMMENT ON VIEW v_ewma_ablation_ratio IS
 'Warm-pool closed-loop cost ratios vs deployable static C=8. Carries the THESIS HEADLINE: chronos/aggregate/L30/rho=15/p90/warm ratio_vs_static=0.6231 (0.62x). For the headline cost ratio use THIS view (readiness=warm), NOT v_cost_ratio whose factorial forecast_p90_chronos_rho15_L30 row (0.6140) is the older cold-start accounting and is superseded (is_current=false).';
COMMENT ON VIEW v_cost_ratio IS
 'Cost ratios across experiments. NOTE: for the closed-loop encoder headline (Chronos p90 rho=15 L30, 0.62x) query v_ewma_ablation_ratio (warm-pool); the factorial:* chronos/p90/L30 rows here are the cold-start sweep and are superseded (is_current=false).';

COMMIT;
