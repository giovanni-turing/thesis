# Verification of the "opus" committee review

Independent fact-check of every finding in `/home/gio/tese/opus/{report,adjudication,cross-check}.md`.
Numbers recomputed from artifacts; tex read from ground truth; papers grepped; specs checked.
Trusting neither reviewer nor thesis. Line numbers refer to `/home/gio/tese/tex/*.tex`.

Methodology note: artifacts under `analysis/trace_eda/*_stats.json`,
`predictors/results_dynamo/consolidated.json`, `simulation/results/{aggregate44,llm_week,riders44,ct_matrix,episode_twins}`,
`collector_artifacts/phaseE_physical_anchor/relock.log`, system YAMLs, and the local BurstGPT PDF.

---

## MASTER FINDINGS (M1–M12)

### M1 — Missing factorial corner: reactive + tail-aware conversion never run
Target: baselines.tex:20–23; closedloop.tex:152–174, tab:cl-triad
Verdict: CONFIRMED
Severity: major
Evidence: The tail-aware conversion is implemented as the env knob `FORECAST_REQ_SCALE`
in `simulation/replay_with_forecast.py:115-122` ("scale the predicted request rate so
mean-throughput sizing lands on tail-adequate replicas"), which is registered ONLY on
the `forecast_file` predictor. Every reactive run uses `"load_predictor":"arima"` with
NO scale (`run_44_riders.sh:28`, the ladder part (c)); `FORECAST_REQ_SCALE=8.0/6.22/…`
appears only on forecast runs (`run_44_riders.sh:45`, `run_llm_week_models.sh:5`,
`run_episode_twins.sh:14`). So the reactive arm is structurally denied the conversion.
The cl-triad numbers reproduce from artifacts: `riders44/fc_lead60_s1.report.json`
p99_ttft=1716.57 (→ "Forecast, mean-based conversion" 1716.6, FAIL) and
`episode_twins/burst1_re` p99_ttft=1615.49 (→ "Reactive best ladder" 1615.5, FAIL) —
i.e. forecast+mean fails ≈ reactive fails, establishing the conversion as a second,
separate separating variable. Fast-onset attribution does survive (p50-with-tail-conversion
still fails burst3 at 2164 ms, closedloop.tex:203–205).
Dup-hint: missing reactive+tail cell

### M2 — burst1 ladder mislabeled "information timing, not thrift"
Target: baselines.tex:160–161
Verdict: CONFIRMED
Severity: major (textual, internal contradiction)
Evidence: baselines.tex:160–161 attributes the burst1 reactive-ladder failure to
"information timing, not thrift" ("by the time the trailing window sees the onset, the
capacity it orders arrives after the queue has formed"). But burst1's onset is 220
minutes (baselines tab:base-react-enc:205), and the reactive ENCODER controller scales
burst1 successfully at every lead incl. L=300 s (588/588/588/638 ms) — a 220-min onset
cannot fail on timing. The chapter's own diagnosis three paragraphs earlier
(baselines.tex:150–152: "The defect is the mean-based capacity conversion") and
closedloop.tex:171 (forecast+mean-conversion, i.e. perfect timing, STILL fails burst1 at
1716.6 ms) both prove the defect is the conversion, not timing. Direct internal contradiction.
Dup-hint: burst1 timing contradiction

### M3 — Diurnal non-stationarity not separated from Fano/Hurst magnitudes
Target: trace-eda.tex:127–134, 314–321, tab:eda-persistence
Verdict: CONFIRMED (partial mitigation acknowledged)
Severity: major → effectively minor for the load-bearing contrast
Evidence: Fano factor is computed on raw un-detrended counts
(`e_comprehensive_stats.json /fano_factor_by_window`: 1.76 @1s → 31.9 @1min → 938 @1h),
which an inhomogeneous Poisson process with a diurnal rate reproduces; the absolute
"scale-free burstiness" magnitude conflates diurnal seasonality with stochastic
clustering. The thesis partially defends: Hurst is fit over the 10min–12h sub-diurnal
band "clear of the diurnal fundamental" (trace-eda.tex:316–318), and the image-vs-request
CONTRAST (69 vs 9 min; CV² 3.83 vs 0.32) is robust because both signals share the same
diurnal component (trace-eda.tex:319–321). So the finding is correct about the *absolute*
magnitudes but the *contrast* — the thesis's actual load-bearing claim — survives. Fix is
a reframe, as the review states.
Dup-hint: detrend Fano/Hurst

### M4 — ">10×" knee separation only on an image-lean window
Target: twopool.tex:24, 276–281, 427–429; tese.tex:53–54
Verdict: CONFIRMED (core); reviewer's "~3×" rejection stands
Severity: major
Evidence: Steady head = 2000 req, 2.77 req/s, 8.0 img/s → 8.0/2.77 = 2.89 ≈ 2.9 img/req
(twopool.tex:217–221), against trace mean 23.7 img/s ÷ 1.65 req/s = 14.4 img/req
(`m_gen_and_global_stats.json`). 14.4/2.9 ≈ 5×, so the steady window is ~5× image-lean;
the vision knee is censored (uncrossed ≥ s=32) partly because the window under-drives the
encoder. twopool.tex:427–429 asserts the 24-h window "corrects" it but that window is only
feasibility-tested, never knee-swept (confirmed: no knee sweep exists for a representative
steady window). Adjudication correctly rejected the reviewer's precise "~3×" projection as
burst-inflated; the honest statement is "unmeasured, plausibly several-fold, not
demonstrated >10×."
Dup-hint: knee lean window

### M5 — Burst-window language verdict stacks three unanchored layers; "shape-fixable" convention-dependent
Target: twopool.tex:365–402; aiconfigurator.tex:475–480; tese.tex:54–55
Verdict: CONFIRMED
Severity: major (all disclosed in body; dropped in abstract)
Evidence: (a) H100 timing not physically validated (twopool.tex:365–372, explicit);
(b) ~3.1% of trace requests up to ~149k tokens priced by stratum-3 extrapolation beyond
the 16,384-token grid (aiconfigurator.tex:476–480) — ~9× beyond the grid edge;
(c) token-convention undercount: twopool.tex:387–400 concedes "under the 196-per-image
convention the frames-class prefills would strain even TP2… the burst-window language
verdict is convention-dependent." Yet tese.tex:54–55 states "a shape-fixable prefill
floor" unconditionally. intro.tex:489–491 DOES carry the caveat; conclusion.tex:79–89 does
not. Confirmed as stated.
Dup-hint: shape-fixable convention

### M6 — Operative encoder cost model is the optimistic bound; ~2× fleet at p99 knee
Target: aiconfigurator.tex:337–344; closedloop.tex:408–418
Verdict: CONFIRMED (disclosed; direction conservative)
Severity: major
Evidence: aiconfigurator.tex:337–338 states the 1.4–1.6× per-batch underprice amplifies to
1.86–2.17× fleet at the knee (burst3 grows 7→13; 13/7 = 1.857 → 1.86 ✓). Direction is
conservative for the thesis's failure/cost-ratio claims: closedloop.tex:408–418 re-prices
the winning p90/ρ15 schedule on measured f(N) and it stays feasible (784 vs 588 ms, both
< bound), which I confirmed indirectly — the p90 headroom over-provisions (24–32 workers
vs 12–16 needed), absorbing the underprice. But absolute fleet sizes inherit the underprice.
Correctly disclosed.
Dup-hint: optimistic cost bound

### M7 — Validation anchor scope thinner than narrative weight
Target: validation.tex:39–42, 64–65, 92, 133–146
Verdict: CONFIRMED (all four sub-findings)
Severity: major
Evidence: (a) live anchor covers only the LANGUAGE pool; encoder controller "exists only
in simulation" (validation.tex:138–139, explicit). (b) Engine timing "identical … by
construction" (mocked engines, validation.tex:39–42), so latency agreement validates
orchestration, not served latency. (c) tab:val-anchor:65 reports ITL 11.5 vs 5.3 ms as
"+6.2 ms"; the ratio is 11.5/5.3 = 2.17× (recomputed), folded into "within run noise"
(validation.tex:92); TTFT +6.8% (695/651 = 1.0676) exceeds the thesis's only stated noise
band ≈4% (closedloop.tex:405–406). (d) n=1 window, one live run per policy, no live error
bars (Table has single Δ column). All verified.
Dup-hint: validation over-weighted

### M8 — Predictors: weak baseline frontier, no significance test on thin margin
Target: predictors.tex:76–79, 151–176, 384–390
Verdict: CONFIRMED
Severity: major
Evidence: Holt–Winters uses "seasonal period of one hour of bins" (predictors.tex:77–79;
`benchmark.py:96` HW_SEASON = one hour of bins) against diurnal (24-h) data, and loses to
naive in every cell (tab:pred-wape: 1-min req HW 43.8 > naive 42.3; img 69.4 > 67.8;
etc.). No diurnal seasonal-naive tested. EWMA margin recomputed at 1-min: req 5.1%, img
2.4%, ctx 3.4%, gen 9.2% → "2–9%" (predictors.tex:153) ✓, and the text itself admits "no
significance test attached" (predictors.tex:175). The surviving claim ("beats these
fixed-parameter baselines in all 20 cells", 0 violations) holds; the stronger operative
reading is not statistically established.
Dup-hint: weak baselines no sig-test

### M9 — Provenance overstatement: "upstreamed"/"contributed upstream"/"fixed upstream"
Target: tese.tex:51,87–88; aiconfigurator.tex:485–486; validation.tex:145; intro.tex:301
Verdict: CONFIRMED
Severity: minor (cross-cutting)
Evidence: PR #1312 is a "draft pull request" (aiconfigurator.tex:109–110); the infilled
slice every simulation consumes is "pending upstream push" (aiconfigurator.tex:113–114).
The `fpm_observation_mode` fix is a LOCAL branch commit (validation.tex header line 6:
"commit 33a9babe01 (local)") yet validation.tex:145 says "fixed upstream". Abstract
tese.tex:51 "(upstreamed to NVIDIA's aiconfigurator)"; resumo tese.tex:87–88 "contribuídos
ao aiconfigurator"; aiconfigurator.tex:485–486 "contributed upstream" — all completed-action
language for draft/local artifacts. intro.tex:301,416 correctly say "contributed upstream
(draft PR … #1312)"/"draft PR".
Dup-hint: upstreamed draft PR

### M10 — "Identically informed" overstates parity (point-rate vs p90 band)
Target: closedloop.tex:36–38, 71, 430–431; baselines.tex:186; intro.tex:257–258; tese.tex:58
Verdict: CONFIRMED
Severity: minor
Evidence: The reactive strawman reads the trailing observed POINT rate (quantile ignored)
while the forecast reads the p90 band (closedloop.tex:36 explicitly: "the raw head-to-head
therefore bundles anticipation with headroom"). The chapter discloses the bundling but the
"identically informed" phrase recurs unqualified in the headline (closedloop.tex:71),
summary (closedloop.tex:430–431), abstract (tese.tex:58), and intro (intro.tex:257). The
two dials are separated only by the later p50/lead-invariance ablations. Wording defect confirmed.
Dup-hint: identically informed parity

### M11 — Conclusion "each leans conservative" omits non-conservative caveats
Target: conclusion.tex:79–89
Verdict: CONFIRMED
Severity: major
Evidence: conclusion.tex:87 "None reverses the direction of the results (each leans
conservative)". Two body-acknowledged limitations are NOT conservative: the unvalidated
H100 language timing (twopool.tex:365–372 — the burst verdict "changes outright" under the
sensitivity) and the token-convention dependence of the burst TP2 pass (twopool.tex:393–400
— under the 196/image convention it "would strain even TP2", i.e. could flip to FAIL).
Neither appears in conclusion.tex:79–89. Confirmed omission.
Dup-hint: conservative omits caveats

### M12 — Abstract-layer caveat shaving
Target: tese.tex:46–61
Verdict: CONFIRMED
Severity: minor (cross-cutting)
Evidence: Abstract asserts (a) "upstreamed" (M9); (b) "an order of magnitude burstier"
without the CV² qualifier — recomputed plain-CV ratio = √3.83/√0.32 = 3.46 ≈ 3.5×, only
CV² is 12× (trace-eda.tex:195 ties it to CV²; abstract drops it); (c) "a shape-fixable
prefill floor" without the convention caveat (M5); (d) "the language fleet
near-break-even, 0.96×" silently selecting the cheapest of three models — Toto 625.3/537.4
= 1.16×, TimesFM 641.1/537.4 = 1.19× are ABOVE break-even (verified from
`llm_week/week_fc_p90_{toto,timesfm}.report.json`); (e) "both verdicts reproduce on the
live Dynamo runtime" without the language-pool/mocked-engine scope (M7). Each has an honest
body counterpart. Confirmed.
Dup-hint: abstract shaves caveats

---

## R7 — VERIFIED FACTUAL ERRORS (the quantitative cluster; each recomputed)

### R7a — Prophet BEATS naive at 15 s (thesis says it trails)
Target: predictors.tex:193–195
Verdict: CONFIRMED
Severity: minor (factual error)
Evidence: `predictors/results_dynamo/consolidated.json`: prophet_15s WAPE = 0.7328,
constant_15s (=naive) = 0.7638. Lower WAPE is better → Prophet (0.7328) BEATS naive
(0.7638). The tex: "Kalman (0.811) and Prophet (0.733) trail even naive persistence
(0.764)" — grouping Prophet with Kalman as trailing naive is WRONG; Prophet is 0.03 WAPE
BELOW (better than) naive. All quoted digits are right (arima_15s 0.6675→0.668, best_fm
0.6374→0.637, kalman 0.8111→0.811); only the "trail" characterization of Prophet is the error.
Dup-hint: Prophet beats naive

### R7b — ARIMA/Prophet 15 s scored on 300 of 2687 origins (undisclosed)
Target: predictors.tex:193–195
Verdict: CONFIRMED
Severity: minor
Evidence: consolidated.json: prophet_15s and arima_15s both n_origins_used = 300; constant_15s
and kalman_15s both n_origins_used = 2687. The 15 s ARIMA/Prophet WAPEs are on 11.2% of the
origins the others use — non-matched samples, undisclosed in the tex. (1-min entries are all
167/167, so the 1-min comparison is matched.)
Dup-hint: 300 vs 2687 origins

### R7c — Clock range 2377–2385 wrong; log rises to 2400 with N
Target: aiconfigurator.tex:302
Verdict: CONFIRMED
Severity: minor
Evidence: `collector_artifacts/phaseE_physical_anchor/relock.log` sm_clock_mhz per N:
2377 (N=1), 2377 (N=2), 2385 (N=4), 2385 (N=6), 2392 (N=8), 2392 (N=16), 2392 (N=32),
2400 (N=64). The tex states "delivered SM 2377–2385 MHz under load" — the ceiling is
wrong (log reaches 2400), and clock rises monotonically with N (an undiscussed,
conservative-direction confounder for the "gap grows with N" trend). The PUBLISHED band is
exact: log footer "min 1.322 max 1.617 mean 1.433" = the stated 1.32–1.62/mean 1.43.
Dup-hint: clock 2385 vs 2400

### R7d — gen-median band "50–140" wrong; artifact spans 37–435
Target: trace-eda.tex:349–350
Verdict: CONFIRMED
Severity: minor
Evidence: `e_comprehensive_stats.json /gen_median_by_numimages`: values across image
counts 1→529 = {1:71, 4:140, 9:140, 16:109, 25:37, 36:131, 49:86, 100:118, 196:86,
225:435, 361:49, 400:50, 441:48, 484:48, 529:52}. Min = 37 (at 25 img), Max = 435 (at 225
img). The tex "median generation stays at 50–140 tokens across image counts from 1 to 529"
understates the spread badly (435 ≫ 140; 37 < 50). The independence point survives: Spearman
GeneratedTokens/NumImages = −0.061 → −0.06 (kept, correct).
Dup-hint: 50-140 vs 37-435

### R7e — gen spectral slope 0.82 → should be 0.81
Target: trace-eda.tex tab:eda-persistence (line 231)
Verdict: CONFIRMED
Severity: nit
Evidence: `m_gen_and_global_stats.json /gen_signal/spectral_slope_beta` = 0.8117766 →
rounds to 0.81, not 0.82. Table reads 1/f^0.82. (Hurst 0.9059→0.91 is right either way, so
only the slope cell is off by one in the last digit.) Cross-checked all other slopes:
requests 0.6579→0.66 ✓, ctx_total 0.7184→0.72 ✓, ctx_multimodal 0.7351→0.74 ✓, ctx_text
0.5139→0.51 ✓, images 0.8650→0.86 ✓ — only gen is misrounded.
Dup-hint: gen slope 0.81

### R7f — BurstGPT is 213 days, not "year-long"
Target: related.tex:204–205
Verdict: CONFIRMED
Severity: minor
Evidence: `papers/2401.17644 - BurstGPT….pdf` (pdftotext): "over 213 days", "GPT-4v) for
213 days. The dataset comprises 8.69 million traces". 213 days ≈ 7 months, not a year. The
tex "BurstGPT's year-long trace" is a factual slip. Single-word fix.
Dup-hint: BurstGPT 213 days

---

## REQUIRED REVISIONS R1–R10 (non-R7)

### R1 — Close/concede the missing factorial corner
Verdict: CONFIRMED (= M1). Severity: major.
Evidence: See M1. The prescribed fix (run reactive+tail-aware, or scope claims to fast
onsets and strike baselines.tex:22–23) is well-grounded.
Dup-hint: run missing cell

### R2 — Fix burst1 mechanism contradiction
Verdict: CONFIRMED (= M2). Severity: major.
Evidence: See M2. baselines.tex:160–161 should be replaced by the conversion diagnosis at
baselines.tex:149–152 / closedloop.tex:99–106,166–174.
Dup-hint: burst1 fix

### R3 — Carry non-conservative caveats into conclusion + abstract
Verdict: CONFIRMED (= M11, M12, M5). Severity: major.
Evidence: conclusion.tex:87 and tese.tex:54–55,60–61 confirmed to omit the H100-timing,
token-convention, and language-pool/mocked-engine caveats that the body carries.
Dup-hint: caveats to summary

### R4 — Correct provenance language
Verdict: CONFIRMED (= M9). Severity: minor.
Evidence: See M9. "Upstreamed"/"contributed upstream"/"fixed upstream" → draft-PR/local-branch
language. Exact loci verified.
Dup-hint: provenance wording

### R5 — Re-establish or soften ">10×" knee quantifier
Verdict: CONFIRMED (= M4). Severity: major.
Evidence: See M4. The quantifier propagates to tese.tex:53–54, twopool.tex:23–24, intro,
conclusion; representative-density separation is unmeasured.
Dup-hint: soften >10x

### R6 — Both-conventions burst sensitivity, or downgrade "shape-fixable"
Verdict: CONFIRMED (= M5). Severity: major.
Evidence: twopool.tex:402 itself states "a both-conventions sensitivity run remains future
work"; the honest text at twopool.tex:393–400 should be promoted to the abstract/summary.
Dup-hint: both conventions run

### R8 — Reframe validation anchor magnitude claims
Verdict: CONFIRMED (= M7). Severity: major.
Evidence: See M7. ITL should be a ratio (2.17×); "within run noise" → verdict-robustness;
state engine timing identical by construction; foreground encoder loop validated nowhere live.
Dup-hint: reframe anchor

### R9 — Statistical minimums for EDA and predictors
Verdict: CONFIRMED (= M3, M8). Severity: major.
Evidence: See M3 (detrended Fano/slope + stationarity) and M8 (significance test at 1-min +
diurnal seasonal-naive). Both feasible on existing data.
Dup-hint: add stats tests

### R10 — State reactive controllers' trailing-window length
Target: baselines.tex:186–191
Verdict: CONFIRMED
Severity: minor
Evidence: The encoder reactive strawman (baselines.tex:186–191) reads "the trailing window
of the observed image rate" but never states the window length or whether it was swept —
a load-bearing tuning parameter. The forecast controller's cadence (15-s bins) is stated;
the reactive window is not. Confirmed absent from baselines.tex.
Dup-hint: trailing window length

---

## SUGGESTIONS S1–S10

### S1 — Leave-one-episode-out interval on 0.27–0.31×; burst-time fc/static ratio
Target: closedloop.tex:315–319, 415–417
Verdict: CONFIRMED
Severity: nit/suggestion
Evidence: Cost ratios are point estimates with no interval; verified 2.376M/7.74M = 0.307
and 2.116M/7.74M = 0.273 from `aggregate44/*.stats.json` (single run each). No bootstrap
exists in the artifacts. Reasonable strengthener.
Dup-hint: LOO interval

### S2 — Unify "deployable static" vs "best static"
Target: intro.tex:206–207 vs 260; conclusion.tex:76
Verdict: CONFIRMED
Severity: nit
Evidence: intro.tex:206 thesis statement "best static encoder fleet's GPU-hours" and
conclusion.tex:76 "best static encoder fleet" vs the defined term "deployable static"
(baselines.tex:105–107; tese.tex:59). Same C=16 fleet, two names; "best" is ambiguous
against per-window optima C*=2–16. Confirmed drift.
Dup-hint: naming drift

### S3 — State 29% utilization denominator; quote feasible-topology figure (~10%)
Target: twopool.tex:308–316
Verdict: CONFIRMED (partial)
Severity: minor
Evidence: The 29% mean utilization is at the 2-worker naive topology; the feasible 6-worker
topology would show ~2×/6 ≈ under 10% — the stronger monitor-blindness figure. The aggregate
week run at 2 workers shows encoder_utilization = 0.0242 (a different span). The specific
"~9.6%" for a 6-worker burst-window run is plausible but I did not locate that exact figure
in an artifact; the qualitative point (denominator is the infeasible 2-worker topology) is
correct. Marked partial on the exact ~10% number.
Dup-hint: util denominator

### S4 — Jaccard threshold sensitivity; DFA/wavelet cross-check on H
Target: trace-eda.tex:316–319, 414–421
Verdict: CONFIRMED
Severity: minor/suggestion
Evidence: Jaccard reported at a single p99 threshold (`q_multires_tails_stats.json`:
106/101/5 → 0.0248); Hurst from a single spectral-slope estimator (tab:eda-persistence note
says so explicitly: "one estimator viewed two ways"). No p90/p95/p99.9 sensitivity or
DFA/wavelet cross-check exists. Confirmed.
Dup-hint: single threshold/estimator

### S5 — Precision fixes at summary layer (CV², onset scope, burst3 name, 0.96× model)
Verdict: CONFIRMED
Severity: minor
Evidence: (a) plain-CV ratio 3.5× vs CV² 12× (M12b). (b) "detects onsets at or before the
signal" vs measured −105..+210 s range (closedloop.tex:117–118; B15). (c) "fastest-onset
burst" is two episodes: tab:base-react-enc shows burst3 AND burst6 both 1-min onset;
reactive CATCHES burst6 (L*=45 s) but loses burst3 (none) — so the "defeats reactive at
every lead" clause is true only of burst3 (B8). (d) 0.96× is Chronos-only; Toto/TimesFM
1.16–1.19× (verified from llm_week reports). All confirmed.
Dup-hint: summary precision

### S6 — Explain L=300 cheaper than L=30; C(t) floor
Target: tab:cl-aggregate
Verdict: CONFIRMED
Severity: nit
Evidence: `aggregate44`: fc_p90 L=30 provisioned 2.376M worker-s vs L=300 provisioned
2.116M — L=300 is cheaper at the same p99 588 ms (longer lead issued earlier, but the
schedule holds fewer surplus workers on the down-ramp). Unexplained in the text; worth one
mechanism sentence. Confirmed the numeric inversion is real.
Dup-hint: L300 cheaper

### S7 — Justify RTX 5090 hardware class; cite chunk-parallel dispatch
Target: aiconfigurator.tex:48; twopool.tex:135–138
Verdict: CONFIRMED
Severity: minor
Evidence: aiconfigurator.tex:48 asserts "represents the vision pool's hardware class"
without argument; twopool.tex:135–138 calls chunk-parallel dispatch "a simulator policy
assumption … consistent with encoder-disaggregated runtimes" without a runtime citation.
Both confirmed as asserted-not-argued.
Dup-hint: 5090 class / dispatch cite

### S8 — Add TimeGPT/MOMENT + Shahrad et al.; narrow ModServe gap
Target: related.tex:88–93, 226–238
Verdict: CONFIRMED
Severity: minor
Evidence: related.tex:226–238 TSFM survey lists TimesFM/Chronos/Chronos-2/Moirai/Lag-Llama/
Time-MoE/Toto but not TimeGPT or MOMENT; §autoscaling omits Shahrad et al. (ATC 2020)
serverless cold-start canon. related.tex:88–93 states ModServe "none asks what demand
signal" while conceding (related.tex:55) it scales on modality — the gap could be narrowed
to the decoupling/forecastability novelty. Confirmed as coverage gaps (not errors).
Dup-hint: missing TSFM/Shahrad

### S9 — Add the 15-second coverage row to predictors §Quantiles
Target: predictors.tex:298–301; closedloop.tex:89–90,133
Verdict: CONFIRMED
Severity: nit
Evidence: closedloop.tex:89–90 cites "empirical coverage 0.88–0.90 at this cadence" for the
15-s forecast, attributing to Chapter 4; but predictors.tex:298–301 reports 0.88–0.90 only
at 1-MINUTE resolution. Cross-check B12: `quantile_coverage.json` supports 0.881–0.896 at
15 s, so the number is right but uncited at that cadence. Confirmed the cadence mismatch.
Dup-hint: 15s coverage uncited

### S10 — Label 5.0 s encoder tail as open-loop upper bound in twopool
Target: twopool.tex:309
Verdict: CONFIRMED
Severity: minor
Evidence: twopool.tex:309 quotes p99 encoder delay 5.0 s at the naive 2-worker topology; it
is an open-loop upper bound (no shedding) labeled as such only in closedloop's limitations
(closedloop.tex:380–384), not in twopool where first stated. Confirmed.
Dup-hint: label 5s tail

---

## CROSS-CUTTING C1–C5

### C1 — Body honest; summary layers shave caveats
Verdict: CONFIRMED
Severity: major (pattern)
Evidence: Aggregates M9 ("upstreamed"), M7b ("validated physically"/mocked engines), M5
("shape-fixable"), M4 ("order of magnitude apart"), M12d ("0.96×"), M11 ("each leans
conservative"), M7c ("within run noise" for 2.17× ITL). Each has an honest body counterpart
and a shaved summary occurrence — all seven individually verified above. The pattern is real.
Dup-hint: caveat-shaving pattern

### C2 — Everything rests on one 7-day trace with a by-construction 50/50 split
Verdict: CONFIRMED
Severity: inherent scope (not a defect)
Evidence: trace-eda.tex:31 "exactly 50.0% of requests are text-only, a by-construction
split"; generality argument runs through mechanism (trace-eda.tex:461–474). No cost-ratio
interval exists (S1); the second trace is absent even from future work (conclusion.tex:91–118
lists three extensions, none a second trace). Confirmed as stated.
Dup-hint: single trace

### C3 — Validation asymmetry between pools
Verdict: CONFIRMED
Severity: major
Evidence: Encoder pool's COST is silicon-anchored (aiconfigurator.tex, relock.log) but its
CONTROL loop is simulation-only (validation.tex:138–139); language pool's control loop is
live-anchored (validation.tex) but its TIMING is sim-only (mocked engines, unvalidated H100,
twopool.tex:365–372). The two anchors never compose into an end-to-end validation of the
pool that carries the 0.27–0.31× headline. Each half stated honestly; the union is never
stated. Confirmed.
Dup-hint: orthogonal anchors

### C4 — Reactive-comparison fairness established on encoder, not language pool
Verdict: CONFIRMED
Severity: major
Evidence: On the encoder pool both arms share law, ρ, hysteresis, lead (baselines.tex:186–192
vs closedloop.tex:33–36) and reactive honestly ties the forecast on slow onsets
(tab:base-react-enc: burst1/steady pass reactively). On the language pool the tail-aware
conversion is a second separating variable never granted to reactive (M1). The defensible
scoped claim the review states is correct.
Dup-hint: fairness encoder-only

### C5 — Numeric integrity is a genuine strength
Verdict: CONFIRMED
Severity: (commendation)
Evidence: Independent recompute of the headline spine all reconciled to the digit: encoder
0.27–0.31× (2.376M/2.116M vs 7.74M worker-s, floor 588 = f(64) 316.369 + handoff 272.001);
language 0.96× (518.6/537.4) with Toto/TimesFM 1.16/1.19×; validation deltas (2.17× ITL,
+6.8%/+1.0% TTFT, −5.3%/−7.6% replica-s); Jaccard 5/202 = 0.0248; CV² 3.83/0.32; Fano
1.76→31.9→938; physical band 1.322–1.617/mean 1.433; 419 TFLOPS = 467.8 × (170/188) ×
(2407/2430); handoff 271.8 ms = 529 img × 196×4096×2 B / 25 Gbps. Not one headline number
failed to reproduce. The results-ledger discipline is real. Confirmed.
Dup-hint: numeric spine holds

---

## EXTERNAL-FACT CHECK: RTX 5090 "419 TFLOPS dense bf16" (aiconfigurator.tex:53,58)

Verdict: CONFIRMED as published-spec-consistent, with one nuance worth a footnote (not a
review finding; not clearly an error).
Evidence: Internal derivation is exact — `rtx_pro_6000_server.yaml` bf16_tc_flops = 467.8
TFLOPS @2430 MHz; scaled by 170/188 SMs × 2407/2430 MHz = 419.0 TFLOPS
(`rtx_5090.yaml`: 418990000000000). 419 dense BF16 is the commonly-published RTX 5090
figure (TechPowerUp / NVIDIA developer-forum consensus). Nuance: on GeForce (consumer)
Blackwell the BF16 tensor rate with **FP32 accumulate** is halved to ≈209 TFLOPS dense;
419 corresponds to the FP16-accumulate dense rate (or the FP32-accumulate *sparse* rate).
The workstation sibling (RTX PRO 6000) does not halve FP32-accumulate, so scaling its
BF16 rate to the 5090 by SM×MHz slightly over-states the 5090's FP32-accumulate throughput.
This only affects AIC's speed-of-light (SOL) bound, which the thesis explicitly labels
~5.9× optimistic and does NOT use operationally (actual costing is the measured silicon
tables). No impact on any headline result. Not flagged by the opus review; recorded here
for completeness because the prompt named it.
Sources: [NVIDIA Developer Forums — RTX 5090 Peak BF16 Tensor
TFLOPS](https://forums.developer.nvidia.com/t/rtx-5090-peak-bf16-tensor-tflops/350543);
[NVIDIA Developer Forums — RTX 5090 FP16 Tensor TFLOPS is
ambiguous](https://forums.developer.nvidia.com/t/rtx-5090-specs-fp16-tensor-tflops-is-ambiguous/351063).

---

## SUMMARY

Counts (42 findings adjudicated: M1–M12, R1–R10, S1–S10, C1–C5):
- CONFIRMED: 41
- PARTIAL: 1 (S3 — the ~10% feasible-topology utilization figure not located in an
  artifact; the qualitative denominator point is confirmed)
- DENIED: 0

Every quantitative and factual finding recomputed from ground-truth artifacts reproduced
the review's claim. No finding in the opus review was found to be wrong. The R7
factual-error cluster is fully confirmed against primary artifacts (not merely against the
thesis or the reviewer):

Top 5 confirmed (by severity × verifiability):
1. **M1 / R1** — reactive+tail-aware conversion cell never run; `FORECAST_REQ_SCALE` is a
   forecast-only knob (`replay_with_forecast.py`, `run_44_riders.sh`); forecast+mean fails
   (1716.6) ≈ reactive fails (1615.5). Conversion is a second, denied separating variable.
2. **R7a/R7b** — Prophet (0.7328) BEATS naive (0.7638) at 15 s yet the text says it trails;
   ARIMA/Prophet 15 s scored on 300/2687 origins, undisclosed (consolidated.json).
3. **M2 / R2** — burst1 (220-min onset) ladder mislabeled "information timing, not thrift",
   contradicting the chapter's own mean-conversion diagnosis; forecast-with-perfect-timing
   still fails burst1 (1716.6), proving it is the conversion.
4. **R7d** — gen-median-by-image band is 37–435 (`e_comprehensive_stats.json`), not the
   stated "50–140"; and **R7c** the physical clock reaches 2400 MHz (relock.log), not the
   stated 2377–2385 ceiling.
5. **M12 / B2** — the abstract's "0.96×" is Chronos-only; Toto (625→1.16×) and TimesFM
   (641→1.19×) are ABOVE static break-even (llm_week reports) — the sign flips for two of
   three forecasters, never flagged in the body.
