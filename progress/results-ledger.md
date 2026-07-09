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
feeds:      chapter in prep: closed loop — L* table (forecast/p90/ρ15: L*=300 on EVERY window; reactive: burst3 L*=none — fails even at 15 s, burst4/5 L*=45, burst1/steady L*=300; p50 non-viable 16/60); operating-point p99=588.4 everywhere = f(64)+handoff floor (zero queueing)
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
commit:     (this commit)
