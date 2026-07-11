# Independent Verification of the Fabel Committee Review

Verifier: independent tool-equipped fact-checker. Scope: every finding in
`fabel/report.md` (R1–R12, S1–S10), `fabel/adjudication.md` (MF-01…MF-45),
`fabel/cross-check.md`. Method: recomputed artifact values, read the `.tex`
sources and producing code, checked the RTX 5090 spec via WebSearch, read the
ModServe/BurstGPT PDFs, and queried PR #1312 status. All artifact paths absolute.
No file outside `/home/gio/tese/verification/` was modified.

Evidence anchors reused below:
- `f_fourier_stats.json` = `/home/gio/tese/analysis/trace_eda/f_fourier_stats.json`
- grid = `/home/gio/tese/simulation/results/grid/`
- week_matrix = `/home/gio/tese/simulation/results/week_matrix/`
- results_44 = `/home/gio/tese/simulation/results/results_44.jsonl`
- yaml = `/home/gio/tese/collector_artifacts/phase2_system_metadata/rtx_5090.yaml`
- anchors = `/home/gio/tese/collector_artifacts/phaseE_physical_anchor/`

---

## MASTER FINDINGS

### MF-01 — RTX 5090 "419 TFLOP/s dense bf16" is a 2x factual error
Target: aiconfigurator.tex:56-58 (+ rtx_5090.yaml in PR #1312)
Verdict: CONFIRMED
Severity: major (factual)
Evidence: yaml field `bfloat16_tc_flops: 418990000000000 # 419.0 TFLOPS dense bf16, 170 SMs at 2407 MHz boost` and its comment "170 SM x 2407 MHz -> ~419 TFLOPS dense bf16, matching NVIDIA published specs". WebSearch (NVIDIA dev-forum threads "RTX 5090 Peak BF16 Tensor TFLOPS"; HN "5090's theoretical BF16 TFLOPs at just 209.5") confirms: dense BF16 on this GeForce part runs at **209.5 TFLOPS** because BF16 GEMMs use FP32 accumulate, which consumer Blackwell runs at half the FP16-accumulate rate; 419 is the FP16-accumulate (or 2:4-sparse) figure. Internal corroboration recomputed: the tower's per-image GEMM FLOPs = 27 blocks x 784 tokens x 2 x (1152·3456 + 1152·1152 + 1152·4304 + 4304·1152) + 4 projector instances x 196 tokens x 2 x (4608·4608 + 4608·4096) = ~707 GFLOP/image; at the measured N=64 GEMM time 3.69 ms/image (aiconfigurator.tex:263) that is 707/0.00369 = **192 TFLOPS = 92% of 209.5, 46% of 419**. 92% GEMM efficiency is plausible; 46% is not. Ceiling error is confirmed three independent ways.
Dup-hint: 419-TFLOPS ceiling; codex/opus likely overlap

### MF-02 — "12- and 8-hour harmonics exceed the 24-hour fundamental" is false
Target: trace-eda.tex:135-138
Verdict: CONFIRMED
Severity: major (factual), local
Evidence: `f_fourier_stats.json` request-signal `top_peaks_period_gt_10min`: 24 h power = **3892.38**, 8 h = **2202.55**, and no 12 h line appears in the top-8 (smallest listed = 33.6 h at 2038.4, so 12 h < 2038 < 3892). Both overtones are weaker than the 24 h fundamental; 8 h < 24 h and 12 h absent. The text's claim is verifiably false in raw spectral power. (The multi-peaked-day framing is unsupported; a "significance-relative-to-background" claim would be different and is not what is written.)
Dup-hint: spectral harmonics false; codex/opus overlap

### MF-03 — "~3% attention agreement" holds only on the superseded raw slice
Target: aiconfigurator.tex:17, 416-418, 488-489; intro.tex:241-242, 419; conclusion.tex:37
Verdict: CONFIRMED (raw-slice via artifact; infilled 7.3% R-cited)
Severity: moderate (adjudicator downgrade from major is defensible; no verdict depends on 3% vs 7.3%)
Evidence: `collector_artifacts/phaseA_validation/result.txt` ledger: attention 1.300 ms measured vs AIC 1.342 ms -> "MATCH within 3%"; tab:aic-validation (aiconfigurator.tex:389-406) is explicitly labelled "Predictions from the raw slice" (pred 7.822 ms at 448²). The 3.2% is the raw-slice number. The 7.3% infilled figure (1.394 vs 1.300) rests on the local AIC commit 656ac8ca run — I did not re-run the frozen SDK, so R-cited, but the raw-slice scoping is proven and every simulation consumes the infilled slice (aiconfigurator.tex:137, 394 "every simulation consumes the infilled slice").
Dup-hint: raw-slice attention scoping

### MF-04 — ModServe gap statement over-claims against closest competitor
Target: related.tex:86-97
Verdict: CONFIRMED
Severity: moderate
Evidence: ModServe PDF (`/home/gio/tese/papers/`, md mirror) shows ModServe does "stage-aware autoscaling ... autoscaling the stages separately" (l.155-156), routes/scales on image-token load ("fewest pending image tokens", l.168; "scale resources to handle modality-specific bursts", l.910). So the encoder pool IS scaled on a per-modality, content-derived signal, contradicting "none asks what demand signal an encoder pool should be provisioned on" and the "(queue depths, utilization, arrival rates)" parenthetical. Note the thesis already hedges the narrow precedence claim at related.tex:94-97 and grants ModServe "~" per-pool signal in tab:rel-positioning (related.tex:343) — an internal tension the prose over-claim creates. Paper-content characterization is R-cited on arXiv:2502.00937.
Dup-hint: ModServe image-tokens signal

### MF-05 — Forecasting headline rests on a weak, unqualified baseline field
Target: predictors.tex:151-152; tese.tex:48-50
Verdict: CONFIRMED
Severity: moderate
Evidence: The all-20-cells claim is arithmetically true (spot-check of tab:pred-wape: at 1-min every FM < EWMA on req 33.4<35.2, img 52.9<54.2, ctx 43.2<44.7, gen 37.4<41.2; at 1-s img 98.8<146.1). But the baselines are fixed-parameter (predictors.tex:76-79: EWMA α=0.3 single alpha, Holt-Winters α/β/γ=0.3/0.1/0.1, context-capped at TimesFM budget, "never sees two full diurnal cycles"), and predictors.tex:384-390 concedes "a full-history seasonal baseline and per-series tuning would narrow the margins ... which should be read accordingly." No seasonal-naive. The headline (151-152) and abstract carry no such qualifier; the 2–9% relative provisioning edge (153) is the claim at risk.
Dup-hint: weak baseline field

### MF-06 — No statistical uncertainty anywhere in the benchmark chapter
Target: predictors.tex:172-176
Verdict: CONFIRMED
Severity: moderate
Evidence: predictors.tex:173-176 states several bold column wins are "decided by ≤0.1 WAPE point over 167 origins, below plausible sampling variability, with no significance test attached." No CI/bootstrap appears in the chapter, including on the FM-over-EWMA margins the conclusions rest on. V-tex; the fix (block bootstrap over origins on the archived parquets) is cheap.
Dup-hint: no uncertainty/CI

### MF-07 — "Order of magnitude" knee separation not stress-tested vs measured f(N)
Target: twopool.tex:276-281 (companion :126-128)
Verdict: CONFIRMED
Severity: moderate
Evidence: tab:sim-knees (twopool.tex:250) censors the vision steady knee at ≥s=32 = ≥256 img/s under composed cost (4.94 ms/image amortized). Under the chapter's own measured f(N) (~8 ms/image at the cap, aiconfigurator.tex:311 "7.99 ms by the cap"), 2 workers sustain ~2·(1000/8) = 250 img/s, so the s=32 point sits at 256/250 ≈ 102% utilization — i.e. the >16x anchor (32/s=2 language knee) would not survive measured cost, collapsing toward ~8x, exactly as the finding states. twopool.tex:428 concedes the steady head is vision-lean (2.9 vs ~14 img/req). The qualitative "far apart" is robust; the multiple needs conditioning. twopool.tex:126-128's blanket "conservative" is anti-conservative for the separation magnitude (earlier vision saturation shrinks the gap).
Dup-hint: knee multiple not conditioned

### MF-08 — "Failure is information timing, not thrift" over-attributes; deconfounding cell never run
Target: baselines.tex:159-161; closedloop.tex:154-175
Verdict: CONFIRMED
Severity: moderate
Evidence: tab:cl-triad (closedloop.tex:166-174) at burst1/60 s lead: reactive planner best 1,615.5 FAIL, forecast+mean-conversion 1,716.6 FAIL (worse than reactive), forecast+tail-aware 736.3 PASS. So on the 220-min burst1 onset the binding defect is the mean-to-tail conversion, not timing; the {reactive,forecast}×{mean,tail-aware} 2×2 is missing its reactive+tail-aware cell (only 3 of 4 rows exist). p50+tail-aware fails burst3 at 2,164 ms (closedloop.tex:204), and p50+tail-aware passes the week at 828 ms (closedloop.tex:237), making the missing arm plausibly a week-pass — which would reattribute the language-pool week verdict. Timing is the correct diagnosis only for fast onsets (burst3).
Dup-hint: missing reactive+tail cell

### MF-09 — Conclusion "each leans conservative" omits a non-conservative limitation
Target: conclusion.tex:79-89 (tied to twopool.tex:396-402, tese.tex:54-55)
Verdict: CONFIRMED
Severity: moderate
Evidence: conclusion.tex:79-89 enumerates four conservative-leaning limitations (offered-work decode bound, single-stream handoff, eager cost model, sim-only vision loop) and asserts "None reverses the direction ... each leans conservative." twopool.tex:396-400 establishes that under the target-model-consistent 196-tokens-per-image convention "the frames-class prefills would strain even TP2" and calls the burst-window language verdict convention-dependent — a direction that could flip the 0.96x TP2 pass, i.e. non-conservative. intro.tex:489-491 does carry this caveat; the conclusion's blanket statement drops it. The TP1 floor is robust; only the fix is convention-dependent.
Dup-hint: convention-dependence omitted

### MF-10 — Abstract hedging lags body; "both verdicts reproduce on live" over-broad
Target: tese.tex:43-45, 60-61
Verdict: CONFIRMED
Severity: moderate
Evidence: tese.tex:43-44 "On the first public production trace of a multimodal inference cluster" is unhedged, where related.tex:212 and intro.tex:388 write "to our knowledge the first." tese.tex:60-61 "both verdicts reproduce on the live Dynamo runtime" follows the two fleet-cost verdicts (0.27–0.31x encoder, 0.96x language), neither of which was live-validated; validation.tex:133-140 scopes the anchor to one window, two policies, language pool only, mocked engines. What reproduced live is the forecast-PASS/reactive-FAIL pair. Ambiguous and over-broad in the most-read paragraph.
Dup-hint: abstract both-verdicts ambiguity

### MF-11 — Reproducibility manifest omits the validation-anchor chapter
Target: apendice.tex:13-15 (manifest tab:ap-manifest, 84-160; env tab:ap-env, 20-43)
Verdict: CONFIRMED
Severity: moderate
Evidence: Read of apendice.tex: tab:ap-manifest rows cover intro/eda/pred/aic/sim/baselines/closedloop figures+tables and even body-only results (quantile coverage, cap sensitivity, cold start), but there is **no row for tab:val-anchor** (the validation chapter's only table), and neither `simulation/live51/` nor `simulation/results/live51/` appears anywhere in the manuscript body (both exist on disk — confirmed). No `phaseE_physical_anchor/` row. tab:ap-env (33-42) lists driver/CUDA, vLLM, aiconfigurator, ai-dynamo, cuDF/cuML/CuPy, PyTorch, chronos, matplotlib — **no etcd/Prometheus/aiperf or live control-plane build**. Exactly the chapter whose bespoke setup most needs a manifest is uncovered.
Dup-hint: manifest missing val-anchor

### MF-12 — tab:base-tp burst3 row uses C=6, caption specifies C*=7
Target: baselines.tex:115-133
Verdict: CONFIRMED
Severity: minor (adjudicator downgrade from major correct; both C pass/fail identically)
Evidence: grid recompute — burst3 TP2×2 (N2_TP2): C6 p99 = **746.25**, C7 = **845.69**; burst3 TP1×4 (N4): C6 = **1313.8**, C7 = **1314.9**. Table burst3 row reads "1,314 / 746" = the **C6** run (746 is unambiguously C6; C7 is 845.69). Caption (line 119) says "at its static-optimal encoder count," and tab:base-grid gives burst3 C*=7 (baselines.tex:78). A stale pre-infill leftover. R5's proposed replacement (1,314.9 / 845.69; TP2 range 746–792 -> ~763–846; max tail cut 1.76x -> ~1.55x) is arithmetically consistent.
Dup-hint: burst3 row C6-not-C7

### MF-13 — "Sample of the traces" provenance/bias omitted
Target: trace-eda.tex:8-11, 22-29, 450-459
Verdict: CONFIRMED (tex omission); Azure-page wording R-cited
Severity: minor
Evidence: trace-eda.tex:456 flags the by-construction 50/50 split but nowhere states the release is "a sample of the traces"; the exact 500k/500k split (line 31 "exactly 50.0%") is evidence of a constructed sample. The per-request thinning -> Fano understating the cluster's overdispersion (favorable-to-thesis direction) is a valid unstated limitation. The "sample" wording on the official Azure page is R-cited (AzurePublicDataset).
Dup-hint: sample-of-traces provenance

### MF-14 — Frontier quotes Chronos-only 899 ms; loose end is TimesFM 993.8 ms
Target: closedloop.tex:334-348
Verdict: CONFIRMED
Severity: minor
Evidence: week_matrix recompute of `forecast_p90_{model}_rho25_L300.jsonl.stats.json` encoder_delay p99: **chronos 899.32, timesfm 993.83, toto 881.62** ms. Text (338) quotes "899 ms" for the ρ=25 loose end — the Chronos cell; the sweep's actual loose end is TimesFM 993.8 ms (0.6% under the 1 s bound), worker-s 1,331,490/7.74M = 0.172x. Separately, `forecast_p90_chronos_rho15_L300` prov_ws = 2,115,689.6 -> /7.74M = **0.2734x**, which is below the "0.31" low end of the clean range labelled "0.44–0.31x" at closedloop.tex:342 — so "0.27–0.31x ... inside that verified range" is internally inconsistent as written (0.27 < 0.31). All 48 cells still pass.
Dup-hint: 899 Chronos vs 993.8 TimesFM

### MF-15 — "p99 unchanged on every window" overstates; only the SLA verdict is lead-invariant
Target: closedloop.tex:91-92
Verdict: CONFIRMED
Severity: minor
Evidence: results_44 recompute, burst3 / forecast / p90 / ρ=15 across leads: chronos and toto = 588.37 at L∈{15,30,45,300}, but **timesfm L=300 = 621.52** (≠ 588). So p99 is not literally "unchanged" on every window/model; the SLA verdict (all <1000) is what is lead-invariant. Adjudicator's steady24h ρ15->ρ25 (733.6->900) is a rating effect, corroborating that p99 moves. "SLA verdict unchanged, pinned at the floor on the burst windows" is the accurate wording.
Dup-hint: p99-unchanged overstated

### MF-16 — "560 cells, every cell an independent two-pool replay" overstates
Target: closedloop.tex:68
Verdict: CONFIRMED
Severity: minor
Evidence: `results_44.jsonl` = exactly **560 rows**, keys per row = {cell, p99_ms, max_ms, feasible, provisioned_ws, busy_ws, schedule}. **No TTFT/ITL/language metric present** (grep confirms has_ttft=False). p99_ms is encoder-delay only. The per-cell runner grades encoder feasibility; the language simulator is not executed per cell. "Independent replay of the composed trace through the encoder pool" is accurate.
Dup-hint: 560-cell encoder-only

### MF-17 — Reactive L=300 Episodes annotation incomplete
Target: closedloop.tex:309-310
Verdict: CONFIRMED
Severity: minor
Evidence: tab:base-react-enc (baselines.tex:205-212) at ρ=15: reactive L=300 fails burst3 (54,170), burst4 (3,063), burst5 (6,729) — all in-span. tab:cl-aggregate's "Reactive, L=300s" row is annotated "fails burst3" only; should read burst3/4/5. (The L=30 row's "fails burst3" is correct: burst4/5 pass at 588 for L=30.)
Dup-hint: reactive L300 burst3/4/5

### MF-18 — Blanket clock-pinning caption does not hold for the physical anchor
Target: apendice.tex:24-26 (+ aiconfigurator.tex:302-303)
Verdict: CONFIRMED (main); PARTIAL on the 2377–2400 sub-nit
Severity: minor
Evidence: all three `phaseE_physical_anchor/anchor_*.json` record **clocks_locked: false** (including `anchor_sdpa_locked2400.json`). SM reads: flash_attention_2 rows 2385/2392/2400 (before/after 2400); sdpa_5x50 2385/2392; sdpa_locked2400 2377/2377/2385/2385. apendice.tex:24-26 "collection and validation runs pin the GPU clocks (SM 2407 MHz ...)" does not hold for the anchor (unlocked, 2377–2400). PARTIAL on the sub-nit "delivered range is 2377–2400 not 2377–2385": aiconfigurator.tex:302 refers specifically to the *stable-clock re-run* (the sdpa_locked2400 file), whose rows are 2377–2385 — accurate for that run; only the earlier unlocked anchors reach 2400. The clock-invariant ratio band (1.32–1.62) is unaffected.
Dup-hint: anchor clocks unlocked

### MF-19 — Undisclosed reactive-controller parameters + binding 32-worker ceiling
Target: baselines.tex:140-198
Verdict: CONFIRMED
Severity: minor
Evidence: results_44 reactive cells max_workers histogram: value **32 appears in 31 cells** (the [1,32] clamp binds hard). baselines.tex:188 states "workers = ⌈demand/ρ⌉, hysteresis 3 minutes, lead L" but nowhere discloses the [1,32] clamp, the 15 s bin width, or the L=0 replica lead used for the 14-config language experiment. The cap trims the headline cost ratio, so it is load-bearing. (Uncapped reactive reaching 37 on burst3, and t+L availability billing, are R-cited on the code path.)
Dup-hint: 32-cap + params undisclosed

### MF-20 — Intro forecast-accuracy framing one-sided
Target: intro.tex:224-233, 397-408
Verdict: CONFIRMED
Severity: minor
Evidence: intro.tex:224-233 (RQ2) and 397-408 (contribution 2) state "beat every baseline in all twenty cells," "accuracy decays only marginally," "covariates nearly irrelevant," "band is headroom" — but omit the absolute ~53% WAPE on 1-min images (predictors.tex:211), the 2–9% relative EWMA margin (153), the explicit three-way-tie caveat (176-177), and the sub-minute no-skill floor. RQ2 poses "with what accuracy" (intro.tex:227) and never answers in absolute terms.
Dup-hint: intro one-sided accuracy

### MF-21 — "~1.4–1.6x conservative-direction" asserted unscoped in intro
Target: intro.tex:243-245, 474-476
Verdict: CONFIRMED
Severity: minor
Evidence: intro.tex:243-244/474 states the ~1.4–1.6x band as "conservative-direction" without scope. It is conservative for saturation/infeasibility, but aiconfigurator.tex:337-338 shows the same underprice amplifies to a 1.86–2.17x (median 2x) fleet-worker correction at the latency knee, and closedloop.tex:411-417 needs the measured-cost replay to preserve the 0.27–0.31x ratio. The conservatism direction is claim-dependent and should be scoped.
Dup-hint: conservative unscoped

### MF-22 — Load-bearing cold-start measurements only in an intro footnote
Target: intro.tex:94-109
Verdict: CONFIRMED
Severity: minor
Evidence: intro.tex:94-109 (footnote) establishes ~3–5 s serving-ready, 0.11 s O_DIRECT read, 0.13 s host-to-device — figures that justify the encoder lead grid at baselines.tex:49-50 ("above the measured 3–5 s model-side floor"). No body/appendix location states the method (warm/cold cache, framework, repetitions); phaseD_cold_start artifacts exist but the number lives only in the footnote.
Dup-hint: cold-start in footnote

### MF-23 — "Invisible to rate/utilization monitoring" lacks a stated timescale
Target: twopool.tex:333-334 (also 27-28, 310-311)
Verdict: CONFIRMED
Severity: minor
Evidence: recomputed from `simulation/results/sweeps/series/vision_burst1_s1.series.json` (busy_workers_end / 2 workers, 29,940 s): overall busy fraction = **0.287** (matches the "29% mean utilization" claim), **max 1-minute mean busy fraction = 0.90**, max 5-minute = 0.51. An HPA at an 80% target on 1-minute metrics would fire (0.6% of 1-min windows exceed 0.8); the "invisible" claim holds cleanly only at ~5-minute cadence. Name the cadence or weaken to "visible only after the queue has formed."
Dup-hint: monitor cadence unstated

### MF-24 — 588 ms "floor" contradicted by static C=16 row (565 ms)
Target: closedloop.tex:286-293
Verdict: CONFIRMED
Severity: minor
Evidence: tab:cl-aggregate: Static C=16 row p99 = **565** ms; the caption (289-292) calls 588 ms the floor "which every adequately provisioned policy reaches." 565 < 588. Mechanism (an always-on 16-worker fleet dispatches smaller sub-64 batches, so its full-batch forward < f(64)) is inferable but unstated; one sentence resolves it.
Dup-hint: 588 floor vs 565

### MF-25 — Prophet-vs-naive self-contradiction + undisclosed subsample
Target: predictors.tex:187-195, 184-185
Verdict: CONFIRMED
Severity: minor
Evidence: predictors.tex:194 "Kalman (0.811) and Prophet (0.733) trail even naive persistence (0.764)" — 0.733 < 0.764, so lower-is-better WAPE makes Prophet **beat** naive; the sentence is false for Prophet, and "all four sit at or below the classical frontier" (187-188) fails likewise. The 300-of-2,687-origin ARIMA/Prophet 15 s subsample is R-cited (ledger, not text) yet quoted to three decimals.
Dup-hint: Prophet beats naive

### MF-26 — Trace-eda generation-median range contradicted by artifact
Target: trace-eda.tex:348-350
Verdict: CONFIRMED
Severity: minor
Evidence: `e_comprehensive_stats.json` gen_median_by_numimages: **25 images -> 37 tokens, 225 images -> 435 tokens** (both outside "50–140"); also 4 img=140, 361 img=49. Text: "median generation stays at 50–140 tokens across image counts from 1 to 529." Range claim wrong; the independence conclusion (Spearman −0.06) is sound.
Dup-hint: gen-median 37/435 range

### MF-27 — Live-anchor ITL row mixes metric definitions, hides a 2.2x gap
Target: validation.tex:64-67
Verdict: CONFIRMED (tex-side); inter_chunk_latency comparison R-cited
Severity: minor
Evidence: tab:val-anchor forecast ITL row reads live 11.5 vs twin 5.3 ms with Δ "+6.2 ms" — the only absolute-unit entry in a percentage column; 11.5/5.3 = 2.17x. The reviewer's claim that archived `inter_chunk_latency/p99` (5.52/161.8) matches the twin's ITL better than `inter_token_latency` (11.47/150.74) needs the live51 metric dumps (R-cited). Verdicts unaffected (both clear 100 ms).
Dup-hint: ITL mixed units 2.2x

### MF-28 — "Within run noise" asserted from a single live run per policy
Target: validation.tex:93
Verdict: CONFIRMED
Severity: minor
Evidence: `simulation/live51/runs/` contains exactly one `live_fc/` and one `live_re/` directory (plus smoke runs). validation.tex:93 "within run noise" and the +6.8% forecast TTFT delta rest on one run each; no repeated-run noise band is supplied.
Dup-hint: single live run

### MF-29 — 245 s stall and first-tick engine_rps not reproducible from archive
Target: validation.tex:121-126, 84-86
Verdict: CONFIRMED
Severity: minor
Evidence: `simulation/live51/runs/live_fc/planner.log` first throughput tick logs **"Agg: 29.86 rps / 5.71 engine_rps = 6 replicas"** (line 307). The thesis (validation.tex:85) quotes live "29.86 rps / 5.31 engine_rps" — the **5.31 matches the offline twin (5.30), not the archived live log (5.71)**. Parsing all timestamps in live_fc/live_re planner.log gives max inter-line gap of only **10.0 s / 15.0 s** — no 245 s stall present (even below the adjudicator's stated max 120 s). Both sub-claims fail against the archive.
Dup-hint: 245s stall + 5.71 rps

### MF-30 — Trace-eda LRD robustness (single OLS, harmonics in fit band)
Target: trace-eda.tex:315-318
Verdict: CONFIRMED
Severity: nit
Evidence: trace-eda.tex:316-317 fits H over "the sub-diurnal band (10 minutes to 12 hours, clear of the diurnal fundamental)." But f_fourier_stats shows 8 h (2202) and 6 h (2280) harmonic lines fall **inside** the 10 min–12 h band, so the fit is not clear of harmonic structure; only the 24 h fundamental is excluded. Single OLS estimator, no CI, no level-shift stress test. "Reflects scale-free structure rather than the daily cycle" is weakened.
Dup-hint: LRD harmonics-in-band

### MF-31 — GeneratedTokens censoring at 16,384 belongs in Limitations
Target: trace-eda.tex:63-69
Verdict: CONFIRMED (tex); 416-at-cap count R-cited
Severity: nit
Evidence: tab:eda-percentiles (trace-eda.tex:440) max GeneratedTokens = **16,384 = 2^14** — right-censored, which biases the Hill tail-index (trace-eda.tex:65 "Hill ≈1.9"). The censoring is not disclosed in the Limitations section (450-459).
Dup-hint: 16384 censoring

### MF-32 — Fano/seasonality "scale-free" phrasing overstates
Target: trace-eda.tex:127-134
Verdict: CONFIRMED
Severity: nit
Evidence: fig:eda-arrival caption (trace-eda.tex:152) "burstiness is scale-free" and the 938 hourly Fano (130-131) conflate deterministic diurnal variance with stochastic burstiness; the surrounding text (132-134) correctly limits the reactive-control implication, so the caption phrasing is the overstatement. V-tex.
Dup-hint: Fano scale-free

### MF-33 — Silhouette near-tie at k=8 omitted
Target: trace-eda.tex:78-82
Verdict: CONFIRMED
Severity: nit
Evidence: `l_silhouette_scan.json`: k=3 0.3777, k=4 **0.388**, k=5 0.3185, k=8 **0.3871** (argmax_k=4). Text shows only the flattering k=3 (0.378) and k=5 (0.319) comparators; the k=8 near-tie (0.3871 vs 0.388) is omitted. k=4 preferred for parsimony is fine but the tie should be reported.
Dup-hint: k=8 silhouette tie

### MF-34 — Small trace-eda overstatements
Target: trace-eda.tex:411-413, 289-293, 239-246, 15-17
Verdict: CONFIRMED (onset p90 via artifact; "few percent" R-cited)
Severity: nit
Evidence: `i_burst_anatomy_stats.json` onset_minutes: p50 **6.0** (matches "median 6 minutes"), p10 1.7 ("2 minutes"), min 1.0 — but **p90 = 51.6 min is omitted** (289-293 reports only the fast tail). trace-eda.tex:239-246/257 gives R²=0.123/0.12 without the bin width or through-origin definition in text (fit is stated as "forced through-origin," 242). "workspace report" (16-17) is not a citable artifact. The "within a few percent of the global medians" (412) is R-cited on the conditioning artifact.
Dup-hint: onset p90 omitted

### MF-35 — aiconfigurator miscellany
Target: aiconfigurator.tex:167-174, 262-263, tab:aic-fn caption, 286-288, 124
Verdict: PARTIAL (mix of confirmed tex + R-cited)
Severity: nit
Evidence: "windowed-attention structure" (aiconfigurator.tex:261-263) — Qwen3-VL uses full per-image block-diagonal attention (no windows); phaseA_validation/result.txt confirms the AIC graph is plain `encoder_attention(16h x 72d, partial_rotary=0.5)`, so "windowed" is a misattribution (one-word fix) — CONFIRMED as an imprecise term, architecture-detail R-cited. The measured f(N) table (tab:aic-fn, caption "measurement is the HF stack") is HF+SDPA, not the production FlashAttention path — CONFIRMED from result.txt ("HuggingFace eager execution"); caption says "HF stack" but not SDPA-vs-FA2. The [mixed] 164 µs/forward remainder and the fa2 interior-dip 1.25 are R-cited.
Dup-hint: windowed-attention misattribution

### MF-36 — predictors nits
Target: predictors.tex:189-192, 48-52, 306-309
Verdict: CONFIRMED
Severity: nit
Evidence: predictors.tex:191 "trails the best foundation model (0.515) by about a WAPE point" — 0.521 − 0.515 = **0.6** point, not ~1 (cross-check §7.7). The 15 s resolution the loop consumes has no main-text WAPE table (tab:pred-wape shows only 1-min and 1-s columns). Coverage sentences (299-304) state one model's numbers.
Dup-hint: 0.6 not a WAPE point

### MF-37 — twopool nits
Target: twopool.tex:80-84, 103/246, 237-251, 321
Verdict: CONFIRMED
Severity: nit
Evidence: twopool.tex:321 "the window's 7,716 frames-class requests (>64 images each)" silently redefines the Chapter-3 frames class, which is k>10 grids i.e. **≥121 images** (trace-eda.tex:87). >64 images vs ≥121 images are different thresholds. The 235B knee "s=1" is inferred (no s=2 run, 82); knee-table arrow notation (237-251) undefined. V-tex.
Dup-hint: frames-class redefinition

### MF-38 — baselines nits
Target: baselines.tex:93-98, 144-146, 17-19, 46-52
Verdict: CONFIRMED
Severity: nit
Evidence: tab:base-tp (baselines.tex:126-130) has burst1–5 only; **burst6 row absent** though its grid artifacts exist (`grid/llm_burst6_C6_N2_TP2_aic.json` etc. — confirmed present). Unit drift: text (18-19) defines "RTX 5090-class worker-seconds," tab:base-grid column header (74) reads "5090 GPU-h." The "2–4× margin" (146) is R-cited. V-tex.
Dup-hint: burst6 row absent

### MF-39 — closedloop nits
Target: closedloop.tex:54-59, 88-90, 321-322, 324, 108-110
Verdict: CONFIRMED (partial)
Severity: nit
Evidence: closedloop.tex:89 and 133 cite p90 coverage "0.88–0.90 at this cadence," but the calibrated coverage (predictors.tex:299) is a **1-minute** figure while the loop consumes 15 s bins; the 15 s coverage (0.888, per the reviewer's quantile_coverage.json) is not surfaced. "≤4%" cost-spread basis (324) unstated; 0.28/0.31 re-rounding (321-322). V-tex/artifact-adjacent.
Dup-hint: coverage cadence mismatch

### MF-40 — validation nits
Target: validation.tex:25-48, 87-92
Verdict: CONFIRMED
Severity: nit
Evidence: validation.tex:25-48 (Setup) states no testbed/host, no explicit "no GPU executes a forward pass" (only "mocked engine execution" appears later at 139), and no live-run count; the forecast component is "archived Chronos p90 path" (34) — replayed, not produced live — and this is absent from the scope list (133-140). The 4-replica budget clamp (57) forces above-cap agreement. V-tex.
Dup-hint: validation scope gaps

### MF-41 — conclusion nits
Target: conclusion.tex:52-54, 55-56, 83-85, 68-69, 96-97
Verdict: CONFIRMED
Severity: nit
Evidence: conclusion.tex:52-54 "meets the tail SLA on every window at every cold-start lead" drops the ρ=15 qualifier (closedloop.tex:341 shows ρ20/25 drop 3/11 cells). conclusion.tex:55-56 "detects onsets at or before the signal itself" overstates the measured **−105..+210 s** envelope (closedloop.tex:118) — +210 s is *after* the signal. conclusion.tex:83-85 "silicon-validated but eager, a conservative bound" conflates the AIC composition (the optimistic bound the sims use) with the eager whole-tower measurement (the pessimistic bound). V-tex.
Dup-hint: rho15 drop + onset envelope

### MF-42 — related citation glosses
Target: related.tex:205-206 (+ :142-145, :168-171, :54-56, :9-11, :145-148, :206-208)
Verdict: CONFIRMED (BurstGPT); others R-cited
Severity: nit
Evidence: BurstGPT PDF (`papers/2401.17644...`, md l.64/200): "over 213 days," "8.69 million traces." related.tex:204 says "BurstGPT's year-long trace" — 213 days ≈ 7 months, not a year. The SageServe "~25% over reactive," ServeGen "per category," ModServe "GPU-hour savings," WarmServe "five-minute" glosses are R-cited on their papers.
Dup-hint: BurstGPT 213 days

### MF-43 — "Every window at every lead" drops the in-span qualifier
Target: intro.tex:253-263, 451; conclusion.tex:53
Verdict: CONFIRMED
Severity: minor
Evidence: intro.tex:451 "every window at every lead from 15 to 300s" and conclusion.tex:53 "on every window at every cold-start lead" drop "in-span"; burst2/6 fall in the 1.4-day forecast-context reservation and are never graded by a forecast policy (closedloop.tex:51-52, 399-404; trace-eda.tex:176-179). closedloop.tex correctly scopes "in-span"; the intro/conclusion do not.
Dup-hint: in-span qualifier dropped

### MF-44 — "Upstreamed" overstates the PR status
Target: tese.tex:50-51; intro.tex:413-418; aiconfigurator.tex:109-116; conclusion.tex:37
Verdict: CONFIRMED
Severity: minor
Evidence: `gh pr view 1312` -> state **OPEN**, isDraft **false**, mergedAt **null**. tese.tex:51 "upstreamed to NVIDIA's aiconfigurator" overstates an open, unmerged PR; and aiconfigurator.tex:109 "contributed upstream as a draft pull request" is now itself stale (no longer draft). The infill feeding every result is local-only commit 656ac8ca (apendice.tex:170 "push pending"). "Contributed upstream (PR #1312, under review)" is the accurate phrasing.
Dup-hint: upstreamed vs open PR

### MF-45 — "Identically informed" bundles anticipation with headroom
Target: tese.tex:58; baselines.tex:186-187; closedloop.tex:34-38
Verdict: CONFIRMED
Severity: minor
Evidence: closedloop.tex:36-38 itself concedes the reactive strawman "reads the trailing observed point rate (quantile ignored) rather than the p90 forecast band; the raw head-to-head therefore bundles anticipation with headroom, and the two dials are separated by the p50-forecast and lead-invariance ablations." The abstract's "identically informed reactive controller" (tese.tex:58) is fair only given the ablations; flag "same signal, same actuation" at first use.
Dup-hint: identically-informed bundling

---

## REQUIRED REVISIONS (map to MFs; verified as above)

### R1 — Correct RTX 5090 BF16 throughput + consequences
Target: aiconfigurator.tex:56-58; rtx_5090.yaml; intro.tex:297-298
Verdict: CONFIRMED (= MF-01)
Severity: major
Evidence: See MF-01 (419 -> 209.5 dense BF16 FP32-accumulate, three-way corroborated). The ~5.9x SOL motivation figure (aiconfigurator.tex:35-36: 0.0061 predicted vs 0.0358 measured unlocked) mixes the 2x-inflated ceiling with an unlocked-clock measurement; halving the ceiling roughly doubles the SOL latency and using the locked measurement moves the ratio toward the review's ~3.4–3.8x — direction and magnitude confirmed analytically, exact restatement R-cited on the SDK SOL path.
Dup-hint: 419 ceiling propagation

### R2 — Correct false spectral-harmonic claim
Target: trace-eda.tex:135-138
Verdict: CONFIRMED (= MF-02)
Severity: major
Evidence: See MF-02.
Dup-hint: harmonics false

### R3 — Scope "~3% attention agreement" to raw slice
Target: aiconfigurator.tex:17,416-418,488-489; intro.tex:241-242,419; conclusion.tex:37
Verdict: CONFIRMED (= MF-03)
Severity: moderate
Evidence: See MF-03.
Dup-hint: 3% raw slice

### R4 — Correct abstract over-broad/unhedged claims
Target: tese.tex:43-45, 60-61
Verdict: CONFIRMED (= MF-10)
Severity: moderate
Evidence: See MF-10.
Dup-hint: abstract hedging

### R5 — Fix tab:base-tp burst3 row to C*=7
Target: baselines.tex:115-133, 96-98
Verdict: CONFIRMED (= MF-12)
Severity: minor
Evidence: See MF-12; proposed values (1,314.9/845.69; TP2 range ~763–846; tail cut ~1.55x) recomputed consistent.
Dup-hint: burst3 C6/C7

### R6 — Rewrite ModServe gap statement
Target: related.tex:86-97
Verdict: CONFIRMED (= MF-04)
Severity: moderate
Evidence: See MF-04.
Dup-hint: ModServe signal

### R7 — Qualify forecasting headline + add uncertainty
Target: predictors.tex:151-152, 172-176, 187-195, 184-185; tese.tex:48-50
Verdict: CONFIRMED (= MF-05, MF-06, MF-25)
Severity: moderate
Evidence: See MF-05/06/25.
Dup-hint: baseline scope + CI

### R8 — Resolve language-pool attribution / missing cell
Target: closedloop.tex:154-175; baselines.tex:159-161
Verdict: CONFIRMED (= MF-08)
Severity: moderate
Evidence: See MF-08.
Dup-hint: reactive+tail cell

### R9 — Reconcile conservatism claim with convention-dependent verdict
Target: conclusion.tex:79-89; twopool.tex:26-28, 441; tese.tex:54-55
Verdict: CONFIRMED (= MF-09)
Severity: moderate
Evidence: See MF-09.
Dup-hint: convention-dependence

### R10 — Condition "order of magnitude" knee separation
Target: twopool.tex:276-281, 126-128
Verdict: CONFIRMED (= MF-07)
Severity: moderate
Evidence: See MF-07.
Dup-hint: knee multiple

### R11 — Restore reproducibility manifest for validation anchor
Target: apendice.tex:13-15, 24-26
Verdict: CONFIRMED (= MF-11, MF-18)
Severity: moderate
Evidence: See MF-11, MF-18.
Dup-hint: manifest + clock caption

### R12 — Tighten closed-loop summary sentences
Target: closedloop.tex:91-92, 334-348, 68, 309-310
Verdict: CONFIRMED (= MF-14, MF-15, MF-16, MF-17)
Severity: minor
Evidence: See MF-14/15/16/17.
Dup-hint: closedloop wording

---

## SUGGESTIONS (map to MFs)

- **S1** (in-span qualifier) = MF-43 — CONFIRMED, minor.
- **S2** (PR/upstream status) = MF-44 — CONFIRMED, minor.
- **S3** ("identically informed") = MF-45 — CONFIRMED, minor.
- **S4** (reactive params + 32-cap + t+L billing) = MF-19 — CONFIRMED, minor.
- **S5** (588 vs 565 floor) = MF-24 — CONFIRMED, minor.
- **S6** (cold-start out of footnote) = MF-22 — CONFIRMED, minor.
- **S7** (sample provenance, 16384 censoring, k=8 tie, R² bin width) = MF-13, MF-31, MF-33, MF-34 — CONFIRMED (tex-side/artifact), nits.
- **S8** (ITL metric, "within run noise," 245 s stall, testbed) = MF-27, MF-28, MF-29, MF-40 — CONFIRMED (MF-29 strongly: 5.71≠5.31 and no 245 s gap).
- **S9** (windowed-attention, HF+SDPA caption, frames-class threshold, knee arrows, burst6 row) = MF-35, MF-37, MF-38 — CONFIRMED (partial on arch detail).
- **S10** (rho=15 qualifier, onset envelope, eager/composition conflation) = MF-41 — CONFIRMED, nits.

---

## SUMMARY

Findings verified: 45 master findings (MF-01…MF-45) + 12 required revisions (R1–R12)
+ 10 suggestions (S1–S10). **Every finding reproduced** against the sources or
artifacts. No finding was DENIED. Two carry a PARTIAL flag on a sub-point only:
MF-18 (the "2377–2400" sub-nit is defensible for the specific stable re-run the
tex describes; the core clocks_locked=false is fully confirmed) and MF-35 (a mix
of confirmed tex terms and R-cited architecture detail). Items resting on external
papers or local-only SDK state (MF-03 infilled 7.3%, MF-04/42 paper glosses,
MF-19/27 code-path specifics) are flagged R-cited but their tool-checkable
components all held. The adjudicator's severity downgrades (MF-03, MF-12) are
sound: no verdict moves.

Counts: CONFIRMED 57 / PARTIAL-subpoint 2 (MF-18, MF-35) / DENIED 0.
By severity (adjudicated): Major 3 (MF-01/02/03), Moderate 8 (MF-04…MF-11),
Minor 18, Nit 13 + cross-cutting MF-43/44/45.

Top 5 confirmed (strongest tool evidence):
1. **MF-01 / R1** — 419 TFLOPS is a 2x error. yaml ships `418990000000000` as
   "dense bf16"; WebSearch confirms dense BF16 FP32-accumulate = 209.5 TFLOPS on
   RTX 5090; the thesis's own N=64 GEMM recomputes to ~192 TFLOPS = 92% of 209.5
   but 46% of 419. Ships in an open public PR — external correction needed.
2. **MF-02 / R2** — Spectral claim false. f_fourier_stats request powers:
   24 h = 3892 > 8 h = 2203, 12 h absent from the top-8. Overtones are weaker
   than the fundamental; the multi-peaked-day statement is unsupported.
3. **MF-14 / R12** — Frontier is Chronos-only. Recomputed rho25/L300 encoder p99:
   Chronos 899.3, TimesFM 993.8, Toto 881.6; text quotes 899. And rho15/L300 =
   0.273x sits below the "0.44–0.31x" clean-range low end as written.
4. **MF-12 / R5** — tab:base-tp burst3 row is the C=6 run (TP2 746.25 = C6, not
   C7's 845.69; TP1 1313.8 = C6), while the caption specifies static optimum C*=7.
5. **MF-29 / S8** — Live anchor not reproducible as stated: live_fc planner.log
   first tick logs 5.71 engine_rps (thesis quotes 5.31, which is the offline
   twin's value), and no 245 s planner stall exists in the archive (max log gap
   10–15 s). Plus MF-23: recomputed max 1-minute busy fraction = 0.90 (mean 0.287),
   so the "invisible to utilization monitoring" claim needs a stated cadence.
