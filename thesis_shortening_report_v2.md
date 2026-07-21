# Second thesis shortening and evidence-preservation audit

Date: 2026-07-20  
Reviewed source: current working-tree manuscript at HEAD 2fd4e76 plus the latest uncommitted corrections in tex/tese.tex, tex/intro.tex, tex/closedloop.tex, tex/validation.tex, and tex/conclusion.tex  
Built artifact checked: tex/tese.pdf, 133 pages, generated 2026-07-20 23:37 -03, with no undefined-reference or citation warnings in tex/tese.log  
Scope: analysis only; no thesis source was modified

## Review method

This is a new source-first review, not a restatement of the earlier report. Three independent reviewers examined:

1. front matter, Introduction, Related Work, and Trace EDA;
2. Predictors, AIC calibration, Two-Pool simulation, and the Conclusion;
3. Baselines, Closed Loop, Validation, the Conclusion, appendix provenance, and primary artifacts.

Their findings were checked against the current TeX, the current PDF, archived JSON/CSV/Markdown artifacts, and the previous reduction plan. Disagreements were adjudicated rather than merged mechanically. In particular:

- the predictor context-cap pointer is adequate at artifact level and is not reported as false;
- the baseline-hyperparameter and AIC row-count pointers are reported as weak, not absent;
- issue-time actuation and readiness-time accounting are treated as a real distinction; after the latest Conclusion edit, only one Closed-Loop caption still conflates their terminology;
- the latest 0.965×, live-error, forecast-covered-window, and burst-versus-span edits are incorporated as fixes or partial fixes, not repeated as wholly open findings.

## Executive adjudication

The thesis is scientifically stronger than it was at the first shortening review, but the latest reduction was mostly sentence-level. It reached the R3 page target—137 to 133 pages—while removing only about 912 de-TeXed words from Chapters 1–10, or 3.3%. The R3 plan proposed about 2,190 words, so roughly 42% of that planned textual reduction materialized. Chapter 8 still contains 7,104 de-TeXed words and spans 18 pages; its complete-ledger section alone is about 3,091 words, 43.5% of the chapter.

The correct next move is a structural edit, not another pass of local sentence trimming. A shorter, evidence-complete thesis should:

- preserve one canonical proof chain for each research question;
- correct the remaining scope, accounting, population, and provenance errors before deleting duplicated qualifications;
- reduce Chapters 1–10 from about 27,072 to approximately 19,500–21,000 words;
- reduce Chapter 8 from 18 to about 10–12 pages and the Introduction from 10 to about 6 pages;
- keep the complete document around 123–128 pages if full ledgers are merely relocated, or around 116–122 pages if the ledgers are compacted and machine-readable artifacts remain canonical.

An additional net reduction of approximately 6,000–7,500 main-text words is defensible. That is an estimate, not a page guarantee: figures, floats, institutional front matter, and appendix policy will determine the built-page result.

The chapter-level cut envelopes below identify approximately 6,480–8,750 gross words of opportunity. They are not additive commitments: compact evidence tables, corrected provenance, and retained adverse qualifications will add text back. The expected net reduction is therefore the narrower 6,000–7,500-word range above.

The central argument does not need more evidence volume. It needs fewer repetitions and more precise promotion of the evidence already present.

## What the latest reduction actually achieved

The comparison below uses the pre-R3 source at e9a515e and the current working tree. Counts are produced with detex on each source file.

| Source | Pre-R3 words | Current words | Change | Current page span |
|---|---:|---:|---:|---:|
| Introduction | 3,382 | 3,067 | −315 | 1–10 |
| Related Work | 2,416 | 2,370 | −46 | 11–18 |
| Trace EDA | 2,537 | 2,495 | −42 | 19–30 |
| Predictors | 2,756 | 2,651 | −105 | 31–40 |
| AIC calibration | 2,507 | 2,410 | −97 | 41–50 |
| Two-Pool simulation | 3,363 | 3,230 | −133 | 51–62 |
| Baselines | 1,621 | 1,592 | −29 | 63–68 |
| Closed Loop | 7,337 | 7,104 | −233 | 69–86 |
| Validation | 1,142 | 1,192 | +50 | 87–90 |
| Conclusion | 923 | 961 | +38 | 91–94 |
| **Chapters 1–10** | **27,984** | **27,072** | **−912 (−3.3%)** | **94 pages** |
| Front-matter source | 2,376 | 2,370 | −6 | roman pages |
| Appendix source | 1,769 | 1,764 | −5 | starts at 95 |

