# Comprehensive adversarial review of the thesis

- **Review status:** reverified against the live tree after the 2026-07-26
  provenance/run-ID updates; not a review of an older PDF or prior report
- **Overall verdict:** **not yet defense/submission ready as confirmatory evidence**
- **Snapshot:** 2026-07-26, `America/Sao_Paulo`
- **Git branch / HEAD:** `thesis-verification-and-provenance-db` / `89c0018f5933558caca076e07e6a3089c0db40b1`
- **Database observed:** 2026-07-26 17:18:11 UTC; latest recorded ingest
  2026-07-26 16:43:24 UTC

## Executive judgment

The thesis's older numerical core is generally reproducible. The 0.62 encoder
ratio, the raw 0.76 hybrid ratio, the raw 0.82 language ratio, the 235B
87.7-ms measurement, the principal static/reactive comparisons, and the live
validation populations all reproduce from the current artifacts or database.
There is no evidence that these headline operands were fabricated or
transcribed wholesale from the wrong experiment.

The principal defects are instead **experimental-status, evaluation-scope, and
provenance defects**:

1. the language policy called “honestly calibrated” was changed after the
   purported held-out e13/F6 result was inspected;
2. a p50 aggregate pass is promoted even though the same policy fails two
   declared burst gates;
3. the hybrid is called seven-fold robust and deployable although F1 was never
   replayed, F2 exposes a second whole-fold pure-forecast failure, and the
   controller and its combination sweep were designed on F6;
4. only four seed rows from the new hybrid family have been renamed into the
   database; the aggregate, fold sweep, formal claim corpus, and reproduction
   manifest remain outside the claimed chain;
5. the headline reactive language baseline did not model the cold-start delay
   that the manuscript says was shared by all policies; and
6. the repeatedly asserted 588-ms physical service floor is falsified by a
   same-span, same-harness run at 565 ms; and
7. the delivery wrapper reports the current tree as “DELIVERY-READY” because a
   malformed regular expression empties the very diff that its containment
   gate claims to inspect.

The present review promotes **7 high-severity, 16 medium-severity, and 9
low-severity findings**, plus **2 additional document-delivery blockers**.
R1 is already counted among the seven high findings and also blocks reliance
on the delivery gate. High-severity findings
must be resolved before the new 0.76/0.82 claims are presented as confirmatory
thesis results. Medium and low findings should be repaired because several are
cross-chapter consistency failures and because their accumulation weakens the
manuscript's otherwise unusually strong reproducibility posture.

## Reverification delta after the latest updates

The previous report revision predates the latest provenance edits, but no
`tex/*.tex` file is newer than the current report. The post-report substantive changes are
concentrated in `provenance/loader/runid.py`,
`provenance/schema/32_scope_misc_runids.sql`, `provenance/verify_all.sh`,
`progress/results-ledger.md`, a violation-curve script/result, and a
two-pool reframe draft. The manuscript claims therefore did not move; their
claimed provenance state did.

Four scoped `encoder_hybrid` rows and one `lang_qsweep` row now exist because
five earlier `misc:*` run IDs were renamed. This is useful hygiene, but it is
not family ingestion: the hybrid aggregate, complete combination grid, and
daily-fold population remain absent. The formal closed-loop claim and
verified JSON files also still predate the 0.76/0.82 results.

The full live wrapper ended **39 passed / 0 failed / 6 warnings** and printed
“DELIVERY-READY.” The underlying registered-check table instead contains 72
enabled checks, 67 passing and five failing. Those statements use different
denominators, and the wrapper's most relevant new-result containment check is
nonfunctional (Reverification Finding R1).

| Reverification disposition | Outcome |
|---|---:|
| Prior findings fully resolved | 0 |
| Prior findings partially narrowed | 1 (Finding 4) |
| Prior findings still standing | 25 |
| Delivery blockers still standing | 2 |
| Newly detected findings | 6 (R1-R6) |

Three independent sub-agents re-audited (1) EDA/forecasting, (2) systems and
baselines, and (3) closed-loop/provenance. Their claims were then
cross-checked against the live source, artifacts, database, and full
verification wrapper before inclusion here.

## Scope and evidence standard

This review covered the live, uncommitted versions of:

- `tex/tese.tex` and all 11 included thesis chapters/appendices, 4,856 TeX
  lines in total;
- analysis, predictor, simulation, workload-conversion, validation, and
  reproduction scripts cited by those chapters;
- raw JSON/JSONL/Parquet/CSV artifacts used by the disputed claims;
- the current PostgreSQL provenance schema, current-run views, ingest ledger,
  forecast tables, and all registered consistency checks;
- the Git index and worktree status, including whether new scripts and results
  are actually versioned; and
- a clean isolated LaTeX build.

Three chapter-scoped adversarial audits ran independently and were then
reproduced and adjudicated against the same current database and source tree.
Sub-agent reports were treated as hypotheses, not as report text.

Evidence precedence was:

1. current live TeX and current executable code;
2. current raw artifacts and recomputation from the raw trace;
3. current database rows joined through current-run views;
4. the ingest/claim/verification ledgers; and
5. narrative progress notes.

The worktree already contained 136 modified or untracked paths. No thesis
source was changed by this review. All line references below are one-based
references to the live files at the snapshot above and may drift after edits.

### Chapter coverage

| Thesis scope | Adjudicated outcome |
|---|---|
| Front matter, introduction, conclusion | Cross-section scope/status defects in Findings 1, 3-4, 10, 16, 18-19, 23, R4, R6, and D1 |
| Related work | Findings R4 and R6; its aggregation wording is covered by Finding 25 |
| Trace EDA | Findings 8, 11, 16, 24-25, and R3-R5 |
| Forecasting | Findings 7, 12, 16-17, and 23 |
| AIC/configurator | Finding 22; the N<=64 accuracy bound survives |
| Two-pool model | Findings 6, 13, and 15; the request-linked join survives |
| Baselines | Findings 5, 8, 14, 20-21, and R2 |
| Closed loop | Findings 1-4, 6, 9-10, 18-19, 26, and R1 |
| Live validation | No material numerical contradiction; scheduled/completed/error populations reproduce |
| Reproduction appendix | Findings 4, 13, 22, R2, R6, and D2 |

### Database and build baseline

| Item | Current observation |
|---|---:|
| All database run rows | 3,314 |
| Current run rows | 2,628 |
| Non-current run rows | 686 |
| Rows with explicit `superseded_by` | 4 |
| Registered checks | 73 |
| Enabled checks | 72 |
| Enabled checks passing | 67 |
| Enabled checks failing | 5 |
| Clean-build pages | 135 |
| Undefined citations/references | 0 |
| LaTeX errors | 0 |

The five live check failures are C002 (error: 1/178 median-TTFT
recomputations outside tolerance) and C107, C207, C214, and C302 (documented
warnings). C207 now reports 306/4,320 ingest rows without a run-spine ID;
C214 has worsened from 9/380 to 69/440 unresolved verification rows while its
definition note still expects exactly nine. They are not evidence that every
affected result is false, but they are failures; a count of definitions is
not a count of successful validations, and a wrapper-level warning is not a
registered-check pass.

---

## High-severity findings

### 1. “Honest held-out calibration” is a post-hoc robustness selection, and it contradicts the declared temporal split

**Classification:** evaluation-protocol contradiction; held-out-set reuse;
confirmatory-scope overclaim.

**Direct manuscript quotations**

- `tex/closedloop.tex:43-50`: “The trace's first 1.4 days are consumed as
  forecast *context* ... and never graded ... the two pre-coverage episodes
  are graded only by forecast-free policies.”
- `tex/closedloop.tex:55-57`: “no policy constant is *tuned* on the evaluation
  span.”
