# Expanded reproduction manifest (S3 depth)

Companion to Appendix A of the thesis. The appendix carries the **complete but
thin** mapping (one row per manuscript element: script, artifact, provenance
run family). This file carries the same mapping with the explanatory prose,
the caveats attached to individual rows, and the workspace layout — the detail
displaced from the appendix during the shortening pass so that the in-document
mapping could stay total without staying long.

Paths are relative to the repository root. Nothing here supersedes the
appendix: where the two differ in wording, the appendix is the manuscript
statement and this file is the elaboration.

## Environment notes

Versions are pinned in Appendix A `tab:ap-env`. Three notes that a
reproduction attempt needs:

- **Two `dynamo.replay` vintages.** The pinned **1.2.1 wheel** is the Phase-2
  baseline. The **1.3.0 source build** runs AIC timing predictions in-core
  (Rust) and is used for every calibrated run from the load sweeps onward. The
  wheel's per-request Python timing callback inflated extreme tail maxima
  *only* — documented in the two-pool chapter. Results reported from the two
  vintages are labelled by vintage wherever both exist (e.g. the 235B family
  transfer: wheel-era s=1 ITL/TTFT p99 87.7/397.7 ms; source-built 1.3.0 s=1
  86.2/387.4 ms, s=2 210.6/524.0 ms — the source-built ladder is the vintage
  that pins the knee).
- **GPU clock discipline.** The AIC data-collection and GEMM-validation runs
  pin clocks via `nvidia-smi -lgc 2400,2400 -lmc 14001` (delivered SM
  2377–2400 MHz, MEM 13801 MHz); the AIC cost model itself is parameterised at
  the 2407 MHz boost reference. The phase-E physical encoder anchor ran
  single-tenant persistence-mode (delivered SM 2377–2400 MHz), *not* a hard
  lock — the two are separate collections and are reported as such.
- **Environment boundaries.** The GPU EDA environment (`eda/`: cuDF/cuML/CuPy
  on the RAPIDS `cu13` stack) rebuilds from this checkout via its tracked `uv`
  lock (`eda/uv.lock`, `eda/pyproject.toml`); its multi-gigabyte `.venv` stays
  gitignored. The aiconfigurator and ai-dynamo environments are separate
  virtual environments *external* to this checkout. The encoder campaign runs
  on draft PR ai-dynamo/aiconfigurator #1312 through commit `b55dd0b7`; only
  the Dynamo live-planner branch remains a local commit.

## Workspace layout

| Directory | Role |
|---|---|
| `analysis/trace_eda/` | GPU exploratory analysis of the Azure multimodal trace |
| `predictors/` | time-series foundation-model benchmark, baselines, EWMA calibration, Dynamo shipped-predictor sweep |
| `collector_artifacts/` | AIC collection/validation audit trail, one artifact directory per phase |
| `workload/` | trace-to-two-pool converter and the encoder FIFO simulation |
| `simulation/` | sweep / grid / planner drivers and their results |
| `verification/` | adversarial reviews, resolutions, rerun reports, verification scripts |
| `provenance/` | PostgreSQL schema, loaders, registered checks, `verify_all.sh` |
| `tex/` + `figuras/` | the manuscript and its figures |
| `defense/` | presentation deck and the `anim/` data-generation campaign (several manuscript rows draw artifacts from `defense/anim/data/`, which is why that path appears in the manifest) |

The collected AIC datasets were contributed upstream as draft PR
**ai-dynamo/aiconfigurator #1312** (campaign through commit `b55dd0b7`, pushed
and open on the draft PR).

## Element → script → artifact → provenance run

Grouped as in Appendix A `tab:ap-manifest`, with the row-level caveats spelled
out. `run_id` prefixes index `provenance.current_runs`; "—" means the
artifacts are file-only (not ingested into the store).

### Chapters 1–2

| Element | Script | Artifact | `run_id` | Notes |
|---|---|---|---|---|
| `fig:intro-arch` | TikZ, in source | — | — | drawn in the manuscript source; no external artifact |
| `tab:rel-positioning` | literature synthesis | bibliography | — | positioning table over prior work; no experiment behind it |

### Trace EDA (RQ1)

| Element | Script | Artifact | `run_id` |
|---|---|---|---|
| `fig:eda-ctx-vs-img` … `fig:eda-multires` (nine figures); `tab:eda-archetypes`, `tab:eda-persistence` | `analysis/trace_eda/*.py` | `*_stats.json` in the same directory | `eda:*` |