The growth in Validation is justified: the latest source now discloses the live success/error populations. The problem is not that every chapter failed to shrink; it is that the largest structural opportunities were left substantially intact:

- Closed Loop achieved 233 of its planned 500-word reduction.
- Introduction achieved 315 of 480.
- Related Work achieved 46 of 225.
- Two-Pool achieved 133 of 280.
- The appendix achieved 5 of 80.
- Validation and Conclusion grew because evidence and precision were added.

The PDF reduction from 137 to 133 pages therefore reflects a useful first pass, but not the full shortening opportunity.

## Status of the first report’s corrections

| Earlier finding | Current status | Adjudication |
|---|---|---|
| burst2 and burst6 were given forecast verdicts despite lying outside forecast coverage | **Fixed in the body; promoted scope improved but not enumerated** | tex/closedloop.tex:43-50 and :530-532 now exclude forecasts. tex/conclusion.tex:49-51 now says “forecast-covered,” but does not name the five-window/four-lead population. |
| “every burst episode” meant only four forecast-covered bursts | **Fixed in the main result; promoted scope still partial** | tex/closedloop.tex:288-293 says all four forecast-covered episodes. tex/conclusion.tex:64-65 still says “inside every episode.” |
| “most forecastable” confused persistence with absolute error | **Core body fixed; one promoted restatement remains vague** | tex/related.tex:273-283 now says persistent despite the largest per-bin error. tex/conclusion.tex:74-81 again calls the signal “most persistent and forecastable.” |
| Validation described three SLA metrics | **Fixed** | tex/validation.tex:54-63 and :151-163 distinguish TTFT/ITL from replica-time and now disclose failed requests. |
| TP1×4 generalization exceeded the displayed table | **Wording fixed; new artifact mismatch found** | tex/baselines.tex:101-110 now says five tabulated windows. The burst5 cells still come from C=16 artifacts while the caption claims the corrected C=8 optimum. |
| 0.96× lacked language-model and denominator scope | **Arithmetic fixed; headline scope partial** | All manuscript occurrences are now 0.965×. The detailed body is correct; the Abstract, Resumo, and Conclusion still omit Chronos-p90 and the same-span time-matched TP2×2 denominator. |
| 0.62× lacked span, unit, and denominator | **Body and Conclusion improved; Introduction RQ remains contradictory** | tex/closedloop.tex:343-405 and :731-763 are precise. tex/conclusion.tex:64-72 now separates burst-window cost from 5.60-day savings. tex/intro.tex:206-214 still asks and answers a combined per-burst compliance-and-cost claim. |
| “physically validated” implied a complete live encoder service | **Detailed scope fixed; abstracts remain broad** | tex/apendice.tex:170-186 and tex/validation.tex:151-157 are precise. tex/tese.tex:55-57 and :95-98 remain broader than the standalone-forward evidence. |
| no limitation reversed result direction | **Fixed** | tex/conclusion.tex:91-97 now retains request-matched 1.03× and fold sensitivity. |
| simulated output was called measured behavior | **Fixed** | The platform result is now described as simulation under calibrated timing. |
| language-week experiment absent from manifest | **Fixed locally; manifest incomplete elsewhere** | tex/apendice.tex:292-297 maps simulation/results/llm_week. Several retained results still lack direct rows. |

## Corrections required before more shortening

These are ordered by risk. The first five affect the thesis’s promoted claims; they should be normalized before repeated qualifications are removed.

### P0.1 — The Introduction’s RQ4 still asks and answers a claim the results refute

The Introduction asks whether per-pool provisioning improves both “SLA compliance and GPU-hours over the best static configuration and a reactive planner during burst episodes,” then answers yes (tex/intro.tex:206-214). The results say the opposite for burst-window encoder cost:

> “every autoscaling arm costs more than static” within each graded burst window (tex/closedloop.tex:739-747).

The 0.62× saving exists over the 5.60-day span because calm periods amortize capacity reduction; it is not a per-burst saving. The language result is near break-even and denominator-sensitive. The latest Conclusion now states the burst-versus-span reversal at tex/conclusion.tex:64-72, which is a material fix. The contradiction remains in the Introduction’s RQ wording and its immediate “yes,” and the Chapter 8 Summary still says only that “RQ4 is answered affirmatively” at tex/closedloop.tex:898-904.

Shortest defensible RQ wording:

> **RQ4 — Closed-loop payoff.** Can pool-specific provisioning improve burst-episode tail-SLA compliance over reactive control, and what provisioned-cost trade-off does it produce relative to deployable static fleets?

