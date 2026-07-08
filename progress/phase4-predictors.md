# Phase 4 (items 1–2) — Per-pool demand forecasting: interface + backend benchmark

Companion to `thesis-roadmap.md` (Phase 4). Records the predictor interface,
the six backends, and the full zero-shot benchmark over the materialized
demand series. Chapter draft: `tex/predictors.tex` (Chapter 2 of the preview
build). Code: `predictors/`. Commits: `8519553` (scaffold), `5a3131a`
(results + metrics), `03a2b2e` (chapter).

---

## What exists

- **Interface** (`predictor.py`): `Bucket` (same-cadence targets + covariates)
  → `Forecast` (point + 9 quantiles, levels 0.1..0.9 = the intersection of the
  three FMs' native heads). `BatchExecutor` for file-driven runs; all backends
  clip forecasts at 0.
- **Backends**: naive last-value, EWMA (α=0.3), additive Holt–Winters
  (α=.3/β=.1/γ=.1, seasonal = 1 h of bins, 15 min at 1 s) — all with Gaussian
  bands; TimesFM-2.0-500M (univariate, mean-head point), Chronos-2 120M
  (native past-covariates, tensor `predict()` path), Toto-2.0-2.5B (joint
  multivariate via variate-axis attention). All run fp32/TF32 on the 5090
  from the `eda/.venv`.
- **Benchmark** (`benchmark.py`): rolling-origin, H=12 steps at native
  cadence, origins on a shared multiples-of-12 grid → forecasts tile the
  timeline contiguously and all models predict identical absolute bins.
  Context budget = model cap − (1+9)×H headroom: TimesFM 1928, Toto 3976,
  Chronos 8072; baselines 1928. Five resolutions (1s/15s/30s/45s/1min ×
  7 days), four signals (requests, images, ctx, gen), uni + cov modes.
  Atomic per-part parquet checkpoints (resumable); ~2.5 h wall total
  (baselines ≈1 min CPU each; Chronos ≈1 h; Toto ≈80 min).
- **Outputs**: `predictors/results/{model}_{variate}.parquet` +
  `{model}_covariates.parquet` (19.2 M forecast values, long format with
  y_true, point, p10..p90, origin/h/step/ts) + `results/metrics/`
  (`precision.py`: h=1 / per-h / overall × point + every percentile;
  cross-model tables on the common span, origin ≥ 8076) + `results/figures/`
  (`figures_tex.py` → `figuras/pred/`).

## Headline results (common span, overall point WAPE)

- **FMs beat every baseline in all 20 (resolution × signal) cells**, zero-shot.
  Margin vs best baseline (EWMA) is ~1–3 pp at 1 min and ~⅓ lower WAPE at 1 s
  (images: 98.8 % vs 146.1 %). Holt–Winters is worse than naive everywhere
  (trend extrapolation vs mean-reverting bursts).
- **Winner is resolution-dependent, spreads tiny (<2 pp)**: Toto-2 takes 15/20
  cells (all ≤30 s, mostly cov mode); Chronos-2 the coarse request/image
  columns; TimesFM 1 min ctx. Model choice matters far less than FM-vs-classical.
- **Horizon degradation is mild** (images@1min ≈52 %→54 % over h=1..12 vs
  naive 62 %→68 %): the EDA persistence is exploitable capital; 12 min lead
  covers the median 6-min burst onset.
- **Covariates ≈ neutral** (±0.4 %), consistently helpful only at 15 s/1 s
  (Chronos −0.39 %, Toto −0.24 % at 1 s) — the forecasting-side echo of the
  R²=0.12 decoupling.
- **No percentile beats a median-point FM** (2/80 cells ≈0 gain); p40-ish
  sub-median quantiles fix TimesFM's mean head (−1.7 % median, 18/20 cells)
  and the baselines' Gaussian bands (up to −45 % for HW images@1s). Band =
  headroom, not point correction.
- Absolute levels: best 1-min image forecast ≈1,302 images MAE/bin
  (21.7 img/s); 1-s bins sit at the shot-noise floor (≈99 % WAPE) — envelope,
  not per-bin, predictability.

## Open items (rest of Phase 4)

3. **Closed loop**: forecast → provisioning decision (cold-start lead) → the
   two-pool simulation → SLA × GPU-hours vs Phase 3 baselines; burst episodes
   as headline scenarios.
4. **Ablations**: horizon vs cold-start; per-pool signals vs request-rate-only
   forecasts (the strawman — forecast image load FROM request rate via the
   covariate machinery); forecast-error sensitivity. Quantile calibration
   (coverage) if the band drives headroom sizing.


## 4.3 closed loop — INFRASTRUCTURE LIVE (2026-07-08)

First end-to-end forecast-driven run executed: trace → archived Chronos
forecast → worker schedule → two-pool simulation → SLA × worker-seconds.

- **Converter C(t) hook** (`--worker-schedule`): piecewise-constant
  capacity, slot-based active windows, LIFO retirement, drain semantics
  (no preemption), provisioned-worker-seconds integral in stats.
  Validated: no-schedule path bit-identical (grid p99 reproduced exactly);
  constant schedule ≡ static; dynamic provisioned integral exact.
- **Controller v1** (`simulation/forecast_schedule.py`): stitched-tile
  forecasts consumed as a scaler would; desired = ceil(q(t)/rho);
  hysteresis = trailing-max; cold start = trailing-min over the lead
  (up-lead/down-now semantics). Ablation axes are flags: quantile, rho,
  lead, hysteresis. Units gotcha fixed + documented: forecast series are
  PER-BIN TOTALS, divide by bin seconds.
- **First result (burst1, p90, rho=20, lead 60 s, hyst 3 min):** delay
  p99 677 ms (SLA met), 316k worker-s, schedule 4..13 workers, 35 steps.
  Framing that the evaluation chapter must use: per-window static C* is
  an ORACLE (window-specific hindsight optimum, 180k) — the deployable
  comparisons are static-all-windows (C=16 → 479k on this window:
  **forecast saves 34%**) and the 3.2 reactive baseline (pending).
- LLM-side actuation decided: register a `forecast_file` predictor in the
  planner's LOAD_PREDICTORS registry (plain string-keyed dict) so the
  predictive policy shares the reactive baseline's exact actuation path.


## 4.3 first policy matrix + LLM-side findings (2026-07-08)

**Encoder C(t) matrix (5 covered windows × {p50,p90} × rho{15,25}),
results `simulation/results/ct_matrix/`:** p90/rho15 passes the tail SLA
on ALL windows (p99 588–905 ms) at **0.10× deployable-static cost on the
calm day** and 0.87–1.18× inside bursts — the band-as-headroom finding
(ch. 4) reproduced inside the closed loop; p50 underprovisions broadly
(worst: 39 s p99 on the 1-min-onset burst3 — onset outruns forecast
lead). Failure modes recorded (burst5 rho25 divergence = capacity
calibration boundary; its grid-implied rho ≈ 7).

**Forecast coverage rule:** span is resolution-dependent (8k-bin context
⇒ 1min forecasts from Oct 20 14:36, 15s from Oct 16 09:36); burst2/6
(Oct 15) structurally unforecastable under the protocol — evaluation
windows must be in-span; both loaders now hard-fail otherwise.

**LLM side through the planner (forecast_file live after the
optimization_target='sla' fix):** at TP1, tail-infeasible at any replica
count (prefill floor — replica scaling cannot fix fleet shape; 3.1's
finding in the control plane). At TP2 with live accurate forecasts:
TTFT p99 1,717 ms / ITL 126.8 at mean ~1.0 replica — the planner's
**average-based capacity conversion** provisions to mean throughput while
the SLA binds on tails. Even perfect predictions through a mean-based
capacity model miss the tail: the design doc's own limitation, measured.
Consequence for the contribution: the predictive policy needs the same
tail-aware per-pool capacity mapping the encoder side uses (knee-derived
per-replica rate), not the planner's throughput regression. Next: env
knob to feed boosted quantiles / knee-mapped targets through
forecast_file; encoder reactive twin; weekly aggregate (E2B).
