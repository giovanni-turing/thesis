# Results ledger — artifact ↔ manuscript provenance

**The habit (user directive, 2026-07-08):** for EVERY new result, record
the exact artifact path, the command/config that produced it, the
timestamp, and which manuscript paragraph/table/figure it feeds or
supersedes — at the moment the result lands, not later. This is the
guard against stale-number drift (see `report.md`'s review findings).

Entry schema — keep it exactly this shape:

```text
### <short name>  (<UTC date>)
artifact:   <repo-relative path(s)>
command:    <exact command or script+args/env>
feeds:      <tex file § / table / figure — or "chapter in prep: <which>">
supersedes: <what it replaced, or "new">
commit:     <hash where artifact+text landed>
```

A number in a chapter with no ledger entry is a defect. An artifact
regenerated without updating its entry (and the tex it feeds) is a
defect. Run a ledger-vs-tex sweep before any submission build.

---

### Vision knee sweeps, post-infill  (2026-07-08)
artifact:   simulation/results/sweeps/summary.json, vision_*_aic_s*.json
command:    python3 simulation/sweep_load.py --pool vision --window {head2k,burst1} --speedups 1 2 4 8 16 32 --force  (grid-exact DB, parallel-chunk dispatch)
feeds:      tex/twopool.tex Tab. 6.2 (steady 199→787; burst 5,013 at s=1), §6.4 prose (p99 5.0 s, 29% util), intro echo
supersedes: pre-infill values (200→794, 4,957) and pre-parallel-dispatch (5,368)
commit:     9fa5c3e

### Burst queue dynamics figure  (2026-07-08)
artifact:   simulation/results/sweeps/burst_queue.png, series/vision_burst1_s1.series.json
command:    eda/.venv/bin/python simulation/burst_queue_fig.py  (reads the s=1 sweep point)
feeds:      tex/twopool.tex Fig. sim-burst-queue + mechanism ¶ (peak 4,701; 805 s >1,000 queued; 83,432 forwards ≤315 ms)
supersedes: pre-infill 4,637/789; pre-parallel 4,452/417 + multi-second-forward mechanism
commit:     9fa5c3e

### Knees figure  (2026-07-08)
artifact:   simulation/results/sweeps/knees.png → figuras/sim/sim_knees.png
command:    eda/.venv/bin/python simulation/sweep_fig.py
feeds:      tex/twopool.tex Fig. sim-knees
supersedes: pre-infill render
commit:     9fa5c3e

### Measured f(N), chapter protocol  (2026-07-08)
artifact:   collector_artifacts/phaseB_batch_validation/measured_f_n_5x50.csv
command:    for N in 1 6 8 16 32 64 96 128: eda/.venv/bin/python collector_artifacts/phaseA_validation/bench_vit_real.py --sizes 448 --batch $N --nruns 5 --iters 50  (locked clocks 2377–2400 MHz)
feeds:      tex/aiconfigurator.tex Tab. aic-fn "Measured" column; §5.3.1 batching-saturation prose (bottom 7.26 @N=6 → 7.99 @64)
supersedes: n=8 single-block sweep (measured_f_n.csv) for quoted values (agreement <1%)
commit:     70b8a5a (values), 4da3fd2 (table)

### Composed f(N), post-infill  (2026-07-08)
artifact:   collector_artifacts/phaseB_batch_validation/aic_f_n_postinfill.csv
command:    EncoderCostModel(448).latency_ms(N), N=1..128, aiconfigurator venv, grid-exact DB
feeds:      tex/aiconfigurator.tex Tab. aic-fn "Composed" column (8.16/31.79/43.13/82.22/160.20/316.37); tex/twopool.tex batching ¶ (f(1)=8.16, f(64)=316.4, 4.94, 1.65×, ~3.2 ms)
supersedes: aic_f_n.csv (PRE-infill curve — retained as the Phase B comparison record; do not quote in tex)
commit:     this entry closes the gap found while writing the ledger

### Kernel ledgers N=1/N=64  (2026-07-08)
artifact:   collector_artifacts/phaseB_batch_validation/kernel_ledger_N{1,64}.json
command:    eda/.venv/bin/python collector_artifacts/phaseB_batch_validation/profile_vit_kernels.py --n 1 64
feeds:      tex/aiconfigurator.tex §5.3.1 attribution ¶ (attention 1.300→1.306 ms/img; GEMM 6.03→3.69; unmodeled 168.6 ms = 92% of 182 ms gap; dispatch 15.3%→2.5%)
supersedes: new (closes the growth attribution promised by the section)
commit:     70b8a5a

### Static-optimal grid, final  (2026-07-08)
artifact:   simulation/results/grid/grid_summary.json (+101 point files)
command:    python3 simulation/sweep_grid.py --windows <w>  (per window; TP ladder; corner cross-checks; grid-exact DB; corner replays re-verified on regenerated traces)
feeds:      chapter in prep: baselines (C* table, TP2×N2 headline, 8×/2× overprovision); tex/aiconfigurator.tex infill note ("one optimum shifted by a single worker")
supersedes: first-pass grid (burst3 C*=6 under pre-infill costs)
commit:     b290fc4 (first), 48fc43c/9fa5c3e (re-derivation)

### 3.1 close-out checks  (2026-07-08)
artifact:   simulation/results/grid/closeout/closeout_summary.json (35 checks)
command:    python3 simulation/closeout_31.py  (router credit 0.25/0.5 + pls 0.5/2.0 at corners; binding C16+TP2×N2 all windows)
feeds:      chapter in prep: baselines ("static-optimal at default routing; router-robust; binding config verified")
supersedes: new
commit:     dd26dad tree

### Encoder C(t) policy matrix  (2026-07-08)
artifact:   simulation/results/ct_matrix/{forecast,reactive}_*.stats.json (30 runs)
command:    POLICY={forecast,reactive} QUANTS=... bash simulation/run_ct_matrix.sh  (time-based lead conversion; in-span windows only)
feeds:      chapter in prep: closed loop (p90/ρ15 PASS all windows, 0.10× static calm-day; head-to-head table; p50 underprovisions)
supersedes: first matrix run (4×-favorable lead on 15 s windows — wiped)
commit:     f5db4de

### Forecast-vs-reactive lead sweep (fleet pilot)  (2026-07-08)
artifact:   simulation/results/pilot_results.jsonl (+pilot_cells.jsonl)
command:    .venv/bin/python simulation/e2b_fleet.py --cells-file simulation/results/pilot_cells.jsonl --out ... --concurrency 12  (template tese-twopool; exact parity vs local verified)
feeds:      chapter in prep: closed loop (reactive fails at every lead 30–300 s, →never-scaled limit; forecast flat 588 ms — regime anticipation)
supersedes: new
commit:     bec4d97

### 3.2 reactive LLM baseline  (2026-07-08)
artifact:   simulation/results/reactive32/r32{A,B}_*.report.json (14 runs)
command:    bash simulation/run_32_reactive.sh  (A: shipped Easy-mode load loop; B: sla target, both loops, ARIMA, 15 s/60 s; composed C*-traces; TP2 bursts/TP1 steady; RUST_LOG=warn)
feeds:      chapter in prep: baselines (14/14 mean-law MET with 2–4× margin, tail SLA FAIL; A≈B ⇒ conversion is the defect)
supersedes: new
commit:     dd26dad

### LLM closed loop, burst1  (2026-07-08)
artifact:   simulation/results/planner/fc_burst1_tp2_s8.report.json (+_tp2, _tp2_s2, fc_smoke2)
command:    FORECAST_REQ_SCALE=8.0 AIC_TP=2 REPLAY_PY=<dynamo/.venv> AIC_VER=0.19.0 REPLAY_ENTRY=simulation/replay_with_forecast.py FORECAST_T0="2024-10-21 12:59:00" bash simulation/run_replay.sh <llm_burst1.jsonl> aic <report> 2 --planner-config simulation/planner_forecast_smoke.json
feeds:      chapter in prep: closed loop (751 ms p99 PASS at mean 2.14 replicas; ×1/×2 identical ⇒ mean-capacity threshold between 2–8×; principled mapping = mean-capacity/knee)
supersedes: new
commit:     2532b53

### 4.4 fleet matrix — 560 cells, per-pool leads  (2026-07-08)
artifact:   simulation/results/results_44.jsonl (560 records, 0 errors) + cells_44.jsonl (+_wave1); template czhmc6picw1w86popfdk rebuilt (payload +toto/timesfm parquets, run_cell model selector)
command:    python3 simulation/gen_cells_44.py; .venv/bin/python simulation/e2b_fleet.py --cells-file cells_44.jsonl --out results_44.jsonl (wave1: 60@60, wave2: 500@500, per user's ramp); parity gate vs pilot bit-exact (588.37/31838)
feeds:      chapter in prep: closed loop — L* table (forecast/p90/ρ15: L*=300 on EVERY window; reactive: burst3 L*=none — fails even at 15 s, burst4/5 L*=45, burst1/steady L*=300; p50 passes only 23/60 at rho15 — corrected 2026-07-09, prior "16/60" was a tally error); operating-point p99=588.4 everywhere = f(64)+handoff floor (zero queueing)
supersedes: pilot lead sweep (subset; retained) and first ct_matrix (lead 60 only)
commit:     acfbdee

### 4.4 rider (d) — burst-onset detection from archived forecasts  (2026-07-08)
artifact:   simulation/results/riders44/detection_delay.json
command:    eda/.venv/bin/python simulation/detect_onsets_44.py  (θ=224 img/s·15 s; stitched 15-s paths; issue-time = tile origin)
feeds:      chapter in prep: closed loop (p90 detects every in-span onset at −105..+210 s incl. BEFORE-signal crossings on the two fastest onsets; point/p50 detect hours late or never; calm-day false alarms = 0 for all models/paths) — the mechanism behind the p90 headroom rule; answers review E5
supersedes: new
commit:     acfbdee

### 4.4 rider (c) — reactive target ladder under realistic LLM lead  (2026-07-08)
artifact:   simulation/results/riders44/ladder_t{400_40,300_30,250_25,200_20}.report.json (+planner_*.json)
command:    bash simulation/run_44_riders.sh  (variant-B planner, grid_burst1_C6 TP2, STARTUP_TIME=60 via new run_replay.sh knob → mocker-native startup_time)
feeds:      chapter in prep: baselines/closed loop — tightening window-mean targets 400/40→200/20 raises spend 18.6→20.4 GPU-h but tail is pinned (TTFT p99 1,616–1,620 ms FAIL at every level; budget not saturated): under a 60-s lead reactive cannot buy tail compliance — the defect is information timing, not thrift
supersedes: refines the "conversion is the defect" 3.2 finding under realistic lead (3.2 ran L=0, maximally charitable)
commit:     acfbdee

### 4.4 LLM forecast closed loop under realistic leads  (2026-07-08)
artifact:   simulation/results/riders44/fc_lead{60,90,120,300}.report.json (+fc_lead60_s1 scale-1 twin)
command:    run_44_riders.sh fc block  (fc_burst1_tp2_s8 config + STARTUP_TIME ∈ {60,90,120,300}); twin = same at FORECAST_REQ_SCALE=1
feeds:      chapter in prep: closed loop — forecast PASSES at every LLM lead (TTFT p99 736–757 ms vs 751 at L=0; ITL ~6.5) — lead-invariance proven on BOTH pools; closes the "instant workers flattered our own result" gap. The scale-1 twin FAILS (1,716.6 ms / ITL 126.8, ≈ the reactive ladder's 1,616): forecast fed through the planner's mean-based capacity conversion fails like reactive — signal quality cannot compensate a mean→tail conversion; the ×8 (to become the principled mean-capacity/knee mapping) IS the tail-aware conversion. Triad on burst1@L60: reactive 1,616 FAIL | forecast+mean-conv 1,717 FAIL | forecast+tail-conv 736 PASS
supersedes: fc_burst1_tp2_s8 as sole LLM closed-loop evidence (L=0)
commit:     acfbdee

### 4.4 weekly aggregate — THE headline  (2026-07-08)
artifact:   simulation/results/aggregate44/*.jsonl.stats.json + *.sched.json (8 configs); windows.json +aggregate (offset 250399, n 749601, span 483,660 s = 5.60 days, 2024-10-16 21:39 → trace end = full 15-s-forecast-covered span)
command:    bash simulation/run_44_aggregate.sh  (chronos schedules, ρ15/15s/hyst3; statics = converter fixed C)
feeds:      chapter in prep: closed loop headline — forecast-p90 PASSES the span (588 ms p99) at 2.38M/2.12M worker-s (L30/L300) = 0.31×/0.27× static-C16 (7.74M, 565 ms); reactive "passes" aggregate (588 @0.34×; 905 marginal @0.22×) ONLY via aggregation masking — matrix shows it failing burst3 at every lead (mirror of Ch.3's dashboard-masking, now in the metric); p50 FAILS (3.0–4.7 s); static C2 FAILS (2.95 s). Headline: forecast-p90 meets the tail SLO in aggregate AND per-episode at 0.27–0.31× the deployable static fleet
supersedes: single-window C(t) results as the cost story; thesis-statement clause now number-backed
commit:     acfbdee

### Principled LLM capacity mapping — the ×8 knob derived and validated  (2026-07-09)
artifact:   simulation/results/riders44/tp2knee_s{1.25,1.5,2}.report.json; fc_scale{6.22,4.64}.report.json (burst1); fc_scale{6.22,7.0,8.0}_burst4_v2.report.json; fc_scale6.22_regress.report.json
command:    (knee) run_replay.sh llm_burst1 aic TP2 N2 --arrival-speedup-ratio {1.25,1.5,2}; (belief) median engine_rps from planner "Agg: X rps / Y engine_rps" ticks, degenerate ticks (>100) dropped → 10.07; (validation) fc runs FORECAST_REQ_SCALE ∈ {4.64,6.22,7.0,8.0}, STARTUP_TIME=60
feeds:      chapter in prep: closed loop — FORMULA: scale = engine_rps(believed)/r_tail(measured tail knee). Measured: belief median 10.07 rps/TP2-replica (p10–p90: 8.5–12.8; mix-varying); r_tail burst1 = 1.62 (s=1.5 PASS 906 ms, s=2 FAIL), burst4 ∈ [1.26,1.44] (scale 7.0 PASS 792 ms, 6.22 FAIL 1,104) → burst4 is the BINDING mix. Validation flips exactly at the formula's boundary: burst1 — 4.64 FAIL/6.22 PASS 932 (−16% GPU-h vs ×8)/8 PASS 736; burst4 — 6.22 FAIL/7.0 PASS/8.0 PASS 754. ⇒ ×8 = belief/1.26 = binding-window knee + ~14% capacity margin: the empirical knob is the principled value with margin, not arbitrary. Margin is MANDATORY: planner-in-loop runs show ~4% p99 run noise (932→968 same config) and r_tail is mix-dependent
supersedes: FORECAST_REQ_SCALE=8 as an unexplained knob ("threshold between 2–8×")
commit:     a3cd122

### forecast_file predictor: sub-minute feed fixes  (2026-07-09)
artifact:   simulation/replay_with_forecast.py (units + tick-clock fixes)
command:    (bug found via burst4 fc runs: scaled demand ~2.4 rps vs actual ~2.2 req/s raw)
feeds:      all future LLM closed-loop runs at 15 s resolution. Two compounding sub-minute bugs: (1) parquet quantiles are per-BIN totals, planner reads per-60s counts → values ×(60/bin_s) (×4 understated at 15 s); (2) predictor advanced 1 bin/tick but ticks are 60 s → path read 4× slow, stuck at window start. Both ×1 no-ops at 1 min (burst1 regression: 968 vs 932 ms = run noise, not the fix). Pre-fix burst4 fc results (fc_scale{6.22,8}_burst4.report.json) are INVALID — superseded by _v2
supersedes: fc_scale6.22_burst4/fc_scale8_burst4 (buggy feed; retained as the bug record)
commit:     a3cd122

### Encoder model-side cold start (Phase D)  (2026-07-08)
artifact:   collector_artifacts/phaseD_cold_start/{trials.jsonl,README.md}
command:    eda/.venv/bin/python collector_artifacts/phaseD_cold_start/measure_cold_start.py --out trials.jsonl  (×3 fresh processes); dd if=<ckpt> of=/dev/null bs=16M iflag=direct
feeds:      tex/intro.tex cold-start footnote (encoder ≈3–5 s model-side, imports-dominated; weights 0.11 s O_DIRECT + 0.13 s H2D warm); 4.4 lead-grid grounding ({10..300 s} = orchestration regimes above a measured floor); chapter in prep: closed loop (per-pool lead times)
supersedes: assumed shared cold-start range for both pools
commit:     6bcb9f5

### LLM/AIC burst knee points — the review's missing row (H1)  (2026-07-08)
artifact:   simulation/results/sweeps/llm_burst1_aic_s{1,2}.json; reports/llm_burst1_aic_tp2_s1.report.json
command:    REPLAY_PY=<dynamo/.venv> AIC_VER=0.19.0 python3 simulation/sweep_load.py --pool llm --window burst1 --timing aic --speedups 1 2  (isolation trace, TP1×2); bespoke run_replay.sh AIC_TP=2 for the TP2×2 point
feeds:      tex/twopool.tex Tab. sim-knees new "LLM/AIC burst" row (none: over at s=1, 1,868 ms; ITL 58.3 ok) + reframed inversion ¶ (TP2×2: 748.4 ms TTFT p99 / 6.6 ms ITL p99 PASS); intro ¶2/RQ1/contribution 4; knees figure curve "burst1·aic"
supersedes: the poly-only burst verdict ("language still meets the full SLA" — false under calibrated timing at TP1)
commit:     c6cca17

### Steady knee refinement s=3 (H2)  (2026-07-08)
artifact:   simulation/results/sweeps/llm_head2k_{poly,aic}_s3.json (+ summary.json rebuilt: poly knee→s=3, aic knee stays s=2 with first_over=s3)
command:    python3 simulation/sweep_load.py --pool llm --window head2k --timing {poly,aic} --speedups 3  (aic under source build)
feeds:      tex/twopool.tex Tab. sim-knees steady rows (poly s=3, 249→374; aic s=2 ITL-bound at s=3: TTFT 554/ITL 109.5); every "≥16×" claim replaced with "order of magnitude" (provable >10× calibrated: vision censored ≥32 vs llm first_over 3)
supersedes: "≥16×" separation (intro ×2, twopool ×2, RQ1, contribution 4, summary) and "both timing models put the knee at s=2"
commit:     c6cca17

### Encoder cap sensitivity (S4.4)  (2026-07-08)
artifact:   simulation/results/cap_sensitivity/vision_burst1_cap{32,128}.jsonl.stats.json
command:    <aic/.venv> workload/trace_to_two_pool.py --offset 843072 --max-requests 64804 --encoder-workers 2 --encoder-batch-images {32,128}
feeds:      tex/twopool.tex limitations (p99 5,163/5,013/6,743 ms at cap 32/64/128, util 29–33% — burst verdict cap-insensitive; cap-128 extrapolates past the collected batch range)
supersedes: new (answers report.md S4.4)
commit:     c6cca17

### Empirical quantile coverage (E6/F3.5)  (2026-07-08)
artifact:   predictors/results/metrics/quantile_coverage.json
command:    pandas pass over predictors/results/*.parquet: frac(y_true<=q) for q∈{p10,p50,p90} + band, per model-mode × signal × resolution, common span (origin>=8076), pooled over horizon
feeds:      tex/predictors.tex new "Is the band calibrated?" ¶ (p90 0.88–0.90 @1min all models/signals; band 69% vs nominal 80%; 29% @1s zero-ties), band-figure caption fix (measured 11% p90 exceedance), limitations update, intro contribution 2
supersedes: the uncalibrated p90-headroom proposal and the caption's "spike ... inside the band" (contradicted by the figure)
commit:     c6cca17

### Clustering silhouette scan (E8)  (2026-07-08)
artifact:   analysis/trace_eda/l_silhouette_scan.json
command:    recompute mirroring analysis/trace_eda/l_request_clusters.py (deterministic: seed 0, n_init 10, 50k subsample)
feeds:      tex/trace-eda.tex archetype ¶ ("k=4 maximizes silhouette over k∈{3..9} at 0.388, vs 0.378 @3, 0.319 @5")
supersedes: unquantified "k=4 by silhouette"
commit:     c6cca17

### Forecast-archive recount + burst-window stat corrections  (2026-07-08)
artifact:   (counts) predictors/results/*.parquet metadata; (burst) simulation/results/sweeps/traces/vision_burst1_s1.jsonl.stats.json + series/vision_burst1_s1.series.json; analysis/trace_eda/{a_quality,i_burst_anatomy}_stats.json
command:    pyarrow metadata sum (21,404,640 rows / 26 files; 20,749,440 common-span); pandas over the trace (dup=151 retained; 101 minutes>p99 → 87 runs → 18 episodes; hot sets ≥p99: 106 req / 101 img; burst1 chunk units Σceil=56,510; worst second 2,726) — all cross-checked against the artifacts named
feeds:      tex/predictors.tex (21.4M ×2); tex/trace-eda.tex (duplicates retained; 101/87/18; Jaccard set defs); tex/twopool.tex burst-mechanism ¶ (56,510 units / 83,376 forwards / ≤316.4 ms / 2,726 worst-second)
supersedes: "19.2M values", "151 dropped", "87 windows", "83,432 chunk forwards", "≤315 ms", "975 images"
commit:     c6cca17

### New thesis figures (review pass)  (2026-07-08)
artifact:   figuras/aic/aic_fn.png (src collector_artifacts/phaseB_batch_validation/fn_figure.png); figuras/pred/pred_models_burst.png (src predictors/results/figures/models_burst.png); figuras/sim/sim_knees.png (regenerated: +burst1·aic curve, s=3 points); intro TikZ architecture (in-source)
command:    eda venv matplotlib scripts (this pass) + simulation/sweep_fig.py rerun
feeds:      tex/aiconfigurator.tex Fig. aic-fn; tex/predictors.tex Fig. pred-models; tex/twopool.tex Fig. sim-knees (new caption); tex/intro.tex Fig. intro-arch
supersedes: knees.png without the calibrated burst curve; no-figure state for f(N)/multi-model/architecture
commit:     c6cca17

### Phase C shape infill  (2026-07-08)
artifact:   collector_artifacts/phaseC_vit_shape_infill/{encoder_attention,gemm}_perf.txt + merged parquets in ai-dynamo/aiconfigurator (AIC commit 656ac8ca, LOCAL — push held)
command:    docker run ... vllm/vllm-openai:v0.22.0 python3 /artifacts/run_infill.py  (465 cases, locked clocks); merge_parquet.py
feeds:      tex/aiconfigurator.tex infill-correction ¶ (7,760/34,710 rows; +4.3%/−5.8%/<1% shifts); every simulation number above
supersedes: interpolated 448 px query path
commit:     48fc43c (thesis side), 656ac8ca (AIC side, local)

### Burst3 LLM closed-loop triad — the quantile dial on the language pool  (2026-07-09)
artifact:   simulation/results/live51/twin_{fc_p90,fc,re}*.report.json (+_cap4 budget-matched variants)
command:    run_replay.sh grid_burst3_C7.jsonl aic <report> 2 --planner-config {planner_forecast_smoke,planner_ladder_t200_20}[.cap4] (fc: REPLAY_ENTRY=replay_with_forecast.py FORECAST_{MODEL=chronos,RESOLUTION=15s,T0="2024-10-18 10:18:00",QUANTILE∈{p50,p90}} FORECAST_REQ_SCALE=8 STARTUP_TIME=60)
feeds:      tex/closedloop.tex §cl-llm "quantile dial on the language pool too" ¶ — reactive FAIL 3,494.7 ms / fc-p50 FAIL 2,164.2 (better-informed, still late) / fc-p90 PASS 651.1 (ITL 5.1); extends the encoder matrix's p50-misses-fast-onsets result to the LLM pool; also the anchor policy pair for Ch. validation
supersedes: new (first LLM closed loop beyond burst1/burst4)
commit:     0eb7323

### 5.1 validation anchor — live Dynamo stack vs offline twins  (2026-07-09)
artifact:   simulation/results/live51/live_runs/{live_fc,live_re,verify_flag}/{profile_export_aiperf.json,manager.jsonl,planner.log.gz}; twins twin_fc_p90_cap4/twin_re_cap4 (budget-matched); harness simulation/live51/ (run_live.sh, worker_manager.py, planner_live*.py, configs)
command:    bash simulation/live51/run_live.sh {fc,re} grid_burst3_C7.jsonl <rundir> 59 2  (etcd+NATS dev compose, prom51 :9090 w/ per-run dynamo_namespace label, aiperf fixed-schedule mooncake replay, FORECAST_QUANTILE=p90)
feeds:      tex/validation.tex Tab. val-anchor + chapter; intro scope ¶ (placeholder resolved); conclusion RQ3 — VERDICT AGREEMENT both directions: fc-p90 PASS live 695 vs twin 651 ms (+6.8%); reactive FAIL live 3,531 vs 3,495 ms (+1.0%); replica-seconds within 8%; demand path byte-identical 12 ticks (live tick1 29.86 rps/5.31 engine_rps = twin 29.86/5.30); spawn-to-ready measured 1.0 s → spawn-delay 59 s = 60 s lead
supersedes: the intro's last placeholder (validation anchors)
commit:     0eb7323

### Live-path divergences + upstream fix fpm_observation_mode  (2026-07-09)
artifact:   ai-dynamo/dynamo branch fix/planner-live-fpm-observation-mode commit 33a9babe01 (LOCAL — push awaits user); verification simulation/results/live51/live_runs/verify_flag/
command:    (fix) PlannerConfig.fpm_observation_mode 'all': recv-mode drain → observe_fpm_extra via add_observations, 68 unit tests pass; (verify) SKIP_PARITY_PATCH=1 PLANNER_CFG_OVERRIDE=planner_fc_flag.json run_live.sh fc smoke_b3head — in-tree drain, Agg tick1 29.86/5.48=6, no monkeypatch
feeds:      tex/validation.tex §val-findings — 4 findings: (1) live startup_time INVERTS offline semantics (registers immediately, stalls requests → routable-but-dead window; leads modeled by delayed spawn); (2) tracking-mode FPM sampling starves agg capacity model at calm load (0 mixed samples in 5 min @2 rps; offline ready tick 1) → fixed via flag; (3) live tick cadence can stall (one 245 s gap; forecast feed realigns to wall time); (4) budget-unit inconsistency (offline replay caps replicas at max_gpu_budget; live divides by decode_engine_num_gpu) — anchor twins budget-matched via max_gpu_budget=4, thesis offline results unaffected (budgets never bind)
supersedes: new
commit:     0eb7323 (dynamo-side 33a9babe01 local)

### Aggregate model-sensitivity rider — table 8.2 is forecaster-robust  (2026-07-09)
artifact:   simulation/results/aggregate44/fc_p90_L{30,300}_{toto,timesfm}.jsonl.stats.json (+.sched.json)
command:    bash simulation/run_44_aggregate_models.sh  (p90/rho15/15s/hyst3, leads {30,300}, schedules from toto/timesfm parquets, same aggregate span + converter as the chronos rows)
feeds:      tex/closedloop.tex §cl-aggregate model-robustness ¶ — all three TSFMs PASS: chronos 0.273–0.307× (588 ms), toto 0.275–0.305× (588 ms), timesfm 0.263–0.297× (664.5 ms at L300, mild queueing, passing); ≤4% cost spread; Chronos quoted as the SMALLEST model (120M vs Toto 2.5B) — headline rests on the cheapest forecaster, not the best
supersedes: chronos-only evidence for the aggregate row (matrix already showed per-window model insensitivity)
commit:     e40ae20

### Week-scale LLM closed loop — language pool graded over the full evaluation span  (2026-07-09)
artifact:   simulation/results/llm_week/week_{fc_p90,re}.report.json (+.log, launch.sh, status.txt)
command:    bash simulation/results/llm_week/launch.sh  (run_replay.sh on results/aggregate44/fc_p90_L30.jsonl [composed trace, winning encoder schedule], aic TP2 N=2, STARTUP_TIME=60; fc: replay_with_forecast FORECAST_{MODEL=chronos,QUANTILE=p90,RESOLUTION=15s,T0="2024-10-16 21:39:00"} SCALE=8, planner_forecast_smoke; re: planner_ladder_t200_20)
feeds:      tex/closedloop.tex §cl-llm "language pool at week scale" ¶ — fc-p90 PASSES the 5.60-day span (TTFT p99 651.1 ms, ITL 6.4) at 518.6 H100 GPU-h = 0.96× burst-sized static TP2×2 (537.4 GPU-h/span); reactive FAILS the week (1,196.6 ms) at 281.8 GPU-h — half the spend, wrong tail. Closes the last coverage asymmetry (LLM pool now week-graded like the encoder pool)
supersedes: window-level-only LLM closed-loop evidence (burst1/3/4 retained)
commit:     5c04ffa

### DeepStack ×4 handoff-payload sensitivity — closes report.md S4.6  (2026-07-09)
artifact:   simulation/results/aggregate44/fc_p90_L30_ds4.jsonl.stats.json
command:    trace_to_two_pool.py --offset 250399 --max-requests 749601 --encoder-workers 2 --worker-schedule fc_p90_L30.sched.json --handoff-gbps 6.25  (×4 payload at 25 Gbps ≡ ×1 at 6.25 Gbps by linearity)
feeds:      tex/closedloop.tex limitations — 4× payload on the modeled 25 Gbps link: handoff p99 272→1,087 ms, encoder-delay p99 1,404 ms (SLA violation from transfer alone); the 588 ms floor assumes embedding-only handoff or a ≥100 Gbps fabric (restores quoted numbers exactly); tex/twopool.tex handoff ¶ now points here instead of promising a "scheduled correction"
supersedes: the unfulfilled "payload correction scheduled for the closed-loop runs" promise
commit:     337211e

### Dynamo shipped-predictor accuracy vs FMs on the image signal  (2026-07-09)
artifact:   predictors/results_dynamo/{consolidated.json,comparison_table.csv,<pred>_<res>.json}; runner predictors/dynamo_predictors_bench.py
command:    dynamo_predictors_bench.py --predictor {arima,kalman,prophet,constant} --res {1min,15s} --window 512 (via ai-dynamo/dynamo/.venv python; arima/prophet@15s capped 300 origins, disclosed); rolling-origin h=1 on the common span origin>=8076 (chronos ctx), WAPE=sum|y-yhat|/sum|y|
feeds:      tex/predictors.tex §Point-forecast accuracy new "Second" ¶ — Dynamo's shipped predictors (arima/kalman/prophet/constant) run through Ch4's protocol on the IMAGE signal all sit at/below the classical frontier, none reaches the FM level: @1min arima 0.521 (ties classical) vs FM 0.515 (~1pt); @15s arima 0.668 vs FM 0.637, kalman 0.811 & prophet 0.733 trail even naive 0.764. VALIDATION: constant reproduces archived naive WAPE exactly (0.6180/0.7638) — grid+metric identical to the FM table. Framing: modest at 1min, clearer at 15s; the point is the shipped predictors do NOT beat the FMs, so a forecast-capable planner gains nothing from predictor choice (mechanical in Ch closedloop)
supersedes: new — Ch4 benched FMs vs naive/EWMA/HW but never vs Dynamo's specific shipped predictors
commit:     3c7c6e4

### Dynamo shipped-predictor closed-loop sweep (v2, redesigned)  (2026-07-09)
artifact:   simulation/results/predictor_closedloop_v2/{steady24h,burst4}/{arima,kalman,prophet}.report.json + configs/ + README.md + analysis_summary.json (heavy logs gitignored)
command:    run_one.sh per (predictor,window): run_replay.sh on grid_{steady24h_C2 (TP1 N2), burst4_C7 (TP2 N2)}.jsonl aic <report> --planner-config <cfg with load_predictor in {arima,kalman,prophet}>, STARTUP_TIME=60; v1 (burst3) DISCARDED — p99 metric-saturated
feeds:      tex/closedloop.tex §cl-matrix "Model choice is second-order" item — swapping Dynamo's shipped predictor leaves the SLA verdict unchanged: steady24h byte-identical served-latency (p99 TTFT 1111.74 ms FAIL all three) despite distinct runs (worker-s 88012.04/88015.59/88012.34, 3 distinct md5); burst4 schedules genuinely split (89/89/87 actions) but p99 TTFT 2784/2776/2784 ms FAIL, mean-TTFT ≤1 ms apart. VALID (unlike v1): metric provably sensitive (worker-s + burst4 schedule move) yet binding outcome invariant → integer-replica conversion quantizes the forecast difference; predictor choice second-order, signal+conversion are not. Does NOT prove predictors equivalent in general or conversion=THE defect. Pre-flight: advisory≠actuation-suppression in offline replay (43/87-89 scale actions applied); load_predictor_warmup_trace no-op in replay (24h window supplies history; why v1 burst3 collapsed)
supersedes: v1 burst3 predictor sweep (discarded — metric-saturated, byte-identical p99 uninterpretable)
commit:     be5e4a8

### Aggregate rho-frontier + DeepStack x4 across policies (idle-core sweeps)  (2026-07-09)
artifact:   simulation/results/aggregate44_rho/fc_p90_rho{10,20,25}_L{30,300}.jsonl.stats.json (rho-frontier); *_ds4.jsonl.stats.json (ds4 across policies); runners simulation/run_agg_{rho,ds4}.sh
command:    run_agg_rho.sh (forecast_schedule.py p90/15s/hyst3 rho{10,20,25} x lead{30,300}, chronos parquet, converter over aggregate span); run_agg_ds4.sh (converter --handoff-gbps 6.25 = x4 payload @25Gbps, reusing each policy's .sched.json)
feeds:      tex/closedloop.tex §week-aggregate — (rho) headline is a TUNABLE FRONTIER not a point: fc-p90 PASSES all rho — 588ms@rho10/15 (0.44/0.31x), 651@rho20 (0.238x), 899@rho25 (0.198x); even cheapest passing setting <0.2x static → answers "0.27-0.31 cherry-picked?"; (ds4) DeepStack x4 is a FABRIC requirement not a policy weakness: ALL policies violate at 4x payload incl static-C16 (1,311ms), common 1,087ms handoff floor; Fig fig:cl-framework-diff 3-panel (accuracy near-parity | closed-loop verdict | online fidelity)
supersedes: single-point 0.27-0.31x framing (now the middle of a rho10-25 frontier); single-policy ds4 disclosure (now all-policy)
commit:     8f14e58

### Per-episode LLM closed-loop twins — fc-p90 passes every onset, reactive fails all  (2026-07-09)
artifact:   simulation/results/episode_twins/{burst1,burst4,burst5}_{fc,re}.report.json (+.log); runner simulation/run_episode_twins.sh (burst3 twins in live51/)
command:    run_episode_twins.sh — run_replay.sh on grid_{burst1_C6,burst4_C7,burst5_C8}.jsonl aic TP2 N2 STARTUP_TIME=60; fc: replay_with_forecast chronos/p90/15s/SCALE8 per-window T0; re: planner_ladder_t200_20
feeds:      tex/closedloop.tex §cl-llm quantile-dial ¶ — the LLM verdict generalizes from burst3 to ALL burst episodes: fc-p90 PASSES each at the service floor (TTFT p99 651–706 ms across 1–220 min onsets: b3 651/b5 651/b4 651/b1 706) while reactive FAILS all four (b3 3495/b4 2776/b5 2152/b1 1615). Same categorical split at every onset speed — closes the "LLM evidence is window-anecdotal" gap
supersedes: window-level-only LLM closed loop (burst1/3/4 individually); now the full episode set
commit:     1ba9243

### Week-scale rho x lead x model surface (112-cell local matrix)  (2026-07-09)
artifact:   simulation/results/week_matrix/*.jsonl.stats.json (112 cells; raw jsonl auto-deleted); runner simulation/run_week_matrix.sh
command:    run_week_matrix.sh — 20-way local xargs: forecast_schedule.py (aggregate window, p50/p90 x chronos/toto/timesfm x rho{10,15,20,25} x lead{15,30,45,300}) + converter over the 5.60-day span, encoder-workers 2. (E2B fan-out abandoned — template windows.json predates aggregate window, 404'd; local 24-core run faster.) NOTE: 3 rho25 cells corrupted by a mid-run disk-full event (raw jsonl filled /home), regenerated clean; driver now rm's raw jsonl per cell
feeds:      tex/closedloop.tex §week-aggregate rho-frontier ¶ (UPGRADED from 2-lead to full surface) — fc-p90 passes ALL 48 cells (every model/rho/lead), cost frontier 0.44x (rho10, 588ms) -> 0.18x (rho25, 899ms), 0.27-0.31x is the middle; fc-p50 passes 0/48 (median policy fails SLA at every rating — week-scale mean-sizing defect); p90/rho15 cells reproduce the committed aggregate headline exactly (588.4ms, 0.273-0.309x) validating the whole surface
supersedes: the 6-cell agg-rho partial sweep (now the full 112-cell surface, 3 models x 2 quantiles)
commit:     04908ca

### Structural-additive LLM prefill predictor ablation — NEGATIVE (closes roadmap item)  (2026-07-09)
artifact:   predictors/results/metrics/additive_structural_ablation.json; predictors/additive_structural_ablation.py
command:    eda/.venv/bin/python predictors/additive_structural_ablation.py  (archive-only; no GPU/sim)
feeds:      tex/predictors.tex §Do covariates help — new closing ¶; CLOSES roadmap "structural-additive LLM predictor" QUEUED item. R2=0.94, image term 34-36% of ctx mass (materially image-driven, NOT the trivial escape); additive ties/loses pooled (+0.07..+1.31pp); no onset edge (steep-rise flips sign by resolution); MECHANISM: image forecast is WORST component at onsets (75-100% WAPE vs direct-ctx 58-72% vs requests 33-38%) — image spike unforecastable exactly where the bet needed it. Do NOT graduate to planner run
supersedes: new (last queued unrun idea)
commit:     305f75f (branch bee4c62)

### Reactive-encoder baseline extended to burst2 + burst6 (all 6 bursts graded)  (2026-07-09)
artifact:   simulation/results/burst26_reactive/{burst2,burst6}_react_L{15,30,45,300}.jsonl.stats.json; runner simulation/run_burst26_reactive.sh (branch exp/burst26-reactive-encoder caeb907)
command:    forecast_schedule.py --policy reactive (observed image rate, quantile ignored) rho15/15s/hyst3 x lead{15,30,45,300}, converter over burst2 (78376/13870) + burst6 (93867/9821)
feeds:      tex/baselines.tex Tab. base-react-enc — reactive ENCODER now graded on ALL SIX bursts (burst2/6 need no forecast so they CAN be graded despite pre-context-window). Both L*=45s: burst2 588/588/588/4282; burst6 588/749/905/4606. New prose: burst6's 1-min onset PASSES at L<=45 (peak 337 img/s drains within a batch) unlike burst3's 1-min onset (same peak, thinner request stream, backlog outlasts lead) — onset speed AND volume both matter
supersedes: reactive-encoder coverage that omitted burst2/6 (5-window table -> 6-window)
commit:     659df69 (branch caeb907)

### Physical encoder anchor (Phase E, first, unlocked-clock)  (2026-07-09)
artifact:   collector_artifacts/phaseE_physical_anchor/{measure_fn_silicon.py,fn_silicon.json,run.log,README.md}
command:    eda/.venv/bin/python measure_fn_silicon.py  (extracted ViT models/Qwen3-VL-8B-ViT, flash_attention_2, batch N{1,6,8,16,32,64} @448px, 5x50 iters, cuda.sync-timed) vs aic_f_n_postinfill.csv
feeds:      tex/aiconfigurator.tex §validation (first whole-tower physical anchor ¶) + tex/conclusion.tex future work. Measured whole-tower f(N) tracks AIC composition at ratio 1.37 (N=1) -> 1.62 (N=64), MEAN 1.47 over N{1,6,8,16,32,64} — squarely in the documented 1.4-1.6x conservative band. Reproduces phase-B 5x50 silicon ref to +/-0.7% (511.26 vs 511.23ms @N=64), same-methodology cross-check, and its ratio growth. fa2 lower band 1.37-1.47. End-to-end burst3 FIFO replay reproduces sim p99 to the digit (54169.6 vs 54169.5) under AIC, 2.87x under measured. CORRECTION: my first direct run (fn_silicon_CONTENDED_INVALID.json) gave inflated 2.7-3.1x — it was GPU-CONTENDED by the concurrent anchor agent; agent's single-tenant run 614d8c3 is authoritative. CAVEAT: unlocked clocks (2385-2392 vs 2407 target) — ratio-stability across batch axis is the clock-invariant load-bearing observation; clean confirmation = locked-clock operator-isolated re-run + real-worker burst replay (future work). Also: DISK-FULL event corrupted the run's json write; recovered from run.log
supersedes: the physical anchor as entirely-future-work (now partially fulfilled with caveat)
commit:     7bd06d2

### Full-week false-alarm rate — p90-as-DETECTOR vs p90-as-provisioning-quantile  (2026-07-09)
artifact:   simulation/results/riders44/fullweek_false_alarms.json; simulation/detect_fullweek_falsealarms.py
command:    eda/.venv/bin/python simulation/detect_fullweek_falsealarms.py  (full 5.60-day span, count bins where forecast path crosses burst threshold 3360 img/bin while observed does NOT, outside true episodes)
feeds:      NUANCE (needs careful framing before tex, HELD): extends detection false-alarm count from calm-day-only to the FULL WEEK. p90 fires 70-102 FA/day (chronos 486, toto 507, timesfm 348 bins / 28684); point+p50 near-zero (0-1). IMPORTANT DISTINCTION: this counts p90-as-binary-DETECTOR crossings, NOT provisioning errors — the p90 band sitting above threshold during moderate activity IS the calibrated headroom (0.88-0.90 coverage) working, and the rho-frontier ALREADY prices it (0.27-0.44x static incl. this headroom). Honest read: p90 = good provisioning quantile but trigger-happy binary detector; point/p50 = clean detectors but fail as provisioning signals. Does NOT contradict the thesis but the existing "zero false alarms" claim must be scoped to "on the calm day / as a provisioning policy, priced in the cost" — check tex/closedloop.tex detection ¶ says "zero false alarms across the calm day" (already correctly scoped) not "zero over the week"
supersedes: refines the calm-day-only false-alarm claim
commit:     1123ed6

### Physical encoder anchor — stable-clock confirmation (Phase E)  (2026-07-10)
artifact:   collector_artifacts/phaseE_physical_anchor/anchor_sdpa_locked2400.json (+relock.log, README §stable-clock)
command:    eda/.venv/bin/python bench_encoder_anchor.py  (sdpa, single-tenant GPU, persistence-on stable clocks SM 2377-2400 / mem 14001; 5x50 @448px, N{1,2,4,6,8,16,32,64}) vs aic_f_n_postinfill.csv
feeds:      tex/aiconfigurator.tex §validation (anchor ¶ — was "locked-clock re-run = future work") + tex/conclusion.tex future-work item. Single-tenant STABLE-clock re-run reproduces the unlocked anchor's batch-axis ratio: mean 1.47 on the matched grid {1,6,8,16,32,64} (=1.469, the reported unlocked mean to the digit); 1.43 / band 1.32-1.62 on the denser grid (adds N=2,4 dipping to 1.32-1.33); N=64 511.68 ms within 0.09% of the phase-B 511.23 ref; CI95<=0.05 ms. Absolutes now publication-grade (SM held 2400 = 0.3% off the 2407 target). CAVEAT: artifact clocks_locked=False — clocks were STABLE via single-tenant + persistence, NOT a hard -lgc lock; remaining Phase-E future work is one REAL encoder worker serving a burst replay end to end (here burst replay was a faithful simulate_vision_pool port, burst3_fifo_replay.json, not a live worker)
supersedes: the "locked-clock re-run for publication-grade absolutes = future work" framing — commit 1feb1de landed this confirmation but was never ledgered; this stamps it and narrows the open item to the real-worker burst replay
commit:     1feb1de (artifact); ledger+tex reconciliation: 66e33fd

### LLM week-scale p50 + model coverage — the conversion-vs-quantile distinction  (2026-07-10)
artifact:   simulation/results/llm_week/{week_fc_p50,week_fc_p90_toto,week_fc_p90_timesfm}.report.json (all 3 models complete; timesfm re-run after an OOM SIGKILL)
command:    run_llm_week_p50.sh / run_llm_week_models.sh — run_replay.sh on composed trace, FORECAST_QUANTILE=p50 (and p90 x toto/timesfm), aic TP2 N2 STARTUP_TIME=60, 5.60-day span
feeds:      tex/closedloop.tex §cl-llm week paragraph — LLM week p50 PASSES (TTFT p99 827.8 ms, 319.9 GPU-h, 38% cheaper than p90's 651ms/519GPU-h) — OPPOSITE of encoder p50 (fails 0/48). NOT forced into false symmetry: the honest finding is the CONVERSION is universal (mean-reactive fails both pools, tail-aware forecast passes both) while the QUANTILE is pool-specific (adds most where signal is burstiest — image demand floods encoder FIFO at p50 mean-sizing; smoother ctx-token demand served OK at p50). This is a CLEANER statement of the thesis's core claim (conversion is the defect) than a forced p50-fails-both symmetry. Per-window burst3 p50-fails-fast-onset claim (line 210) stays correct + correctly scoped to fast onsets
supersedes: the (wrong) expectation that LLM p50 would fail at week scale mirroring encoder
MODEL-INDEPENDENCE (2026-07-10, commit da790f3): all 3 TSFMs pass the week at the IDENTICAL 651.1 ms tail; only provisioning cost shifts (chronos 518.6 < toto 625.3 < timesfm 641.1 GPU-h) — forecast model sets headroom bought, not SLA pass/fail. Landed in tex/closedloop.tex week ¶
commit:     0e48ee4 (p50); da790f3 (toto/timesfm + model-indep clause)

### Iso-cost TP1x4 vs TP2x2 language-pool comparison (Table base-tp)  (2026-07-10)
artifact:   simulation/results/grid/llm_burst{1..5}_C*_{N4_aic,N2_TP2_aic}.json (existing static-optimal grid points; NO new run — analysis only)
command:    tabulate ttft_ms.p99 from matched-encoder-C pairs: llm_<W>_C<C>_N4_aic (TP1x4 = 4 GPU) vs llm_<W>_C<C>_N2_TP2_aic (TP2x2 = 4 GPU), windows burst1-5
feeds:      tex/baselines.tex §"static optimum" — NEW Table tab:base-tp + sharpened structural-fact #1. At IDENTICAL 4-GPU cost TP1x4 FAILS every burst window (TTFT p99 1314-1331 ms) while TP2x2 PASSES every one (746-792 ms), a 1.66-1.76x tail cut from the parallelism LAYOUT alone. Isolates the TP benefit from GPU budget — answers "why TP2 not TP1 for an 8B model": the burst bottleneck is a per-request PREFILL-LATENCY floor (36k-token frames-class prefills), not throughput; only intra-request tensor-parallelism shortens the single prefill that independent replicas can only queue. ITL p99 within bound in both columns (decode never the issue). Win is concentrated in the p90/p99 tail (means 176-223 vs 112-139 ms close)
supersedes: the prior TP1-vs-TP2 framing that contrasted the TP1x16 plateau (16 GPU) against TP2x2 (4 GPU) — now the clean iso-cost 4-GPU A/B across all 5 windows
commit:     66e33fd

### Silicon-in-the-loop encoder burst replay (Phase E) — measured-service FIFO  (2026-07-10)
artifact:   collector_artifacts/phaseE_physical_anchor/{silicon_in_loop.py, oneworker_artifact/silicon_burst{3,5}.json, silicon_burst{3,5}.log, burst{3,5}_reqs.json}  (run by a prior session 2026-07-09 ~23:20, status=done; committed+ledgered now)
command:    eda/.venv/bin/python silicon_in_loop.py --window {burst3,burst5}  (1 worker, 64-cap FIFO port of simulate_vision_pool; per-batch service = LIVE Qwen3-VL ViT forward measured on RTX 5090 @ stable 2400 MHz, memoized per dispatched N; schedule from burst{3,5}_reqs.json)
feeds:      LANDED tex/aiconfigurator.tex anchor ¶ (commit 10e7ae3); burst3 2.87× measured-FIFO was already there. FINDING: replaying MEASURED-silicon service through the encoder FIFO amplifies the per-batch 1.4-1.6× f(N) gap into an END-TO-END p99 encoder-delay ratio of 2.89× (burst3, 143k img, thin 1-min-onset stream) GROWING to 6.65× (burst5, 555k img, dense stream) — queueing compounds the per-op slowdown and it worsens with window density. Both silicon+AIC FAIL single-worker (burst3 174,395 vs 60,253 ms; burst5 330,695 vs 49,709 ms). busy_s ratio ~1.6× (tracks f(N)) but p99-delay ratio 2.9-6.7× (backlog amplification). Reinforces "measured silicon slower than AIC → conservative for every infeasibility claim". CAVEAT: single-worker, measured-service FIFO port (not a live serving-worker process); a live encoder worker on the real request path remains the open Phase-E item
supersedes: extends the burst3-only 2.87× measured-FIFO note (7bd06d2) with burst5 + the amplification-scaling mechanism
commit:     d643a25

### Multi-worker silicon feasibility — does the AIC-sized encoder fleet survive real silicon?  (2026-07-10)
artifact:   collector_artifacts/phaseE_physical_anchor/{silicon_multiworker.py, silicon_multiworker.json}
command:    aiconfigurator/.venv/bin/python silicon_multiworker.py  (imports the grid's EXACT simulate_vision_pool + build_series + percentiles from workload/trace_to_two_pool.py; swaps ONLY the encoder cost object — AICEncoder=aic_f_n_postinfill.csv vs MeasuredEncoder=stable-clock silicon f(N) linearly interpolated between the 12 anchor points; grid-exact feasibility gate = p99<1000 AND not queue_divergent; text-only reqs padded as 0-delay; grid-exact window construction via load_window (all 6 burst windows); one canonical stable-clock 5090 f(N) interpolated between anchor points; worker sweep 1..64; pure CPU)
feeds:      LANDED tex/aiconfigurator.tex §validation closing ¶ (commit 5c457ea), framed as silicon-portable calibration (same queue-feasibility search, only f(N) changes — a quick per-accelerator benchmark) rather than a sizing hazard. HARNESS VALIDATED bit-exactly: AICEncoder reproduces the committed grid C* — burst3 C*=7 @ p99 904.7 = vision_burst3_C7.json to the decimal; burst5 C*=16. FINDING (all 6 windows; AIC reproduces the committed grid C* on EVERY one): robustness is set by WHICH CONSTRAINT binds C*, NOT onset speed/density. 5 of 6 are p99-latency-knee-limited (C*=6-8) and need ~2x the workers on silicon (burst1 2.17x [slowest onset 220min!], burst2 2.0x, burst3 1.86x, burst4 2.0x, burst6 2.0x; each composition-sized fleet fails on silicon at p99 1420-1846 ms). ONLY burst5 -- alone divergence-limited (C*=16, far above its p99 knee) -- absorbs the 1.4-1.6x underprice untouched (p99 588->784, both PASS). The per-batch underprice amplifies to a ~2x worker margin at the knee (same queueing amplification as the single-worker replay). CORRECTS my earlier 2-window (burst3/burst5) 'dense-vs-thin' framing -> 'knee-vs-divergence' across all 6. tex upgraded to the six-window statement (commit d1f2cb7)
supersedes: new (the deployable-fleet complement to the single-worker silicon burst replay)
commit:     c19c3ae

### Single-worker silicon amplification, all 6 windows (Phase E)  (2026-07-10)
artifact:   collector_artifacts/phaseE_physical_anchor/silicon_multiworker.json (.single_worker_amplification)
command:    aiconfigurator/.venv/bin/python silicon_multiworker.py  (W=1 p99 ratio silicon/AIC per window, grid-faithful simulate_vision_pool)
feeds:      CAUTION / not yet in tex. Extends the burst3/burst5 single-worker amplification to all 6. Grid-faithful W=1 ratios: burst3 2.87 (== committed 2.87x fifo-replay; supersedes silicon_in_loop's 2.89), burst6 4.56, burst5 7.19 (vs silicon_in_loop 6.65 — batching-model diff), burst4 18.62, burst2 19.23, burst1 24.86. CAVEAT: at 1 worker every window is deeply infeasible; the ratio is BACKLOG-DEPTH-DOMINATED (window length + sustained volume), NOT a clean per-op amplification (burst2 1.9h=19x but burst6 1.37h=4.6x). Saturation illustration only. RECOMMEND: do NOT expand the tex amplification claim to the all-6 numbers; the robust amplification claim is the multi-worker ~2x knee margin (already in tex, commit d1f2cb7). Optional consistency nit: tex burst3 single-worker "2.89x" -> "2.87x" to match the grid-faithful harness
supersedes: the silicon_in_loop 2.89/6.65 burst3/5 single-worker points (less-faithful per-request model) for cross-window comparison
commit:     142a138

### Closed-loop cost ratio under measured silicon — 0.27-0.31x SURVIVES  (2026-07-10)
artifact:   collector_artifacts/phaseE_physical_anchor/{silicon_closedloop.py, silicon_closedloop.json, fc_schedules/burst{1,3,4,5}_p90_rho15_L30.json}
command:    forecast_schedule.py --window burst{1,3,4,5} --quantile p90 --rho 15 --resolution 15s --cold-start-s 30 --hysteresis-min 3 (chronos_images.parquet) -> C(t) schedule; then aic venv silicon_closedloop.py replays each window's image schedule through simulate_vision_pool with that worker_schedule under AIC f(N) vs memoized stable-clock silicon f(N), grid feasibility gate
feeds:      tex/closedloop.tex §cl-limits — RESOLVES the D1 review finding (economic headline priced on AIC, which underprices knee windows ~2x on silicon). RESULT: the winning p90/rho15/L30 schedule is silicon-FEASIBLE on all 4 in-span burst windows — AIC p99 588 -> silicon p99 784, both < 1000. The rho15/p90 headroom provisions 24-32 workers at burst peaks (vs silicon-feasible C* 12-16), so both hit their zero-queueing floors (588 AIC / 784 silicon) and the underprice is absorbed with NO added workers. Schedule unchanged + feasible => 0.27-0.31x worker-seconds ratio PRESERVED on silicon. burst2/6 forecast-free by design (excluded). NOTE: per-burst-window fc/static ws ratio is 1.12-1.30x (forecast tracks the peak there); the 0.27-0.31x is the full-week integral (calm-dominated), preserved because the schedule doesn't change. CAVEAT: measured f(N) is eager whole-tower (pessimistic bound); live-worker confirmation still future work
supersedes: the closedloop 'untested — silicon-priced re-run is future work' caveat (now tested + resolved)
commit:     c951424

### Evaluation-window stratification figure (fig:eda-windows)  (2026-07-10)
artifact:   analysis/trace_eda/r_eval_windows.py; figuras/eda/eda_eval_windows.{png,pdf}
command:    eda/.venv/bin/python analysis/trace_eda/r_eval_windows.py  (1-min image rate over the week; bands = grid_summary window spans incl. +/-10min pad, calm day 10-19, forecast context [trace start, FORECAST_T0 2024-10-16 21:39))
feeds:      tex/trace-eda.tex NEW Fig fig:eda-windows (below fig:eda-sevenday) — shows the stratified sub-sample the experiments run on: b1-b6 + calm day + context split; explains why b2/b6 are forecast-free-only. Text links added in trace-eda §vision episodes ¶ and baselines §protocol
supersedes: new (user-requested; the stratification previously existed only in prose)
commit:     8f13ac3

### Six-reviewer verification + blocker corrections (major)  (2026-07-10)
artifact:   verification/{adjudicated-issues,false-positives,fix-plan,headline-cascade}.md, verify-{codex,opus,glm,grok,gemini,fabel}.md, rerun-{b1,ablation,stability-e2e,issuetime,citations}.md; scripts in verification/scripts/; reruns in simulation/results/rerun_verify/
command:    6 Opus-4.8 verifier agents (RAG + ./papers + web + code recompute) over codex + 5 LLM committee reviews; then targeted re-runs (image-bearing p99, stability criterion, e2e p99, reactive+tail-aware ablation, issue-time onset audit/scheduler)
feeds:      thesis-wide corrections, commits ca16adc..9ab8353. HEADLINE: 0.27-0.31x -> 0.55-0.61x (B5: burst5 C=16 was an endpoint-divergence artifact; honest AIC deployable static C=8 = 3.869M worker-s; verified backlog-slope ~0, tiled backlog constant, week-scale C=8 feasible p99 644ms; user chose AIC-consistent number only). B1: encoder p99 stated as all-request user-population tail + image-bearing note (burst optima rise 1-2 workers; denominator/headline framing consistent). B2/B3/B4: forecast actuates on issue-time not target-time -> the flat 588ms floor SURVIVES honest issue-time (actuation bug did NOT inflate headline), but 'detects every onset' is false -> graduated-headroom mechanism (burst4/5 anticipated, burst1/3 late); lead 15-300s -> 15-165s (archive max issued lead; H>=21 GPU regen NOT warranted). B6: true e2e ingress-to-first-token p99 ~1.30s reported (2x marginals, r=0.52 correlated tails). B7/P0-7: precedence claims narrowed + ModServe/Diao/Toner/HeteroServe credited. P2-1: reactive+tail-aware ablation run (fails fast onset -> anticipation decisive). +9 factual fixes (419->209.5, harmonics, C6->C7, Prophet, clocks, gen-band/slope, BurstGPT, 245->120s) + staffing citations (Halfin-Whitt/Borst/Gross) + scope/nits. Descriptive core (R2=0.123, forecastability, silicon model) unchanged.
supersedes: the 0.27-0.31x headline (artifact-inflated); the 'detects every onset'/'15-300s lead' mechanism claims; the three broad precedence claims; 9 factual values
commit:     ca16adc..9ab8353 (13 tex commits + verification package)

### Round-2 audit corrections (meta-review closure)  (2026-07-11)
artifact:   verification/rerun-{itl-timesfm,issuetime}.md; scripts in verification/scripts/ (now tracked); simulation/results/rerun_verify/
command:    L=165 aggregate schedule (forecast_schedule.py --cold-start-s 165, integrated to 2.215M worker-s); ITL like-for-like recompute (p99_tpot); TimesFM common-p50 recompute
feeds:      thesis-wide, commits ab0bd3e..efff418. HEADLINE consistency: the 0.55x endpoint rested on the non-realizable L=300 target-time cell -> honest L=165 aggregate = 0.57x; range 0.55-0.61 -> 0.57-0.61x (realizable issued leads 15-165s); tab:cl-aggregate +L165 row, L300 relabeled target-time UB. B4 summary regression fixed (graduated headroom). B3 language-hook caveat (tests conversion under held cursor, not language anticipation). B6 e2e -> 'modelled reconstruction'. B7 intro -> 'forecast-framed first'. B9 provenance: rerun scripts/outputs committed; draft-note + reproduction-guarantee softened; manifest corrected (burst5 C=8). ITL estimand fix: offline 5.3/160.3 (pooled) -> 9.7/152.7 (per-request p99_tpot, like-for-like) -- TIGHTENS live-vs-offline agreement; verdicts unchanged. TimesFM lone 1-min ctx win = mean-head artifact (0 wins at common p50). Clock caption split; 'exhaustive'->'grid'; open-loop conservative->direction-unknown.
supersedes: the 0.55-0.61x range (L300-anchored); ITL 5.3/160.3; the B4/B6/B7 overclaims; the 'all phases complete' guarantee
commit:     ab0bd3e..efff418

### Round-3 audit corrections (headline rebuilt to issue-time)  (2026-07-11)
artifact:   simulation/results/aggregate44/fc_p90_L{30,165}_issuetime.{sched,jsonl.stats,ledger}.json; simulation/results/aggregate44_rho/fc_p90_rho{10,20,25}_L30_issuetime.*; verification/rerun_b1_results.json (regenerated); verification/scripts/{forecast_schedule_issuetime,e2e_ingress_to_first_token}.py
command:    bash simulation/run_44_aggregate_issuetime.sh  (regenerates every issue-time schedule+replay: warm-pool L{15,30,45,165} rho15, rho-frontier {10,20,25} at L30, and strict-rewarm L{15,30,45,165}; denominator static C8 = 3,869,278 ws). Per-run: eda/.venv/bin/python verification/scripts/forecast_schedule_issuetime.py --window aggregate --quantile p90 --rho 15 --cold-start-s L [--strict-rewarm] --out SCHED, then ai-dynamo/aiconfigurator/.venv/bin/python workload/trace_to_two_pool.py --offset 250399 --max-requests 749601 --encoder-workers 2 --worker-schedule SCHED
feeds:      thesis-wide, commit 16c9498. HEADLINE REBUILT: the round-2 L=165 number (2.215M / 0.57x) was still the TARGET-TIME generator (forecast_schedule.py --cold-start-s 165), not the honest issue-time generator -- a second reviewer caught it. Reproduced both: honest issue-time L=30 = 2,410,755 ws (0.623x) and L=165 = 2,406,585 ws (0.622x), BOTH at p99 588.37 ms, non-divergent, over the exact static-C8 denominator 3,869,278 ws. The lead knob barely moves cost (0.17% across 15-165s) because issue-time is bounded by archived-forecast availability, not nominal lead. => HEADLINE 0.57-0.61x -> 0.62x (single lead-invariant number) everywhere (abstract EN+PT, intro, closedloop, conclusion, related, baselines). tab:cl-aggregate: forecast rows now issue-time (2.41M/0.62x for L30 & L165); target-time bound (2.12-2.21M/0.55-0.57x) demoted to caption as optimistic-not-realizable. rho-frontier rebuilt issue-time: rho10 0.89x(588), rho15 0.62x(588), rho20 0.48x(629), rho25 0.40x(748); clean band rho{10,15}=0.62-0.89x (was target-time 0.58-0.88). B4: mechanism para now honest about threshold-dependent burst5 anticipation (ahead only at the 1-min threshold; late at the honest 15-s-cadence threshold; only burst4 anticipates under both). B3: closedloop summary no longer attributes anticipation to the language pool (conversion under held cursor); 'counterpart' tightened. B6: twopool arithmetic fixed (1.24-1.30s range = replay-651 vs modelled-706 prefill; marginals 0.59+0.65-0.71), 'actual'->'modelled first-token wait'; e2e script relabeled true_end_to_end->modelled_end_to_end + regenerated. B7: intro contribution 2 narrowed to 'provisioning-framed, rolling-origin' + credits prior work; related 'first to integrate' hedged 'to our knowledge'. B9: issue-time schedules/stats/ledgers committed (124MB per-request jsonl gitignored, regenerable); rerun_b1_results.json regenerated+tracked; manifest points headline to issue-time script; draft note folded (no longer 'being folded'). Clock contradiction was already resolved (round-2).
supersedes: the round-2 0.57-0.61x headline (target-time L=165); the target-time rho-frontier numbers (0.58-0.88x); the B4 burst5-anticipated claim; the B6 1.30-vs-0.59+0.65 arithmetic; the B3 language-anticipation summary line
commit:     16c9498
descriptive core (R2=0.123, forecastability, silicon f(N), decoupling, SLA verdicts) unchanged; the SLA passes and every verdict direction hold under honest issue-time actuation.

### Round-3b: readiness-model disclosure + prior-work sincerity + provenance closeout  (2026-07-11)
artifact:   simulation/results/aggregate44/fc_p90_L{15,45}_issuetime.*; simulation/results/aggregate44_strict/fc_p90_L{15,30,45,165}_strict.*; simulation/run_44_aggregate_issuetime.sh (executable driver); verification/scripts/forecast_schedule_issuetime.py (+--strict-rewarm); verification/scripts/e2e_ingress_to_first_token.py (issue-time input)
command:    bash simulation/run_44_aggregate_issuetime.sh ; verification agents (raggae/papers) over ElasticMM (2507.10069), ModServe (2502.00937), TokenScale/HeteroScale
feeds:      thesis-wide (this commit). A THIRD reviewer verified 16c9498 and flagged: (1) the "lead-invariant 0.62x" is warm-pool-model-specific -- the generator's lifetime running_max lets a scaled-down replica re-scale up with no re-warm, matching the converter's LIFO free slot reactivation (build_slot_windows, trace_to_two_pool.py) but not a strict deallocate/re-warm model. Reproduced: warm-pool L{15,30,45,165}=0.6231/0.6231/0.6229/0.6220x (flat); STRICT re-warm (a matured level warm only [O+L,O+165+L])=0.6202/0.6171/0.6140/0.5877x, ALL pass p99 588.37 non-div -- reproduces the reviewer's 0.620/0.617/0.614/0.588 EXACTLY. => disclosed the readiness model in closedloop headline; 0.62x kept as the CONSERVATIVE figure across both models; dropped unqualified "lead-invariant". (2) B4 thesis-wide propagation: conclusion.tex:58, intro.tex:467, closedloop.tex:507 still said burst4/5 anticipate 'the gradual onsets' -> singularized to 'the clearly-gradual onset' (only burst4 anticipates at the honest 15-s threshold). (3) B3: added held-cursor guard to closedloop.tex:252 'both pools'. (4) prior-work SINCERITY (verified against the PDFs): ModServe per-pool-signals ~->checkmark (it autoscales image/text pools on modality-specific token load; thesis prose already conceded this); ElasticMM forecast --- -> ~ (proactive burst-tolerance allocation, but NO demand forecaster); TokenScale/HeteroScale forecast --- -> ~ (predictive metrics/time-of-day, not per-pool TS forecast); 'none asks/reactive' prose softened to 'predominantly reactive' conceding ElasticMM's proactive step; Forecast column defined in caption. (5) B6: e2e script now reads the issue-time jsonl (all-req p99 unchanged 1295.17; image-bearing 1348.83->1335.43); rerun-stability-e2e.md 'true e2e'/'actual user wait' -> 'modelled'. (6) B9: L15/L45 issue-time + strict artifacts committed; executable issue-time driver added; ledger '<this round>' placeholders -> 16c9498; manifest paths prefixed simulation/.
supersedes: the unqualified "exactly lead-invariant 0.62x"; the ModServe '~'/ElasticMM+TokenScale '---' cells; the 'purely reactive/none asks' blanket; the target-time e2e input; the '<this round>' ledger placeholders
commit:     61aac0e

### Round-3c: issue-time factorial rebuilt + committed; propagation + novelty closeout  (2026-07-11)
artifact:   simulation/run_44_factorial_issuetime.py (executable, portable, QUANTILE-param); simulation/results/factorial_issuetime/factorial_issuetime_{p90_rho15,p50_rho15}_results.json (later rounds add p90_rho{10,20,25})
command:    QUANTILE=p90 eda/.venv/bin/python simulation/run_44_factorial_issuetime.py ; QUANTILE=p50 eda/.venv/bin/python simulation/run_44_factorial_issuetime.py   (two invocations; 5 in-span windows x 3 TSFMs x leads{15,30,45,165} x {warm,strict} per-window replays, --offset/--max-requests per windows.json, same harness as run_cell.py; RHO env added round-3d)
feeds:      thesis-wide (this commit). A FOURTH reviewer flagged the main remaining blocker: the "p90 passes all 60 cells, every lead 15-165s" (closedloop) cited the ARCHIVED 560-cell factorial, which is TARGET-time at leads {15,30,45,300} (gen_cells_44.py) -- not rebuilt issue-time. REBUILT the 60-cell factorial under issue-time actuation, both readiness models: p90 warm 60/60 (p99 548.4-685.3ms), p90 strict 60/60 (564.0-733.6ms), all 4 burst windows pinned at 588.37ms; p50 warm 24/60, strict 23/60, calm-day p99 1073.1ms at every cell (reproduces the thesis's 1073ms EXACTLY). Committed the driver + consolidated results. closedloop sec cl-matrix rewritten to cite the issue-time factorial; 560-cell grid relabeled target-time exploratory; p50 '23/60'->'23-24/60'; week-sweep relabeled (target-time to locate, load-bearing cells rebuilt issue-time). PROPAGATION: unqualified cost 'lead-invariant' -> 'warm-pool model (0.59-0.62x strict)' in caption/intro/summary/conclusion. B3: h=1 'strictly before'->'at or before (zero lead)'; language p50 'still late/detection lagged'->'under-provisioned: mean sizing, not timing'. B4/B6 verification DOCS de-staled (rerun-issuetime 'burst4/5 anticipate'->threshold-scoped; rerun-stability-e2e 'true e2e'->'modelled', 1349->1335). B7 (ModServe PDF verified pp.6-10 via agent): ModServe DOES characterize per-modality independence+burstiness + reports 79% pred-error (DynamoLLM) + 25-41.3% cost saving -> intro 'first forecast-framed characterization' narrowed to 'first to QUANTIFY decoupling + frame signals as forecasting targets consumed closed-loop'; related 'does not forecast that signal'->'does not drive its autoscaler with a future-horizon forecast'; 'GPU-hour'->'25-41.3% serving-cost (fewer GPUs at SLO)'. B9: factorial driver portable (TESE_ROOT/EDA_PY/AIC_PY), aggregate driver made portable, manifest paths explicit (simulation/results/ prefix) + factorial row added.
supersedes: the target-time 560-cell factorial as the 60-cell headline evidence; unqualified cost lead-invariance; the h=1 'strictly before' + language-p50 timing language; stale verification-doc headings; the 'first forecast-framed characterization' novelty claim; 'GPU-hour savings'
commit:     7e73f61

### Round-3d: rho=20 is also 60/60 clean (new result from the corrected factorial)  (2026-07-11)
artifact:   simulation/results/factorial_issuetime/factorial_issuetime_p90_rho{20,25}_results.json; simulation/results/week_surface_issuetime/week_surface_issuetime_results.json (full 96-cell issue-time week surface); simulation/results/aggregate44/fc_p50_L30_issuetime.*; simulation/results/aggregate44_strict/{fc_p50_L30_strict,fc_p90_rho20_L{15,165}_strict}.*; simulation/results/aggregate44_rho/fc_p90_rho20_L{15,165}_issuetime.*; simulation/run_44_week_surface_issuetime.py (driver)
command:    RHO=20 QUANTILE=p90 eda/.venv/bin/python simulation/run_44_factorial_issuetime.py ; RHO=25 QUANTILE=p90 eda/.venv/bin/python simulation/run_44_factorial_issuetime.py ; eda/.venv/bin/python simulation/run_44_week_surface_issuetime.py ; bash simulation/run_44_aggregate_issuetime.sh  (regenerates the p50 + rho20 aggregate endpoints too)
feeds:      thesis-wide (this commit). A FIFTH reviewer found that the CORRECTED issue-time factorial reveals a NEW result the manuscript hadn't caught: rho=20 also passes EVERY per-window cell. Verified: rho=20 p90 warm 60/60 (p99 588.4-746.4ms), strict 60/60 (588.4-859.5ms); rho=25 51/60 both readiness, ALL 9 failures (x2) on burst5 -- reproduces the reviewer exactly. rho=20 aggregate cost: warm 0.482x(L15)-0.481x(L165), strict 0.480x-0.456x. => STALE 'rho=20/25 drops 3/11 cells' -> 'only rho=25 drops 9 (all burst5)'; 'only rho{10,15} clean' -> 'rho{10,15,20} clean, 0.48-0.89x'; headline framing: 0.62x KEPT as the deliberately CONSERVATIVE operating point (holds 588ms floor with margin), rho=20 disclosed as cheapest clean rating (~0.48x, but per-window p99 to 860ms strict, near bound). Aggregate p50 ROW was still target-time (3047ms) -> issue-time warm 2735ms/0.98M/0.25x (reviewer: 2735/982875/0.254 exact; strict 2955/968655/0.250, both fail, verdict unchanged). Full 96-cell issue-time week surface committed (p90 48/48 pass, p50 0/48 -- backs 'quantile decisive, rating cost knob'). B3 CODE disclosed: closedloop caveat now states the hook reads one 15s bin/tick from a cursor one interval ahead of T0, one-interval-stale sampled-bin (adequate for conversion, not timing). Two factorial WORDING fixes: intro/closedloop 'every window at 588' -> 'burst windows 588, calm day below 734'. B6 nuance: 1.30 = per-request joint reconstruction, 1.24 = marginal sensitivity (not a 2nd joint). B7 further: related 'not characterized as forecasting targets'/'no prior incl ModServe provides per-pool view' -> concede ModServe's per-modality analysis+79% error, claim the QUANTIFIED decoupling + forecastability + closed-loop. B4 doc rerun-issuetime.md :66/:87 threshold-scoped. B9: forecast_schedule_issuetime.py hardcoded /home/gio/tese -> TESE_ROOT/file-relative; ledger factorial command split into two executable invocations.
supersedes: 'rho=20/25 drops 3/11 cells'; 'only rho{10,15} per-episode-clean'; the target-time p50 aggregate row (3047ms); the 'every window at 588ms' wording; remaining B7 'not characterized' overclaims; the generator's hardcoded paths
commit:     fd50174
Note: 0.62x headline retained as the conservative operating point (reviewer-sanctioned option A); rho=20/~0.48x disclosed as cheapest clean rating. SLA + all verdicts hold under both readiness models across rho{10,15,20}.

### Round-3e: propagation/provenance closeout (6th review)  (2026-07-11)
artifact:   no new experiments; text/code/provenance fixes over fd50174. (validation live-log value re-checked against simulation/results/live51/live_runs/live_fc/planner.log.gz)
command:    n/a (edits); aggregate p50+rho20 endpoints now regenerable via bash simulation/run_44_aggregate_issuetime.sh
feeds:      thesis-wide (this commit). A SIXTH reviewer: 5 issues FULL, B3+B9 partial + 3 propagation defects. FIXED: (1) closedloop:175 clean band still 'rho{10,15}' -> 'rho{10,15,20} 0.48-0.89x' (contradicted the corrected :447). (2) intro:464 'every window at the service floor' -> 'burst windows 588, calm day below 734'. (3) driver hardcoded 'p90/rho15' in the JSON grid metadata -> QUANTILE+RHO interpolated; corrected the committed rho20/rho25 JSON grid fields (were mislabelled rho15). (4) FACTUAL: validation.tex live first-tick engine_rps 5.31 -> 5.71 (verified: live_fc log records '29.86 rps / 5.71 engine_rps = 6'; 5.30 is the OFFLINE twin) -- reframed as demand byte-identical, capacity belief differs from tick 1, both -> 6 replicas. (5) B3 disclosure was internally contradictory ('cursor one interval ahead of T0' + 'one-interval-stale') and inaccurate -> corrected to the actual code (series starts T0-1min; _bin samples the single bin at index 4t per tick, does NOT aggregate the minute's 4 bins); framed as a synthetic sampled-signal experiment; code comment added to replay_with_forecast.py. (6) methodological: 'no policy constant selected by outcomes' -> 'no constant TUNED on the eval span; rho=15 chosen ex post as conservative, full frontier reported'. B9: trace_to_two_pool.py TRACE default /home/gio/tese -> TESE_ROOT/file-relative; drivers export TESE_ROOT; aggregate driver run() takes a quantile + regenerates the p50/rho20 endpoints; ledger factorial command de-ellipsised. Appendix \clearpage before the manifest section (A.2 figures no longer defer past the A.3 heading). Verification docs: 'Proposed edits' sections banner-marked SUPERSEDED. Build 131pp, 0 undefined.
supersedes: the 'rho{10,15}' clean-band line; 'every window at 588'; the mislabelled JSON grid metadata; the WRONG live engine_rps 5.31; the contradictory B3 disclosure; the converter's hardcoded trace path; the ellipsised ledger command
commit:     36c192a

### Round-3f: live-validation claims narrowed + rho10 run + relocation/layout (7th review)  (2026-07-11)
artifact:   simulation/results/factorial_issuetime/factorial_issuetime_p90_rho10_results.json (NEW: backs the rho10 60/60 claim)
command:    RHO=10 QUANTILE=p90 eda/.venv/bin/python simulation/run_44_factorial_issuetime.py
feeds:      thesis-wide (this commit). A SEVENTH review flagged the LIVE-VALIDATION chapter making claims its own archive contradicts, + B9 relocation. VERIFIED each against the archive, then fixed:
  (1) LIVE p50 does not exist (only live_fc/live_re) -> validation.tex no longer says the p50 leg reproduces live; states only the p90-pass-vs-reactive-fail pair was carried live (p50 offline-only). Abstract EN+PT narrowed: "the language-pool p90-vs-reactive verdict pair reproduces through Dynamo's real control plane with mocked engines; encoder cost anchored separately on silicon; week economics simulated" (was "both verdicts reproduce on the live runtime").
  (2) "within run noise" (1 run/policy, no repetitions) -> "within 1-7% (a point difference, not a noise band)" at both validation.tex spots.
  (3) "budgets never bind" is FALSE -- verified burst4_fc.log clamps 24->8 repeatedly, burst1_fc.log 15->8 (max_gpu_budget=8) -> reworded: the cap DOES bind (forecast requests up to 24 language replicas, clamped to 8), reported provisioning is the post-cap applied capacity, policy still meets SLA at the cap, verdict unaffected.
  (4) intro RQ4 "560-cell factorial" (target-time exploratory) -> "per-window issue-time factorial ... both readiness models; a broader 560-cell target-time grid located the operating point".
  (5) B9 rho10: manuscript claimed rho10 60/60 with no artifact -> RAN it: warm 60/60 (p99 417.3-588.4), strict 60/60 (417.3-588.4); committed.
  (6) B9 relocation: forecast_schedule.py TRACE hardcoded /home/gio/tese (imported by the issue-time generator) -> TESE_ROOT/file-relative; SMOKE-TESTED TESE_ROOT=/tmp/relocated redirects TRACE for both forecast_schedule.py and trace_to_two_pool.py.
  (7) factorial driver obsolete final print (missing rho) -> fixed; replay_with_forecast.py docstring "NEXT tick's bin" -> accurate (samples single bin at 4t, no aggregation, starts T0-1min); B6 historical note separates 1.30 joint from 1.24 marginal.
  (8) LAYOUT: tab:ap-manifest "Float too large by 109.6pt" -> converted to longtable (breaks across pages); \usepackage{longtable} added. Build 131pp, 0 undefined, no float-too-large, no longtable errors.
supersedes: the implied live p50 run; "within run noise"; "budgets never bind"; the intro 560-cell factorial; the uncommitted rho10 claim; forecast_schedule.py hardcoded trace; the manifest float overflow
commit:     b7af7f5
Residual (structural, not a defect): eda/ and ai-dynamo/ are external venvs (separate repos in the workspace tree per CLAUDE.md); scripts are env-portable but those interpreters can't be vendored into this repo.

### Round-3g: fix the false "1-7% on every metric" + narrow B3 globally (8th review)  (2026-07-11)
artifact:   none (text/doc/layout fixes over b7af7f5; rho10 already reproduced byte-identical by the reviewer, SHA c8afeb59...)
command:    n/a
feeds:      thesis-wide (this commit). An EIGHTH review caught a number I introduced last round + residual B3 scope:
  (1) MUST-FIX: "within 1-7% on every compared metric" is FALSE (forecast ITL 11.5 vs 9.7ms = 18.6%; reactive replica-sec 7.6%). Replaced at validation.tex:158 with the honest per-metric breakdown: TTFT 1.0-6.8%, replica-sec 5.3-7.6%, ITL verdicts agree (forecast ITL +1.8ms/18.6%, both under the 100ms bound). Also tightened the TTFT-specific "1-7%" -> "1.0-6.8%" at validation.tex:97, closedloop.tex:349 (run-noise -> "directionally, within 1.0-6.8%; single run, not a noise band"), conclusion.tex:47, intro.tex:516.
  (2) "within run noise" (closedloop.tex:349) -> "directionally ... single live run per policy, not a repeated-trial noise band".
  (3) B3 GLOBAL narrowing: abstract EN+PT and conclusion.tex now state the language-pool result is a same-input CONVERSION under a held cursor, NOT a second anticipation experiment (encoder anticipates; language converts). Code docs fixed: replay_with_forecast.py "sampled one control-minute ahead"/"next bin = one past" -> "indexed bin of the held path (samples roughly the current minute, no aggregation, no look-ahead); same-input conversion, not anticipation".
  Residuals: ledger obsolete unsuffixed factorial names -> rho-suffixed; driver docstring p90/rho15 + output filename -> QUANTILE/RHO; appendix live manifest now lists live_runs/{live_fc,live_re,verify_flag}/{planner.log.gz,manager.jsonl,profile_export_aiperf.json}; headline-cascade.md + fix-plan.md "true e2e" banner-marked SUPERSEDED-WORDING; tab:ap-manifest ragged columns + long path split -> worst overfull 63pt -> 45pt. Build 131pp, 0 undefined, no float-too-large/longtable errors.
supersedes: the false "1-7% on every metric"; "within run noise"; the global B3 anticipation implication (abstract/conclusion/code); obsolete factorial filenames; the 63pt manifest overfull
commit:     0ea47f5

### Round-3h: B3 narrowed thesis-wide + provenance/gitignore closeout (9th review)  (2026-07-11)
artifact:   none (text/doc/gitignore fixes over 0ea47f5)
command:    n/a
feeds:      thesis-wide (this commit). A NINTH review: numerical blocker confirmed fixed; B3 still over-implied at the HIGH-LEVEL statements + minor provenance defects. Chose the reviewer-sanctioned NARROWING (option A) over fixing+rerunning the language hook (option B needs the fragile live control-plane rerun and risks shifting an established result mid-defense-prep). B3 GLOBAL: the "each pool on a forecast of its own signal" thesis statement, RQ4, intro closed-loop clause, architecture figure, and conclusion (x2) now consistently distinguish -- vision pool = FORECAST-anticipated (signal forecastable but not rate-visible); language pool = tail-aware CONVERSION under a held cursor (signal rate-visible). Encoder anticipation (the genuine contribution) untouched; language over-claim removed. Minor: conclusion RQ3 "real control plane" -> "with mocked engines" (local to the principal conclusion); appendix live path -> under simulation/results/live51/ (was live51/...); .gitignore now ignores aggregate44_{rho,strict}/*.{jsonl,log} (12 raw JSONLs were untracked-but-unignored, making the driver's comment false); appendix env note now discloses the external eda/ + ai-dynamo venvs as pinned/restorable (versions in tab:ap-env + upstream commits 1e8b9cac/656ac8ca/33a9babe01) with TESE_ROOT relocation; replay_with_forecast.py docstring interval inconsistency (60s interval vs 15s bins) clarified. Build 131pp, 0 undefined.
supersedes: the global "forecast each pool" over-implication (both pools); the RQ3 "real control plane" without mocked-engines; the appendix live path; the false "all intermediates gitignored" claim
commit:     e2995de

### Round-3i: exact rounding + secondary B3 phrases + honest env paragraph (10th review)  (2026-07-11)
artifact:   none (wording/rounding fixes over e2995de); live percentages recomputed from simulation/results/live51/live_runs/{live_fc,live_re}/profile_export_aiperf.json + twin reports
command:    n/a
feeds:      thesis-wide (this commit). A TENTH review: manuscript in accept/minor-revision territory; three wording/rounding sets, no experiments. (1) EXACT ROUNDING (verified from the archived profile exports): reactive TTFT live 3531.4532/offline 3494.7259 = 1.05% -> "+1.1%" (table + "within 1%"->"within 1.1%"); forecast ITL live 11.4696/offline 9.7183 = 18.02% -> "18.0%" (was 18.6%, from rounded cells); TTFT range "1.0-6.8%" -> "1.1-6.8%" at all 5 spots (validation x2, closedloop, intro, conclusion). Verdicts unchanged. (2) SECONDARY B3 phrases narrowed: intro closed-loop clause "language pool's forecast converted"-> "language pool's demand converted"; intro contribution "per-pool forecasts driving worker schedules"-> "the vision pool's forecast driving its encoder worker schedules"; architecture figure CAPTION "a per-pool forecaster converts each pool's signal"-> "a per-pool provisioner maps ... vision by forecast (anticipatory), language by tail-aware conversion of a held signal"; twopool "close the loop with the per-pool forecasts"-> "vision pool on the forecasts ..., language pool on their tail-aware conversion". (3) ENV PARAGRAPH (my round-3h overclaim) toned down: removed "restorable"/"scripts resolve ALL data paths from TESE_ROOT" (false globally); now states no full dependency lock is tracked; 656ac8ca + 33a9babe01 called LOCAL commits (push/archival pending), 1e8b9cac the upstream draft PR; only the "load-bearing issue-time encoder pipeline" is TESE_ROOT-relocatable, older scripts still hard-code paths; fixed nonexistent "dynamo/.venv" -> "ai-dynamo/dynamo/.venv" in the env paragraph AND the manifest caption. Build 131pp, 0 undefined.
supersedes: the rounded-cell percentages (1.0%/18.6%/1.0-6.8%); the 4 secondary B3 forecast-implying phrases; the overclaimed "restorable"/"all paths TESE_ROOT" env paragraph; the root-relative dynamo/.venv path
commit:     d315f31
