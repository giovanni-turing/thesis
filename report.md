# Mediated Review of `tex/tese.tex`

## Resolution log — 2026-07-08 pass

Every item below was checked against the tree and artifacts (several of
this review's factual claims were themselves verified computationally —
noted where the verdict differed from the claim). Statuses as in
THESIS-FEEDBACK.md's log: DONE / DONE-BY-DATA / SCHEDULED / DEFERRED /
REJECTED.

| Item | Status | Resolution |
|---|---|---|
| B0.1 placeholders | **DONE** | 8/9 resolved with content from the completed experiments; 1 kept by design (validation anchors) |
| B0.2 preview root | **DONE** | `tese.tex` is the submission root pro tem: real title, abstract+resumo, LoF/LoT/abbreviations, hyperref, appendix; institutional class + bib migration deferred as one later switch (documented in source) |
| E1.1 validation scope overstated | **DONE** | Attention-only agreement scoped everywhere ("≈3%", strictly 3.2%); composed forward labeled model-derived with the attributed 1.4–1.6× band; "production sits between" → expectation + scheduled measurement |
| E1.2 counts inconsistent | **DONE** | "raw slice" (7,679/34,326; 7.82 ms) vs "infilled slice" (7,760/34,710; 8.16 ms) defined once; every use labeled; simulator consumes the infilled slice (stated) |
| E1.3 long-context extrapolation | **DONE-BY-DATA** | Share computed: 3.14% of requests exceed the 16,384-token grid (max ≈149k). Disclosed in Ch.5 (stratum-3) and Ch.6 limitations, incl. that burst TTFT tails live in the extrapolated region |
| E1.4 srcbuild provenance | **DONE** | Table caption names the source-built runtime; appendix manifest maps the table to `results/srcbuild/*` |
| E1.5 duplicates not dropped | **DONE (review was right)** | Verified: loaders sort but retain; only `a_quality.py` counts (151). Prose changed to "retained; ties processed in file order" |
| E1.6 forecast archive | **DONE (review was right)** | Recounted: 26 files, 21,404,640 rows (20,749,440 on common span). All "19.2M" mentions replaced with exact figures |
| E1.7 stale burst numbers | **DONE (mixed)** | Verified per-number: queue peak 4,701 and 805 s>1,000 were already correct; stale were forwards (83,432→ 56,510 chunk units / 83,376 executed forwards), max forward (315→316.4 ms), worst second (975→2,726). Prose rewritten from the current artifact |
| C2.1 estimator agreement | **DONE** | = feedback E1: Hurst=(1+β)/2 identity disclosed; "agree on this ordering" removed; contrast restated as images-vs-requests |
| C2.2 spectral self-contradiction | **DONE** | "rejects any *non-harmonic* sub-diurnal line — 12/8/6 h are harmonics of the diurnal fundamental" |
| C2.3 Fano unbounded | **DONE** | "keeps growing across the measured range… a seven-day record cannot establish asymptotic growth" |
| C2.4 heavy-tail qualifications | **DONE** | Operational definition at first use; Hill estimator + top-percentile threshold + no-GoF-claim stated |
| C2.5 "not derivable" | **DONE** | Scoped to the tested relationships (constant-fraction, rank, lagged linear); nonlinear/multivariate explicitly not ruled out, bridged to Ch.4 covariate null |
| C2.6 underfit claim | **DONE** | "suggests… may structurally underfit — a risk, not a theorem, tested in Ch.4" |
| C2.7 "exactly the inputs" | **DONE** | "trace-derived offered-work signals… necessary demand features, not a complete control state" |
| F3.1 H=12 vs bin width | **DONE** | Already bins-based; wall-clock span per resolution now explicit (12 s → 12 min) |
| F3.2 common span | **DONE** | Coverage asymmetry disclosed (20% vs 98.7%; burst over-representation; within-column reading only) |
| F3.3 TimesFM univariate | **DONE** | Rewritten as univariate-per-target control, explicitly ≠ request-rate-only policy |
| F3.4 "tuned" | **DONE** | "fixed-parameter classical baselines" |
| F3.5 quantile calibration | **DONE-BY-DATA** | Coverage computed per model/signal/resolution (artifact `quantile_coverage.json`): p90 0.88–0.90 at 1-min everywhere; p10/band distorted by zero ties (69% vs 80% nominal; 29% at 1 s). New subsection + limitations update |
| F3.6 "raw" quantiles | **DONE** | "recorded as produced apart from the global nonnegativity floor; no monotonicity repair" |
| F3.7 TimesFM winner scope | **REJECTED (already narrow)** | The chapter attributes TimesFM only the 1-min context column, which matches the table; no broad superiority claim existed |
| F3.8 accuracy ≠ SLA | **DONE** | Explicit bridge paragraph (WAPE ≠ tail protection; closed loop scores SLA × worker-seconds) |
| F3.9 1-min vs second-scale | **DONE** | Timescale-binding paragraph (provisioning input vs scheduler signal; capacity decides queue survivability) |
| S4.1 isolated vs composed | **DONE** | Limitations state composed claims only where composed runs exist (grid on shifted traces, all windows) |
| S4.2 missing AIC LLM burst row | **DONE-BY-DATA** | = feedback H1: run performed; row added; feasibility language reframed (TP1 fails 1,868 ms; TP2×2 passes 748 ms) |
| S4.3 stage p99 budgets | **DONE** | Union-bound (≈p98) phrasing + heuristics label |
| S4.4 64-image cap artifacts | **DONE-BY-DATA** | Sensitivity run: p99 = 5,163/5,013/6,743 ms at cap 32/64/128 (util 29–33%) — verdict cap-insensitive; cap-128 extrapolation flagged; one limitation sentence + ledger entry |
| S4.5 ingress outside model | **DONE** | Boundary statement in limitations (accelerator-side service + queueing only) |
| S4.6 DeepStack payload | **DONE (review was right)** | Handoff ¶ rewritten: main stream charged in runs; 3 DeepStack streams quadruple payload (≈6.4 MB/img; ≈250 ms at 121-img max) — quantified, second-order vs queueing tails, converter parameter scheduled for closed-loop regen |
| S4.7 chunk parallelism assumption | **DONE** | Labeled a simulator policy assumption consistent with EPD-style runtimes; sequential alternative retained + quantified (2.9 s floor) |
| S4.8 handoff not conservative | **DONE** | Bound relabeled bandwidth-only lower bound; contention/topology unmodeled stated |
| S4.9 silicon vs workload conflation | **REJECTED (checked)** | No hardware-normalized cross-GPU claim exists in the text; RTX-vs-H100 appear only as different pools pricing different stages, never as a silicon comparison |
| S4.10 episode/window terms | **DONE** | Terminology fixed once in Ch.6; usage swept |
| S4.11 9,409/64 off-by-one | **DONE** | 148 forwards (verified against converter: 147×f(64)+f(1)) |
| S4.12 235B not normalized | **DONE** | Spot-check ¶ already stated TP8/same-data/same-window; per-replica (8-GPU) framing made explicit in Ch.6 TP2 discussion; no cross-size throughput ratios remain |
| S4.13 Qwen 32B dims | **DONE-BY-DATA (review was right)** | HF configs fetched: 8B/235B = 4096/4096, 32B = 5120/5120 (tower identical). Intro + Ch.5 family sentences qualified (final projector GEMM + handoff ×5/4 for 32B); Qwen model-card citation added |
| R5.1 dataset citation | **DONE** | `\cite{AzureLMM2025}` at first use; schema fields enumerated; dataset-style bib entry with access date |
| R5.2 RTX 5090 source | **DONE** | nvidia-smi-observed vs vendor-spec cross-check stated + NVIDIA spec citation |
| R5.3 Qwen config citations | **DONE** | Qwen3VL2025 bib entry (model cards/configs, fields verified 2026-07-08), cited at family claims |
| R5.4 PR durable reference | **DONE** | Footnote: PR #1312, branch, campaign commit 1e8b9cac, local infill commit 656ac8ca (push pending), artifact snapshot pointer |
| R5.5 URLs | **DONE** | `\url{}` via url+hyperref; access dates on web references; grey-lit convention stated in the footnote |
| R5.6 Dynamo planner versioning | **DONE** | Footnote pins design docs + v1.3.0 source-build inspection date; bib entry carries docs URL + version line |
| R5.7 reproducibility appendix | **DONE** | Appendix A: environment table + figure/table→script→artifact manifest, distilled from `progress/results-ledger.md` |
| T6.1 SLO/SLA | **DONE** | Defined once (Ch.1); "evaluation SLA" fixed as term of art |
| T6.2 TPOT/ITL | **DONE** | Mapping defined at first use (Ch.1) and at the SLA ¶ (Ch.6); abbreviations list entry |
| T6.3 units | **PARTIAL/DEFERRED** | Headline tables carry units; full `\num{}`-normalization pass deferred to final copy-edit |
| T6.4 colloquialisms | **DONE** | All flagged phrases replaced (see feedback W2) |
| T6.5 sentence length | **PARTIAL** | Worst offenders split; global pass deferred per this review's own rewrite order (step 6) |