Shortest defensible answer:

> Compliance improves, but cost does not uniformly: the encoder forecast costs more than static in every graded burst yet provisions 0.62× the deployable static C=8 fleet over the 5.60-day span; the Chronos-p90 language schedule is near break-even and denominator-sensitive.

This correction also removes the ambiguous phrase “best static.” Use the manuscript’s defined deployable/grid-SLA-minimal C=8 fleet and keep it distinct from each window’s oracle C*. Do not import a static optimum or ratio computed over a different time span into the 5.60-day headline.

### P0.2 — One Closed-Loop caption still conflates schedule actuation with worker-time integration

The authoritative accounting convention is explicit:

> “The encoder pool bills from readiness, its cold-start reported separately” (tex/baselines.tex:21-32).

The latest Conclusion no longer says that encoder work is billed at forecast issue time; its “issue-time actuation, warm-pool readiness” wording at tex/conclusion.tex:64-72 is correct. One current caption still blurs the two concepts:

- tex/closedloop.tex:351-358 says “Forecast worker-time is actuated on forecast issue time.”

Issue time controls when the capacity order or schedule decision is made. Readiness time controls when encoder worker-time begins to accrue. Cold-start warm-up is reported separately.

Canonical replacement:

> Forecast schedules use issue-time actuation; encoder worker-time is integrated from readiness under the warm-pool model, with cold-start warm-up reported separately.

This is now a localized accounting-language fix rather than a promoted contradiction, but it should be corrected before the surrounding explanation is shortened.

### P0.3 — 0.965× is now numerically correct but not self-scoping

The latest edit correctly replaced every manuscript occurrence of 0.96× with 0.965×. The artifact stores 518.606345 H100 GPU-hours and 483,668.382 seconds. A four-GPU TP2×2 fleet over that duration costs 537.409314 H100 GPU-hours, giving:

\[
518.606345 / 537.409314 = 0.9650118.
\]

The detailed explanation at tex/closedloop.tex:295-307 and :755-763 is correct. The shorter promoted forms remain incomplete:

- tex/tese.tex:65-67 and :108-112 say only “near-break-even, 0.965×”;
- tex/conclusion.tex:70-71 says “0.965× its burst-sized static shape.”

A cost is not relative to a “shape,” and the result is not common to every TSFM. Toto and TimesFM preserve the pass verdict but cost 625 and 641 H100 GPU-hours. Request-matched normalization gives 1.03×.

Canonical promoted sentence:

> Over the 5.60-day forecast-covered span, the Chronos-p90 language schedule passes at 518.6 H100 GPU-hours—0.965× a time-matched static TP2×2 reference of 537.4 H100 GPU-hours; request-matched normalization gives 1.03×.

The Abstract can omit the final 1.03× clause if the Conclusion’s bounded-cost sentence retains it, but it must still say Chronos-p90 and time-matched TP2×2.

### P0.4 — “Every window,” “every lead,” and “every episode” remain underspecified

The decisive encoder factorial is:

- five forecast-covered windows;
- three TSFMs;
- four issued leads: 15, 30, 45, and 165 seconds;
- 60 cells per readiness model.

The episode result covers four in-span burst episodes. burst2 and burst6 are outside the forecast archive; the trace contains 18 detected episodes and six selected major bursts.

Current wording at tex/conclusion.tex:49-51 has improved to “every forecast-covered window at every tested cold-start lead,” but it still does not enumerate the population. tex/conclusion.tex:64-65 still says “inside every episode.” Replace both with:

> all five forecast-covered windows at all four issued leads, including all four in-span burst episodes.

This adds very little text and prevents a shortened headline from expanding its population.

### P0.5 — Abstract and Resumo are not yet a compact semantic pair

The English Abstract is about 263 de-TeXed words and the Resumo about 340. They should be rewritten together to approximately 200–220 words each, sentence-for-sentence in semantic scope.

Current problems:

- “forecast-covered week” at tex/tese.tex:65-67 and :108-112 should be “5.60-day forecast-covered span”;
- the English abstract omits the one-window live population while the Portuguese says “the hardest burst”;
- neither says that the anchor is one live run per policy;
- “physically validated” at tex/tese.tex:55-57 and :95-98 is broader than the standalone eager-vLLM vision-tower forward described at tex/apendice.tex:170-186;
- the English version says the AIC contribution is a draft PR while the Portuguese presents it as already contributed;
- the Portuguese text causally turns persistence into predictability more strongly than the English evidence supports;
- one parenthetical joins 0.62× encoder worker-time and 0.965× language H100 GPU-hours despite their different hardware, units, and denominators.