- `tex/closedloop.tex:317-333`: “The operating point, honestly calibrated ...
  Re-selecting the operating point ... on the trace's first 1.4 days alone
  (the forecast-context split: burst2 and burst6) and grading held-out ...
  The cheapest point that clears e13 with margin ... costs 440.0 GPU-hours,
  0.82× static.”
- `tex/closedloop.tex:345-348`: “All three arms are calibrated on the same
  split.”
- `tex/closedloop.tex:934-936`: burst2/6 are “never [graded] by a *forecast*
  policy.”
- `tex/tese.tex:67-72` promotes the conclusion to the abstract as an
  “e13-robust saving under honest calibration”; the Portuguese abstract
  repeats it at lines 119-126.
- `tex/trace-eda.tex:153-158` still captions burst2/burst6 as “graded only by
  forecast-free policies.”

**Cross-check**

The live database contains 35 current forecast-policy language runs on each
of burst2 and burst6. Twenty-four burst2 cells and 15 burst6 cells pass the
joint TTFT/ITL gate. These are real forecast-policy grades using the
expanding-context archive. They make the repeated categorical “never graded”
statements false, even though using those windows as a calibration split is
methodologically legitimate.

The selection script is unambiguous:

- `simulation/analyze_lang_calib.py:61-73` selects the cheapest cell passing
  burst2 and burst6 and prints it as the held-out evaluation point.
- Its current output is `q=p70, scale=6, cost=17.41`.
- The resulting p70/s6 week run was generated at 2026-07-24 21:25 and its
  F6/e13 failure, TTFT p99 1133.656 ms, at 23:01.
- Only after that failure was seen was the p90/s6 F6 rescue generated, at
  23:52; the p90/s6 week run followed at 2026-07-25 01:02.

The current weekly operands are:

| Policy | TTFT p99 | ITL p99 | GPU-h | Ratio to 537.409 static |
|---|---:|---:|---:|---:|
| p70/s6, calibration-selected | 757.613 ms | 12.534 ms | 330.350 | 0.6147× |
| p90/s4 | 702.645 ms | 10.934 ms | 337.435 | 0.6279× |
| p90/s6, selected after F6 inspection | 651.140 ms | 7.254 ms | 440.041 | 0.8188× |

The forecast generator itself is temporally honest:
`predictors/benchmark_expctx.py:73-78` supplies each origin only values before
that origin. This is **not future-target leakage**. The defect is reuse of the
held-out F6 result to select the reported “robust” point and then to prove its
robustness.

The statement at `tex/closedloop.tex:259` that the conversion is “derived, not
tuned” is also no longer true of the new quantile-by-scale selection: the
conversion scale was directly swept.

**Adjudication**

The 440.041 GPU-h, 0.82×, and 886.423-ms F6 values are numerically correct.
Their evidential status is wrong. P70/s6 is the calibration-selected policy;
p90/s6 is a post-hoc robustness-frontier policy on this trace.

**Required correction**

Define the split consistently throughout:

- burst2/burst6 are forecast-graded only for language-policy calibration using
  the expanding-context archive;
- p70/s6 is the policy selected by that calibration;
- p90/s6 is a post-hoc e13 robustness sensitivity; and
- an untouched trace/window or nested validation is required before calling
  p90/s6 independently held-out or deployment-validated.

### 2. The p50 language conclusion knowingly promotes an aggregate-masked SLA failure

**Classification:** SLA-population error; contradiction with the thesis's own
joint aggregate-plus-episode gate.

**Direct manuscript quotation**

`tex/closedloop.tex:350-358`:

> “The p50 forecast also **passes the week** ... the smoother context-token
> demand is served adequately even at p50.”

**Cross-check**

The current same-controller p50/s8 rows are:

| Scope | TTFT p99 | ITL p99 | Joint verdict |
|---|---:|---:|---|
| 5.60-day aggregate | 819.461 ms | 13.366 ms | pass |
| burst3 | 2164.190 ms | 137.030 ms | **fail both** |
| burst5 | 1679.101 ms | 120.314 ms | **fail both** |

The older week artifact quoted by the paragraph is 827.813 ms and
319.910 GPU-h; replay noise does not affect the verdict. Both old and current
runs use p50 with conversion scale 8 and a 60-second startup delay.

The manuscript itself states at `tex/closedloop.tex:463-471` that an aggregate
pass must be rejected when a declared episode fails. The current results
ledger is even more explicit at `progress/results-ledger.md:1981-1989`: the
p50 aggregate is a “CALIBRATION FALSE-POSITIVE” and “MUST NOT be quoted.”

**Adjudication**

“Passes the aggregate” is true. “Served adequately” and the inference that
quantile matters less are false under the thesis's declared SLA protocol.
This is not a small stale-number defect; it changes the policy verdict.

**Required correction**

State that p50/s8 passes only the aggregate but fails burst3 and burst5.
Remove it as evidence of adequate p50 service. Compare p70/s6 and p90/s6 when
discussing the valid language frontier.

### 3. The hybrid is not demonstrated as seven-fold robust, deployable, or globally cost-minimal

**Classification:** incomplete population; post-hoc controller design;
readiness/generalization overclaim.

**Direct manuscript quotations**

- `tex/closedloop.tex:474-501`: “across the seven daily folds ... dropping the
  single fold-scale onset, to 0.76× fold-robust.”
- `tex/closedloop.tex:502-506`: “A sweep of the combiner confirms the point is
  cost-minimal.”
- `tex/conclusion.tex:74-76`: “The deployable fold-robust point is a hybrid
  forecast--reactive schedule at 0.76×, recovering the single daily-fold onset
  (e13).”
- `tex/conclusion.tex:89-90`: “0.76× for the deployable fold-robust hybrid.”
- `tex/tese.tex:67-70` says the hybrid “stays robust to the hardest onset” in
  the abstract; the Portuguese abstract repeats that claim at lines 121-123.
- `tex/intro.tex:390-394` says it “recovers the one daily-fold onset ... at
  0.76×.”

**Cross-check**

The same-harness fold artifacts show:

| Fold/arm | Encoder-delay p99 | Verdict |
|---|---:|---|
| F2 forecast | 1318.984 ms | fail |
| F2 reactive | 368.880 ms | pass |
| F2 hybrid | 368.880 ms | pass |
| F6 forecast | 1264.206 ms | fail |
| F6 reactive | 1228.555 ms | fail |
| F6 hybrid | 678.660 ms | pass |

F2 begins before full forecast coverage. It therefore does **not** refute the
narrow statement that e13 is the single missed *covered onset*. It does refute
the broader whole-fold implication: pure forecast fails two of the seven
calendar folds, for two different reasons.

More importantly, no F1 forecast or hybrid replay exists.
`simulation/results/encoder_hybrid/folds/F1_gen.log` says:

> “no forecast rows cover window F1”

and then records a `FileNotFoundError` for `F1_fc.sched.json`.
`simulation/run_encoder_hybrid_folds.sh:7` uses `set -u`, not `set -e`;
lines 24-30 continue after generator/combiner errors, and line 35 still prints
“complete.” The ledger's statement that the hybrid safely degenerates to
reactive on F1 is therefore an intended fallback, not a replayed result.

The hybrid was designed after observing the F6 failure. The combiner variants
were swept only on F6; the reactive quantile/window were not exhaustively
swept; the reported aggregate uses warm-pool readiness; and no strict-rewarm
or bill-from-order hybrid run exists. Other folds are useful no-regression
evidence, but they are not independent workload validation of a controller
designed on F6.

**Adjudication**

The raw aggregate arithmetic is correct:
2,944,979.7 / 3,869,278.8 = 0.7611×, with aggregate p99 589.301 ms.
The F6 recovery is also real. The words “deployable,” “seven-fold robust,” and
unqualified “cost-minimal” exceed the evidence.

**Required correction**

