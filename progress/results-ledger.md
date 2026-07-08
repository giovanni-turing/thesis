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

### Phase C shape infill  (2026-07-08)
artifact:   collector_artifacts/phaseC_vit_shape_infill/{encoder_attention,gemm}_perf.txt + merged parquets in ai-dynamo/aiconfigurator (AIC commit 656ac8ca, LOCAL — push held)
command:    docker run ... vllm/vllm-openai:v0.22.0 python3 /artifacts/run_infill.py  (465 cases, locked clocks); merge_parquet.py
feeds:      tex/aiconfigurator.tex infill-correction ¶ (7,760/34,710 rows; +4.3%/−5.8%/<1% shifts); every simulation number above
supersedes: interpolated 448 px query path
commit:     48fc43c (thesis side), 656ac8ca (AIC side, local)