This report replaces the previous accumulated review text with a mediated,
decontaminated version. I read the accumulated `report.md`, compared its
claims against `tex/tese.tex`, the included chapter files, and selected
analysis/simulation artifacts, and removed content that was duplicative,
mostly congratulatory, stylistically subjective, or not supported by the
source tree.

The remaining comments are organized by scientific and editorial priority.
Each item is intended to be actionable: it identifies the problem, explains why
it matters, and states the correction expected before submission.

## Executive Verdict

The manuscript has a coherent high-level thesis: multimodal serving demand is
not adequately represented by request rate alone, and vision-prefill workloads
require explicit modeling of images, tokens, arrivals, batching, and
disaggregated service. However, the current draft is not yet submission-ready.

The dominant risks are not prose polish. They are unresolved placeholders,
incomplete front matter/build structure, stale or inconsistent numerical claims,
overgeneralized conclusions from single-trace or single-scenario evidence, and
several places where the artifact trail does not match the manuscript text.
Those issues should be corrected before any final copy-editing pass.

## Priority 0: Submission Blockers

### B0.1 Unresolved placeholders remain in the manuscript

**Evidence.** The introduction still contains explicit TODO-style or
placeholder text around thesis organization and contribution framing, including
the markers near `tex/intro.tex:49-52`, `tex/intro.tex:190-193`,
`tex/intro.tex:230-237`, `tex/intro.tex:360-368`,
`tex/intro.tex:391-394`, and `tex/intro.tex:414-418`. The related-work chapter
also contains placeholder narrative around systems sections near
`tex/related.tex:163-164` and `tex/related.tex:311-313`.