Runs under `eda/.venv` (GPU). Each figure script writes its own `_stats.json`
beside the figure, so every annotated number in the EDA chapter is re-readable
without re-running the GPU pass.

### Forecasting (RQ2)

| Element | Script | Artifact | `run_id` |
|---|---|---|---|
| `tab:pred-wape`, `tab:pred-cov`; `fig:pred-horizon`, `fig:pred-band`, `fig:pred-heatmap`, `fig:pred-models`, `fig:cl-framework-diff` | `predictors/{benchmark,precision,figures_tex}.py` | `predictors/results/*.parquet` (the 4-signal × 6-model base grid); runtime logs `predictors/results/logs/` | `predictors:*` |
| Dynamo shipped-predictor comparison | registry sweep through the same protocol | `predictors/results_dynamo/{arima,kalman,prophet,constant}_*.json`; `comparison_table.csv` | — |
| Additive context decomposition; quantile coverage | structural ablation and coverage pass over the archive | `predictors/results/metrics/additive_structural_ablation.json`, `quantile_coverage.json` | — |
| EWMA calibration loop (`tab:cl-ewma`) | EWMA p90 calibration through the identical encoder loop | `verification/results/ewma_{baseline_*,sweep}.json` | `predictors:ewma_*` |

The ARIMA comparison is **matched-origin**: the rescore artifact
`predictors/matched_origin_rescore_2026-07-26.json` is the one that backs the
framing used in the manuscript. Quantile evaluation is reported through
downstream quantities (under-provision probability, burst-time coverage,
worker-count regret) in preference to WAPE rankings.

### AIC cost model

| Element | Script | Artifact | `run_id` |
|---|---|---|---|
| `tab:aic-validation` | `collector_artifacts/phaseA_validation/` | audit artifacts per phase | — |
| `tab:aic-fn`, `fig:aic-fn` | `collector_artifacts/phaseB_batch_validation/` | `measured_f_n_5x50.csv`; `aic_f_n_postinfill.csv`; `kernel_ledger_N{1,64}.json` | — |
| Shape infill | `collector_artifacts/phaseC_vit_shape_infill/` | merged parquets (AIC branch `656ac8ca`); row counts 7,679→7,760 attention, 34,326→34,710 GEMM | — |
| Encoder cold start | `collector_artifacts/phaseD_cold_start/` | `trials.jsonl` | — |
| Physical encoder anchor | `collector_artifacts/phaseE_physical_anchor/{bench_encoder_anchor,silicon_in_loop,silicon_multiworker}.py` | `anchor_sdpa_*.json`; `oneworker_artifact/`; `silicon_multiworker.json` | — |
| Matched-engine vLLM dense sweep + queue replay (`tab:app-engine`, `fig:app-engines`) | `collector_artifacts/phaseE_physical_anchor/{vllm_eager_dense,vllm_multires,vit_compile_dense,tier2_vllm_replay,make_engine_fig}.py` | `vllm_eager_dense.json`; `vllm_multires.json`; `vit_compile_dense.{json,log}`; `merged_sdpa.csv`; `merged_fa2.csv`; `{winsched,static_c8}_{ctrl_aic,treatment_vllm}.stats.json`; `replay_provenance.md`; `figuras/aic/aic_fn_engines_aiccurve.csv` | — |

Sampling scope for the matched-engine sweep: a **dense N=1–64 sweep plus five
off-cap probes** (N ∈ {96, 128, 192, 256, 512}) — not a dense N=1–512 sweep.
See `kernel_collection_history.md` for the engine-sensitivity detail.

### Two-pool simulation

| Element | Script | Artifact | `run_id` |
|---|---|---|---|
| `tab:sim-poly-aic` | `simulation/run_replay.sh` | `simulation/results/srcbuild/llm_head2k_*_src.json` | `srcbuild:*` |
| `tab:sim-knees`, `fig:sim-knees` | `simulation/sweep_load.py`; `sweep_fig.py` | `simulation/results/sweeps/summary.json` | `sweeps:*` |
| `fig:sim-burst-queue` | `simulation/burst_queue_fig.py` | `simulation/results/sweeps/series/vision_burst1_s1.series.json` | `sweeps:*` |
| 235B family transfer | wheel-era spot check `simulation/run_replay.sh` (`AIC_TP=8`, `AIC_MOE_TP=8`); source-built ladder `defense/anim/build/gen_g3_32b.py` | `simulation/results/235b/llm_head2k_aic235btp8_s{1,4,16}.json` (wheel era); `defense/anim/data/g3_32b/reports/235b_tp8_s*.report.json` | `g3_32b:235b_tp8_*` |
| Cap sensitivity | `workload/trace_to_two_pool.py` | `simulation/results/cap_sensitivity/` | `cap_sensitivity:*` |

