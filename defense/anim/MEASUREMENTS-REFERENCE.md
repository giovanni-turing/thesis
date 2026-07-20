# Measurements reference — defense session

Operational companion to `NEW-MEASUREMENTS.md` (which maps results → thesis gaps).
This file gives, per measurement: **what it measures · settings · methodology ·
status · files · notes**. Everything here is a *new* run generated this session;
ledgered thesis results are reproduced exactly at every anchor endpoint.

Last refreshed after the full pipeline completed (A15 + week-TimesFM arms + three-model rebuild, finisher exit 0 at 20:09:37).

---

## 0. Shared apparatus (applies to every run below unless overridden)

**Trace.** `data/AzureLMMInferenceTrace_multimodal.csv.gz` — Azure LMM inference
trace, **1,000,000 requests**, sorted by arrival. Windows/offsets in
`defense/anim/data/windows_ext.json` (episodes + max-spans + full trace).

**Two pools.**
- **Encoder (vision).** RTX 5090, silicon-calibrated via **aiconfigurator (AIC)**.
  A forecast p90 image-rate schedule (`forecast_schedule_issuetime.py`) drives a
  converter (`a2_conv_snapshot.py`) that folds each request's encoder delay into
  its arrival time and emits a *composed* trace. The shim drops the
  post-snapshot `encoder_patch_embed_gemm` op (+0.931 ms @ f(64)) to match the
  thesis snapshot numbers. Settings: `--quantile p90 --rho 15 --cold-start-s 30`,
  encoder issue-time lead **L=30 s**, `--encoder-workers 2`.
- **Language (text).** H100, **Dynamo `dynamo.replay` mocker** — discrete-event
  virtual clock, CPU/RAM-bound (no GPU/VRAM). `AIC_TP=2` (2 GPUs/replica, TP2),
  `AIC_VER=0.19.0`, startup 60 s, initial 2 replicas. Runs on each pool's
  **composed** trace so the language stage sees the encoder's arrival shaping.

**Policies.**
- **Forecast** (`fc_chronos` / `fc_toto` / `fc_timesfm`): archived rolling-origin
  p90 forecast → planner `simulation/planner_forecast_smoke.json` +
  `replay_with_forecast.py`. `FORECAST_QUANTILE=p90`, `FORECAST_RESOLUTION=15s`,
  `FORECAST_REQ_SCALE=8.0` (tail-aware capacity conversion), replica leads
  **{60,120,300} s**.
- **Reactive**: Dynamo SLA planner (ARIMA), ladder
  `simulation/results/riders44/planner_ladder_t200_20.json` (200 ms TTFT /
  20 ms ITL targets).

**Forecast models.** Chronos-2, Toto-2.0, TimesFM-2.0. Median point head
(Chronos/Toto), mean (TimesFM); **p90** is the provisioning signal. Four demand
signals forecast: requests, images, ctx, gen. **Predictions are archived
offline** (never computed in-flight) — replay is lookup-only.

**SLA.** TTFT p99 ≤ **1000 ms**; ITL p99 ≤ **100 ms**.

**Per-request records — the enabling patch.** `ai-dynamo/dynamo` source build,
commit **`70c965db26`**: `PlannerReplayBridge.report_jsonl_path` threads
per-request records through the *planner* replay path (previously only the
non-planner path recorded), and lifts the `--report-jsonl not supported with
--planner-config` guard. Rebuilt with
`maturin develop --uv --release --features aic-forward-pass`. Every per-request
language/E2E number below depends on this.

**Methodology note (why offline forecasts are valid).** Forecast = offline
prediction of **exogenous** demand (WAPE-graded). Everything endogenous (TTFT,
queue, replica decisions, SLA verdicts) is computed by the discrete-event mocker
from silicon-calibrated timings per (config, policy, lead). The archive is
rolling-origin, so replaying it is online-equivalent for the exogenous signal;
the one endogenous piece (language capacity conversion) is already in-loop.
Endogenous demand (abandonment/retry) is **narrowed, not closed**. A16
(`defense/anim/data/a16_runs/verification.json`, report recomputed by
`defense/anim/build/a16_endogenous_report.py`) bounds it under a *stated
mean-field client model*: abandonment is resolved **offline**, by iterating the
client model around the unmodified replay, **not in-clock** — the mocker has no
Abandon event kind. Under that model both arms settle into a **period-2 limit
cycle**, not a fixed point, so only cycle envelopes are quotable and no single
iterate or envelope midpoint is a point estimate. In-clock abandonment remains
the honest future-work frontier.
Confirmed sound — **no methodology change this session.**

---

## A2 — Encoder race (the headline board)

- **Measures.** Per-episode encoder-pool provisioning: forecast vs reactive vs
  static, worker staircase + running p99 encoder delay + live cost/latency/queue.