**Why it matters.** These markers make the document visibly incomplete. They
also prevent a reader from knowing whether later claims are final conclusions
or drafting scaffolds.

**Required action.** Replace every placeholder with final thesis text or remove
the unsupported subsection. Do this before resolving lower-priority wording
issues, because the surrounding argument may change once the final scope is
settled.

### B0.2 `tex/tese.tex` is still a preview wrapper, not a final thesis root

**Evidence.** The root file declares itself as a preview-oriented compilation
unit near `tex/tese.tex:1-3`, includes only selected chapter files near
`tex/tese.tex:28-33`, and carries a large manual bibliography block near
`tex/tese.tex:35-316`. The expected thesis front matter, abstract,
acknowledgements, list structures, and formal bibliography workflow are absent
from this root.

**Why it matters.** The draft may compile for inspection, but it does not yet
represent a final thesis document. This affects citation integrity, front
matter compliance, page numbering, and reproducible build review.

**Required action.** Decide whether `tex/tese.tex` is a preview artifact or the
submission root. If it is the submission root, add the required front matter and
switch bibliography management to the project-standard mechanism. If another
root file is intended for submission, state that explicitly and keep this file
as a preview-only build.

## Priority 1: Evidence-Chain Corrections

### E1.1 The AIC validation scope is overstated

**Evidence.** The AIC chapter uses an AIC PR validation to justify simulator
parameters, but the precise comparison is for the attention operation, not the
full encoder forward. The validation table and surrounding text in
`tex/aiconfigurator.tex` should distinguish attention-kernel agreement from
end-to-end model-forward agreement. Later paragraphs apply this validation too
broadly to full-forward timings and cross-family extrapolation.

**Why it matters.** Attention-kernel validation does not automatically validate
the full encoder runtime. Full encoder runtime also includes patch embedding,
projection, layer-normalization, framework overhead, launch overhead, and memory
traffic. Treating an attention-only agreement as full-forward validation
inflates the strength of the empirical claim.

**Required action.** Rephrase the claim as: the AIC probe validates the
attention component within the measured configuration; full-forward
configuration remains an approximation requiring separate calibration or an
explicit uncertainty band. Where full-forward latency ratios are used later,
label them as model-derived or simulator-derived, not directly PR-validated.

### E1.2 AIC request/image counts are internally inconsistent

**Evidence.** The AIC chapter reports original counts and then an infilled set.
The artifact trail distinguishes pre-infill counts, approximately 7,679
requests and 34,326 images, from post-infill counts, approximately 7,760
requests and 34,710 images. The chapter summary still appears to mix these
states. The same issue appears in the latency summary, where 7.822 ms and
8.16 ms refer to different pre/post-infill contexts.

**Why it matters.** These differences are small in relative terms but important
for trust. A thesis reader must be able to reconstruct which dataset each
reported statistic refers to.

**Required action.** Introduce explicit labels such as `raw AIC slice` and
`infilled AIC slice`. Then update all counts, means, tables, and summary
sentences to use one label consistently. If both values are retained, say which
one feeds the simulator.

### E1.3 Long-context H100 evidence is partly extrapolated and must be disclosed

**Evidence.** The H100 context-attention grid used in the local progress notes
tops out at ISL 16,384, while the trace includes much longer multimodal
requests: frames-class requests reach roughly 36k p99 input length and about
121k-148k maximum input length depending on the artifact slice. Around 3% of
requests therefore require extrapolated pricing. The manuscript does not make
this limitation sufficiently visible.

**Why it matters.** The main systems conclusion depends on whether long-context
cost is measured or extrapolated. Extrapolation may be reasonable, but it is
not equivalent to measurement, especially when attention cost is nonlinear and
runtime implementations change at long sequence lengths.

**Required action.** Add a limitation in the AIC/simulation chapters: the H100
context-attention probe is measured up to 16,384 input tokens, and longer
trace requests are priced by extrapolation. State the fraction of affected
requests and the extrapolation rule.

### E1.4 Simulation table provenance is unclear for the source-build row

**Evidence.** The two-pool chapter includes a corrected source-build AIC row,
but the adjacent summary artifacts appear stale relative to the prose. The
chapter should distinguish between values sourced from
`simulation/results/sweeps/summary.json` and values sourced from the
source-build artifact such as
`simulation/results/srcbuild/llm_head2k_aic_src.json`.