The compact pair should retain only:

1. trace scope and per-pool signal decoupling;
2. the zero-shot forecast result with its fixed-baseline/common-span scope;
3. separate encoder anticipation and held-signal language conversion mechanisms;
4. 0.62× over 5.60 days and Chronos-p90 near-break-even on the language pool;
5. standalone-forward physical anchoring and one-window mocked-engine live-control anchoring.

Remove draft-PR workflow and most saturation-mechanism detail from the abstracts. Remove the draft-status note at tex/tese.tex:124-139 from the defense/submission build; it is project status, not scientific evidence.

### P1.1 — Table base-tp has a burst5 provenance mismatch

The caption says every row uses the window’s static-optimal encoder count (tex/baselines.tex:126-130). The corrected burst5 optimum is C=8, but the archived burst5 values 1,316 ms and 781 ms come from:

- simulation/results/grid/reports/grid_llm_burst5_C16_N4_aic.report.json;
- simulation/results/grid/reports/grid_llm_burst5_C16_N2_TP2_aic.report.json.

No matching C=8 TP-comparison artifacts are archived. The numerical TP1×4-versus-TP2×2 comparison is supported at C=16; the claimed corrected per-window-optimal context is not.

Choose one:

- rerun the burst5 comparison at C=8; or
- relabel the table as using the “archived composed-trace encoder count” and stop claiming corrected per-window optimality.

Do not move or compact this table until the provenance is repaired, because shortening its caption would make the mismatch harder to detect.

### P1.2 — Evidence offloading is not uniformly supported by the manifest

The shorter manuscript increasingly replaces inline settings and results with “Appendix” pointers. Those pointers must be classified precisely.

| Promise in the body | Status | Actual evidence |
|---|---|---|
| per-model context caps, tex/predictors.tex:45-48 | **Adequate at artifact level** | tex/apendice.tex:233-237 maps predictors/benchmark.py and output Parquets; the generator fixes and stores the caps. |
| exact fixed-baseline settings, tex/predictors.tex:68-70 | **Weak; introduced by R3 shortening** | benchmark.py is mapped, but EWMA/Holt–Winters numerical defaults live in predictors/ewma.py:68-75 and predictors/holt_winters.py:80-89; no named archived configuration is mapped. |
| full benchmark wall clock, tex/predictors.tex:82-86 | **False pointer** | runtime logs under predictors/results/logs are not mapped. |
| Dynamo per-configuration results, tex/predictors.tex:161-169 | **False pointer** | evidence is under predictors/results_dynamo, ledgered at progress/results-ledger.md:298-303, but absent from the appendix. |
| additive-component ranges, tex/predictors.tex:203-214 | **False pointer** | actual artifact is predictors/results/metrics/additive_structural_ablation.json, ledgered at progress/results-ledger.md:333-338, but not mapped. |
| AIC raw/infilled row counts, tex/aiconfigurator.tex:100-114 | **Weak** | tex/apendice.tex:248-250 maps the infill state, but not the reported counts; the counts are in the results ledger. |

The manifest also says it maps each retained figure and table (tex/apendice.tex:8-14), but result-chapter rows are missing for:

- tab:base-tp;
- tab:cl-ewma;
- fig:cl-framework-diff;
- tab:cl-ledger-enc;
- tab:cl-ledger-llm;
- tab:cl-ledger-joint.

Direct rows are also missing for the all-four language episode replays, controller inference cost, daily folds, and the population behind the per-burst cost ranges.

A shorter thesis can rely more heavily on the manifest only after these mappings are made exact. Add rows for retained evidence; do not add a row for a figure or table that is deleted.

### P1.3 — Daily-fold evidence is one-sided

The current limitations section reports the encoder fold range and one failure (tex/closedloop.tex:873-896), but omits the adverse language-fold result. The archived language forecast/static ratios are:

| Fold | Ratio |
|---|---:|
| F1 | 1.276× |
| F2 | 1.101× |
| F3 | 0.931× |
| F4 | 1.709× |
| F5 | 3.808× |
| F6 | 1.022× |
| F7 | 2.144× |

Thus the language ratio ranges 0.93–3.81× and is more expensive than the feasible static comparator in six of seven folds (defense/anim/data/g4_folds/folds_table.md:10-16).

