# Extractor-flagged issues (pre-verification)

## aiconfigurator  (111 claims, 46 headline)

Read all 527 lines of /home/gio/tese/tex/aiconfigurator.tex. Extracted 111 quantitative claims (46 headline, 49 supporting, 16 incidental) spanning 109 distinct lines.

THREE INTERNAL INCONSISTENCIES FOUND:
1. Line 244 (fig:aic-fn caption) says ratio "rises to 1.62x at N=64 ... easing to 1.43x at the largest dispatch", but line 281 and tab:aic-fn both treat N=64 AS the dispatch cap with ratio 1.62. Caption contradicts table/body: either the figure extends past N=64 (contradicting "the 64-image dispatch cap") or 1.43 is stale. HIGH PRIORITY.
2. Line 444 says unfused elementwise + projector layernorms = "~0.25 ms" at 448^2 batch 1, while line 293 says unfused elementwise = "1.18 ms per image" at N=1. Same stack, same shape, ~5x apart.
3. Line 294 quotes DeepStack gather as 0.26 ms at N=1; line 450 quotes 0.248 ms for the same shape. Likely rounding but presented as independent measurements.

ARITHMETIC CHECKS THAT PASS: 11.360=9.624+1.736; 1.736/11.360=15.28%~15.3%; (1.342-1.300)/1.300=3.23%~"strictly 3.2%"; 9.624-0.459-0.248=8.917~8.92; 0.459/9.624=4.77%~4.8%; 168.6/182=92.6%~92%; 32768*65536*2=2^32 bytes=4GiB; 784/4=196 vision tokens; 5120/4096=5/4; 43.58/6=7.263~7.26; 511.23/64=7.988~7.99; 11.30/7.26=1.556~1.56. Every ratio cell in both tables reproduces from its own measured/composed pair.

VERIFIABILITY SPLIT: simulation-side claims (encoder-delay p99 589/606/644 ms, 120/120 rho=20 feasibility grid, burst5 8-vs-16 workers, six windows at 6-8 workers, 3.1% extrapolated trace requests) map cleanly onto provenance.encoder_run_summary, factorial_cell, measured_request. Silicon-side claims (dataset row counts 7679/34326, 7760/34710, 7770/34775; all kernel-ledger decompositions; the ~3% attention agreement; the ~17% unlocked-clock inflation; the ~5.9x SOL factor) have no provenance-DB home -- they live in AIC data files and collector artifacts. ~40 of 111 claims, including 12 headline ones, are marked UNVERIFIABLE against the given schema. provenance.collector_fn is the key bridge: every f(N) value in tab:aic-fn plus the vLLM anchor residuals (-2.2/+11.3/+5.5% at N=8/32/64), the dense-sweep max +12.7% at N=52, and +21.8% at N=512 should all be checkable there. Recommend concentrating the verification pass on collector_fn.

NUMBERS A REVIEWER WOULD MOST LIKELY CHALLENGE: the 12.8% vLLM-vs-composition bound (asserted 5 times: lines 248, 262, 317, 352, 517) resting on a single max-deviation value of +12.7% at N=52 -- the bound is only 0.1pp above the observed max, so any re-run that shifts N=52 breaks the headline claim. Also the 92%-of-182ms attribution at N=64 (line 296), and the 1.45 vs 1.38 N=1 ratio reconciliation (lines 233-236) which depends on both prediction and measurement moving simultaneously.

---

## apendice  (59 claims, 14 headline)

Read all 383 lines of /home/gio/tese/tex/apendice.tex. Numeric density is concentrated in the engine-sensitivity appendix (lines 110-242); the manifest longtable (244-373) is mostly paths, with numbers only where it encodes experiment design (cell counts, rho levels, lead times, C*).

INTERNAL INCONSISTENCIES FOUND (recomputed directly from tab:app-engine, lines 148-151):

1. FIFO cap contradiction. Line 168 (fig:app-engines caption): "the dotted line the FIFO cap ($N{=}64$)". Line 198: "growing to $+21.8\%$ only past the FIFO cap at $N{=}512$". Both cannot hold. N=512 is the sweep endpoint (line 205: "dense $N{=}1$--$512$ sweep"), and lines 116/196 define the serving regime as N<=64, so line 198's "at $N{=}512$" appears to be a text error. This is load-bearing: the +21.8% drift is excused as being outside the pool's batching regime.

2. HF-SDPA upper ratio. Line 180 asserts HF-SDPA "runs $1.36$--$1.61\times$ above the composition". Table ratios: 11.3/8.2=1.378, 58.7/43.1=1.362, 253.8/160.2=1.584, 511.6/316.4=1.617 -> upper bound rounds to 1.62, not 1.61.

3. vLLM residual at N=8. Line 186 states "$-2.2\%$" at N=8, but the table gives 42.2/43.1-1 = -2.09% (-2.1%). Related: the same sentence bounds agreement at "within $11.4\%$" while the largest residual it lists is +11.3% (table: 178.3/160.2-1 = +11.30%); the 11.4% figure presumably comes from the dense sweep rather than the anchor shapes, but as written it is unsourced.

4. torch.compile speedup range. Line 192 asserts "$1.2$--$1.4\times$"; table HF-SDPA/compile gives 11.3/10.1=1.12 at N=1, below the stated lower bound (1.20/1.36/1.38 at N=8/32/64 are in range). Range appears to be silently scoped to N>=8.

