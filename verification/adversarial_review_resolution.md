# Adversarial-review resolution report

- **Campaign date:** 2026-07-26
- **Review resolved:** `thesis_adversarial_review.md` (snapshot 2026-07-26, HEAD `89c0018`)
- **Scope:** all 34 review items — Findings 1–26, R1–R6, D1, D2
- **Method:** parallel compute agents (F1 fold replay, provenance ingestion, EDA
  regeneration, ARIMA matched-origin rescore, governance/check repairs) + per-chapter
  editor→verifier→fixup→re-verify edit groups (closedloop, frontmatter, baselines,
  trace-eda, predictors, …) + this finalize pass (cross-chapter residuals, guard repair,
  full build, full gates, this report). Every number cited below was recomputed from an
  artifact or the provenance DB during the campaign; no value was transcribed untested.
- **Tally: 32 FIXED / 1 PARTIAL (Finding 4) / 1 DOCUMENTED-OPEN (D1).**

## Final gate outcomes (this finalize pass, final tree)

| Gate | Result |
|---|---|
| `latexmk -pdf tese.tex` (full build) | **0 errors, 0 undefined refs/citations, 141 pages** (2,408,279 bytes) |
| Overfull \hbox census | 6 content overfulls, worst **12.5 pt** (related.tex paragraph); the review's 50.3 pt / 45.5 pt closed-loop-table and 41.0 pt appendix overflows are **gone** |
| `provenance/verify_all.sh` (full) | **43 passed / 0 failed / 6 warnings — DELIVERY-READY** (warnings: 1 registered warn-level check summary + 5 silicon-phrase manual-review near-misses, all documented) |
| Registered DB check suite (`provenance.check_all()`) | 74 evaluated: **69 pass / 5 fail** — C002 (error, documented ACCEPTED: 1/178 median-TTFT recompute outside 1e-3), C107, C207, C214, C302 (warn, each with a note) |
| `provenance/loader/selftest.py` | **ALL GREEN (3/3)** — collision guard; 87 dirs / 3,381 files / 0 misc; run_id injectivity (2,055 ids) |
| DB census at finalize | 3,352 run rows, 2,666 current; 75 check definitions, 74 enabled |

An intermediate verify_all run failed one gate ("stale 0.96x present at 1 site"): a guard
false-positive on the *legitimate* Finding-10 fold ratio `0.96` (F1: 91.9538 GPU-h /
95.795 GPU-h = 0.9599) inserted by the closed-loop repair. The guard pattern was narrowed
to the forbidden ×-ratio forms (`0.96$\times$`/`0.96\times`/`0.96x`), fixture-tested
(3/3 stale forms caught, 0 live hits, 0.965 sites excluded), and the suite rerun green.

---

## High-severity findings