The encoder 0.47–1.10× range is against fixed C=8 as an accounting reference. F3’s C=8 row has p99 465.1 ms but is marked infeasible because the truncated fold ends with a small non-empty queue; no same-fold C* is reported. The prose must not imply that every same-fold C=8 denominator is independently feasible.

Retain one compact two-pool fold sentence or a small limitations table. This adverse result is more important than the full per-fold ledger.

### P1.4 — Per-burst cost ranges omit their evaluated arm population

tex/closedloop.tex:739-743 reports forecast ranges of 1.80–2.90× versus C=8 and 2.06–3.32× versus per-window C*. The sentence does not say that the range is approximately over the multi-model warm-readiness arms at issued leads 15, 30, and 45 seconds, excluding the 165-second arm.

Either name that population or report the canonical Chronos-p90, rho=15, L=30 warm arm:

- 2.25–2.63× versus C=8;
- 2.28–3.01× versus per-window C*.

A promoted numerical range without its arm population is not evidence-complete.

### P1.5 — Predictor claims lose cadence and comparator qualifiers when promoted

The exact p90 coverage 0.88–0.90 is established at one-minute resolution (tex/predictors.tex:253-265), but the Summary, Introduction, and Conclusion call this “provisioning cadence.” The closed loop consumes 15-second forecasts, so that phrase is ambiguous. Say “at one-minute cadence.”

The common one-minute evaluation span is only the final 33.4 hours and is burst-heavy (tex/predictors.tex:45-57). The classical baselines are fixed-parameter and context-capped (tex/predictors.tex:323-326). Promoted claims that TSFMs beat “every classical baseline” in all 20 cells should therefore read:

> all tested fixed-parameter classical baselines on their common evaluation spans.

This qualifier should be stated once in the Abstract/Introduction and once in the RQ2 answer, not repeated in every predictor subsection.

### P1.6 — Several broad statements should be narrowed while being shortened

- tex/related.tex:95-100 introduces HPA custom metrics and KEDA event sources, then says “All watch the one request stream.” That is too broad as an API-capability claim. Limit it to the reviewed default/model-serving configurations.
- tex/related.tex:158-167 says “every system above” uses one text request/token stream. This is too broad after discussing general-purpose custom metrics. Name the closest model-serving systems instead.
- tex/related.tex:273-283 says no prior work states or tests the property without “to our knowledge,” although the following narrow precedence claims use that hedge.
- tex/trace-eda.tex:238-242 concludes there is “one burst type” after identifying a mixed-composition outlier. Say “frames-dominated episodes plus one mixed-composition outlier.”
- tex/trace-eda.tex:115-134 and :386-391 extrapolate from measured 1-second-to-1-hour Fano factors to “any scale,” “every scale,” or “no aggregation window.” Say “across the tested 1-second-to-1-hour range”; the spectral result can separately support longer-range dependence.
- tex/intro.tex:390-392 says band shape, “not forecast accuracy,” is load-bearing. Use “not point accuracy alone.”
- tex/conclusion.tex:15-22 says RQ1 requires both more replicas and a fleet-shape change. The vision failure yields to more encoder workers; only the language TP1 prefill floor requires a TP-shape change (tex/twopool.tex:287-309).
- tex/intro.tex:283-284 labels the seam as one 196×4096 tensor per image, while the full Qwen3-VL handoff includes the main stream plus three DeepStack projections (tex/twopool.tex:143-159). Label the arrow “modeled main stream” or show the full 4× payload.

### P2 — Smaller consistency issues

These can be fixed during the structural edit:

- tex/closedloop.tex:624-628 says forecast ITL is approximately 5.1 ms on all five windows; the table spans 5.1–6.3 ms.
- tex/closedloop.tex:823-828 says “remaining windows” were not replayed end-to-end, while tex/closedloop.tex:288-293 says all four covered bursts were replayed. Name burst2, burst6, and calm explicitly, or delete the sentence.
- tab:cl-ewma prints 588 ms while the verification harness stores 589.301 ms; the main issue-time artifact stores 588.37 ms. Either print 589 for the verification row or explain the sub-1% cross-harness normalization.
- tex/aiconfigurator.tex:91-114 reports a raw snapshot of 7,679/34,326 rows, while :351-353 summarizes 7,760/34,710 after infill. Call the latter the load-bearing simulation snapshot rather than saying the model “now rests” on it without a snapshot label.
- tex/aiconfigurator.tex:241-249 points worker-grid and capacity-frontier details to Two-Pool, but the worker grid is in Baselines and the rating frontier in Closed Loop.
- the 3.1% H100 beyond-grid caveat is repeated in AIC and Two-Pool; Two-Pool should own it.
- the H100 3.1% share is under the trace-token convention; a Qwen-consistent recount is not reported.