5. Grid extrapolation threshold. Line 237's "past $N{\approx}42$" follows from the GEMM m-grid (32768/784 = 41.8), not from the attention grid mentioned immediately before it (batch 64). The arithmetic is right but the sentence attributes it to the wrong grid.

CONSISTENT / CHECKED OK: all four vLLM/AIC ratio cells (0.98, 0.98, 1.11, 1.05) reproduce from the table; HF-FA2 1.25x@N=8 and 1.47x@N=64 reproduce; 784*512 = 401408 checks out; the two 0.62x cost-ratio mentions (lines 11, 333) agree; the clock band 2377-2400 MHz is stated consistently at lines 30, 129 and 165.

WEAKEST DB COVERAGE: GPU clock telemetry, all software versions in tab:ap-env, artifact file counts, and the upstream PR/commit references have no column in the provenance schema — marked UNVERIFIABLE. The two most reviewer-exposed numbers that DO have DB backing are the encoder-delay p99 pair 606 ms / 589 ms (line 210, encoder_run_summary) and burst5 C* = 8 (line 301, factorial_cell), the latter explicitly flagged in-text as a correction superseding grid_summary.json.

Software-version table cells were included as "incidental" claims rather than dropped, since the task asked for every table cell; they can be filtered on metric='software_version' if unwanted.

---

## apendice_ecosystem  (19 claims, 3 headline)

Read all 168 lines of /home/gio/tese/tex/apendice_ecosystem.tex. This appendix is almost entirely qualitative/architectural prose describing the five ai-dynamo repositories; it contains NO latency, throughput, GPU-hour, cost, accuracy, or feasibility numbers, and its one table (tab:app-ecosystem) has no numeric cells. The numeric tokens present are: component/item counts, two dynamo release dates, a cadence claim, and four software version pins. All 19 are recorded rather than sampled.

ONE REAL DEFECT FOUND (headline, line 126): "\texttt{aiperf} 0.11.0 (Table~\ref{tab:ap-env})" cross-references tab:ap-env, but that table (tex/apendice.tex:35-48) has NO aiperf row. Its eight rows are NVIDIA driver/CUDA, vLLM container, aiconfigurator, ai-dynamo, cuDF/cuML/CuPy, PyTorch/transformers, chronos-forecasting, matplotlib. So the aiperf 0.11.0 pin is unsupported by the table it cites. Fix: add an aiperf row to tab:ap-env (it IS a load-bearing version — aiperf is the client for the Phase-4.3 live_fc/live_re closed-loop runs) or drop the cross-reference.

Cross-checks that PASSED:
- ai-dynamo "1.2.1 (wheel) / 1.3.0 (source)" matches tex/apendice.tex:42 verbatim.
- aiconfigurator "0.10.0 (editable, data branch)" matches tex/apendice.tex:41 verbatim.
- "roughly twelve-month 0.x line" is arithmetically consistent with the stated 2025-03-17 -> 2026-03-13 span (11 months 27 days).
- "the missing patch-embedding operator, large-batch GEMM and attention coverage, and a collector OOM fix" = 3 items, matching the 3 fix commits named in tex/apendice.tex:70-72 (656ac8ca infill, 12306db5 collector fix, 492a3444 large-batch ViT coverage).
- RTX 5090 silicon-validation hardware matches the benchmark node in tab:ap-env (apendice.tex:39).
- tab:app-ecosystem body rows = 5 ai-dynamo components, matching the "five repositories" claim at lines 13/70/85; the "engines" row sits below a \midrule and is correctly excluded from the count.

STILL TO VERIFY OUTSIDE THE DB (not checkable in provenance schema, flagged in db_check): the two dynamo release dates (v0.1.0 = 2025-03-17, v1.0.0 = 2026-03-13) and the "roughly monthly" minor cadence. These need `git -C /home/gio/tese/ai-dynamo/dynamo tag -l --sort=creatordate --format='%(refname:short) %(creatordate:short)'`. I did not run it because the checkout's tag set may lag upstream and a stale local mirror would give a false negative; recommend the parent verify against upstream GitHub releases.

Also note the file header (lines 2-7) says this appendix is a DRAFT "NOT wired into tese.tex yet" — worth confirming whether it is now included, since none of its claims will be reviewed if it never renders.

---

## baselines  (151 claims, 73 headline)

File is 261 lines, read in full. 151 claims (73 headline, 75 supporting, 3 incidental) covering: chapter SLA thresholds; protocol constants (window margins, lead sweeps, hysteresis, 1.4-day forecast-context split, 3-5 s model floor); all 7 rows x 5 numeric columns of tab:base-grid; the stage-conditional C* revision and its 5090-hours; tab:base-tp (5 windows x 3 columns); tab:base-ladder (4 rows x 3 columns); tab:base-react-enc (7 windows x 4 leads + L*); and every inline prose number in sec:base-static, sec:base-reactive-llm, sec:base-reactive-enc and sec:base-summary.

INTERNAL-CONSISTENCY FINDINGS (arithmetic re-derived during extraction):

1. LIKELY WRONG NUMBER (line 108). Prose says TP1x4 fails every burst window with "TTFT p99 1{,}314--1{,}331" ms, but the minimum in tab:base-tp is 1,315 (burst3, line 141). Values present: 1315, 1316, 1317, 1318, 1331. The lower bound should read 1,315 unless burst6 (absent from tab:base-tp) supplies 1,314 — which would be a second problem, since the prose claims TP1x4 fails "every burst window" while the table lists only burst1-burst5.