**Why it matters.** Mixing stale sweep summaries with source-build corrections
weakens reproducibility. A reader cannot know which executable or configuration
produced the table.

**Required action.** Add an explicit provenance note below the table or in the
caption. If the table combines multiple artifact families, name each source and
explain why the corrected row supersedes the stale sweep summary.

### E1.5 Duplicate handling in the trace chapter does not match the loaders

**Evidence.** The trace chapter says that 151 duplicate timestamps are dropped.
The inspected loaders in `analysis/trace_eda/_common.py` and
`workload/trace_to_two_pool.py` parse timestamps, sort rows, and slice windows,
but they do not visibly drop duplicates.

**Why it matters.** Duplicate handling affects inter-arrival distributions,
burst counts, and windowed request rates. If the prose says duplicates are
dropped but the artifact keeps them, the reported statistics are not
reproducible from the stated method.

**Required action.** Verify the actual preprocessing path. Then either update
the loaders to drop duplicates before statistics are computed or revise the
manuscript to say duplicates are retained and describe how simultaneous arrivals
are treated.

### E1.6 Forecast archive size appears stale or ambiguous

**Evidence.** The forecasting chapter refers to roughly 19.2 million forecast
values. A current count over `predictors/results/*.parquet` found 26 files and
21,404,640 rows.

**Why it matters.** The discrepancy may be harmless if the chapter reports a
filtered subset, but that subset is not defined clearly enough for
reproduction.

**Required action.** State the exact file set, filters, and counting unit. If
the current archive is authoritative, update the manuscript to 21,404,640 rows.
If the 19.2M count is intentional, define the excluded files or rows.

### E1.7 Burst-scenario numbers are stale in the two-pool chapter

**Evidence.** The current `vision_burst1_s1` artifact reports 64,804 requests,
43,768 image-bearing requests, 3,478,128 images, mean image arrival rate about
116.173 images/s, maximum observed second of 2,726 arriving images, 83,376
encoder forwards, maximum encoder batch service about 316.369 ms, p99 encoder
delay about 5.013 s, and queue lengths above 1,000 images for hundreds of
seconds. The prose still contains older values such as 83,432 forwards, 315 ms,
and a much smaller burst intensity.

**Why it matters.** This chapter is quantitative. Stale values change the
severity of the burst and may change the interpretation of whether the vision
pool is lightly loaded or queue-dominated.

**Required action.** Regenerate the chapter's table and prose from the current
stats/series artifacts, or pin the older artifact with its path and timestamp.
Do not mix values from different runs in one paragraph.

## Priority 2: Conceptual and Scientific Precision

### C2.1 Persistence claims overstate agreement among estimators

**Evidence.** The trace chapter reports strong long-memory indicators, but not
all signals support the same interpretation at the same horizon. For generated
tokens, a high Hurst estimate near 0.91 coexists with a short autocorrelation
half-life of about five minutes.

**Why it matters.** A statement that all estimators agree on strong persistence
would be scientifically stronger than the evidence supports. Different
estimators capture different aspects of dependence, and finite traces can make
them diverge.

**Required action.** Rephrase as: persistence is present, but estimator
agreement varies by signal and timescale. Use the generated-token case as an
explicit example rather than hiding it as an anomaly.

### C2.2 The spectral interpretation contradicts itself

**Evidence.** The trace chapter identifies 12 h, 8 h, and 6 h spectral
components, but elsewhere rejects sub-diurnal spectral structure too broadly.

**Why it matters.** The reported components are themselves sub-diurnal
harmonics. The intended point appears to be that the trace lacks strong
non-harmonic sub-diurnal periodicity, not that it lacks all sub-diurnal power.

**Required action.** Replace broad rejection language with a narrower statement:
the trace contains harmonic diurnal structure at 12 h, 8 h, and 6 h, while
non-harmonic sub-diurnal lines are weak or not dominant.

### C2.3 "Fano grows without bound" is too strong for a seven-day trace

**Evidence.** The trace chapter discusses Fano factor growth across aggregation
windows. The available observation window is finite.

**Why it matters.** Unbounded growth is an asymptotic claim. A seven-day trace
can show increasing dispersion over the measured window, but it cannot prove
unbounded behavior.

**Required action.** Say that Fano factors continue to increase over the
measured aggregation range. If an asymptotic statement is desired, add a model
fit and confidence interval that justify extrapolation.

### C2.4 Heavy-tail claims need threshold and fit qualifications

**Evidence.** The trace chapter uses heavy-tail terminology for images and token
volumes, but the draft does not consistently state thresholds, fitting method,
goodness-of-fit checks, or censoring from platform limits.

**Why it matters.** "Heavy-tailed" can mean qualitative skew, subexponential
behavior, power-law tail, or regularly varying tail. These are not equivalent.

**Required action.** Either define the term operationally, for example "large
upper-tail mass relative to the median," or report a tail-fitting procedure
with threshold, estimator, and goodness-of-fit diagnostics.

### C2.5 "Not derivable from request rate" is stronger than the evidence

**Evidence.** The trace chapter argues that image counts, input tokens, and
generation demand are not derivable from request rate. The shown evidence is
largely pairwise, rank, and lag-zero dependence evidence.