- **Settings.** Encoder pool as §0; leads swept; ρ=10/15; dual cost accounting
  (readiness-billed = ledgered, order-billed = each up-step pays its warm-up).
- **Method / files.** Drivers `build/gen_a2_fleet.py` (chronos, 40 cells),
  `gen_a2_toto.py` (`a2t_runs`, 36), `gen_a2_timesfm.py` (`a2tf_runs`, 36),
  `gen_a2_extra.py` (`a2x_runs`, e7–e18, **100 tags**). Extractor
  `extract_a2_fleet.py`; template `build/a2_template.html`; output
  `a2_the_race.html` (7.6 MB, 3-model toggle). Cost: `a2_cost_accounting.csv`.
- **Status.** ✅ **DONE + committed** (3-model Chronos/Toto/TimesFM).
- **Notes.** Reactive fails **9 of 18** episodes @ L30
  (burst3,e8,e10,e11,e13,e14,e15,e17,e18). **e13** (263 img/s, 7-min onset) is a
  genuine **p90 forecast-miss boundary** — both policies fail, only static C8
  passes, identical across all 3 models and ρ=10/15.

## A11 — Language race (per-request planner replays)

- **Measures.** Language-pool closed loop: replica staircase, per-bin worst TTFT,
  running mean/p99 TTFT + p99 ITL, cumulative GPU-h — forecast vs reactive.
- **Settings.** Language pool as §0; TP2; windows burst1/3/4/5 × leads
  {60,120,300} + week × {60}; policies {chronos,toto,timesfm,reactive}.
- **Method / files.** Drivers `gen_a11_runs.py` (chronos/toto/reactive),
  `gen_a11_timesfm.py`; extractor `extract_a11.py` (staircase parsed from
  "Scaling events", ITL from per-request records, asserted vs report); template
  `build/a11_template.html`; output `a11_llm_race.html` (**2.59 MB**); data
  `data/a11_runs/` (**52 tags**).
- **Status.** ✅ **DONE — 3-model rebuilt.** 52 tags; all extract cross-checks
  ok. `week_fc_timesfm_L60` = **651.1 ms** (556.88 GPU-h), matches its
  `ledger_expected` exactly.
- **Numbers.** Forecast **651 ms PASS** vs reactive **3.49 s FAIL**; reactive
  **lead-invariant** (burst5 2151/2151/2155 @ L60/120/300); week fc 651 vs
  reactive 1195. SLA-verdict template bug fixed (`sla_ttft`, was `sla_ms`).

## A12 — Composed E2E (modelled → measured; upgrades Ch. 6)

- **Measures.** Request-linked **ingress→first-token** = each request's own
  encoder delay (recovered from the seam) + its own replayed TTFT; per-bin + p99,
  per pool and E2E. Arrival alignment asserted < 1 ms.
- **Settings.** Encoder L=30 issue-time + language replica L=60; windows
  burst1/3/4/5 + week; arms {toto,chronos,timesfm,reactive}.
- **Method / files.** Drivers `gen_a12_e2e.py`, `gen_a12_timesfm.py`; extractor
  `extract_a12.py` (FIFO key-match encoder delays; language matched by
  `request_<N>` session ids = trace line order); template `build/a12_template.html`;
  output `a12_composed_e2e.html` (**0.89 MB**); data `data/a12_runs/` (**20 tags**).
- **Status.** ✅ **DONE — 3-model rebuilt.** 20 arms; `week_fc_timesfm`
  = 651.1 ms (610.65 GPU-h). Composed E2E p99 **1,239.5 ms** for all three
  models on burst3/5/4 + week.
- **Numbers.** burst3 fc composed E2E p99 **1,239.5 ms** (enc 588.4 + TTFT 651.1)
  = the thesis Ch. 6 modelled ≈1.30 s, now **measured**. New finding: reactive
  composed **21,868 ms** (enc 16,079 *compounds* into lang 10,574) — per-pool
  grading understates the composed failure.

## A13 — Full-trace coverage guarantee

- **Measures.** Every request of the 1 M trace simulated through **both** pools
  with per-request records — the coverage guarantee.
- **Settings.** Encoder {static C8, static C2, reactive}; language {static
  TP2×2, reactive planner}; each exactly 1,000,000.
- **Method / files.** Driver `gen_a13_fulltrace.py` (converters 2-wide, language
  1-wide for RAM); manifest builder `build_coverage_manifest.py`; output
  `data/coverage_manifest.json`; data `data/a13_runs/` (5 runs).
- **Status.** ✅ **DONE + committed** (`a073840`). Guarantee
  `encoder_all_1M_covered: true`, `language_all_1M_covered: true`,
  `complete: true`.