Use wording such as:

> “A post-hoc F6-designed max hybrid passes the six folds on which a forecast
> schedule exists, including e13, at 0.76× static under warm-pool readiness;
> it is cost-minimal among the tested F6 max-combiner settings.”

Implement and replay the F1 reactive fallback, add strict-readiness and
bill-from-order sensitivities, and validate on an untouched trace before
restoring “deployable.”

### 4. The new 0.76/0.82 headlines are only partially inside the claimed end-to-end provenance chain

**Classification:** reproducibility/provenance failure; stale formal
verification.

**Direct manuscript quotations**

- `tex/closedloop.tex:876-878`: “the provenance store behind every number
  above held 2623 simulation runs ... validated by 73 automated consistency
  checks.”
- `tex/apendice.tex:8-13`: “Nearly every quantitative claim ... is generated
  by a versioned script over archived inputs ... [and] maps each figure and
  table to its generating script and primary artifact.”
- `tex/tese.tex:144-151`: reruns “are archived ... recorded in the results
  ledger, and mapped in the reproduction manifest.”

**Cross-check**

- `provenance/loader/runid.py:77-82` now recognizes `encoder_hybrid` and
  `lang_qsweep`, and `provenance/schema/32_scope_misc_runids.sql:9-15`
  renamed five earlier `misc:*` rows. The database therefore now contains
  four `encoder_hybrid` run IDs—F6 forecast, reactive, hybrid, and one
  `fc_p50` combination seed—and one `lang_qsweep` row.
- This is a run-ID repair, not complete ingestion. The database still lacks
  the 0.7611 aggregate hybrid result, the complete combination sweep, and the
  seven-fold hybrid population: only four run IDs represent a raw tree with
  35 hybrid summary files. The migrated hybrid/reactive rows also lack
  canonical policy/window identities.
- All `simulation/run_encoder_hybrid*`, `simulation/combine_schedules.py`, and
  `simulation/results/encoder_hybrid/` paths are untracked.
- The appendix's only daily-fold row, `tex/apendice.tex:287-289`, points to the
  older `defense/anim/data/g4_folds/folds_table.md`; it does not map the hybrid
  scripts, aggregate, folds, or combination sweep.
- The language calibration has 162 current database rows, but
  `tex/apendice.tex:319-324` maps only the old p90/s8 `llm_week` family. It
  does not map `run_lang_calib*.sh`, `run_lang_folds.sh`,
  `lang_qsweep/eval_p90_s6`, or its fold artifacts.
- The 0.82 language operands and folds are therefore numerically DB-backed,
  but their headline run rows have null `commit_sha`/artifact commit identity.
- `simulation/results/lang_qsweep/`, the calibration scripts, and
  `provenance/loader/load_langcalib.py` are also untracked.
- `provenance/audit/claims/closedloop.json` (2026-07-19 21:57) and
  `provenance/audit/verified/closedloop.json` (22:29) predate the July 24-25
  results and contain no 0.76, 0.82, hybrid, 440.0, or 330.4 claim.
- The derived-value section of `provenance/verify_all.sh:175-190` still checks
  the old 0.965 language result and 0.62 encoder result, not 0.76 or 0.82.
- Its containment gate at `provenance/verify_all.sh:223-238` says newly added
  `fold-robust` results must fail. The current diff contains two such lines,
  but the gate passes because its diff-filter regular expression removes
  every added line (Reverification Finding R1).
- A full live run consequently ends “39 passed / 0 failed / 6 warnings” and
  “DELIVERY-READY,” matching the claim at
  `progress/results-ledger.md:2373-2389`, without checking either new ratio
  and while the registered database suite still has five failures.
- The appendix has no mapping for the per-model controller-cost numbers
  promised at `tex/closedloop.tex:860-870`.

**Adjudication**

The latest migration improves namespace integrity and invalidates the prior
blanket statement that the database had zero hybrid rows. It does not close
the evidential chain. The new result files exist locally, and their arithmetic
is reproducible. This is not evidence that the numerical results are false.
It is evidence that the manuscript's stronger claim—database, checks,
versioned scripts, formal claim verification, and appendix mapping behind
every number—is false for its newest conclusions.

**Required correction**

Before submission:

1. version the new scripts and immutable result artifacts;
2. ingest the complete hybrid aggregate/fold/combination families with run
   status, hashes, canonical policy/window identity, and source paths;
3. add explicit manifest rows for hybrid, language calibration, language
   folds, and controller cost;
4. regenerate the formal claim and verified corpora;
5. extend derived-value checks to the 0.76 and 0.82 claims; and
6. repair and regression-test the containment gate before accepting its
   delivery verdict.

### 5. The headline reactive language baseline did not model the cold-start lead claimed as a shared control

**Classification:** baseline-protocol mismatch; fairness/causal-attribution
defect.

**Direct manuscript quotations**

- `tex/baselines.tex:34-37`: “Both baselines get every structural advantage
  the predictive policy ... will have—same windows, actuation mechanics,
  cold-start leads—so whatever separates the policies is information, not
  plumbing.”
- `tex/baselines.tex:57-61`: “Cold-start lead is modeled explicitly ...
  language L in {60,...,300} s.”

**Cross-check**

`simulation/run_32_reactive.sh:31-42` launches all 14 headline language
reactive configurations without `STARTUP_TIME`.
`simulation/run_replay.sh:38-44` documents and implements:

> “unset = instant workers”

The predictive language runs explicitly use `STARTUP_TIME=60`, for example
`simulation/run_44_riders.sh:33`.

The database independently confirms 14 current runs under experiment
`reactive`, sourced from `simulation/results/reactive32/`, and
`count(cold_start_s) = 0`.

**Adjudication**

The 14/14 mean-target pass and 14/14 tail-SLA failure still reproduce, with
maximum TTFT p99 3494.726 ms. Instant scale-up advantages the reactive
baseline, so the narrow conclusion that reactive tail sizing fails is
conservative. These runs nevertheless cannot support equal-plumbing,
equal-lead, lead-aware cost, or attribution solely to information. The
separate burst1 sensitivity at `tex/baselines.tex:163-167` did use 60 seconds
and is not affected.

**Required correction**

Either rerun all 14 configurations with `STARTUP_TIME=60`, or label the
headline runs as an optimistic zero-startup reactive lower bound and remove
the equal-cold-start assertion.

### 6. The repeatedly asserted 588-ms “physical service floor” is not a floor

**Classification:** metric-population error; invalid addition of marginal
percentiles; physical-interpretation overclaim.

**Direct manuscript quotations**

- `tex/closedloop.tex:85-90`: “588 ms, the platform's zero-queueing service
  floor: a full-batch forward ... plus the p99 handoff transfer ...
  what remains is physics.”
- `tex/closedloop.tex:399-401`: rows “coincide at the zero-queueing service
  floor.”
- `tex/closedloop.tex:930-932`: “The 588 ms floor therefore assumes ...”
- `tex/conclusion.tex:95-97`: “the 588 ms floor ... assume[s] an
  embedding-only handoff or a >=100 Gbps fabric.”

**Cross-check**

On the same 5.60-day span and under the same converter:

| Run | All-request encoder-delay p99 | Batch-service p99 | Handoff p99 |
|---|---:|---:|---:|
| issue-time p90 forecast | 588.370 ms | 316.369 ms | 272.001 ms |
| static C16 | **565.249 ms** | 316.369 ms | 272.001 ms |

A same-harness result below 588 ms disproves a universal or physical lower
bound.

The derivation is also statistically invalid: the sum of two marginal p99s is
not generally the p99 of the per-request sum. Moreover,
`workload/trace_to_two_pool.py:486-497` assigns zero encoder delay to every
text-only request, and lines 577-583 compute the published percentile over
**all** requests. In this span only 350,168 of 749,601 requests contain
images. The current issue-time image-bearing conditional p99 recomputes to
799.410 ms, showing that population choice is material.