**Why it matters.** Those tests can refute simple proportionality or strong
linear dependence, but they do not rule out nonlinear, lagged, or multivariate
prediction from request rate plus calendar features.

**Required action.** Rephrase as: request rate alone is insufficient to recover
the other demand dimensions under the tested relationships. Avoid universal
"not derivable" language unless a stronger predictive impossibility analysis is
added.

### C2.6 "Short-memory forecasters will underfit" should be framed as a risk

**Evidence.** The trace chapter uses persistence statistics to motivate
forecasting. The current phrasing implies a broad conclusion about all
short-memory models.

**Why it matters.** Persistence diagnostics alone do not prove that every
short-memory model underfits. That conclusion requires model comparison.

**Required action.** Use a weaker and more defensible statement: the observed
persistence suggests that purely short-memory forecasters may underfit, and the
forecasting chapter evaluates this risk empirically.

### C2.7 The four demand signals are not "exactly" the inputs to any scaler

**Evidence.** The introduction and trace chapter frame request rate, image
rate, input tokens, and generated tokens as the exact candidate inputs to a
scaling policy.

**Why it matters.** A real scaling policy may also use queue depth, observed
latency, utilization, KV-cache pressure, error rates, admission-control state,
and replica startup delays. The four signals are important offered-work
features, but not an exhaustive scaling state.

**Required action.** Call them trace-derived offered-work signals or minimal
exogenous demand features. Then say they are necessary but not sufficient for a
complete control policy.

## Priority 3: Forecasting Chapter

### F3.1 `H=12` must be tied to bin width

**Evidence.** The forecasting chapter describes a horizon of `H=12` as a
12-minute horizon. That is true only for the one-minute resolution. At five-,
ten-, or fifteen-minute bins, the same horizon index covers different wall-clock
durations.

**Why it matters.** Horizon length changes task difficulty and operational
meaning. Treating `H=12` as always 12 minutes can mislead comparisons across
resolutions.

**Required action.** Define horizon as `12 bins`, then state the wall-clock
duration for each resolution. When comparing models across resolutions, compare
equivalent wall-clock horizons or explicitly state that the horizon index is
being held fixed.

### F3.2 "Common span" is not a common wall-clock evaluation set

**Evidence.** The chapter uses a common-span phrasing across resolutions. Unless
explicitly aligned, different bin widths can imply different numbers of
examples and edge effects even over the same trace interval.

**Why it matters.** Forecast accuracy across resolutions is sensitive to the
number of windows, boundary trimming, and aggregation. A common trace interval
does not automatically produce a common evaluation population.

**Required action.** Define the evaluation split precisely: wall-clock interval,
binning rule, horizon, stride, boundary handling, and whether all resolutions
share the same endpoint set.

### F3.3 TimesFM univariate results are not a request-rate-only ablation

**Evidence.** The chapter compares Chronos variants with TimesFM. TimesFM is a
univariate model, but in this setup it is run separately on each target series,
not only on request rate.

**Why it matters.** Calling TimesFM a request-rate-only baseline confuses model
input structure with target selection. It can lead readers to think the model
predicts all dimensions from request rate alone.

**Required action.** State that TimesFM is a univariate per-target forecaster.
If a request-rate-only ablation is desired, add a separate model that predicts
non-request targets using only request-rate history.

### F3.4 Classical baselines should not be called "tuned" unless they were tuned

**Evidence.** The forecasting artifacts indicate fixed baseline parameters
rather than a tuning search.

**Why it matters.** "Tuned" implies hyperparameter optimization and can
unfairly strengthen the baseline comparison.

**Required action.** Replace "tuned classical baselines" with "fixed-parameter
classical baselines" or document the search space and validation procedure.

### F3.5 Quantile and headroom claims need calibration evidence

**Evidence.** The chapter uses p10/p90 and headroom language to support
capacity planning. The text does not show coverage calibration across traces,
targets, or bursts. Some observations appear to be from a single burst episode.

**Why it matters.** A quantile forecast is operationally useful only if its
coverage is calibrated under the workload being controlled. One burst example
does not establish general coverage reliability.

**Required action.** Either add calibration tables, for example empirical
coverage of p10/p50/p90 by target and horizon, or reframe the quantiles as
illustrative uncertainty bands rather than validated admission-control margins.

### F3.6 Chronos "raw crossed quantiles" are already zero-clipped

**Evidence.** The base predictor in `predictors/predictor.py` clips predicted
points and quantiles to nonnegative values by default. It does not appear to
apply monotonicity repair across quantiles.

**Why it matters.** If the chapter calls the outputs "raw crossed quantiles,"
readers may infer that negative values are present and unmodified. The actual
issue is crossing after nonnegativity clipping.

**Required action.** Use precise language: Chronos quantiles are nonnegative
clipped but not monotonicity-repaired. If crossing rates matter, report them
after clipping.

### F3.7 The TimesFM winner interpretation is too broad

**Evidence.** The chapter notes that TimesFM wins on image-count WAPE at some
resolution. This is a narrow metric/target/resolution result.