2. ROUNDING INCONSISTENCY (line 93). Stage-conditional 5090-hours "58.2/3.6/25.2/10.9" for burst1/3/4/6. First three reproduce exactly from tab:base-grid spans (8.32x7=58.24, 0.45x8=3.60, 3.15x8=25.20), but burst6 is 1.37x8=10.96, which rounds to 11.0, not 10.9 — looks like truncation, or the span/C* differs from what the table implies.

3. Line 171 "TTFT p99 stays pinned at 1{,}616--1{,}620" vs tab:base-ladder values 1615.5/1616.0/1616.6/1619.6. Defensible as rounding (1615.5 -> 1616, 1619.6 -> 1620) but the stated lower bound is above the actual minimum.

4. Target-ladder base target mismatch: line 159 states the planner's shipped targets are 500/50 ms, but the ladder (line 169, tab:base-ladder) starts at 400/40. Not arithmetically wrong, but the "tightening from" baseline is not the previously stated operating point.

VERIFIED-CONSISTENT (no action): all 14 GPU-hour cells of tab:base-grid reproduce as span x C* (5090) and span x 4 or span x 2 (H100); all 5 tail-cut ratios in tab:base-tp reproduce from their row (e.g. 1318/763=1.727 -> 1.73); the 4x/2x calm-day overprovisioning follows from 8/2 and 4/2; the 10% spend increase matches 18.6 -> 20.4 (9.7%); burst3's "9.5--54 s" matches 9481 and 54170 ms; peak "337--370 img/s" is consistent with burst6's 337.

UNVERIFIABLE flags: 1 claim — the 3-5 s model-side cold-start floor (line 51) has no backing table in the listed provenance schema.

Note on db_check style: static-grid cells point at provenance.factorial_cell (config_c/feasible/provisioned_ws), language tails at llm_run_summary joined to runs on (window_name, tp, n_replicas), reactive-encoder cells at encoder_run_summary joined to runs on (window_name, lead_s, rho), all with is_current filters.

---

## closedloop  (136 claims, 81 headline)

671-line chapter read in full; 136 claims covering 419 numeric literals; 81 headline, 45 supporting, 10 incidental; 13 marked UNVERIFIABLE. All table cells (tab:cl-ewma 4 rows, tab:cl-triad 3 rows, tab:cl-aggregate 7 rows) and both figure captions (fig:cl-framework-diff, and the two table captions) extracted cell-by-cell.

TWO INTERNAL INCONSISTENCIES FOUND:
(1) Service floor quoted as 588 ms in sec:cl-matrix (lines 79, 91, 114, 121) and tab:cl-aggregate (lines 452, 468-469, 483, 499, 522, 531, 543, 593, 627) but as 589 ms in tab:cl-ewma (lines 224, 241, 254, 265-268) and the vLLM reprice discussion (lines 606, 621). Consistent with 316.4+272=588.4. Needs reconciliation or an explicit statement that these are distinct harnesses.
(2) Line 337 claims a "~14% margin above the binding knee" as retained policy, but the quoted validation boundary is burst4 scale 6.22 fails / 7.0 passes -> 7.0/6.22 = 12.5%, not 14%. Also 10.07/1.44 = 6.99, which would make the margin ~0%. Arithmetic does not reproduce 14% from any pair of quoted numbers.

ARITHMETIC CHECKS THAT PASS: 2.41/3.87=0.623 (0.62x); 2.61/3.87=0.674 (0.67x); 1.67/3.87=0.431 (0.43x); 0.97/3.87=0.251 and 0.98/3.87=0.253 (both 0.25x); 316.4+272=588.4; (12-1)*15=165; 518.6/537.4=0.965 (0.96x); 625/537.4=1.163 (1.16x); 641/537.4=1.193 (1.19x); 1-319.9/518.6=38.3% (38%); 3100/749601=0.41% ("under half a percent"); 0.62-0.48=0.14; (647-644)/644=0.47% ("<0.5%"). Design-size checks: factorial 5x3x4=60; reactive 5x4=20 (matches "13-14 of 20"); encoder p50 week 3x4x4=48; full week sweep 3x2x4x4=96 (=48 p50 + 48 p90). Cross-reference checks: burst3 reactive 3,495 ms and p50 2,164 ms and p90 651 ms agree between sec:cl-llm (lines 350-356) and fig:cl-framework-diff (lines 415-417); tab:cl-triad 736.3 ms agrees with the 736-757 ms range at line 282; reactive range "1,615-3,495" (line 366) agrees with tab:cl-triad 1,615.5; Chronos rho-frontier 0.89/0.62/0.48/0.40 (line 242) agrees with lines 522 and 529.

UNVERIFIABLE CLUSTER: the detector/mechanism paragraph (lines 153-178, plus line 209) — threshold-crossing leads (225 s, 345 s, 105 s), false-alarm counts (zero on calm day), per-day crossing rates (70-102 vs <=1), and detection lags (55 min to 4 h) — depends on the riders44/ detection artifact and has no corresponding column in the provenance schema as described. Also unverifiable: the forecast-hook sampling implementation detail (line 293), forecast inference cost "~seconds per tick" (line 564), the ~1.6 MB per-image handoff payload (line 584, a platform model parameter), and Chronos-2 120M / Toto-2.0 20x-larger parameter counts (line 509, a published model-card fact).

---

## conclusion  (35 claims, 24 headline)

Read all 140 lines of /home/gio/tese/tex/conclusion.tex. It is a summary chapter (no tables, no figures), so every number is a restatement of a body-chapter result — which makes it the highest-value consistency-check surface in the thesis. Flags for the verification pass:

(1) DENOMINATOR MISMATCH on the headline cost ratio. Line 81 says "0.62x the deployable static encoder fleet's provisioned worker-time"; line 95 restates it as "roughly two-thirds of the best static encoder fleet's GPU-time". "deployable static" vs "best static" may be different denominators, and 0.62 rounds to ~five-eighths, not two-thirds. Verify both against v_cost_frontier_dual with the same baseline.

(2) COUNTERINTUITIVE DIRECTION at line 84: 0.62x under a warm-pool readiness model but 0.59--0.62x under STRICT RE-WARM. Strict re-warm should provision more, not less. Either the range is mislabeled or the readiness column semantics are inverted. Check factorial_cell.readiness.

(3) ARITHMETIC on lines 24-25: "6--8 encoder workers ... against 2 workers ... a 4x/2x overprovisioning". 4x holds only at the 8-worker end (8/2); the 6-worker end gives 3x. The stated ratio silently picks the max.

(4) REPEATED LITERALS — verify all instances trace to one computation: 12.8% appears 3x (lines 41, 104, 121); 588 ms 2x (68, 102); 1.4--1.6x 2x (42, 106); 15 s appears as both a lead bound (60) and a detection threshold (65), different quantities sharing a value.

(5) SPAN TENSION: line 98 says "one seven-day production trace" but line 79 grades over a "5.60-day covered span" (~80%). Recent commits in this repo claim "full-trace coverage GUARANTEE — all 1,000,000 requests"; reconcile coverage/coverage_meta against which of those two numbers the conclusion should assert.

(6) THREE CLAIMS ARE LIKELY UNVERIFIABLE from the listed provenance schema — R^2=0.12 / 0.65 (line 17-18), Jaccard 0.02 (line 19), and the 15-second detection-lag analysis (line 65) — because the schema exposes no r2, jaccard, or detection-lag column. They must be recomputed from measured_request + windows, or backed by a trace-characterization artifact outside the DB. Same for the >=100 Gbps fabric assumption (line 103), which is analytic by construction.

(7) Two non-numeric but load-bearing verdict claims were recorded with empty numbers arrays (ITL p99 pass/fail agreement, line 54; reactive aggregate-vs-per-episode dissolution, line 85) because a reviewer would challenge them as results even though no literal appears.

Excluded per instructions: "four research questions" (line 12), "Three extensions remain" (line 118), "A fourth" (line 127) — document structure, not measurements. Also excluded "an order of magnitude apart" (line 19-20), which asserts a magnitude but contains no numeric literal.

---

## intro  (82 claims, 43 headline)

Read all 558 lines of /home/gio/tese/tex/intro.tex. 82 claims extracted (43 headline, 30 supporting, 9 incidental), spanning lines 38-539. No tables in this chapter; one figure (fig:intro-arch) contributed 6 claims from its TikZ node labels (1M/7 days, three SLO bounds, 196x4096 handoff payload).

Cross-reference / consistency observations for the verification pass:

1. R^2 restatement: line 147 gives R^2=0.123 for the image-rate constant-fraction model; line 406 restates it as R^2=0.12. Rounding is consistent but both should trace to the same EDA artifact.

2. Repeated numbers that must agree across the chapter (verify once, check all sites):
   - 588 ms encoder floor: lines 265, 479, 514
   - 734 ms calm-day bound: lines 266, 480
   - 0.62x cost ratio: lines 271, 481, 514
   - 15-165 s lead range: lines 264-265, 479
   - 29% encoder mean utilization: lines 179, 461
   - 12.8% / 1.4-1.6x engine figures: lines 249 and 510 (identical restatement in Scope)
   - ~3% dominant-operator agreement: lines 248, 443
   - 20 forecast cells / 3 foundation models: lines 233, 427 (and the 4 signals x 5 resolutions grid on line 426 must multiply to 20)
   - 50% text-only: lines 131, 415, 501
   - 7-day / 1M-request trace: lines 128, 337, 501

3. Derived-consistency checks a reviewer would run:
   - Line 153-154: 370 img/s "nearly sixteen times its weekly mean" implies a weekly mean image rate of ~23 img/s. Verify that against the trace.
   - Line 155: burst-minute request peak "below 4.5" vs weekly p99 "4.35" -- only 3.4% above p99, so "barely above" is defensible but tight.
   - Line 133-134: 2.7% of requests carrying 81.2% of image volume implies a ~140x mean-image-count ratio between frames and non-frames classes.
   - Line 431: 21.4M archived rows should equal (models x signals x resolutions x origins x horizons); worth reconciling against the 20-cell grid and 9 quantiles.
   - Line 476: the 560-cell target-time grid vs the "windows x models x realizable leads" issue-time factorial on lines 474-476 -- two different grids, easy to conflate.

4. Possible reviewer challenge (not an error, but scoped narrowly in the text): lines 536-538 claim live-vs-simulated agreement "within 1.1-6.8%", but that bound is explicitly TTFT-only. The ITL pair for the forecast policy (11.5 vs 9.7 ms) differs by ~18.6%, well outside the quoted band; the reactive pair (150.7 vs 152.7 ms) differs by ~1.3%. The text handles this by claiming only directional agreement for ITL, but the 18.6% gap is not stated anywhere.