## The evidence spine that must survive

The thesis can be much shorter if each research question retains one canonical chain rather than every table and interpretive repetition.

| RQ | Core claim | Canonical evidence to keep in the main text | Qualification that must remain |
|---|---|---|---|
| RQ1 | request rate poorly carries vision demand; the pools saturate differently | R² 0.123 versus 0.654; persistence/CV² table; extreme Jaccard 0.02; tab:sim-knees | one seven-day trace; arrival-stamped generated tokens are offered work; tested-scale and topology boundaries |
| RQ2 | zero-shot TSFMs retain a modest edge and usable lead; p90 supplies headroom | causal rolling-origin/common-span protocol; tab:pred-wape; horizon result; one-minute p90 coverage | fixed-parameter baselines; 33.4-hour burst-heavy one-minute common span; image has worst absolute per-bin error; lower band is not calibrated |
| RQ3 | encoder timing is silicon-anchored; timing-model sensitivity is quantified; live control reproduces offline verdicts | matched vLLM N≤64 bound; tab:sim-poly-aic; tab:val-anchor with success/error counts | standalone forward only; H100 timing not independently measured; mocked engines; one hardest window, two policies, one live run each |
| RQ4 comparator | static and reactive baselines share mechanics and expose different failure modes | tab:base-grid; compact reactive encoder table; reactive language result | pool-specific hardware/accounting; order-time language billing versus readiness-time encoder billing; repair base-tp provenance |
| RQ4 encoder mechanism | p90 passes the five-window/four-lead issue-time factorial where p50 and same-signal reactive fail | compact factorial summary; compact EWMA/headroom ablation; tab:cl-aggregate | issued leads 15–165 s; warm versus strict re-warm; standing headroom, not clean onset detection |
| RQ4 language mechanism | the held signal passes only through tail-aware belief-to-knee conversion | tab:cl-triad; compact language-week table | held cursor, not second anticipation; Chronos-p90/time-matched scope; alternate TSFMs cost more |
| RQ4 economics | encoder saves over 5.60 days, not within bursts; language buys compliance near break-even | tab:cl-aggregate; one compact joint aggregate/burst3 table; denominator sentence; compact two-pool folds | every burst-window encoder arm costs more than static; request-matched language ratio 1.03×; one encoder fold fails; never sum RTX and H100 cost |

The latest Validation error disclosure belongs inside the spine. Table val-anchor should retain that the forecast run completed 3,092 of 3,093 scheduled requests and the reactive run 3,089 of 3,093; latency verdicts are conditional on successful responses and do not grade availability.

## Recommended shorter structure

### Front matter and Introduction

Target: remove about 900–1,200 words across the front matter and Introduction.

- Rewrite Abstract and Resumo as semantic mirrors of 200–220 words.
- Remove the draft-status note for defense/submission.
- Keep one thesis statement. The preferred version is the formal statement at tex/intro.tex:164-179, rewritten to separate burst compliance from span-level economics. Turn the early result preview into neutral problem setup; do not retain both as full thesis claims.
- Present the RQs as questions only. Their present inline answers repeat the Conclusion.
- Keep the architecture figure after correcting the seam-payload label; let it replace nearby architecture prose.
- Give each contribution one novelty clause, one method clause, and at most one numerical result.
- Convert scope/limitations to a compact matrix.
- Reduce the chapter roadmap to one sentence; the table of contents already supplies navigation.

Target: Introduction about 6 pages rather than 10.

### Related Work and Trace EDA

Target: remove about 1,100–1,500 words combined.

Related Work:

- organize systems by watched signal and signal-to-capacity conversion rather than one paragraph per system;
- retain the positioning table with an explicit evaluation boundary for this thesis;
- keep three narrow “to our knowledge” precedence claims;
- delete the repeated thesis inversion around the table once the table and three claims are self-contained.

Trace EDA:

- retain trace construction, square-grid/nonconstant-token facts, persistence, decoupling, onset, tested-scale overdispersion, resolution loss, and extreme Jaccard;
- retain the seven-day signal view and the figures that carry causal interpretation;
- move exploratory clustering, detailed ACF/negative tests, secondary multiresolution plots, and redundant window visualizations to supplementary evidence;
- state the tested 1-second-to-1-hour range exactly;
- delete the repeated Summary once the following chapter’s opening supplies the transition.

Targets: Related Work about 5 pages; Trace EDA about 7–8.