**Why it matters.** Generalizing from one WAPE cell to a broad conclusion about
model superiority is not justified.

**Required action.** State the exact metric, target, and resolution where
TimesFM leads. Then distinguish that result from the broader multivariate or
multi-target planning objective.

### F3.8 Forecast accuracy does not by itself validate SLA control

**Evidence.** The chapter uses WAPE/MAE-style accuracy metrics, while later
chapters discuss p99 latency and queueing behavior.

**Why it matters.** A low average forecast error does not guarantee p99 latency
protection. SLA control depends on tail underprediction, burst timing,
provisioning delay, queue state, and control-loop actuation.

**Required action.** Add an explicit bridge: forecast metrics measure demand
prediction quality, not end-to-end SLA control. If the thesis wants to claim
control usefulness, add a backtest that maps forecasts into capacity decisions
and reports latency or shortage outcomes.

### F3.9 One-minute forecasts are not automatically adequate for second-scale FIFO failures

**Evidence.** The simulation chapter reports second-scale burst and queue
effects, while the forecasting chapter emphasizes minute-level bins.

**Why it matters.** A one-minute aggregate can hide sub-minute head-of-line
blocking. The forecasting horizon may be useful for provisioning, but not for
fine-grained scheduler reaction.

**Required action.** State the control timescale explicitly. Minute-level
forecasts are better framed as replica or pool provisioning inputs, while
second-scale queue management still requires online scheduling signals.

## Priority 4: Simulation and Systems Modeling

### S4.1 Isolated per-pool knees are not the same as composed-system evidence

**Evidence.** The two-pool chapter reports separate LLM and vision pool
capacity behavior, then draws conclusions about the composed serving system.

**Why it matters.** A composed system can fail because of synchronization,
handoff, shared queues, correlated bursts, or tail convolution even if each pool
looks acceptable in isolation.

**Required action.** Clearly separate isolated-pool capacity results from
end-to-end composed-system results. Use composed-system claims only where both
pools, handoff, and queueing are included in the same simulation.

### S4.2 The AIC LLM burst row is missing or misleading

**Evidence.** The two-pool chapter's current grid emphasizes H100/TP1 burst
behavior and AIC vision behavior. Later calibrated evidence suggests TP1 burst
handling can be infeasible under the burst scenario, while the prose can be read
as implying that the pool meets the full burst SLA.

**Why it matters.** If the AIC configuration is only evaluated for part of the
system, readers may incorrectly infer full-system feasibility.

**Required action.** Add the missing AIC LLM burst row or remove full-system
feasibility language for configurations that were not evaluated end to end.
State explicitly whether the reported AIC numbers cover the vision pool only,
the LLM pool only, or the composed system.

### S4.3 Separate p99 budgets do not imply end-to-end p99 satisfaction

**Evidence.** The chapter allocates p99 budgets to vision and text stages.

**Why it matters.** The p99 of a sum is not the sum of independent p99s in a
simple way, and stage latencies are often correlated under burst load. Meeting
stage-level p99 targets separately does not prove end-to-end p99 satisfaction.

**Required action.** Either report end-to-end request p99 directly or qualify
the stage budgets as engineering heuristics. If stage budgets are retained, add
a short explanation of how they relate to end-to-end SLA evaluation.

### S4.4 The 64-image batch cap can create artificial head-of-line blocking

**Evidence.** The simulator chunks large image requests under a 64-image cap.
The burst scenario contains very large image requests.

**Why it matters.** A fixed cap may be realistic for memory reasons, but it also
introduces scheduling artifacts. Large requests can occupy repeated chunks and
delay smaller requests, especially under FIFO-like dispatch.

**Required action.** Add a sensitivity check over the cap, for example 32, 64,
and 128 images if feasible, or justify 64 from measured kernel/model limits.
Report whether qualitative conclusions change.

### S4.5 Input-side preprocessing and ingress are outside the model

**Evidence.** The simulation focuses on encoder and LLM service times.
Preprocessing, image fetch/decode, upload, tokenizer/processor work, and
front-end ingress are not modeled in comparable detail.

**Why it matters.** These costs can be significant for image-heavy requests and
can dominate perceived latency before accelerator service begins.

**Required action.** Add an explicit boundary statement: the simulator models
accelerator-side service and queueing, not full request ingress. If possible,
quantify omitted preprocessing cost from logs or cite it as future work.

### S4.6 Handoff payload may undercount DeepStack-style intermediate tensors

**Evidence.** The AIC and two-pool chapters compute handoff bandwidth from
image token counts and model dimensions, but DeepStack-style or multi-stage
vision paths may materialize additional intermediate tensors or metadata.

**Why it matters.** The handoff argument is central to disaggregated serving.
If the payload omits required tensors, the bandwidth conclusion may be
optimistic.

**Required action.** State exactly which tensor crosses the pool boundary:
projected visual tokens, pre-projection features, or a larger intermediate
state. For each model family, cite the configuration fields used.

### S4.7 Chunk-parallel dispatch is a runtime assumption, not a property of the trace