**Adjudication**

Approximately 588-589 ms is a repeatable *observed all-request plateau* for
several policies and schedules. It is not a physical/service lower bound and
cannot be derived by adding the two marginal p99s.

**Required correction**

Call it an observed no-queue/all-request plateau, state the population on
every table/caption, and optionally report the image-bearing conditional
p99. Remove “what remains is physics,” “floor,” and additive-percentile
derivations unless a request-linked lower-bound proof is supplied.

---

## Medium-severity findings

### 7. ARIMA “matches Chronos under the same protocol” compares different origin populations

**Direct quotation**

`tex/predictors.tex:164-173` says the Dynamo predictors are “Run through the
same protocol” and that “at 15s ... ARIMA matches Chronos”; the claim is
repeated at `tex/predictors.tex:332-335`.

**Cross-check**

| Predictor/family | Origins used / available | Image WAPE at 15 s |
|---|---:|---:|
| ARIMA | 300 / 2,687 | 66.751% |
| Prophet | 300 / 2,687 | 73.283% |
| Constant | 2,687 / 2,687 | 76.378% |
| Kalman | 2,687 / 2,687 | 81.110% |
| Chronos/cov | full reference population | 66.740% |
| Toto/cov | full reference population | 63.740% |

ARIMA and Prophet use an evenly subsampled 11.2% of origins. Sharing the
common time span is not the same as sharing the evaluated origin population,
and a 0.011-WAPE-point apparent all-population tie cannot be interpreted
without paired origins and uncertainty.

A fresh rescore of the archived foundation-model forecasts on the exact same
300 origins gives Chronos/cov 66.1203%, TimesFM 66.5152%, Toto/cov 60.8896%,
and ARIMA 66.7506%. The apparent 0.011-point ARIMA/Chronos tie therefore
becomes a 0.630-point gap on matched origins. ARIMA remains close; “same
protocol” and the precision implied by “matches” do not.

**Correction:** score every method on all 2,687 origins, or rescore every
method on the identical 300 origin keys and report paired uncertainty.
Until then call ARIMA an evenly subsampled estimate, not a demonstrated match.

### 8. A burst-episode merge bug changes the onset values and the reported median

**Direct quotation**

- `tex/trace-eda.tex:253-265` reports “baseline-to-peak in a median of 6
  minutes” and captions the figure “across the 18 episodes ... a median of 6
  minutes.”
- `tex/intro.tex:134-136` repeats “a median of six minutes.”
- `tex/baselines.tex:217-225` calls burst3 and burst6 “The two fastest
  onsets,” says they “share their aggregate load,” and attributes the
  different controller outcome to “the fine shape of the onset, not the
  volume.”

**Cross-check**

`analysis/trace_eda/i_burst_anatomy.py:61-70` merges overlapping spans by
keeping the earlier `start_baseline` but, when a later peak is higher, copies
that later episode's already-computed `onset_minutes`. It does not recompute
onset from the final merged span.

Two rows expose the defect:

| Peak | Final start | Stored onset | Timestamp/recomputed onset |
|---|---|---:|---:|
| 2024-10-16 00:29 | 2024-10-15 23:36 | 1 min | 53 min |
| 2024-10-21 19:53 | 2024-10-21 13:09 | 220 min | 404 min |

`analysis/trace_eda/k_episode_clusters.py:47-76` first merges spans and then
recomputes peaks/onsets. Its 18-episode population has median 6.5 minutes.
The “one third are 1-2 minutes” statement survives: 6/18 corrected episodes
are at most two minutes.

The defect now propagates into the baseline mechanism.
`tex/baselines.tex:196-201` and `simulation/windows.json` still label
burst1/burst6 as 220/1
minutes; their recomputed merged onsets are 404/53 minutes. Burst3 is truly a
one-minute onset, but burst6 is not a matched-fast comparator. Its success
where burst3 fails can therefore be explained by a 53-versus-1-minute onset,
not by demonstrated fine-shape effects between equally fast, load-matched
episodes.

**Correction:** merge spans before computing peak, onset, ramp, jump, and
decay; regenerate the stats, figure, and `windows.json`; report 6.5 minutes
or “about 6-7 minutes”; and remove the matched-fast-onset causal claim unless
a corrected, properly matched shape analysis supports it.

### 9. “2,623 simulation runs validated by 73 checks” misstates both nouns

**Direct quotation**

`tex/closedloop.tex:876-878`: “2623 simulation runs across the committed
families, validated by 73 automated consistency checks.”

**Cross-check**

- The live database now contains **2,628 current run records**, so the
  manuscript's 2,623 census is stale even on its own denominator.
- That denominator is not simulation-only. At minimum it includes 41
  `predictors`, 16 `eda`, and 10 `live` runs—67 clearly non-simulation
  records.
- 73 is the count of check **definitions**. Only 72 are enabled.
- The live full suite returns 67 passes and five failures:
  C002 (error), plus warnings C107, C207, C214, and C302.
- C207 currently reports 306 of 4,320 ingest rows whose `run_id` is not a
  run-spine ID.
- C214 now reports **69 of 440** unresolved verification rows, not its
  documented expected nine. Of the 60 new unresolved rows, 52 A11 labels
  exactly match existing runs but lack pointers and eight A11 week
  L120/L300 labels have no run-spine row.

The five check IDs are known, but C214's increased failure population is a
new defect under its own check note. The failures do not establish that every
affected value is wrong. They do prevent the unqualified word “validated.”

**Correction:** repair/adjudicate the C214 regression and use a timestamped
census such as “2,628 current provenance run records; 73 defined checks, 72
enabled, 67 passing and five known failures.” Separate simulation from EDA,
forecasting, and live-validation records, and do not call untracked families
“committed.”

### 10. The limitations quote fold economics from an older, superseded language policy

**Direct quotations**

- `tex/closedloop.tex:970-972`: “The language pool's fold ratios run
  0.93-3.81× ... above parity in six of seven folds.”
- `tex/conclusion.tex:103-105`: “the language ratio reads 1.03× under
  request-matched normalization.”

**Cross-check**

Those values describe the original p90/s8 edge. The newly foregrounded
e13-robust p90/s6 policy has current same-fold ratios:

`0.960, 0.689, 0.725, 1.424, 0.657, 0.709, 1.677`.

Its range is therefore 0.66-1.68× and only 2/7 folds are above parity. Its
request-matched aggregate ratio is 0.87×, not 1.03×. The old values remain
valid for the old policy, but the prose no longer names that scope and reads
as a limitation of the selected robust policy.

**Correction:** label 0.93-3.81× and 1.03× explicitly as p90/s8, and provide
the p90/s6 range and denominators beside them.

### 11. The 99.99% square statistic is correct, but the bulk-request characterization is false and its class artifact is stale

**Direct quotation**

`tex/trace-eda.tex:31-36`:

> “image counts are perfect squares ... Images therefore arrive as k×k tile
> or frame grids: bulk batches, not independent single images.”

**Raw-trace recomputation**

| Population | Count |
|---|---:|
| All requests | 1,000,000 |
| Image-bearing requests | 500,000 |
| Positive nonsquare image counts | 53 |
| Distinct positive nonsquare values | 22 |
| Single-image requests | 330,029 |

Thus 499,947/500,000 = 99.9894% are square-count requests: the manuscript's
rounded 99.99% statistic is correct. The categorical lead-in “image counts
are perfect squares” is overbroad, and the follow-on characterization is
materially misleading because 66.0058% of image-bearing requests have exactly
one image. Bulk grids dominate **image volume**, not image-bearing request
arrivals.