### Predictors

Target: remove about 400–600 words.

- keep causal rolling-origin evaluation, common-span bias, tab:pred-wape, horizon persistence, one-minute p90 calibration, and the operational forecast figure;
- move model-registry catalogs, detailed Dynamo per-config results, full covariate table, and additive-decomposition cells after direct manifest mapping;
- retain one exact sentence for the ±0.4% covariate finding and one for the failed additive decomposition;
- state fixed-parameter/common-span qualifiers once;
- merge the quantile interpretation, forecast-as-signal explanation, and Summary so the same “headroom, not point correction” claim appears once.

Target: about 7 pages rather than 10.

### AIC calibration and Two-Pool simulation

Target: remove about 1,000–1,400 words combined.

- AIC should own collection state, interpolation/composition, one unified physical-forward validation, and snapshot provenance.
- Two-Pool should own simulation architecture, calibrated-versus-polynomial sensitivity, saturation knees, burst queue mechanism, token-convention sensitivity, and the H100 beyond-grid caveat.
- combine raw/infilled/current row-count descriptions into one snapshot table;
- eliminate the duplicate 3.1% H100 caveat and duplicate vLLM/HuggingFace validation narrative;
- keep the calibrated-timing table, saturation table, and burst queue figure;
- replace repeated limitation prose with a compact matrix of timing, token, handoff, topology, and workload boundaries.

Target: 14–15 pages combined rather than 22.

### Baselines

Target: remove about 200–300 words.

- keep tab:base-grid and the reactive encoder result;
- retain the reactive language failure and TP-shape mechanism in compact form;
- after repairing burst5 provenance, move the full base-tp table to the appendix or reduce it to a one-row five-window range/pass summary;
- state the two billing conventions once and refer back to them.

Target: about 4–5 pages rather than 6.

### Closed Loop

Target: remove 2,500–3,200 words.

Current approximate composition:

| Material | Words | Decision |
|---|---:|---|
| chapter setup and controller | 445 | keep, merge with protocol |
| encoder mechanism | 1,158 | keep decisive factorial/ablations, compact |
| language mechanism | 888 | keep held-cursor conversion and triad |
| week aggregate/economics | 659 | keep, correct billing and range populations |
| complete evidence ledgers | 3,091 | compact or relocate; 43.5% of chapter |
| limitations and summary | 862 | keep adverse facts, deduplicate |

Keep in full in the main narrative:

- tab:cl-triad;
- tab:cl-aggregate;
- the causal request-identity join rule: join per request before computing percentiles; never add percentiles;
- the per-burst-versus-span cost reversal;
- the request-matched 1.03× language denominator;
- adverse daily-fold directions.

Keep as compact summary tables:

- encoder p90/p50 pass counts by readiness model and four issued leads;
- EWMA/reactive/headroom verdicts and aggregate cost;
- Chronos/Toto/TimesFM p90, p50, reactive, and time-matched static language-week rows;
- joint aggregate plus burst3 only;
- two-pool daily-fold ranges.

Move or replace:

- full encoder, language, and joint ledgers;
- detailed controller-cost inventory;
- evidence-volume prose at tex/closedloop.tex:789-809;
- full daily-fold cells.

Delete fig:cl-framework-diff unless it is made to replace a comparable amount of prose. It repeats forecasting, live-validation, and closed-loop conclusions, has a long argumentative caption, and lacks a direct manifest row. If retained, drastically shorten the caption and delete the corresponding prose.

Target: about 10–12 pages rather than 18.

### Validation

Target: remove about 200–300 words while retaining the latest error disclosure.

- keep tab:val-anchor, success/error populations, one paragraph establishing demand/decision agreement, and the exact one-window/two-policy/mocked-engine/one-run scope;
- move most live-stack engineering diagnostics to a supplementary subsection;
- retain one sentence naming the discovered divergences because they are useful platform findings;
- do not collapse “latency pass” into platform availability: failed-response counts must survive.

Target: about 2–3 pages rather than 4.

### Conclusion

Target: remove about 180–250 words.

- answer each RQ once with exact populations and denominators;
- delete “The thesis statement, revisited” at tex/conclusion.tex:74-81; it duplicates the four RQ answers and reintroduces “best static” and “most forecastable” ambiguity;
- move the already-completed negative structural-predictor experiment out of Future Work at tex/conclusion.tex:110-111;
- keep one bounded limitations paragraph containing the 5.60-day span, request-matched 1.03×, encoder fold failure, standalone-forward boundary, mocked-engine live boundary, and one-trace scope;
- present future work as three short items.