### Finding 1 — "Honest held-out calibration" is post-hoc; split contradiction — **FIXED**
- **Changed:** `tex/closedloop.tex` — split redefined ("burst2/6 enter results grading only
  through the forecast-free policies …; forecast policies do replay them … solely as the
  calibration split for the language operating point …, never as evaluation results");
  p70/s6 named the calibration-selected point; p90/s6 stated as "chosen after p70/s6's e13
  failure was inspected, so it is a post-hoc robustness sensitivity on this trace, not an
  independently held-out selection"; "derived, not tuned" scoped to the knee ratio;
  arm-symmetry rescoped; ledger line "(0.82×) by the post-hoc p90/s6 sensitivity".
  `tex/tese.tex` (EN+PT abstracts) "honest calibration" → "calibration selects an
  aggressive point that drops e13, and a post-hoc robustness variant recovers it at
  0.82×". `tex/trace-eda.tex` fig:eda-windows caption (finalize pass): "(so b2 and b6 …
  enter results grading only through forecast-free policies; forecast policies replay them
  solely as the language calibration split …, never as evaluation results)".
- **Evidence:** DB `provenance.llm_run_summary`: eval_p70_s6_week 757.613 ms / 330.3501 GPU-h;
  eval_p90_s6_week 651.140 ms / 7.2536 ms / 440.0415 GPU-h; static 537.4093 GPU-h →
  440.0415/537.4093 = 0.8188; fold_F6_p70_s6 1133.656 ms (fail), fold_F6_p90_s6
  886.423 ms (pass). 70 current forecast-policy calib_burst2/6 runs exist (calibration
  replays are real, so the categorical "never graded" was false as the review said).

### Finding 2 — p50 aggregate-masked SLA failure promoted — **FIXED**
- **Changed:** `tex/closedloop.tex` — "The p50 quantile does not survive per-episode grading
  on this pool either. … clears the week-scale aggregate … but under the joint
  aggregate-plus-episode gate … fails burst3 (2164 ms TTFT p99, 137 ms ITL p99) and burst5
  (1679 ms, 120 ms). The aggregate pass is a calibration false positive …"; "served
  adequately" and the quantile-matters-less inference removed; valid frontier = p70/s6 + p90/s6.
- **Evidence:** DB: eval_p50_s8_week 819.461/13.366/318.069; burst3 2164.190/137.030 (fail
  both); burst5 1679.101/120.314 (fail both); burst1 944.8 / burst4 756.4 pass. Original
  artifact `week_fc_p50.report.json` 827.813 ms / 319.910 GPU-h → "819–828 / 318–320" wording.

### Finding 3 — hybrid not seven-fold robust / deployable / cost-minimal — **FIXED**
- **Changed:** (a) *F1 replay implemented and run*: `simulation/combine_schedules.py` gained
  `--allow-missing` (hybrid degenerates to pointwise max of remaining arms, hard-fails
  otherwise); `simulation/run_encoder_hybrid_folds.sh` hardened (`set -euo pipefail`,
  per-step error checks; the only tolerated condition is the generator's documented
  "no forecast rows cover window F1" refusal). New artifacts
  `simulation/results/encoder_hybrid/folds/F1_hybrid.{sched.json,jsonl.zst,jsonl.stats.json,conv.log}`;
  F1_hybrid == F1_re by construction and by measurement (byte-identical replay,
  p99 589.301 ms, 564,220.8 worker-s). (b) `tex/closedloop.tex` — pure forecast fails two
  whole folds for different reasons (F2 1319 ms coverage failure vs reactive 369 ms; F6=e13
  1264 ms); hybrid "designed after the F6 failure was inspected, a post-hoc repair rather
  than a pre-registered controller"; "seven-fold replay is six informative folds plus one
  designed fallback — no-regression evidence …, not independent workload validation";
  0.76× "under warm-pool readiness"; "cost-minimal among the tested F6 max-combiner
  settings"; no "deployable"/"fold-robust" token remains. (c) `tex/conclusion.tex`,
  `tex/intro.tex`, `tex/tese.tex` abstracts mirror the post-hoc framing.
- **Evidence:** fold hybrid p99 (stats artifacts + DB `encoder_run_summary`): F1 589.301 /
  F2 368.880 / F3 523.020 / F4 589.301 / F5 441.406 / F6 678.660 / F7 589.301 ms — all
  < 1000. Aggregate hybrid 2,944,979.7 ws / 3,869,278.8 ws = 0.7611. F6 combos: h_p50
  1228.6 / h_p70 1015.7 (leaner quantile reopens e13); h70_rho12 575,808.5 ws (0.833×),
  h70_rho10 671,927.3 ws (0.972×); F6_hybrid cheapest passing combiner (0.79× F6 static).

### Finding 4 — 0.76/0.82 headlines outside the provenance chain — **PARTIAL**
- **Done:** (2) complete ingestion: `provenance/loader/load_encoder_hybrid.py` (NEW) ingested
  33 runs / 55 files / 18,156 schedule rows / 12 duplicate-artifact registrations —
  aggregate fc/re/hybrid, all folds, F6 combos, with canonical window/policy/quantile/rho/
  cold-start/actuation identity and sha256 ingest gates; `provenance/loader/load_lang_qsweep.py`
  (NEW) ingested the 9 per-request reruns + burst2 smoke (10 runs). Loader selftest ALL
  GREEN; settle-run changes nothing. Headline now derivable in-DB: 2,944,979.7/3,869,278.4
  = 0.7611. (3) appendix manifest rows added: `tex/apendice.tex` now maps the hybrid family
  (`run_encoder_hybrid{,_folds,_combos}.sh`, `combine_schedules.py`,
  `simulation/results/encoder_hybrid/`, DB runs `encoder_hybrid:*`) and the language
  calibration (`lang_qsweep/`, DB runs `langcalib:*`, `lang_qsweep:*`), plus the A2 cell
  and 235B rows. (4) claim corpus regenerated with 0.76/0.82/hybrid/440.0/330.4 claims
  (campaign task, completed). (5) `verify_all.sh` now carries artifact-read derived-value
  gates: 0.76× (raw 0.76112), 0.82× (raw 0.81882), 440.0, 537.4 — all PASS in the final
  run. (6) containment gate repaired + fixture-tested (see R1). Census sentence in
  `tex/closedloop.tex` rewritten to the timestamped 2,666-run / 75-defined / 74-enabled /
  69-pass / 5-fail form (Finding 9).
- **Open (why PARTIAL):** sub-item (1), git-versioning of the new scripts and artifacts —
  the whole campaign worktree is deliberately uncommitted; committing is the author's
  decision and agent commits were forbidden. Until committed, run rows carry null
  commit identity.

### Finding 5 — reactive language baseline had no cold-start lead — **FIXED** (relabel fallback)
- **Changed:** `tex/baselines.tex` — equal-plumbing sentence replaced; the 14 headline
  language reactive runs are labeled "*instant* workers (no startup lead) — an optimistic
  zero-startup lower bound for reactive control, so their tail-SLA failures below are, if
  anything, conservative"; protocol text scopes language leads to predictive runs + the
  burst1 sensitivity ("this sensitivity, unlike the headline runs, does model the startup
  lead"); summary reads "while violating the tail SLA even with instant workers".
- **Evidence:** DB: 14 current `reactive` runs from `reactive32/`, `count(cold_start_s)=0`;
  `run_32_reactive.sh` has no STARTUP_TIME (`run_replay.sh`: "unset = instant");
  `run_44_riders.sh:33` STARTUP_TIME=60. Max TTFT p99 3,494.726 ms (14/14 tail fail
  reproduces). The rerun-with-lead option was **not** taken (see residual risk).

### Finding 6 — 588 ms "physical service floor" is not a floor — **FIXED**
- **Changed:** `tex/closedloop.tex` — 588 ms recast as "the observed no-queue plateau this
  harness reproduces whenever provisioned capacity keeps the queue empty", with (i) the
  population note (percentile over all requests; 350,168 of 749,601 bear images) and
  (ii) the counterexample ("a same-harness static C=16 run over the same span reads
  565.2 ms, below it"); the additive f(64)+handoff-p99 derivation and "what remains is
  physics" deleted; caption "(not a physical floor)"; limitations "588 ms plateau".
  Mirrors: `tex/conclusion.tex` "observed all-request no-queue plateau", `tex/intro.tex`
  "observed 588 ms all-request plateau".
- **Evidence:** DB `encoder_run_summary`: aggregate44:static_C16 encoder_delay_p99 =
  565.249 ms, requests 749,601, requests_with_images 350,168. The optional image-bearing
  conditional p99 was not inserted (not recomputed from the per-request artifact).

---

## Medium-severity findings

### Finding 7 — ARIMA "matches Chronos" across different origin populations — **FIXED**
- **Changed:** `tex/predictors.tex` — discloses the 300/2,687 subsample asymmetry; reports
  the matched-origin rescore ("ARIMA at 66.8% WAPE against 66.0–66.1% for Chronos and
  66.5% for TimesFM — sub-point gaps a paired origin bootstrap cannot distinguish from
  zero — while Toto with covariates, at 60.9%, beats ARIMA by a statistically significant
  margin"); limitations echo "statistically indistinguishable from Chronos on matched
  origins". Finalize pass repaired the residual clause: "ARIMA edges ahead of the
  classical baselines (naive scores 69.0% on the same 300 origins; Prophet, at 73.3%,
  trails both)". New durable artifact `predictors/matched_origin_rescore_2026-07-26.json`
  (300 origin keys + sha256, per-model WAPEs, B=10,000 paired bootstrap CIs).
- **Evidence (recomputed in this finalize pass):** origin keys regenerated from
  `dynamo_predictors_bench.py` rules — sha256 `0b9644a5…74fc84` matches the artifact;
  matched-300 WAPEs via DB join: chronos/cov 0.661203, chronos/uni 0.660039, timesfm
  0.665152, toto/cov 0.608896, naive 0.689919, ewma 0.719019; ARIMA 0.667506 and Prophet
  0.732828 from `predictors/results_dynamo/{arima,prophet}_15s.json` (both 300/2,687).
  Bootstrap: ARIMA−chronos/cov +0.63 pp CI95 [−4.60, +6.95] (spans 0); ARIMA−toto/cov
  +5.86 pp [+1.11, +12.29] (excludes 0).

### Finding 8 — burst-episode merge bug (onsets, median) — **FIXED**
- **Changed:** `analysis/trace_eda/i_burst_anatomy.py` — merge-spans-first, then recompute
  peak/onset/decay/ramp (mirrors k_episode_clusters); artifacts regenerated
  (`i_burst_anatomy_stats.json`: p50 6.5 min, p10 2.0, n=18; rank-1 onset 404 min, rank-6
  53 min); `simulation/windows.json` burst1/burst6 notes 220→404 / 1→53; figures
  regenerated (`i_burst_onsets`, `eda_i_burst_onsets` incl. the 404-min point).
  Text: `tex/trace-eda.tex` 6→6.5 min + "6 of 18"; `tex/intro.tex` "six and a half
  minutes"; `tex/baselines.tex` onsets 1–404, table rows 404/53, matched-fast-onset causal
  claim removed (burst6 attributed to its 53-min merged onset). Finalize pass: stale
  `tex/closedloop.tex` "onsets of 1–220 minutes" → "1–404" (covered bursts 1/3/4/5 =
  404/1/60/35 min, recomputed from the regenerated artifact); `tex/predictors.tex`
  "arriving 6 minutes late" → "6.5 minutes". DB `eda_burst_episode` i_burst rows verified
  correct (404/48/1/60/35/53) after loader settle.
- **Evidence:** independent CPU recompute from `rates_1min.parquet` with merge-first
  algorithm reproduces the 18 onsets [1,2,2,2,2,2,3,6,6,7,11,13,26,35,48,53,60,404],
  median 6.5, 6/18 ≤ 2 min; top-6 peaks/spans invariant under the fix.

### Finding 9 — "2,623 runs validated by 73 checks" misstates both nouns — **FIXED**
- **Changed:** `tex/closedloop.tex` — "at the 2026-07-26 snapshot … 2666 current run
  records — mostly simulation replays, plus 41 forecasting, 16 EDA, and 10 live-validation
  records — and is exercised by 75 defined automated consistency checks, 74 of them
  enabled, of which 69 passed and five failed at that snapshot (one error-level, four
  warn-level, each carrying a documented note)". "Committed"/"validated by" removed.
- **Evidence:** re-verified live at finalize: 2,666 current / 3,352 total runs; 75/74
  check definitions; `check_all()` → 69 pass / 5 fail (C002 error; C107, C207, C214,
  C302 warn; all with notes). The C214 regression was repaired during the campaign
  (52 pointers backfilled, 8 week labels adjudicated: 69/440 → 17/440 unresolved).

### Finding 10 — fold economics quoted from superseded p90/s8 policy — **FIXED**
- **Changed:** `tex/closedloop.tex` — vintages labeled: "the original p90/s8 edge runs
  0.93–3.81× … while the e13-robust p90/s6 point runs 0.66–1.68× on the same folds (0.96,
  0.69, 0.73, 1.42, 0.66, 0.71, 1.68 on F1–F7), above parity in two of seven, 0.87×
  request-matched in aggregate". `tex/conclusion.tex` — "the published language point, p90
  at conversion scale 8, reads 1.03× and the e13-robust p90/scale-6 point 0.87×".
- **Evidence (re-recomputed at finalize):** fold_F{1..7}_p90_s6 GPU-h 91.954/66.114/69.608/
  136.688/63.105/68.062/160.991 vs 4-GPU same-fold static 95.795–96.000 GPU-h → ratios
  0.9599/0.6887/0.7251/1.4239/0.6574/0.7090/1.6770; 440.0415/503.74 = 0.8736 → 0.87×;
  518.6063/503.74 = 1.0295 → 1.03×.

### Finding 11 — square statistic right, bulk-request characterization false, artifact stale — **FIXED**
- **Changed:** `analysis/trace_eda/j_classes.py` — explicit `nonsquare` class; `single` =
  exactly 1 image; artifact regenerated (text 500,000 exactly; nonsquare 53; frames
  image_share 0.811312). `tex/trace-eda.tex` — 99.9894%, request-frequency vs image-volume
  distinction ("66.0% of image-bearing requests carry exactly one image; it is image
  *volume* … that the bulk grids dominate"), 81.2→81.1%, 93–96→92–96%. Finalize pass:
  `tex/intro.tex` 81.2% → 81.1%. DB `eda_request_class` now carries the corrected six-class
  census (verified post-settle: text 500,000, nonsquare 53, frames 27,169 / share 0.811312).
- **Evidence:** raw-trace recount: image-bearing 500,000; square 499,947 (99.9894%);
  nonsquare 53 (22 distinct); single-image 330,029 (66.0058%); frames requests 27,169 =
  2.7% of all requests (recomputed at finalize).

### Finding 12 — forecast facts not relationally retractable — **FIXED**
- **Changed:** provenance migration (campaign task): `run_id` attached to the forecast fact
  tables + current-only views joined to the run spine; `tex/predictors.tex` prose updated
  ("archived and hash-verified …, and every archived forecast fact carries a run
  identifier in the provenance store's current-run views").
- **Evidence (verified live at finalize):** `provenance.forecast` 22,003,500/22,003,500
  rows with run_id; `forecast_metrics` 41,600/41,600; current views
  (`current_forecast`, `current_forecast_metrics`, `current_quantile_coverage`) filter on
  `runs.is_current`; 0 orphan run_ids (verify_all Gate A PASS).

### Finding 13 — 235B result mixes vintages, lacked appendix mapping — **FIXED**
- **Changed:** `tex/twopool.tex` — 87.7 ms labeled as the wheel-era artifact with the
  source-built 1.3.0 sweep beside it ("reproduces that operating point (86.2 ms) and is
  the vintage that pins the knee: s=2 fails (210.6 ms)"). `tex/apendice.tex` — 235B
  manifest row added mapping both vintages (`simulation/results/235b/…s{1,4,16}.json` and
  the source-built `reports/235b_tp8_s*.report.json`, DB runs `g3_32b:235b_tp8_*`).
- **Evidence:** legacy artifact 87.721685 ms ITL p99; source-built series 86.150977 ms (s1)
  / 210.587850 ms (s2). verify_all Gate B "intact: 235B ITL p99 87.7 ms" PASS.

### Finding 14 — burst5 C8 is a superseding correction — **FIXED**
- **Changed:** `tex/baselines.tex` — "A grid search (…101 points archived…), plus a
  superseding burst5 stability test that corrected its raw grid endpoint (C* 16 → 8; the
  original divergence flag was an endpoint artifact), yields the effective optima per
  window"; drain-boundary sentence distinguishes end-of-arrivals queue from drained replay
  end; caption disclosure retained.
- **Evidence:** DB `v_grid_c_star_effective`: burst5 raw 16 / corrected 8 / superseded,
  correction `burst5:c_star:supersession`, source `verification/rerun-stability-e2e.md`;
  all seven effective C* match the table (6/8/7/7/8/6/2).

### Finding 15 — 7,716 is the dispatch-cap population — **FIXED**
- **Changed:** `tex/twopool.tex` — "The window's 7,716 requests above the 64-image dispatch
  cap — the chunked population, 7,643 of them in the canonical frames class".
- **Evidence:** burst1 slice: NumImages>64 → 7,716; k>10 (≥121) → 7,643; converter
  `requests_chunked=7716` (review cross-check confirmed; wording adopted verbatim).

### Finding 16 — "nothing forecasts single bins" false for 3/4 signals — **FIXED**
- **Changed:** `tex/trace-eda.tex` — "Below the one-minute scale it is the image signal
  that loses forecastability: at one-second cadence its best point forecast reaches 98.8%
  WAPE, essentially the zero-prediction floor — a white shot-noise floor at which
  finer-grained inputs add noise, not information — while the smoother signals retain
  measurable skill (62.9% requests, 81.6% gen, 86.0% ctx)". `tex/predictors.tex` —
  "nothing forecasts single **image** bins", with request skill cross-noted; the
  shot-noise antecedent restored in sec:eda-predictability so predictors' references resolve.
- **Evidence:** DB `current_forecast_metrics` 1 s / point / pooled / common: requests
  0.629113, gen 0.816312, ctx 0.860426, images 0.987610.

### Finding 17 — contamination bound not causal — **FIXED**
- **Changed:** `tex/predictors.tex` — "stays broadly competitive — reassuring indirect
  evidence against large-scale contamination, though not a bound: in the consumed 15 s
  image cell TimesFM trails the best Toto-2 mode by 4.3 WAPE points pooled (6.5 at h=1),
  and a different architecture's score cannot separate contamination from intrinsic model
  differences, so the magnitude of any contamination advantage remains unidentified."
- **Evidence:** 15 s images point: pooled timesfm 81.1026% vs toto/cov 76.7764% (4.326 pp);
  h=1 70.2604% vs 63.7426% (6.518 pp).

### Finding 18 — denominator switching and double-rounding — **FIXED**
- **Changed:** `tex/closedloop.tex` — "moving to the calibration-selected point removes
  36.3% of the p90-edge spend (518.6 GPU-hours)"; robust point "removing 15.2% of the
  p90-edge spend"; p70/s6 prints **0.61×** at all three language sites; cost bullet labels
  1.03× as "that same p90/s8 edge". All 14 remaining `0.62` tokens in the file verified
  encoder-scoped (2,410,754.7/3,869,278.8 = 0.62305).
- **Evidence:** (518.6063−330.3501)/518.6063 = 0.36304; (518.6063−440.0415)/518.6063 =
  0.15149; 330.3501/537.4093 = 0.61471.

---

## Low-severity findings

### Finding 19 — summary drops episode qualification — **FIXED**
- `tex/closedloop.tex` summary: "meets the SLA in aggregate and in each of the four
  declared in-span burst windows at 0.62 times …; the finer daily-fold grain surfaces the
  one missed covered onset, e13, recovered at 0.76× by the post-hoc hybrid."

### Finding 20 — full-trace result lacks canonical window identity — **FIXED**
- `provenance/schema/33_fulltrace_window_backfill.sql` (NEW, idempotent): backfills
  `window_name='fulltrace'` on exactly a13:ft_reactive_L30 / ft_static_C8 / ft_static_C2,
  recording correction IC004 with recomputed operands (3,323,189.5 / 4,838,397.6 =
  0.686837 → the printed 0.687×). Applied: UPDATE 3 / INSERT 1; re-run: UPDATE 0.

### Finding 21 — 2→8 swing is fourfold — **FIXED**
- `tex/baselines.tex`: "a fourfold fleet-sizing swing, the operational consequence of the
  order-of-magnitude workload-rate mismatch of Chapter trace-eda" (8/2 = 4 exactly).

### Finding 22 — "dense N=1–512" overstates off-cap sampling — **FIXED**
- `tex/aiconfigurator.tex` and `tex/apendice.tex`: "a dense N=1–64 sweep plus five off-cap
  probes (N ∈ {96,128,192,256,512})" (matches `vllm_eager_dense.py`, 69-row artifact).

### Finding 23 — "no fixed quantile improves" has two tiny counterexamples — **FIXED**
- `tex/predictors.tex`: "no fixed quantile **materially** improves on the point path …
  the largest gain anywhere is 0.06 WAPE point, at 1-second image bins"; `tex/intro.tex`:
  "no fixed quantile materially improves on a point forecast that is already the median".
  DB census: only two improving cells (chronos p40, 1 s images: 0.0253 / 0.0629 pp).

### Finding 24 — "all analyses ran on GPU" literally false — **FIXED**
- `tex/trace-eda.tex`: "Analyses use GPU-accelerated preprocessing and model kernels
  (cuDF, cuML, CuPy; RTX 5090), with reduced statistics and plotting on CPU" (CPU paths
  confirmed in a_quality.py, i_burst_anatomy.py, k_episode_clusters.py).

### Finding 25 — "no aggregation window" extrapolates — **FIXED**
- `tex/trace-eda.tex`: "burstiness persists at every tested scale, and no tested averaging
  window smooths it away"; "no tested aggregation window (1 s–1 h)" (19 windows in
  `q_multires_tails_stats.json`, exactly 1 s–3600 s).

### Finding 26 — "still-generating" stale state language — **FIXED**
- `tex/closedloop.tex` both sites: "(a16, g2, g3_32b, g6) … an exclusion fixed at the
  2026-07-26 manuscript snapshot because their run populations were not yet frozen"
  (families hold a16 51 / g2 32 / g3_32b 232 / g6 456 current rows).

---

## Reverification findings

### R1 — delivery containment gate false-green — **FIXED** (verified in this pass)
- **Changed (earlier today):** `provenance/verify_all.sh` — the BRE `grep -v '^\+\+\+'`
  filter that silently emptied `$ADDED` was replaced by a structural awk hunk parser
  (`_added_lines()`: skip `+++` headers, keep added lines, preserve leading `+`), guarded
  by an inline parser regression fixture that hard-fails the run if the parser output
  drifts ("containment-gate parser self-test FAILED (regression)"). The two `fold-robust`
  additions were then explicitly adjudicated: the token was removed from the forbidden
  list (dated comment in the script) *and*, independently, the closed-loop repair removed
  every `fold-robust` token from the manuscript.
- **Verified here:** final verify_all run shows no parser self-test failure and
  "post-manuscript defence material contained (none added to results chapters)" **PASS**
  with the gate now actually seeing the diff. The adjacent derived-value section no longer
  hard-codes rounded encoder operands: artifact-read gates recompute 0.62 (raw 0.62305),
  0.76 (0.76112), 0.82 (0.81882), 440.0, 537.4, 0.965 (0.96502), 1.03 (1.02959), 0.687
  (0.68684) — all PASS.

### R2 — burst4 165-s lead outside declared experiment — **FIXED**
- `tex/baselines.tex`: caption "L* = largest *tested* lead at which the SLA holds"; dagger
  footnote marks 165 s as "a supplementary sub-grid cell outside the declared
  {15,30,45,300} s factorial … the 165–300 s interval is unswept, so 165 s is the largest
  tested passing lead, not an identified feasibility threshold". `tex/apendice.tex` now
  maps the A2 generator (`defense/anim/build/gen_a2_fleet.py`) + `defense/anim/data/a2_runs/`
  + DB run `a2:burst4_reactive_L165` (904.739 ms recomputed from the artifact).

### R3 — "image dispersion decays the slowest" false — **FIXED**
- `tex/trace-eda.tex` body+caption: "remains the highest of the four signals at every
  tested window, although it falls 6.7× from 1 s to 60 s (CV² 25.7 → 3.83)" —
  25.713806/3.830447 = 6.713; images are max-CV² at all 19 windows; ratio to requests
  ≥ 11.8 everywhere, so the retained "order of magnitude burstier" survives.

### R4 — "invisible"/"do not co-occur" overstated — **FIXED**
- `tex/trace-eda.tex`: the largest image minute's request rate "does sit above its own p99
  (4.35) but at only 2.7× its mean — an excursion far smaller than the image signal's, and
  one of just five minutes in the week where the two signals' top percentiles coincide";
  caption "moves far less". `tex/related.tex`: "the two signals share only five
  top-percentile minutes". Finalize pass, `tex/intro.tex`: "extremes almost never
  co-occur … essentially disjoint (five shared minutes in the week)". Operands recomputed:
  req mean 1.6534/s, p99 4.35/s, at peak minute 4.4833/s (2.71×, above p99, below weekly
  max 7.8/s); image peak 370.18 = 15.62× mean; overlap intersection 5, Jaccard 0.0248.

### R5 — H≈0.93 does not exclude the daily cycle — **FIXED**
- `tex/trace-eda.tex`: H called "a proxy derived from the 1/f^β spectral slope"; unnotched
  12/8/6-h harmonics disclosed; endpoint sensitivity reported (H≈0.90 at 6 h upper period,
  ≈0.82 at 3 h); "indicative, not an independent Hurst estimate; the robust persistence
  evidence is the autocorrelation contrast itself — 69 versus 9 minutes". Finalize pass,
  `tex/intro.tex`: "autocorrelation half-life is 69 minutes against 9 for requests, and
  its spectral-slope long-range-dependence proxy is the strongest of the four (Hurst
  ≈0.93 versus 0.83)" — operands recomputed from `d_signals_stats.json` (69/9) and
  `f_fourier_stats.json` (0.93249/0.82895).

### R6 — single-source-build wording — **FIXED**
- `tex/tese.tex` bibitem and `tex/related.tex`: "calibrated runs from the load sweeps
  onward use the v1.3.0 source build; the Phase-2 baseline runs use the pinned 1.2.1
  wheel (Appendix ap:artifacts)" — the appendix's defensible scope, used everywhere.

---

## Delivery blockers

### D1 — document declares itself preliminary — **DOCUMENTED-OPEN**
- The preliminary-version note in `tex/tese.tex` (~line 144) is deliberately retained: the
  review's own remediation order says to remove it only after provenance closure and
  institutional formatting, and the institutional template/ABNT front matter are a
  submission-time decision for the author. Its "mapped in the reproduction manifest"
  claim is no longer stale: the appendix now carries the hybrid, language-calibration,
  A2, and 235B manifest rows.

### D2 — tables materially overrun the text block — **FIXED**
- `tex/closedloop.tex`: tab:cl-ewma → \footnotesize + 3 pt \tabcolsep + b1..b5 headers
  (natural width 335.15 pt); tab:cl-aggregate → \footnotesize + 3 pt \tabcolsep
  (383.08 pt); both inside the 390.0 pt text block; data cells byte-identical. The
  appendix 41-pt overflow is gone. Finalize pass removed the two remaining >20 pt
  overfulls: `tex/apendice.tex` env paragraph (\allowbreak in `eda/uv.lock` /
  `eda/pyproject.toml` paths; 22.1 pt → gone) and the `tex/baselines.tex` §7.2 running
  header (\sectionmark{The static optimum}; 23.1 pt → gone). Final build: 6 content
  overfulls remain, worst 12.5 pt (related.tex paragraph) — cosmetic, listed below.

---

## Residual risk (everything PARTIAL / OPEN / accepted-by-fallback)

1. **Git versioning (Finding 4.1).** All campaign scripts, artifacts, tex edits, loaders,
   and migrations are in the uncommitted worktree. Run rows carry null commit identity
   until the author commits. Agent commits were out of scope by rule.
2. **Reactive-baseline relabel, not rerun (Finding 5).** The 14 headline language reactive
   runs remain zero-startup; the manuscript now labels them an optimistic lower bound
   (reviewer's fallback). A STARTUP_TIME=60 rerun of all 14 would upgrade the fallback to
   the primary correction.
3. **Hybrid external validity (Finding 3).** Strict-rewarm and bill-from-order hybrid
   sensitivities and untouched-trace validation do not exist; "deployable" was removed
   rather than re-earned. F1 remains a designed fallback (no forecast coverage), disclosed
   as such.
4. **p90/s6 evidential status (Finding 1).** No untouched trace/window or nested
   validation exists; the point is presented as a post-hoc robustness sensitivity, per the
   reviewer's required wording. Upgrading it to held-out requires a second trace.
5. **Registered check suite still has 5 documented failures** (C002 error-level accepted
   with note: 1/178 median-TTFT recompute outside 1e-3; C107/C207/C214/C302 warn-level;
   C214 reduced 69→17 unresolved, remainder are pre-thesis a11/a16/g1 preflight labels).
   The manuscript census states exactly this.
6. **Presentation materials are stale** (outside thesis tex): `slides/slides.tex` and
   `defense/defense-qa.tex` still carry 81.2% and 93–96% (superseded by 81.1% / 92–96%),
   and defense/anim mirrors of pre-fix onset values may persist. Sync before the defense.
7. **Cosmetic build residue:** 6 overfull hboxes ≤ 12.5 pt (related.tex 12.5, validation
   7.1, apendice 6.9, twopool 4.1/0.4, closedloop 3.9) — visible only under close
   inspection; the institutional reformat (D1) will re-set them anyway.
8. **Workspace docs / DB nits:** analysis/trace_eda REPORT.md/summary.md were updated, but
   other progress notes may still quote pre-campaign numbers; `progress/results-ledger.md`
   older entries retain the superseded "39 passed / DELIVERY-READY" claim as historical
   record (append-only discipline) — the new campaign entry supersedes them.

## Collateral changes made by the finalize pass (beyond tasks 1–3)

- `provenance/verify_all.sh`: N96OLD stale-ratio guard narrowed to ×-ratio forms
  (false-positive on the Finding-10 fold ratio 0.96); fixture-tested.
- `tex/trace-eda.tex` (fig:eda-windows caption), `tex/closedloop.tex` (1–220 → 1–404),
  `tex/predictors.tex` (ARIMA/Prophet clause; 6 → 6.5 minutes), `tex/intro.tex`
  (81.2 → 81.1%; co-occurrence wording; Hurst-proxy wording): cross-chapter residuals
  flagged to finalize by the edit-group verifiers; every number recomputed (operands above).
- `tex/apendice.tex` (\allowbreak) and `tex/baselines.tex` (\sectionmark): overfull-only,
  no content change.
- Re-ran `provenance/loader/load_trace_eda.py` (settle; DB `eda_request_class` and
  `eda_burst_episode` now match the regenerated artifacts).
- This report + the results-ledger campaign entry. No git commit was made.