The checked-in class artifact is also stale relative to its generator.
`analysis/trace_eda/j_classes_stats.json` reports 500,017 text requests with
nonzero image share instead of the exact 500,000 text-only requests: the 17
`NumImages=2` rows leaked into `text` when that artifact was generated.
Current `analysis/trace_eda/j_classes.py:17-29` would instead absorb those
positive two-image nonsquares into the class named `single`. The JSON predates
that code and was not regenerated, but regeneration alone would trade a stale
count for a mislabeled class.

**Correction:** state 99.9894%, distinguish request frequency from image
volume, give nonsquare requests an explicit class rather than rounding their
square root, and regenerate the class artifact/figure with the fixed code.

### 12. Forecast facts cannot be relationally retracted or filtered to current runs

**Direct quotations**

- `tex/predictors.tex:24-26`: “Every number and figure is reproducible ...
  the full forecast set is archived.”
- `tex/intro.tex:318-321` states that every phase leaves an audit artifact and
  that corrections are recorded.

**Cross-check**

The current database schemas are:

- `forecast`: model/mode/variate/resolution/origin/horizon/value/source tag,
  but **no `run_id`**;
- `forecast_metrics`: model/mode/span/resolution/variate/candidate/metrics,
  but **no `run_id` or source path**; and
- `quantile_coverage`: model/signal/detail, but **no `run_id`**.

The ingest-ledger rows for the metric Parquets, quantile coverage, and
ablation have `run_id = NULL`. `v_forecast_thesis_corpus` filters mode, not
current/retracted run status. The new scoped-run-ID migration changes five
miscellaneous run labels; it does not add keys to these forecast fact tables.

Current disk hashes match the ingest ledger, so this review found no presently
stale forecast value. The defect is governance: a future correction or
supersession cannot propagate relationally into these facts.

**Correction:** attach source/run IDs to forecasts and all derived metrics,
and expose current-only views joined to the run spine.

### 13. The 235B result is numerically valid but mixes result vintages and lacks the promised appendix mapping

**Direct quotation**

`tex/twopool.tex:71-79`:

> “with ITL p99 87.7 ms at that rate ... its knee drops to s=1 ... (per-metric
> numbers in Appendix).”

**Cross-check**

The tracked legacy artifact
`simulation/results/235b/llm_head2k_aic235btp8_s1.json` exactly supports
87.721685-ms ITL p99 and 397.679638-ms TTFT p99. It was committed as the
thesis-era wheel-based spot check and sampled only `s={1,4,16}`.

The current database's later source-built series instead reports:

| Run | Runtime | ITL p99 | TTFT p99 |
|---|---|---:|---:|
| 235B TP8 s1 | source 1.3.0 | 86.150977 ms | 387.368397 ms |
| 235B TP8 s2 | source 1.3.0 | 210.587850 ms | 523.976648 ms |

Both vintages support the scientific conclusion that s1 is feasible and the
235B envelope is lower. The 1.8% s1 difference changes no verdict. The issue
is lineage: the printed 87.7 comes from the old wheel run, while the adjacent
s2 failure that precisely pins the current knee comes from the later
source-built sweep. No single displayed vintage provides both facts, and
the database still has zero `m235b` rows and zero rows sourced from
`simulation/results/235b/`. `tex/apendice.tex` contains no 235B mapping
despite the explicit promise.

**Correction:** either report the internally consistent source-built
86.2/210.6-ms pair and map it, or label 87.7 explicitly as the sparse
wheel-era spot check and avoid implying that it directly measured the s2
crossing.

### 14. Burst5 C8 is a superseding stability correction, not the raw grid-feasible optimum

**Direct quotations**

- `tex/baselines.tex:47-48`: “every replay begins and ends with a drained
  encoder queue.”
- `tex/baselines.tex:67-70`: “A grid search ... yields the smallest
  grid-feasible fleet per window.”

**Cross-check**

The current supersession-aware view reports for burst5:

- raw `c_star = 16`;
- corrected/effective `c_star = 8`; and
- rationale: the original divergence flag was an endpoint artifact, with a
  later three-times tiling showing stability for C>=8.

At the published C8 point, the current run still has
`queue_divergent = true` and 501 images at the end of arrivals, then drains
0.386 seconds later. Because `vision_sim_end_s` explicitly includes that drain
tail, this does **not** falsify the literal statement that the replay itself
ends drained. It does show why the raw endpoint heuristic rejected C8 and why
the later stability test, rather than the raw grid alone, is load-bearing.

**Correction:** say “the archived grid plus a superseding burst5 stability
test yields the effective optima.” If discussing the boundary, distinguish
the nonempty end-of-arrivals state from the drained replay end. Retain the
appendix's existing supersession disclosure.

### 15. “7,716 frames-class requests” silently substitutes a dispatch-cap population

**Direct quotations**

- `tex/twopool.tex:312-315`: “The window's 7,716 frames-class requests (>64
  images each) ...”
- `tex/trace-eda.tex:74-78`: the canonical frames class is “k>10 grids.”

**Cross-check**

On the exact burst1 slice:

- `NumImages > 64`: 7,716 requests;
- canonical square-grid `k>10`, equivalent to `NumImages >= 121`: 7,643
  requests.

The 73 extras are 25 requests with 81 images and 48 with 100 images.
The archived converter's `requests_chunked=7716` confirms that 7,716 is the
population exceeding the 64-image dispatch cap, not the EDA frames class.

**Correction:** call 7,716 “requests exceeding the 64-image dispatch cap” or
“chunked requests.” Use 7,643 for the canonical frames class.

### 16. “Nothing forecasts single bins” is false for three of four signals

**Direct quotation**

- `tex/predictors.tex:145-151`: “at sub-minute cadence, nothing forecasts
  single bins, and no policy should assume otherwise.”
- `tex/trace-eda.tex:305-307`: “Below the one-minute scale, all signals reach
  a white shot-noise floor: finer-grained inputs add noise, not information.”

**Cross-check**

At one-second cadence, the best foundation-model point WAPE is:

| Signal | Best WAPE |
|---|---:|
| requests | 62.911% |
| generated tokens | 81.631% |
| context tokens | 86.043% |
| images | 98.761% |

Only the image signal is approximately at the 100% zero-prediction/no-skill
floor. The other three retain material sub-100% WAPE.

**Correction:** restrict the statement to individual image bins and state
that the smoother signals retain measurable one-second skill.

### 17. The contamination comparison cannot establish the claimed causal bound

**Direct quotation**

`tex/predictors.tex:322-328`:

> TimesFM “predates the release and lands within approximately 2 WAPE points
> of the other two ... bounding any contamination advantage at about that
> size.”

**Cross-check**

For the consumed 15-second image forecast:

| Horizon | TimesFM | Best Toto | Difference |
|---|---:|---:|---:|
| pooled | 81.102577% | 76.776355% | 4.326 pp |
| h=1 | 70.260371% | 63.742556% | 6.518 pp |

Approximately two points is an average across signals, not a bound in the
consumed image cell. More fundamentally, performance by a different
architecture cannot causally bound an unknown contamination advantage:
intrinsic model differences can offset or amplify it.

**Correction:** call the near tie reassuring indirect evidence and say the
contamination magnitude remains unidentified.

### 18. The language cost prose changes denominators and double-rounds the aggressive ratio

**Direct quotations**

- `tex/closedloop.tex:317-324`: the p90 edge is “approximately 36%
  over-provisioned.”
- `tex/closedloop.tex:843-847`: “0.82×/0.87× ... or 0.62× if the single e13
  onset is dropped.”

**Cross-check**

Against the old 518.606-GPU-h edge:

- moving to aggressive p70/s6 (330.350 GPU-h) removes 36.3% of the **original
  spend**;
- equivalently, the old point is 57.0% above the aggressive requirement; and
- moving to robust p90/s6 (440.041 GPU-h) removes only 15.2% of the original
  spend.