Both 235B vintages are kept and labelled; the wheel-era artifact is the
87.7 ms ITL p99 operating point, the source-built 1.3.0 ladder reproduces it
(86.2 ms) and is the vintage that pins the knee (s=2 fails at 210.6 ms).
Reporting one without the other is the error this row exists to prevent.

### Baselines

| Element | Script | Artifact | `run_id` |
|---|---|---|---|
| `tab:base-tp` (iso-cost TP; burst5 archived at C=16) | `simulation/sweep_grid.py` (TP cells) | `simulation/results/grid/reports/grid_llm_*_{N4_aic,N2_TP2_aic}.report.json` | `grid:*` |
| `tab:base-grid` (burst5 C\* corrected to 8) | `simulation/sweep_grid.py` (+35 close-out corner runs); burst5 stability correction `verification/scripts/burst5_stability.py` | `simulation/results/grid/grid_summary.json` (burst5 row superseded by `verification/rerun-stability-e2e.md`) | `grid:*` |
| Reactive planner | `simulation/run_32_reactive.sh` | `simulation/results/reactive32/r32{A,B}_*.report.json` | `reactive:*` |

The burst5 row is a **superseding correction**, not a re-run of preference:
the raw grid endpoint C\*=16 was an endpoint artifact and the stability test
corrected it to 8. The superseded value stays visible in the artifact so the
correction is auditable.

The 14 headline language reactive runs are labelled **instant workers (no
startup lead)** — an optimistic, not a matched, baseline. Any comparison that
treats them as cold-start-matched is invalid.

### Closed loop (RQ3)