## A14 — Per-model max-span E2E (model-independence, end to end)

- **Measures.** Each forecast model over its **own max forecastable span**, both
  pools E2E — proves model choice is second-order as an E2E measurement.
- **Settings.** Fixed-context spans: Chronos 749,601 / Toto 872,980 / TimesFM
  931,628 req (= 75.0/87.3/93.2 % of 1 M).
- **Method / files.** Driver `gen_a14_maxspan.py`; spans in `windows_ext.json`
  (`span_chronos/toto/timesfm`); data `data/a14_runs/`.
- **Status.** ✅ **DONE** (folded into coverage manifest).
- **Numbers.** All three TTFT p99 **651.1 ms** (chronos 528.28 GPU-h,
  toto 751.43, timesfm 704.98). Identical 651.1 → model-independence is now
  measured, not inferred from accuracy.

## A15 — Expanding-context E2E (closes the warm-up boundary)

- **Measures.** Each model over `span_expctx` = **999,599 req (99.96 % of 1 M)**,
  both pools, per-request records — using expanding-context forecasts so
  provisioning starts 3 min into the trace instead of 1.4 days.
- **Settings.** offset 401, t0 2024-10-15 12:03:00; encoder p90/ρ15/cold-30;
  language TP2 + `FORECAST_SUFFIX=_expctx`; encoders 3-wide, language 3-wide.
- **Method / files.** Driver `build/gen_a15_expctx_e2e.py`; reads
  `predictors/results/{model}_images_expctx.parquet` + `_expctx` language
  archives (`replay_with_forecast.py` patched with `FORECAST_SUFFIX`); data
  `data/a15_runs/`.
- **Status.** ✅ **DONE.** All 3 models: n=**999,599** (99.96 % of 1M),
  enc_p99 588.4, **TTFT p99 651.1**, ITL p99 6.0-6.2, GPU-h 704.68 (timesfm) /
  757.17 (toto) / 776.85 (chronos). Identical 651.1 to fixed-context A14 while
  covering 99.96 % instead of 75/87/93 %.

## Expanding-context forecast archives (the enabler for A15)

- **Measures.** Forecasts issued from the earliest possible origin by *growing*
  context as history accrues, instead of waiting for a full fixed window.
- **Settings.** origin o forecast from `series[max(0,o-ctx):o]`; origins from
  bin 12 (= 3 min @ 15 s) stepping by H; grouped by context length for uniform
  `predict_batch`. Chunk overrides + `expandable_segments` for Toto OOM.
- **Method / files.** `predictors/benchmark_expctx.py` (reuses shipped
  `benchmark.py` machinery); output `predictors/results/{model}_{signal}_expctx.parquet`
  (**12 files** = 3 models × 4 signals). Thesis archives untouched.
- **Status.** ✅ **DONE.** Coverage per model 75/87/93 % → **99.96 %**; first
  forecast at 12:03:00 (3 min in). RTX 5090.

---

## Status board

| Fleet | Runs | Status |
|---|---|---|
| A2 encoder (chronos/toto/timesfm/extra) | 40+36+36+100 | ✅ committed, 3-model |
| A11 language | 52 | ✅ 3-model rebuilt |
| A12 composed E2E | 20 | ✅ 3-model rebuilt |
| A13 full-trace | 5 | ✅ committed |
| A14 max-span | 3 | ✅ done |
| A15 expanding E2E | 3 | ✅ done (999,599 × 3, all 651.1) |
| expctx forecasts | 12 parquets | ✅ done |

**Nothing in progress or scheduled — the pipeline is complete.** Final sequence
(finisher `bd03gp6h1`, exit 0): A15 drained 18:40 → week arms `a12
week_fc_timesfm` + `a11 week_fc_timesfm_L60` both rc=0 at 20:08 → `extract_a11`
(52 tags, all cross-checks ok) → `extract_a12` (20 arms) → `build_a11`
(2.59 MB) / `build_a12` (0.89 MB) → coverage manifest re-run, guarantee **True**.
Both boards screenshot-verified with the TimesFM arm selected (A11 week:
PASS 651 ms / 556.6 GPU-h vs reactive FAIL 1.19 s; A12 week: enc 588 + TTFT 651
→ E2E 1.24 s PASS vs reactive 1.70 s FAIL).

**Known cosmetic notes (not defects).**
- `extract_a11` prints a 1.7 % percentile-convention note on `burst3_reactive_*`
  (recovered p99 3554.7 vs report 3494.7) — nearest-rank vs the report's
  heavy-tail convention; assert tolerance is 5 %.
- `burst1` forecast tails run slightly above the flat 651.1 (chronos 680.1,
  toto 670.5, timesfm 651.1 @ L60) — real window behaviour, all PASS.