Thus “36% over-provisioned” is meaningful only with the original-spend
denominator and the aggressive, e13-failing objective. It is not the robust
policy's overprovisioning.

Also, 330.3500529 / 537.4093139 = 0.614708. Correct direct rounding is 0.61
at two decimals or 0.615 at three. The ledger first rounds to 0.615 and then
rounds that intermediate to 0.62. “Near 0.62×” is acceptable; an exact
two-decimal `0.62×` is not.

**Correction:** name the denominator/objective (“36.3% of original p90/s8
spend removed by the aggressive point”), report 15.2% for the robust point,
and print 0.615× or 0.61× for p70/s6.

---

## Low-severity but confirmed findings

### 19. The chapter summary drops its own episode qualification

**Direct quotation**

`tex/closedloop.tex:1001-1004`:

> “the policy meets the SLA in aggregate and per-episode at 0.62 times ...”

Earlier, `tex/closedloop.tex:423-427` correctly limits this to “every declared
in-span burst episode” and immediately discloses e13 at the finer grain. The
summary's unqualified “per-episode” reads as all detected/fold episodes, which
is false for e13.

**Correction:** say “aggregate and the four declared in-span burst windows at
0.62×; e13 fails at the finer daily-fold grain.”

### 20. The full-trace result is numerically correct but has no canonical database window identity

**Direct quotation**

`tex/baselines.tex:239-243` reports a one-million-request full-trace result
and reactive cost of 0.687× static C8.

**Cross-check**

Current A13 rows reproduce the claim:

- reactive: 3,323,189.5 worker-s, p99 588.370 ms;
- static C8: 4,838,397.6 worker-s, p99 677.461 ms; and
- ratio: 0.686837×.

All three rows have `window_name IS NULL`, although the canonical alias layer
distinguishes `fulltrace` from the 5.60-day aggregate. They cannot join to
that window identity.

**Correction:** backfill canonical `window_name='fulltrace'` with a recorded
provenance correction, or add an explicit manifest mapping.

### 21. A 2-to-8 fleet swing is fourfold, not an order of magnitude

**Direct quotation**

`tex/baselines.tex:112-118`:

> “the encoder requirement swings from 2 workers ... to 8 ... the
> order-of-magnitude missizing ... now as a fleet-sizing fact.”

The effective fleet swing is exactly 4×, and the following sentence correctly
calls calm-day overprovisioning 4×. “Order of magnitude” may describe an
upstream rate mismatch, but not this fleet result.

**Correction:** “a fourfold fleet-sizing swing, the operational consequence
of the order-of-magnitude workload-rate mismatch.”

### 22. “Dense N=1-512 sweep” overstates the off-cap sampling

**Direct quotation**

- `tex/aiconfigurator.tex:227-233`: “A dense sweep (N=1-512) confirms ...”
- `tex/apendice.tex:170-176`: the appendix likewise says N was “swept densely
  over N=1-512.”

`collector_artifacts/phaseE_physical_anchor/vllm_eager_dense.py:20` defines
`N=1..64` plus only `{96,128,192,256,512}`. The 69-row artifact is dense
through the serving cap and sparse above it. The load-bearing 12.8% claim for
every `N<=64` remains supported.

**Correction:** “a dense N=1-64 sweep plus five off-cap probes.”

### 23. “No fixed quantile improves” has two tiny counterexamples

**Direct quotation**

- `tex/predictors.tex:348-359`: “for median-point models no fixed quantile
  improves on the point path.”
- `tex/intro.tex:348-353`: “no fixed quantile beats a point forecast that is
  already the median.”

Under the chapter's common-span pooled-horizon protocol:

- Chronos/cov, 1-s images: point 99.284628%, p40 99.259310%
  (0.025319-point improvement);
- Chronos/uni, 1-s images: point 99.587516%, p40 99.524607%
  (0.062909-point improvement).

The body at `tex/predictors.tex:248-250` already uses the defensible wording
“improve essentially nothing.”

**Correction:** use “no fixed quantile materially improves” and optionally
disclose that the two exceptions are at most 0.063 WAPE point.

### 24. “All analyses ran on GPU” is literally false

**Direct quotation**

`tex/trace-eda.tex:15-17`: “All analyses ran on GPU (cuDF, cuML, CuPy;
RTX 5090).”

Examples of CPU work include:

- `analysis/trace_eda/a_quality.py:43-58`: `.to_pandas()` and NumPy
  `polyfit`;
- `analysis/trace_eda/c_temporal.py:14-29`: pandas reindexing and subsequent
  statistics;
- `analysis/trace_eda/i_burst_anatomy.py:11-20`: pandas conversion followed by CPU episode
  detection, merging, and statistics; and
- `analysis/trace_eda/k_episode_clusters.py:29-88`: CPU span construction and feature
  engineering before cuML clustering.

**Correction:** “GPU-accelerated preprocessing and selected model kernels,
with reduced statistics and plotting on CPU.”

### 25. “No aggregation window” extrapolates beyond the tested range

**Direct quotation**

`tex/trace-eda.tex:130-135`:

> “burstiness is scale-free, so no aggregation window smooths it away.”

The evidence is raw, undetrended Fano/seasonality analysis over a finite tested
stack, approximately one second through one hour. It cannot establish every
possible aggregation window. The same extrapolation reappears at
`tex/trace-eda.tex:325-326`: “no practical aggregation window recovers a
well-behaved image signal.” `tex/intro.tex:138-143` already uses the proper
scope: “every tested operational scale” and “no tested averaging window.”

**Correction:** reuse the introduction's tested-range wording.

### 26. “Still-generating” is stale, untimestamped experiment-state language

**Direct quotations**

- `tex/closedloop.tex:528-530`: “experiment families still generating at the
  time of writing (a16, g2, g3_32b, g6).”
- `tex/closedloop.tex:892-893`: “the still-generating families ... are
  excluded.”

The current database contains 771 current rows from those families: a16 51,
g2 32, g3_32b 232, and g6 456. Row presence does not prove that generation
has finished—partial results can coexist with active jobs—and their exclusion
from the displayed tables may be intentional. The defect is that
“still-generating” is an untimestamped state label that a later reader cannot
reproduce from the manuscript or run registry.

**Correction:** say “excluded experiment families at the [dated] manuscript
snapshot” and state why they are excluded.

---

## New findings detected by the 2026-07-26 reverification

### R1. The delivery containment gate is false-green

**Severity:** high. **Classification:** verification-control implementation
failure; false delivery attestation.

**Direct quotations**

- `provenance/verify_all.sh:223-227`: post-manuscript results “must never” be
  added to a results chapter and the test therefore examines “newly-added
  lines only.”
- `provenance/verify_all.sh:231-235` explicitly treats `fold-robust` as a
  forbidden newly added pattern.
- `progress/results-ledger.md:2373-2386`: “Verification restored green” and
  “39 passed / 0 failed / 6 warnings ... DELIVERY-READY.”

**Cross-check**

The current diff contains two added `fold-robust` lines:

- `tex/closedloop.tex:474`: “A finer grain, and the fold-robust point.”
- `tex/closedloop.tex:500-502`: “0.76× fold-robust.”

Nevertheless, the exact assignment at `provenance/verify_all.sh:229-230`
produces an empty `ADDED` variable. The first command correctly selects added
lines with extended regex `grep -E '^\+'`; the second uses basic-regex
`grep -v '^\+\+\+'`. Under GNU basic regular expressions, `\+` is a
repetition operator, so this pattern matches every selected line rather than
only the `+++` diff header. The inversion removes all evidence before any
forbidden pattern is tested.

The live reproduction is decisive:

| Diff stage | Bytes | `fold-robust` hits |
|---|---:|---:|
| Added lines including header | 7,077 | 2 |
| Exact gate pipeline | 0 | 0 |
| BRE-corrected reproduction `grep -v '^+++'` | 7,006 | 2 |

The adjacent “derived-value recomputation” is also less independent than its
comment claims. `provenance/verify_all.sh:162-188` says every headline is
recomputed from raw operands, but the encoder 0.62 check hard-codes rounded
2,410,800/3,869,300 operands rather than reading the current artifact values
2,410,754.7/3,869,278.8. The rounding verdict happens to survive; the check
would not detect drift in those source artifacts.

**Adjudication**

The wrapper's final green verdict is not evidence that containment passed.
It is evidence that the relevant input was silently erased. This directly
contradicts the script's design rule at `provenance/verify_all.sh:11-13`:
“it never hides [failures]” and “an unevaluated check that prints green is
worse than no check at all.”

**Required correction**

Parse additions structurally inside diff hunks (for example, an `awk` parser
that begins after `@@` and resets at `diff --git`) rather than deleting
header-shaped strings. A simple `grep -v '^+++'` is sufficient to demonstrate
this bug but could itself discard a legitimate added source line beginning
with `++`. Regression-test positive, negative, and leading-plus fixtures, and
avoid a future `grep -q`/`pipefail` SIGPIPE trap by testing a here-string or
file. Then explicitly adjudicate whether the two `fold-robust` additions are
permitted. Independently add artifact-read derived-value gates for 0.62,
0.76, and 0.82; the current wrapper checks neither new ratio and hard-codes
the encoder operands.

### R2. Burst4's 165-second lead is outside the declared experiment and is mis-mapped as a factorial result

**Severity:** medium. **Classification:** post-manuscript cell promoted into
the main protocol; incomplete manifest; threshold overclaim.

**Direct manuscript quotations**

- `tex/baselines.tex:57-61` declares encoder leads
  `L in {15,30,45,300} s`.
- `tex/baselines.tex:187-190` defines `L*` as “largest lead at which the SLA
  holds.”
- `tex/baselines.tex:199,207-210` publishes burst4 `L*=165 s` from a
  “supplementary sub-grid lead.”

**Cross-check**

The backing row is `a2:burst4_reactive_L165`, p99 904.739 ms, sourced from
`defense/anim/data/a2_runs/burst4_reactive_L165.jsonl`.
`progress/results-ledger.md:555-562` originally calls L165 a “NEW CELL” and
“supplementary, not cited in tex”; lines 565-570 identify the later
defense-animation fleet that generated burst4's 904.7-ms value.

The appendix instead maps `tab:base-react-enc` at
`tex/apendice.tex:304-312` to
`simulation/run_44_factorial_issuetime.py` and the factorial artifacts. Those
artifacts do not contain this reactive L165 cell. Moreover, a pass at 165 and
a failure at the next tested point, 300, identify only the largest **tested**
passing lead, not an exact feasibility threshold.

**Required correction**

Write “largest tested passing lead,” add the A2 generator and artifact to the
manifest, and either sweep the 165-300-second interval or avoid presenting
165 as an identified `L*`. Do not describe the result as part of the declared
four-point factorial.

### R3. “Image dispersion decays the slowest” is numerically false

**Severity:** medium. **Classification:** incorrect cross-signal
interpretation of correct operands.

**Direct manuscript quotations**

- `tex/trace-eda.tex:321-324`: “The image signal's excess-dispersion also
  decays most slowly with window size.”
- `tex/trace-eda.tex:331-335`: the image signal “decays the slowest.”

**Cross-check**

The current database operands give:

| Signal | CV² at 1 s | CV² at 60 s | Fraction retained | Proportional drop |
|---|---:|---:|---:|---:|
| requests | 1.066798 | 0.321157 | 0.3010 | 3.32× |
| images | 25.713806 | 3.830447 | 0.1490 | 6.71× |
| context tokens | 4.826441 | 0.852828 | 0.1767 | 5.66× |
| generated tokens | 4.585145 | 0.395092 | 0.0862 | 11.61× |

Images remain the most dispersed signal at both endpoints and every tested
window, but their CV² decays proportionally faster than requests and context
tokens. “Highest throughout” does not imply “slowest decay.”

**Required correction**

Replace the causal-rate wording with the supported result: “image CV² remains
highest across every tested window, although it falls 6.7× from 1 s to
60 s.”

### R4. “Invisible” and “do not co-occur” overstate a valid relative-decoupling result

**Severity:** medium. **Classification:** categorical wording contradicted by
the headline minute; denominator/scope omission.

**Direct manuscript quotations**

- `tex/trace-eda.tex:235-238`: at the largest image episode, request rate is
  “only 4.48 requests/s—bursts are invisible in the request signal.”
- `tex/intro.tex:123-129`: the two signals' extremes “do not co-occur.”
- `tex/related.tex:279-284`: image rate is “nearly invisible” in request
  rate.

**Cross-check**

The request-rate mean is 1.653439/s and its p99 is 4.35/s. At the largest
image minute, request rate is 4.483333/s: 2.71× its mean and **above its own
p99**. It is one of the five shared hot minutes. Across the complete
top-percentile sets, however, the intersection is only 5 and Jaccard
similarity is 0.0247525.

**Adjudication**

The broader decoupling is strong and should remain: image and request
extremes overlap only rarely, and the request excursion is far smaller than
the image excursion. The specific largest image minute is not invisible and
is not a non-co-occurrence.

**Required correction**

Say that the request excursion is much smaller and that only five
top-percentile minutes overlap, while acknowledging that the largest image
minute itself is above request p99.

### R5. The H≈0.93 fit does not isolate the daily-cycle alternative it claims to exclude

**Severity:** medium. **Classification:** band-sensitive spectral inference;
unstated sensitivity.

**Direct manuscript quotation**

`tex/trace-eda.tex:272-276` says H≈0.93 is fit over 10 minutes to 12 hours,
“clear of the diurnal fundamental,” and therefore “reflects scale-free
structure rather than the daily cycle.”

**Cross-check**

The same chapter identifies 12-, 8-, and 6-hour diurnal harmonics at
`tex/trace-eda.tex:122-125`. Yet
`analysis/trace_eda/f_fourier.py:69-75` fits the whole 10-minute-to-12-hour
band without notching those harmonics. An endpoint sensitivity on the same
data gives image H approximately 0.93 with a 12-hour upper period, 0.90 at
6 hours, 0.86 at 5 hours, and 0.82 at 3 hours.

**Adjudication**

The 69-versus-9-minute autocorrelation contrast still supports greater image
persistence. The exact 0.93 value and the claim that the fit distinguishes
scale-free dependence from daily structure are not independently established.

**Required correction**

Call H a spectral-slope-derived proxy, notch or sensitivity-test the
12/8/6-hour harmonics, report endpoint sensitivity, and avoid using 0.93 as
an independent Hurst estimate.

### R6. Single-source-build wording contradicts the runtime census and appendix

**Severity:** low. **Classification:** environment-scope inconsistency.

**Direct manuscript quotations**

- `tex/related.tex:143-147`: “the commit used for this thesis's simulations
  (v1.3.0 source build).”
- `tex/tese.tex:264-270`: “simulations use the v1.3.0 source build.”

**Cross-check**

`tex/apendice.tex:35-50` explicitly lists “1.2.1 wheel / 1.3.0 source” and
says “the pinned 1.2.1 wheel is the Phase-2 baseline.” The current-run
database census contains 595 source-build rows, 110 wheel rows, and 1,923
rows with runtime build unspecified.

**Required correction**

Use the appendix's defensible scope everywhere: “calibrated runs from the
load sweeps onward use v1.3.0; Phase-2 baseline runs use the pinned 1.2.1
wheel.” Backfill missing runtime identity where it is needed for comparison.

---