**Evidence.** The chapter assumes chunks of large image requests can be
processed in parallel or dispatched across workers.

**Why it matters.** Parallel chunk dispatch depends on runtime scheduler
semantics. Some runtimes may serialize request chunks or preserve stronger
request-level ordering.

**Required action.** Label chunk parallelism as a simulator policy assumption.
If it is meant to represent a real runtime, cite the runtime behavior or add a
small validation.

### S4.8 The handoff bound is not automatically conservative under contention

**Evidence.** The manuscript frames network handoff as small relative to other
costs.

**Why it matters.** The byte count may be small in isolation, but contention,
serialization, PCIe/NIC placement, cross-node topology, and synchronization can
raise tail latency. A bandwidth-only calculation is not a tail-latency proof.

**Required action.** Rephrase the handoff result as a lower-bound or
bandwidth-only estimate. Add a limitation that contention and topology are not
modeled unless they are explicitly simulated.

### S4.9 Image-size assumptions conflate AIC characteristics with silicon

**Evidence.** Some text attributes efficiency differences to silicon or
accelerator choice while also changing image/token geometry and model-family
assumptions.

**Why it matters.** AIC-vs-H100 conclusions should isolate hardware effects
from workload shape, image tokenization, and model architecture differences.

**Required action.** State which comparisons are hardware-normalized and which
are scenario-level comparisons. Avoid saying the result is caused by silicon
alone unless the model, tokenization, and workload are held fixed.

### S4.10 "Burst episode" and "scenario window" are used inconsistently

**Evidence.** The two-pool chapter alternates between burst episode, burst
window, and scenario window when discussing trace slices and simulation runs.

**Why it matters.** These terms affect denominators for arrival rates, counts,
and p99 latency. A burst episode may be a subset of a larger evaluated window.

**Required action.** Define the terms once. For every reported rate, state the
denominator interval.

### S4.11 The 9,409/64 chunk count has an off-by-one risk

**Evidence.** A request with 9,409 images divided into chunks of 64 requires
`ceil(9409 / 64) = 148` chunks, not 147.

**Why it matters.** This is a small arithmetic issue, but it appears in a
section about queue mechanics, where exact chunk counts matter.

**Required action.** Correct the chunk count and audit any derived latency or
queue examples that depend on it.

### S4.12 The 235B comparison is not resource-normalized

**Evidence.** The manuscript compares behavior across Qwen model sizes and
references decode/vision ratios. The 235B model has different resource
requirements and likely different parallelism assumptions from smaller models.

**Why it matters.** Comparing raw latency or throughput across model sizes
without normalizing for GPU count, memory residency, tensor parallelism, and
batching can lead to misleading conclusions.

**Required action.** Frame 235B numbers as scenario-specific, not
resource-normalized. Report the assumed GPU count, parallelism, and memory
state. If ratios are stale, regenerate them from the current artifacts.

### S4.13 Qwen visual projection dimensions differ by model size

**Evidence.** The inspected Qwen configuration files show that the 8B and 235B
configs use `hidden_size=4096` and `vision_config.out_hidden_size=4096`, while
the 32B config uses `hidden_size=5120` and `out_hidden_size=5120`.

**Why it matters.** A blanket statement that the projector handoff dimension is
identical across Qwen sizes is false for the inspected 32B configuration.

**Required action.** Either remove the general statement or qualify it by model
size. Use the actual configuration fields in the handoff-byte calculation.

## Priority 5: Literature, Citations, and Reproducibility

### R5.1 Dataset and schema claims need a primary citation

**Evidence.** The trace chapter relies on the Azure LMM trace and its schema.
The citation key exists in the root bibliography block, but the chapter should
make the dataset source and schema version explicit at the first use.

**Why it matters.** Trace-derived science is only reproducible if readers know
the exact dataset, schema, and preprocessing boundary.

**Required action.** At first mention, cite the Azure LMM dataset/source and
state the schema fields used: timestamps, image counts, input tokens, generated
tokens, and any fields discarded.

### R5.2 RTX 5090 hardware specifications need a source

**Evidence.** The AIC chapter uses RTX 5090 or local GPU hardware claims.

**Why it matters.** Hardware specifications are externally verifiable facts and
can change across board variants.

**Required action.** Cite a vendor specification, system inventory, or benchmark
environment log for memory capacity, interconnect, and relevant precision
support.

### R5.3 Qwen model-configuration claims need model-card/config citations

**Evidence.** The AIC and two-pool chapters use Qwen architecture dimensions,
vision-token behavior, and model-size comparisons.

**Why it matters.** These values are not generic properties of Qwen; they are
specific to model revisions and config files.

**Required action.** Cite the exact model card or configuration snapshot for
each Qwen variant. Include the fields used for hidden dimension, projected
vision dimension, number of layers, and token accounting.

### R5.4 The AIC draft PR needs a durable reference

**Evidence.** The validation narrative relies on an AIC draft PR and local
measurements.

**Why it matters.** A draft PR can move, be rebased, or disappear. Thesis
evidence should be stable.