5. Claims marked UNVERIFIABLE in db_check (8 total): the footnote startup/readiness microbenchmarks (3-5 s readiness, 1.15 GB / 0.11 s / 0.13 s checkpoint load, the ~5 s orchestration-attribution threshold), the model-architecture facts (576M params, 8B/32B/235B shared tower, 4096-d and 5120-d projectors with 5/4 scaling, 196x4096 handoff payload), and the upstream PR number (ai-dynamo/aiconfigurator #1312, verifiable via gh but not in Postgres). These have no backing table in the provenance schema and need artifact-level or external verification.

6. Several EDA statistics (R^2, CV^2, Jaccard, Fano, Hurst, ACF half-life, burst-onset durations) have no dedicated provenance table in the listed schema -- db_check points at recomputation from provenance.measured_request minute aggregates plus provenance.windows for episode bounds. If a trace_eda_metrics table exists but was not listed, those db_checks should be retargeted.

---

## predictors  (65 claims, 33 headline)

Read all 428 lines of /home/gio/tese/tex/predictors.tex. 65 claims: 33 headline, 24 supporting, 8 incidental. Table tab:pred-wape is captured as 8 row-level claims (one per model, each carrying all 8 cells for the 1-min and 1-sec blocks = all 64 cells); tab:pred-cov as 2 row-level claims (all 10 cells). Both figure captions (fig:pred-horizon, fig:pred-band) are covered.

Internal-arithmetic cross-checks already performed (candidates for DB verification, flagged in db_check fields):
1. CONSISTENT: origin counts. (10080-8076)/12 = 167.0 exactly; (604800-8076)/12 = 49727.0 exactly. Common-span coverage 1-8076/604800 = 98.66% -> "98.7%" OK; (10080-8076) min = 2004 min = 33.4 h = 19.9% of week -> "33.4 h (20%)" OK.
2. CONSISTENT: context budgets 2048-120=1928, 4096-120=3976, 8192-120=8072 all check out.
3. CONSISTENT: quantile-sweep cell counts. 18 (TimesFM) + 31 (baselines) + 2 (Chronos-2/Toto-2) = 51, matching line 279's "51 of 160". 160 = 8 configs x 5 res x 4 signals. 80 = Chronos-2/Toto-2 both modes x 5 x 4.
4. CONSISTENT: coverage figures. p90 coverage 0.888 -> exceedance 11.2%, matching the "11% of common-span image bins" at lines 325 and 361. Band 0.888 - ~0.19 = ~0.70 vs the stated 69% p10-p90 coverage.
5. CONSISTENT: MAE 1302 images/bin / 60 s = 21.7 images/s, as stated.
6. CONSISTENT: one-third reduction at 1 s images: 1 - 98.8/146.1 = 32.4% vs EWMA (37.0% vs naive).
7. SUSPECT (line 152 / line 412, headline): the "2--9% relative" EWMA margin at 1-minute bins. Computed from tab:pred-wape best-per-column: req 5.1%, img 2.4%, ctx 3.4%, gen 9.2%. The generated-token cell is 9.2%, marginally outside the stated upper bound of 9%.
8. SUSPECT (line 191, headline): "ARIMA, 0.521 ... trails the best foundation model (0.515) by about a WAPE point". The gap is 0.006 in WAPE units = 0.6 percentage points, or 1.2% relative. "About a WAPE point" is a loose reading of either scale; worth checking against forecast_metrics precision.
9. SUSPECT (tab:pred-wape bolding, lines 129-133): two bold decisions are ties at the displayed precision. Chronos-2's 33.4 (1-min req) is bolded while TimesFM also shows 33.4; Toto-2's 98.8 (1-s img) is bolded while Toto-2 (cov) also shows 98.8. Needs the underlying higher-precision values from forecast_metrics to confirm which is actually the minimum. This is the same phenomenon the text itself concedes at line 176 ("decided by <=0.1 WAPE point over 167 origins").
10. LOOSE-BUT-TRUE (line 382, headline): "TimesFM ... lands within ~2 WAPE points of the other two at 1-minute bins". From the table the max gap is 0.5 points (53.4 vs 52.9 on images). The claim is conservative rather than wrong, but the stated contamination bound could be tightened by 4x.

Claims with no plausible provenance-DB backing (marked UNVERIFIABLE in db_check): model parameter counts (lines 15, 101), baseline hyperparameters alpha/beta/gamma and the 15-minute seasonal period (lines 76, 79), the WAPE=100% no-skill floor (line 157, definitional), and the unexercised fine-tuning split days 1-3/4-7 (line 373). Three claims depend on side-experiments that may not be registered in provenance.runs: the additive context reconstruction "WAPE within 1.3 points" (line 248) and the burst-onset-conditional WAPE ranges 75-100 / 58-72 / 33-38% (line 252) — these need an onset-filtered forecast_metrics slice. Two claims (R^2=0.12 at line 231, R^2=0.94 and 34-36% context mass at line 242) are cross-chapter imports from the EDA chapter and should be verified against that chapter's artifacts for consistency, as should the 6-minute median burst onset (line 335) and the 370 images/s peak (lines 318, 358).

---

## related  (24 claims, 8 headline)

related.tex is 402 lines and is numerically sparse by nature: most numbers are values attributed to OTHER papers, not this thesis's own measurements. Only 6 numeric claims are the thesis's own results, and every one of them is a forward-reference to another chapter — so this chapter's correctness is entirely a CONSISTENCY problem against trace-eda, predictors, and closedloop.

Thesis-owned numbers (all must match their source chapters exactly):
- R^2 = 0.123 (line 188) — request rate vs vision-pool demand
- R^2 = 0.12 (line 225) — SAME quantity, rounded differently. Flagged: the chapter states this figure three times in two different roundings (0.123 / 0.12 / 0.123). Not wrong, but a reviewer will notice; recommend unifying.
- R^2 = 0.123 vs 0.654 (line 335) — vision vs decode demand. The 0.654 decode figure appears ONLY here in this chapter and is the load-bearing contrast; verify it against trace-eda.
- Hurst up to ~0.93 (line 207) — asserted as the max across signals AND attributed to the vision signal; both parts need checking, not just the value.
- Fano growing "nearly three orders of magnitude" with window size (line 206) — vague quantifier over a recomputable quantity; check the actual span is ~10^3 and not, say, 10^2.5.
- 0.62x provisioned worker-time (line 361) — the single most challengeable number in the chapter. It carries three conjoined conditions: (a) ratio vs the DEPLOYABLE (i.e. feasible) static encoder fleet, not the static-optimal; (b) tail SLA held in aggregate; (c) tail SLA held PER-EPISODE. All three must verify together or the sentence is false as written.

External/cited numbers (verify against the source papers, NOT the provenance DB): ModServe 25–41.3% cost savings and 3.3–5.5x throughput; ModServe's 79% predictor error (headline — it motivates the whole forecasting contribution); SageServe ~25% GPU-hour savings; WarmServe 5-minute horizon; BurstGPT 213-day trace.

One reproducibility number worth confirming: Dynamo v1.3.0 (line 168) is the pinned planner version for all simulations; it should match provenance.runs and Appendix ap:artifacts.

No numbers appear in the positioning table's cells (it is a checkmark/tilde matrix), but I recorded it as one claim because this thesis's row makes a falsifiable negative assertion — the "~" in the last column claims NO real-cluster closed-loop evaluation exists, which should be confirmed against provenance.runs.actuation.

Excluded per instructions: citation years, URL access dates (2025-12-15, 2026-01-12, 2026-07-07), section/chapter refs, and LaTeX sizing (p{3.1cm}, tabcolsep 3pt).

---

## tese  (22 claims, 17 headline)

SCOPE CORRECTION (important for the orchestrator): /home/gio/tese/tex/tese.tex is 540 lines but is the ROOT/front-matter file only — documentclass, title page, Abstract, Resumo, draft note, abbreviations table, and a 60-entry manual thebibliography. It contains NO tables, NO figures, NO results sections. All chapter content is pulled in via \include from sibling files in /home/gio/tese/tex/: intro.tex, related.tex, trace-eda.tex, predictors.tex, aiconfigurator.tex, twopool.tex, baselines.tex, closedloop.tex, validation.tex, conclusion.tex, apendice.tex (plus apendice_ecosystem.tex, which is present on disk but NOT \include'd anywhere in tese.tex — worth flagging separately, it may be dead or orphaned content). The "300+ numeric tokens should yield many claims" expectation does not apply to this file; it applies to those chapter files, which need their own audit passes.

WHAT IS HERE: 22 claims. Because everything numeric in this file sits in the Abstract, Resumo, or draft note, nearly all of it is load-bearing by definition — hence 17 headline. The distinct underlying quantities are only 9: trace size (one million requests / seven days), R^2 = 0.12, "order of magnitude" burstier, Jaccard 0.02, saturation knees "an order of magnitude" apart, 29% mean encoder utilization, 0.62x encoder cost ratio, 0.96x language cost ratio, and the p90 quantile for the language-pool verdict. Each appears twice (English abstract + Portuguese resumo), and 0.62x a third time in the draft note.

CROSS-LANGUAGE CONSISTENCY: I checked every abstract number against its resumo counterpart. All agree exactly — 0.12/0,12; 0.02/0,02; 29%/29%; 0.62/0,62; 0.96/0,96; p90/p90; one million/um milhão; seven/sete. No translation drift.

ONE WORDING DISCREPANCY WORTH A REVIEWER'S ATTENTION (not a numeric error, but it changes what the headline number means): the English abstract (line 67) defines the 0.62x denominator as "the deployable static encoder fleet's GPU-time", while the Resumo (line 112) says "a menor frota estática viável" — the SMALLEST feasible static fleet. "Deployable" and "smallest feasible" are not the same denominator, and the cost ratio is only defensible against the smallest feasible one (any larger static fleet would trivially inflate the savings). The draft note on line 133 further attributes the figure to the "issue-time week-scale aggregate". The DB check I recorded pins the denominator to the smallest feasible config_c via provenance.factorial_cell feasibility, with is_current and actuation='issue_time' filters, so a superseded-run contamination would surface.

VERIFIABILITY GAP: the four trace-EDA descriptors (R^2 0.12, burstiness order-of-magnitude, Jaccard 0.02, and by extension the Hurst/Fano family) have no home in the listed provenance schema — runs/llm_run_summary/encoder_run_summary/factorial_cell/forecast_metrics all store run outputs, not trace statistics. I marked these "UNVERIFIABLE from the listed tables directly" with a recompute recipe from provenance.measured_request. If the audit is meant to fully close, either those EDA statistics need a provenance table or the recompute needs to be run and archived. The same four numbers are the abstract's opening argument, so they are the highest-exposure unverifiable claims in the document.

Two "order of magnitude" claims are recorded with the verbatim phrase in the numbers array rather than a fabricated "10" — they assert a ~10x ratio but the thesis never writes a numeral, so any check should confirm the ratio is genuinely >= 10 and not, say, 6x.

I also captured Dynamo v1.3.0 (line 256, incidental) as a config-provenance claim, since every simulation depends on it and provenance.runs.engine should corroborate. Excluded as instructed: citation years, arXiv IDs, journal volume/page ranges, the 2026-07-11 draft date, product names (RTX 5090, H100, Qwen3-VL), LaTeX sizing (12pt, a4paper, [2ex]), and the abbreviations table.

---

## trace-eda  (78 claims, 27 headline)

Read all 490 lines. 78 claims (27 headline / 43 supporting / 8 incidental), sorted by line, covering all four tables cell-row-by-cell (tab:eda-archetypes 4 rows, tab:eda-persistence 6 rows, tab:eda-multires 4 rows, tab:eda-percentiles 7 rows) and all 8 figure captions.

IMPORTANT CAVEAT ON db_check: this is a trace-EDA chapter. Almost every number is a statistic of the raw AzureLMMInferenceDataset2025 parquet, not an output of a provenance-tracked experiment. Only a handful touch the provenance schema: provenance.windows (the six burst episodes b1-b6, the calm day 2024-10-19, the p99 threshold 224 img/s, the 370 img/s peak) and provenance.runs (the "b2/b6 evaluated only by forecast-free policies" claim, checkable as absence of forecasting-model runs for those window_names). The remaining ~65 are marked UNVERIFIABLE in provenance with the specific recomputation named.

Arithmetic cross-checks I ran while extracting, flagged inside db_check fields — worth a closer look by the verification pass:
1. L196 peak/mean 4.7x for requests: 7.8/1.7 = 4.59 (rounds to 4.6). Only reaches 4.7 if the unrounded mean 1.653 req/s is used (7.8/1.653 = 4.72). The table publishes 1.7, so text and table are mutually inconsistent at one decimal. Images 370/23.7 = 15.6 checks out exactly.
2. L241/L244 R^2 tension: Pearson r = 0.36 for images implies r^2 = 0.130, but the stated R^2 is 0.123. Explicable by the forced-through-origin fit, but the two are quoted side by side without that caveat. Decode side is clean (0.81^2 = 0.656 vs 0.654).
3. L241 alpha = 15.1 img/req vs ratio of means 23.7/1.7 = 13.9 (or 23.7/1.653 = 14.3). Through-origin LS is volume-weighted so a gap is expected, but 15.1 should be confirmed against the script.
4. L265: 101 windows above p99 forming 87 contiguous runs means only 14 windows ever sit adjacent to another. Arithmetically possible, but a suspiciously atomized run structure for a signal claimed to have a 69-minute memory — verify the run-merging code.
5. L387 + L443: implied 1-second image peak = 370/0.039 ~ 9,487 img/s, which is essentially one max-size request (9,409 images) landing in one second. Worth confirming the 1 s peak is not literally a single request, since the whole multires row is normalized by it.
6. Consistency checks that PASS and are worth keeping: 97^2 = 9409 matches the table max; all NumImages percentiles (25, 196, 529, 1089, 9409) are perfect squares; 7 days = 10,080 minutes; Jaccard 5/202 = 0.0248 -> 0.02; 106 = 100 nominal + 6 tied; H = (1+beta)/2 holds for all six rows of tab:eda-persistence; ctx-rate mean 4813/1.653 = 2911 tok/req and gen-rate mean 309/1.653 = 187 tok/req exactly reproduce the request-level means (strong internal corroboration of the rate tables).
7. Column sums in tab:eda-archetypes: requests 99.9%, image volume 100.0%, prefill 99.9% — rounding-consistent. But the video/frame p50 of 400 images is not a perfect square, in mild tension with the L33 perfect-squares claim (medians can interpolate between order statistics).
8. L84 "a third of all prefill tokens" = 32.9% in the table; L284 says multimodal requests carry 72.5% of prefill while the two vision archetypes sum to 66.4% — different partitions (modality vs cluster), so not a contradiction, but the 6-point gap should be intentional.
9. L129 inter-arrival CV of 1.55 collides numerically with the p50 of requests/s (1.55) in tab:eda-percentiles. Almost certainly coincidence, but flagged since a copy-paste error would look exactly like this.
10. L317 fits the Hurst slope over "10 minutes to 12 hours, clear of the diurnal fundamental" while L136 names 12 h as a diurnal overtone — the band's upper edge sits on a named harmonic.

---

## twopool  (85 claims, 47 headline)

Read all 478 lines of /home/gio/tese/tex/twopool.tex. 85 claims extracted covering: the polynomial-vs-AIC timing table (tab:sim-poly-aic), the 235B family-transfer spot-check, the encoder batching law and handoff bound, the SLA definition and composed first-token reconstruction, the saturation-knee table (tab:sim-knees) and figure captions, the burst-window queueing mechanism, and all Limitations numbers.

Arithmetic cross-checks that PASS: 307/248=1.238 (claimed 1.24x); 4518/2540=1.78 (1.8x); 348/181=1.92 (1.9x); 316.4/64=4.944 (4.94 ms/img) and 8.16/4.944=1.651 (1.65x) with intercept 3.27 ms (~3.2 ms); 147*64+1=9409 and 147*f(64)+f(1)=46.5 s (~46 s); 196*4096*2 B=1.606 MB, x121=194 MB, /25 Gbps=62 ms; 4x payload -> 6.42 MB and 249 ms (~250); 64804/(8.3*3600)=2.169 req/s (2.17, table 2.2); 2.77*3=8.31 (8.3 req/s), 2.77*2=5.54 (5.5), 8.0*32=256 img/s; 1868/1000=1.87 (1.9x), 910 -> 9% under, 5013/1000=5.01 (5x); 8.0/2.77=2.89 images/req matches the 2.9 at line 458; 529*196=103,684 (~104k) and ~3x of 36k; (448/224)^2=4, (672/448)^2=2.25; 588+651=1239 (~1.24 s) and 588+706=1294 (~1.30 s).

DISCREPANCIES FLAGGED for the verification pass:
1. Line 315 "TTFT budget still has 1.8--2.1x slack" at the knee successor points conflicts with tab:sim-knees, whose successor TTFT p99 values are 374 ms (poly, s=4) and 418 ms (AIC, s=3) -> slack of 2.67x and 2.39x, not 1.8-2.1x. Load-bearing for the "decode-bound" argument.
2. Line 217 "within 8% at p99: 706 modelled versus 651 replayed" -> (706-651)/651 = 8.45%, above 8%; only 7.8% if normalized by 706. Denominator convention needs stating.
3. Line 79 "2x the decode latency ... 87 vs 142 output tok/s per user": 142/87 = 1.63, not 2x; and TPOT 7.9 ms implies 127 tok/s, not 142, while tab:sim-poly-aic pairs ITL avg 7.67 ms with 142.0 tok/s (implies 130). The tok/s convention is inconsistent with the ITL/TPOT figures.
4. Table row 276 reports polynomial steady TTFT p99 as 249 ms while tab:sim-poly-aic reports 248 ms for the same run/window.
5. Line 403 says the steady knee "moves by one octave" between timing models, but the knee moves s=3 -> s=2 (a factor 1.5); the sweep is only octave-spaced above s=4.
6. Line 309 claims separation "factor >10"; the measured ratio is 32/2 = 16 (censored lower bound), so ">10" is conservative but the stated basis (octave spacing above s=4) should be checked against the actual swept speedup set.
7. Line 355 "worst second lands 2,726 images" vs line 251 "peaking at 370 img/s" -- these differ by 7.4x; reconcilable only if 370 img/s is a 1-minute mean (figure caption supports that), worth confirming.
8. Line 297 "encoder idles at 4.5% utilization" at the calibrated language knee (s=2) is not obviously consistent with 29% mean utilization on the burst window at s=1 -- different windows, but the steady-window utilization should be checked directly against encoder_run_summary busy/provisioned.
9. Line 426 (TP2 margin under the 196-per-image convention) is explicitly unbacked -- the text says the both-conventions sensitivity run is future work, so it is marked UNVERIFIABLE.
10. Line 70 (max TTFT 7.6 vs 4.5 s) and several avg/max cells depend on measured_request-level aggregation; llm_run_summary only exposes p99 columns, so those cells need the per-request table to verify.

---

## validation  (50 claims, 33 headline)

Read all 166 lines of /home/gio/tese/tex/validation.tex. 50 claims extracted (33 headline), covering all 18 table cells of tab:val-anchor plus both verdict rows, the setup constants, the four findings in sec:val-findings, and the concluding ranges in sec:val-scope.

THREE ARITHMETIC DEFECTS found by recomputing deltas from the table's own cells:

(1) Line 72, tab:val-anchor, reactive TTFT p99 delta printed as +1.1%. (3531-3495)/3495 = 1.0300% -> rounds to +1.0%, NOT +1.1%. This wrong lower bound propagates to three further sites where it is restated as the range lower bound: line 83 ("p99 within 1.1% of the simulation"), line 97 ("within 1.1--6.8%"), and line 159 (the concluding claim "TTFT differs by 1.1--6.8%"). Either the table cells or all four percentage statements are stale.

(2) Line 161, sec:val-scope, forecast ITL relative delta printed as 18.0%. (11.5-9.7)/9.7 = 18.557% -> rounds to 18.6%, NOT 18.0%. 18.0% is only reachable from unrounded values near 11.46/9.71, so the text and the table row (line 68) disagree.

(3) Unit inconsistency between line 57 and line 140: the table caption says the runs are "budget-matched at 4 TP2 replicas" while sec:val-findings says max_gpu_budget=8 "clamps it to 8" replicas. At 2 GPUs per TP2 replica, 8 GPUs = 4 replicas. The chapter itself flags live/offline budget-unit divergence as an upstream defect (lines 136-138), so the same unit confusion appears to have leaked into the prose.

DELTAS THAT VERIFY CORRECT: +6.8% (6.759), -5.3% (-5.266), -1.3% (-1.310), -7.6% (-7.649), "agrees within 8%" (max 7.649), and the 5.3--7.6% concluding range.

VERIFIABILITY GAP: a large share of the chapter's mechanism claims have no backing table in the provenance schema. Per-tick planner numbers (line 86 twelve matching ticks, line 87 29.86 rps, lines 88/92 6 replicas, line 91 5.71 vs 5.30 engine_rps), the capacity-starvation finding (line 122: zero mixed prefill+decode passes in five minutes at 2 req/s), the ~120 s tick stall (line 131), the pre-cap 24 requested replicas (line 139), and the cold-start constants (lines 42-43: 59 s delayed spawn, 1.0 s spawn-to-registered) all live in archived planner logs under simulation/results/live51/live_runs/, not in runs/llm_run_summary/cost_accounting. These are marked UNVERIFIABLE with the artifact path to check instead. Worth noting that "the demand path is byte-identical" is load-bearing for the RQ3 platform-validity argument and currently rests on logs alone; ingesting per-tick planner decisions into the DB would close this gap.

---