| Element | Script | Artifact | `run_id` |
|---|---|---|---|
| `tab:cl-triad`; LLM lead sweep + capacity mapping | `simulation/run_44_riders.sh`; `replay_with_forecast.py` | `simulation/results/riders44/{ladder_*,fc_lead*,fc_scale*,tp2knee_*}.report.json` | `riders:*` |
| Per-window factorial (60-cell p90 headline + p50; ρ-rating surface); `tab:base-react-enc`; week-scale surface | `simulation/run_44_factorial_issuetime.py` (`QUANTILE`/`RHO` env; issue-time, warm+strict); `run_44_week_surface_issuetime.py` (96 aggregate cells); target-time exploratory grid `{gen_cells_44.py, e2b_fleet.py}`; burst4 reactive L=165 supplementary cell `defense/anim/build/gen_a2_fleet.py` | `simulation/results/factorial_issuetime/factorial_issuetime_{p50_rho15,p90_rho{10,15,20,25}}_results.json`; `simulation/results/week_surface_issuetime/week_surface_issuetime_results.json`; target-time grid `simulation/results/results_44.jsonl`; supplementary cell `defense/anim/data/a2_runs/burst4_reactive_L165.jsonl{,.stats.json}` | `factorial:*`; `a2:burst4_reactive_L165` |
| Onset detection | `simulation/detect_onsets_44.py` | `simulation/results/riders44/detection_delay.json` | `riders:*` |
| `tab:cl-aggregate` (encoder week headline) | `simulation/run_44_aggregate_issuetime.sh`, wrapping `verification/scripts/forecast_schedule_issuetime.py` (`--strict-rewarm` for the sensitivity); target-time bound from `simulation/run_44_aggregate.sh` | `simulation/results/aggregate44/fc_p90_L{15,30,45,165}_issuetime.*`, `fc_p50_L30_issuetime.*`; `aggregate44_rho/*_issuetime.*` (ρ frontier); `aggregate44_strict/{fc_p90_L*,fc_p50_L30,fc_p90_rho20_L*}_strict.*` (re-warm sensitivity) | `aggregate44:*`; `aggregate44_rho:*`; `aggregate44_strict:*`; static reference `a6:static_C8` |
| Hybrid encoder schedule max(fc,re): aggregate, F1–F7 folds, combiner sweep | `simulation/run_encoder_hybrid{,_folds,_combos}.sh`; combiner `simulation/combine_schedules.py` | `simulation/results/encoder_hybrid/`: `{fc,re,hybrid}.*` (aggregate), `F6_{fc,re,hybrid}.*`, `folds/F{1..7}_*.*`, `combos/*.*` (its p90/re cells are byte-identical to the `F6_*` runs) | `encoder_hybrid:*` |
| Daily folds | fold split + per-fold replay | `defense/anim/data/g4_folds/folds_table.md` | `g4:*` |
| `tab:cl-ledger-enc` … `tab:cl-ledger-joint` (request-linked arm set) | `simulation/composed_fill_join.py` (request-linked join; the four archive-dependent cells read replay inputs tracked as `.jsonl.zst` beside their plain paths — `defense/anim/data/a2_runs/steady24h_{forecast,reactive}_L30.jsonl.zst`, `defense/anim/data/a13_runs/{ft_static_C8,ft_llm_static.requests,ft_reactive_L30,ft_llm_reactive.requests}.jsonl.zst` — inflate with `zstd -d` first; `verification/repro_clean_checkout.sh` automates the whole check) | `simulation/results/composed_fill/composed_fill_joined.json` (byte-reproducible from a clean checkout); provenance store: `v_joint_e2e`, `v_pool_latency`, `v_pool_cost` | (joined views) |
| Language-pool week replay | `simulation/results/llm_week/launch.sh` (composed trace + winning encoder schedule through the planner) | `simulation/results/llm_week/week_{fc_p90,fc_p90_toto,fc_p90_timesfm,fc_p50,re}.report.json` | `planner:week_*` |
| Language operating-point calibration: q×s grid, held-out frontier, daily folds | `simulation/run_lang_calib.sh` (burst2/burst6 grid); `run_lang_calib_eval.sh` (held-out windows); `run_lang_folds.sh` (folds) | `simulation/results/lang_qsweep/{burst2,burst6}_p{50,60,70,80,90}_s{2..8}.report.json`, `eval_{p50_s8,p70_s6,p90_{s1,s4,s6}}/`, `folds_*/` | `langcalib:*`; `lang_qsweep:*` |
| Controller inference cost | `defense/anim/build/gen_a16_controller_cost.py` | `defense/anim/data/a16_controller_cost/{accounting.{csv,json}, timing_{chronos,toto,timesfm}_{cpu,cuda}.json, timing_arima_cpu.json, REPORT.md}` | — |

Row-level caveats that must travel with these artifacts:

- The **0.62×** encoder-week figure is the *issue-time* schedule and is an
  **encoder-pool** number. `run_44_aggregate.sh` gives the target-time bound.
  The language p70/s6 point is **0.61×**, a different quantity — the two are
  not interchangeable.
- The burst4 reactive **L=165 s** cell is a supplementary sub-grid cell
  *outside* the declared {15, 30, 45, 300} s factorial; the 165–300 s interval
  is unswept, so 165 s is the largest **tested** passing lead, not an
  identified feasibility threshold.
- Calibration and evaluation are separate: burst2/burst6 enter results grading
  only through the forecast-free policies. Forecast policies replay them
  solely as the language calibration split, never as evaluation results. The
  **p90/s6** point was chosen after the p70/s6 e13 failure was inspected, so it
  is a **post-hoc robustness sensitivity on this trace**, not an independently
  held-out selection.
- Factorial-cell counts are parameter robustness. The evidential unit is the
  day/episode.

### Live validation anchor

| Element | Script | Artifact | `run_id` |
|---|---|---|---|
| `tab:val-anchor`; live divergences | `simulation/live51/worker_manager.py` (live control plane: etcd/NATS, KV router, per-process TP2 mockers, Prometheus, planner) | `simulation/results/live51/`: offline twins `twin_fc*`, `twin_re*`; live runs `live_runs/{live_fc,live_re,verify_flag}/{planner.log.gz, manager.jsonl, profile_export_aiperf.json}` | `live:arm:*` |

The live anchor exercises Dynamo's **real control plane with mocked engines**
(one live run per policy). It is not real-H100 execution, and no claim in the
manuscript may read that way. The only physically measured pool is the
RTX 5090 encoder.