**Required action.** Add URL, status, commit hash, and archival date, or place a
snapshot of the measured configuration in an appendix/artifact manifest.

### R5.5 URL handling should be made LaTeX-safe and archival

**Evidence.** The related-work/root bibliography block includes raw URLs in
manual entries and text blocks. The checked URLs for vLLM EPD and LMSYS EPD are
live, but they are not formatted as durable bibliography entries.

**Why it matters.** Raw URLs can overflow lines and are harder to audit.
Blog-style evidence also needs access dates.

**Required action.** Use `url`/`hyperref` or BibTeX/BibLaTeX fields for URLs.
Add access dates for web references and prefer stable archive or release-note
URLs where available.

### R5.6 Dynamo planner claims need versioned citations

**Evidence.** The related-work chapter discusses Dynamo planner behavior in
detail.

**Why it matters.** Planner behavior is implementation-specific and can change
quickly. The thesis should avoid implying timeless behavior from one code
snapshot.

**Required action.** Cite the specific Dynamo documentation, commit, release,
or paper used for planner claims. If the description is from code inspection,
say so and record the inspected commit.

### R5.7 Reproducibility appendix is required

**Evidence.** The thesis depends on multiple local scripts, generated parquet
files, JSON summaries, model configs, simulation outputs, and benchmark logs.

**Why it matters.** Without a manifest, future readers cannot reproduce the
numbers or distinguish raw artifacts from derived summaries.

**Required action.** Add an appendix or table with: script path, input artifact,
output artifact, commit hash, environment, and checksum for every table/figure.
At minimum, cover trace EDA, predictor archives, AIC measurements, and two-pool
simulation runs.

## Priority 6: Terminology and Style With Scientific Value

### T6.1 SLO and SLA are used too loosely

**Issue.** The manuscript sometimes uses SLA to mean an internal target or SLO.

**Correction.** Use SLO for measured service objectives inside the experiment,
and SLA only when referring to an external contractual guarantee.

### T6.2 TPOT and ITL need a precise mapping

**Issue.** The systems chapters use TPOT and ITL-like terminology. These are
related but not always identical depending on whether first-token behavior,
streaming gaps, and decode-only intervals are included.

**Correction.** Define both terms once and state which metric each table
reports. If only one is used, remove the other synonym.

### T6.3 Units and numeric formatting should be normalized

**Issue.** The draft mixes forms such as `img/s`, `req/s`, `tok/s`, prose
units, and LaTeX numeric macros.

**Correction.** Use consistent SI-style formatting throughout, preferably
`\num{}` and explicit units. Keep denominators visible in table headers.

### T6.4 Replace colloquial systems phrasing in final copy

**Issue.** Phrases such as "where load lives," "locates the exit," "plumbed,"
"caught," and "prices" are understandable in engineering notes but too informal
or ambiguous for a thesis.

**Correction.** Replace with direct scientific verbs: "identifies,"
"measures," "routes," "observes," "estimates," or "models," depending on the
context.

### T6.5 Sentence length and dash-heavy prose should be edited globally

**Issue.** Some paragraphs carry several claims through long dash-separated
sentences. This is especially common in the introduction and systems chapters.

**Correction.** After the evidence corrections above, perform one global pass
that splits long sentences into claim, evidence, and implication. Do not spend
time on isolated comma edits before the factual layer is fixed.

## Discarded or Deprioritized Subagent Suggestions

The following classes of prior comments were removed from the operative review:

- Praise-only passages that did not identify a defect or required action.
- Duplicate comments that repeated the same stale-count or citation issue under
  different headings.
- Micro-edits such as adding individual commas, changing "where" to "whereas,"
  or enforcing one preferred dash style. These may be handled during final
  copy-editing but should not lead the scientific review.
- Prescriptive grammar preferences such as requiring "data are" everywhere.
  Use the thesis style guide if one exists; otherwise prioritize consistency.
- Generic statements that a section is "strong," "clear," or "compelling."
  Those do not help decide what must change.
- "No changes required" blocks. The final report should focus on actionable
  defects and residual risks.

## Recommended Rewrite Order

1. Remove all placeholders and decide whether `tex/tese.tex` is a preview root
   or the submission root.
2. Regenerate or pin every numeric claim in the AIC, forecasting, and two-pool
   chapters.
3. Correct scope language around validation: attention-only, full-forward,
   forecast accuracy, and end-to-end SLA control must remain distinct.
4. Add missing provenance for datasets, model configs, AIC PR state, simulation
   artifacts, and web references.
5. Rework conclusions so that single-trace and single-scenario evidence is not
   generalized beyond what the artifacts support.
6. Only then perform a final prose pass for terminology, units, sentence
   length, and LaTeX bibliography hygiene.

## Verification Notes

- The strongest numerical corrections above were checked against local chapter
  files, predictor outputs, simulation stats/series artifacts, model config
  files, and selected analysis scripts.
- Label/citation/image-path checks from the earlier pass did not reveal an
  immediate missing-file class of issue, but a full LaTeX build was not run as
  part of this decontamination pass.
- This file, `report.md`, is the only intended write target for the review.