Target: about 2–3 pages rather than 4.

## Adjudication of the main structural choices

### Keep one explicit thesis statement

The thesis benefits from an explicit statement, but not from the same statement in the opening preview, formal quotation, contribution list, Chapter 8 Summary, and Conclusion. Keep the formal statement after rewriting its economic scope; remove the later “thesis statement, revisited.”

### Compact ledgers rather than merely moving them

Moving all ledger tables verbatim shortens Chapter 8 but not the complete document. It is the conservative option when a committee requires every cell in the PDF. The recommended option is to keep machine-readable artifacts canonical, map them exactly, and publish compact appendix tables containing populations, extrema, pass counts, and adverse cells. This preserves evidentiary completeness while reducing the complete document.

### Add provenance rows even while cutting prose

Manifest additions are not counter to shortening. A precise one-row artifact mapping can replace paragraphs of inline configuration and makes evidence offloading legitimate. The current false/weak pointers must be repaired before their supporting prose is removed.

### Preserve adverse results, not every cell

The following must stay visible even if their full ledgers move:

- encoder autoscaling costs more than static in every graded burst;
- language cost is 1.03× under request matching;
- the language fold ratio is above one in six of seven folds;
- one encoder fold fails;
- live latency metrics exclude one forecast and four reactive failed responses;
- the 4× DeepStack payload violates the modeled handoff bound for every policy on the default link;
- p50 fails all 48 week-scale encoder cells;
- the language result is conversion evidence under a held signal, not a second anticipation experiment.

These facts bound the headline more efficiently than many pages of favorable cells.

## Recommended editing order

1. **Freeze canonical claim sentences.** Correct the Introduction’s RQ4, the remaining actuation caption, the 0.965× scope, five-window/four-episode populations, and physical/live boundaries.
2. **Repair provenance.** Resolve base-tp burst5 and add or correct manifest rows for every retained quantitative result.
3. **Build compact result tables.** Create the encoder-factorial, language-week, joint, and two-pool fold summaries.
4. **Cut Chapter 8 structurally.** Replace full ledgers and repeated interpretation only after the compact evidence exists.
5. **Rewrite Abstract/Resumo, Introduction, and Conclusion together.** Use the same canonical claim vocabulary and denominators.
6. **Compress background and methods.** Remove catalogs and duplicate validation/limitation narratives.
7. **Rebuild and verify.** Measure the actual PDF rather than inferring page savings from word counts.

## Verification checklist for the shortened manuscript

- No unqualified “every window,” “every episode,” “covered week,” “best static,” or “physically validated” remains in a promoted claim.
- Every 0.62× occurrence states or inherits the 5.60-day encoder C=8 denominator.
- Every promoted 0.965× occurrence identifies Chronos-p90 and the same-span time-matched TP2×2 H100 reference.
- Issue time is used only for forecast/order actuation; encoder billing starts at readiness.
- Abstract and Resumo are semantic mirrors and keep the same live/physical boundaries.
- Every retained quantitative table/figure has a direct manifest row and primary artifact.
- base-tp burst5 either has a C=8 rerun or is relabeled as C=16 archived context.
- Predictor promotions retain one-minute/common-span/fixed-baseline qualifiers.
- Validation retains scheduled, successful, and failed request populations.
- Fold limitations report both pools and identify fixed C=8 as an accounting denominator.
- No RTX-5090 worker-time is summed with H100 GPU-hours.
- Joint p99 is computed after request-identity joining, never by summing pool percentiles.
- detex counts and PDF page spans are recomputed after editing.
- The final LaTeX log has no undefined references/citations, and every moved label still resolves.

## Final assessment

The thesis can be shortened substantially without weakening its evidence. The current 133-page version has already corrected several important problems, including the 0.965× arithmetic and live-response populations, but it still spends too much space repeating the thesis statement and enumerating result cells.

The strongest shorter version would keep a 19,500–21,000-word main narrative, a 10–12-page Closed-Loop chapter, and one canonical proof chain per RQ. The evidence remains complete if compact tables retain populations, comparators, adverse cells, and denominators, while the manifest directly maps each retained result to its artifact.

Before cutting, fix the remaining claim boundary: the Introduction’s RQ4 must separate burst compliance from span-level economics, and the Closed-Loop caption must distinguish issue-time schedule actuation from readiness-time worker accounting. The latest Conclusion already makes both distinctions substantially better. Once those formulations are canonical, the rest is primarily structural compression.