## Additional delivery blockers

### D1. The document still declares itself preliminary and institutionally incomplete

`tex/tese.tex:141-156` contains the explicit note:

> “This is a preliminary version (2026-07-11) prepared for advisor review ...
> Pending for the defense version: institutional formatting (departmental
> template, ABNT front matter, biblatex bibliography) and final institutional
> review.”

This is admirably candid and not a scientific contradiction. It is still a
hard submission/defense-version blocker, and its claim that reruns are mapped
in the reproduction manifest is stale for the new hybrid/language results
(Finding 4).

### D2. The clean build succeeds but several tables materially overrun the text block

The isolated build produced a 135-page, 2,387,543-byte PDF with no undefined
references/citations and no LaTeX error. It also reports:

- 50.295-pt overflow at `tex/closedloop.tex:201-214`, the EWMA comparison
  table beginning “Forecaster (p90)”;
- 45.455-pt overflow at `tex/closedloop.tex:404-421`, the aggregate policy
  table beginning “Policy / p99 / Mworker-s / vs. static / Episodes”;
- 40.968-pt overflow at `tex/apendice.tex:104-111`; and
- multiple 20-24-pt manifest-path overflows.

The two closed-loop tables visibly extend into the right margin. They are not
clipped in the current PDF, but they are not submission-quality. Reformat
them with wrapped columns, shorter labels, or a landscape/`tabularx` layout.

---

## Claims that survived adversarial cross-checking

The following results should **not** be retracted merely because nearby
wording or provenance needs repair:

1. **Encoder 0.62× arithmetic.** The current issue-time forecast uses
   2,410,754.7 worker-s versus the 3,869,278.8 static-C8 denominator:
   0.6231×. The 60-cell p90 factorial passes all tested windows/models/leads
   under both readiness modes.
2. **Hybrid raw arithmetic.** The aggregate hybrid has 589.301-ms p99 and
   2,944,979.7 worker-s: 0.7611× static. F6 genuinely improves from
   1264.206/1228.555 ms for the pure arms to 678.660 ms for the hybrid.
   Findings 3-4 concern generalization and provenance, not those operands.
3. **Language 0.82× arithmetic.** P90/s6 has 651.140-ms TTFT p99,
   7.254-ms ITL p99, and 440.041 GPU-h; 440.041/537.409 = 0.8188×. All seven
   current p90/s6 language fold rows pass. Finding 1 concerns its post-hoc
   selection status.
4. **Aggressive p70/s6 arithmetic.** It has 330.350 GPU-h and week aggregate
   TTFT p99 757.613 ms. It fails F6/e13 at 1133.656 ms, so the number is real
   but its SLA scope must be explicit.
5. **The 235B 87.7-ms observation.** The legacy raw artifact contains
   87.721685-ms ITL p99. Finding 13 concerns mixed vintage and missing mapping,
   not a false transcription.
6. **Request-linked composed latency.** The A12 extraction performs a
   per-request join and checks sub-millisecond arrival alignment. The joint
   p99 is not merely a sum of marginal p99s; that candidate complaint was
   rejected.
7. **Trace/span populations.** The 5.60-day span is 483,659.8 seconds
   (5.5979 days), with 749,601 requests and 11,408,002 images. The expanding
   context sensitivity has 999,599 requests over 6.998 days. These reproduce.
8. **Live-validation counts.** Each policy schedules 3,093 requests; forecast
   completes 3,092 with one error and reactive completes 3,089 with four
   errors, exactly as disclosed. The live test validates the real control
   plane over mocker workers, not H100 silicon, and the current text generally
   preserves that scope.
9. **Full-trace reactive ratio.** 3,323,189.5 / 4,838,397.6 = 0.686837×.
   Finding 20 is a database identity gap, not a numeric failure.
10. **AIC-vLLM bound through the serving cap.** Every integer N<=64 was
    measured and the 12.8% bound over that regime is supported. Finding 22
    concerns only the description of 65-512 as dense.
11. **Database core health.** The registered suite still has the same five
    failing check IDs, and no headline operand changed under the latest
    run-ID migration. C214's increase to 69 unresolved pointers is a real new
    provenance regression, not proof that the associated values are false.
    It must be repaired rather than hidden behind wrapper-level warnings.
12. **Build integrity.** The current source builds cleanly with no undefined
    references or citations. Remaining build defects are layout and
    submission-format issues.
13. **Recent corrections that should be preserved.** The current text
    correctly reports the 45-second model wins as a 2-2 Chronos/Toto split
    and the one-minute wins as Chronos two, Toto one, TimesFM one
    (`tex/predictors.tex:153-156`); scopes Fano to requests while Hurst spans
    signals (`tex/related.tex:183-186`); exempts ServeGen from the text-only
    characterization (`tex/related.tex:196-198`); narrows the ramp claim to
    the fastest bursts (`tex/related.tex:279-284`); and uses “tested
    operational scale” in the introduction (`tex/intro.tex:137-143`). These
    repairs should not be reverted while addressing nearby findings.

## Required remediation order

1. **Freeze the evidential claims.** Relabel p90/s6 and the hybrid as post-hoc
   sensitivity results unless new independent validation is run.
2. **Restore the SLA gate.** Remove the p50 “served adequately” conclusion and
   keep aggregate and per-episode verdicts inseparable.
3. **Complete the hybrid population.** Implement/replay F1 fallback and strict
   readiness; narrow “cost-minimal” to the actual F6 sweep.
4. **Repair the delivery gate.** Fix B3's malformed diff filter, add
   positive/negative regression fixtures, rerun it on the current diff, and
   remove “DELIVERY-READY” until the result is real.
5. **Close provenance before prose.** Version, fully ingest, manifest,
   extract, and verify the new 0.76/0.82 families; extend the arithmetic
   gates and repair the C214 pointer regression.
6. **Repair protocol statements.** Rerun or relabel the zero-startup reactive
   language baseline; define the changed calibration/evaluation split once
   and use it everywhere; distinguish largest tested lead from an identified
   threshold.
7. **Correct metric interpretations.** Replace the 588-ms physical-floor
   claim and state all-request versus image-bearing populations.
8. **Regenerate affected EDA/forecast text.** Fix the onset merge, ARIMA
   population, image classes, dispersion decay, Hurst sensitivity, and
   categorical forecasting/visibility claims.
9. **Reconcile every cross-chapter scope.** Update fold ratios, denominators,
   runtime vintages, summaries, appendix mappings, and evidence-volume
   language together.
10. **Run the complete gates on the final tree.** The formal claim corpus
    predates the new results, and the current containment result is invalid.
11. **Finish delivery.** Remove the draft note only after provenance closure,
    adopt the institutional format, and repair table overflow.

## Final adversarial ruling

The thesis has a defensible and unusually well-instrumented experimental
core, but the current uncommitted revision has moved faster than its own
validation protocol. The latest namespace migration improves five run IDs;
it does not make the result families complete, and the false-green delivery
gate makes the latest “DELIVERY-READY” attestation unusable. The strongest
new claims are **numerically plausible but not yet confirmatory**:

- 0.82× is a post-hoc e13-rescue operating point, not an independently
  selected held-out point;
- 0.76× is a real F6-recovering hybrid result, but not yet a fully replayed,
  provenance-backed, independently validated deployment policy; and
- several categorical explanations—p50 adequacy, equal cold-start plumbing,
  a matched-fast-onset mechanism, and a 588-ms physical floor—are contradicted
  by the current results or code.

After the seven high-severity items are corrected, the principal economic and
systems conclusions can remain, but they must be stated as:

> On this single trace and measured/simulated stack, pure forecast achieves an
> aggressive aggregate saving but misses e13; post-hoc robustness variants
> recover that onset at higher cost. Independent validation is still required
> before calling those variants deployment-robust.
