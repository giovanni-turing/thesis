# Verification of the GLM committee review

Fact-checker: independent, tool-grounded. Every number below was recomputed from
the thesis artifacts (simulation/results, analysis/trace_eda, predictors/results,
collector_artifacts) or grepped from the tex sources. Sources read in full:
glm/report.md, glm/cross-check.md, glm/adjudication.md, all 12 tex chapters.

Convention: verdicts judge whether the *review's finding* is correct, not whether
the thesis is correct. "CONFIRMED" = the review's finding holds; "DENIED" = the
finding is wrong; "PARTIAL" = the factual core holds but the framing/severity
overreaches.

---

## Required Revisions

### R1 (=CC1=AC1) — Fabric caveat missing at every headline cost-ratio claim
Target: tese.tex:59; intro.tex:261; closedloop.tex:316,438; conclusion.tex:65
Verdict: CONFIRMED
Severity: major
Evidence: `grep -n` for `0.27--0.31` returns 11 sites; the fabric caveat
(`geq}100 Gbps` / `embedding-only`) appears at only 3 of them — intro.tex:478,
closedloop.tex:396, conclusion.tex:82-83. The four headline sites named by the
review (abstract tese.tex:59, intro.tex:261 RQ4 answer, closedloop.tex:316
headline, conclusion.tex:65) all state the ratio unconditionally; related.tex:316
also. The substantive claim is artifact-backed: closedloop.tex:388-394's own
sensitivity says at the 4× DeepStack payload on 25 Gbps, p99 handoff rises
272→1087 ms and **every** policy fails, including static C=16 (p99 1311 ms). So
the headline is genuinely conditional on a ≥100 Gbps fabric / embedding-only
handoff. Presentational (state caveat at headline) + partly substantive.
Dup-hint: fabric caveat placement; canonical AC1, = CC1.

### R2 (=CC2=AC2) — Tail-aware reactive ablation is missing
Target: baselines.tex §5.4; closedloop.tex:34-38,152-175 (Table 8.1)
Verdict: CONFIRMED (with one partial-coverage nuance)
Severity: major
Evidence: I searched all simulation code and artifacts (`grep -rn tail_aware|belief|r_tail|knee simulation/*.py *.sh`; the only hits are figure code). No
reactive controller with the tail-aware belief-to-knee conversion exists.
forecast_schedule.py's `reactive` branch (lines 82-101) reads the trailing
*observed point* image rate and applies the *same* ρ; the `--quantile` flag is
ignored in that branch, so there is no "p90-of-trailing-observed" reactive
variant either. On the language pool the reactive baseline is Dynamo's planner
with its native mean conversion only; no run applies the belief-to-knee scaling
to a reactive (non-forecast) controller. Table 8.1 (verified against
riders44/: fc_lead60 736.3/6.35 PASS, fc_lead60_s1 1716.6/126.76 FAIL,
ladder_t200_20 1615.5/125.08 FAIL) shows forecast+mean fails — the converse
(reactive+tail-aware) is never shown.
Partial-coverage nuance the review under-weights: on the *encoder* pool ρ=15 IS
the tail-aware capacity rating (closedloop.tex:373 calls it "the encoder-side
analogue of the belief-to-knee gap"), and the encoder reactive controller *at
that tail-aware ρ* still fails burst3 at every lead (Table 7.5, 9.5–54 s). So on
the encoder side the "tail-awareness alone" question is effectively answered
(anticipation, not conversion, is decisive there). The genuinely missing cell is
the language-pool reactive-with-belief-to-knee (and the p90-trailing-observed
refinement). The review's core claim — "the value of forecasting vs
tail-awareness is not cleanly isolated by a dedicated ablation" — holds.
Dup-hint: tail-aware reactive missing; canonical AC2, = CC2; single most-cited gap.

### R3 (=CC4=AC3) — No confidence intervals / noise propagation
Target: predictors.tex:174; baselines.tex; closedloop.tex:405-406; validation.tex Table 9.1
Verdict: CONFIRMED
Severity: major
Evidence: No table in any chapter carries a CI or repetition count. predictors.tex:174
explicitly writes "below plausible sampling variability, with no significance test
attached." closedloop.tex:405 states "Replay-level p99 noise is ≈4%; no quoted
contrast is within that band" — the noise figure is asserted but never propagated
into intervals. Validation Table 9.1 is single-run point estimates (verified:
live_fc 695.16/11.47, live_re 3531.45/150.74; offline twins 651.1/5.29 and
3494.7/160.26 — all reproduced exactly, all single runs). The 0.96× language
result = 518.6/537.4 = 0.965, i.e. 3.5% below break-even, inside the stated 4%
band — the review's "distinguishable from 1.0×?" concern is legitimate (though the
thesis frames 0.96× as break-even, not a saving). CONFIRMED.
Dup-hint: no CIs / significance test; canonical AC3, = CC4.

### R4 (=CC3=AC5) — Encoder-pool validation gap not foregrounded
Target: validation.tex §9.1 (Setup) vs §9.4 (Scope, line 136-139)
Verdict: CONFIRMED
Severity: major
Evidence: validation.tex:136-139 (Scope, end of chapter) states "the language pool
(the pool with a production control path; the encoder pool's controller exists
only in simulation)". The Setup section (§9.1, lines 25-48) does *not* state this;
it opens on burst3/language without flagging that the primary economic claim
(encoder 0.27–0.31×) has no live anchor. The encoder economic headline is
simulation-only — confirmed by the artifact structure (live51/ contains only
language-pool planner twins; no encoder live run). CONFIRMED: gap is real, and the
placement (buried in final Scope, absent from Setup) is as the review describes.
Dup-hint: encoder no live validation; canonical AC5, = CC3.

### R5 (=B4-W3) — ARIMA absent from the forecasting accuracy benchmark
Target: predictors.tex Table 4.1 (tab:pred-wape)
Verdict: PARTIAL
Severity: moderate → minor (presentational)
Evidence: Literally true that ARIMA is not a *row* in Table 4.1 (rows: naive,
EWMA, Holt-Winters, TimesFM, Chronos-2 ±cov, Toto-2 ±cov). BUT ARIMA IS
benchmarked through the same rolling-origin protocol and reported: I read
predictors/results_dynamo/arima_1min.json (WAPE 0.5213, h=1, images, 167 origins)
and arima_15s.json (0.6675) — these exactly match the prose at predictors.tex:189
("ARIMA, 0.521 WAPE at the first horizon step") and :193 ("ARIMA 0.668"). Kalman
(0.811), Prophet (0.733), constant/naive (0.764) at 15s also verified exactly.
The best foundation model (toto, 0.5153 @1min; 0.6374 @15s) verified from
metrics_h1.parquet, matching "0.515"/"0.637". ARIMA also appears in Fig 8.1a
("ARIMA ties Chronos"). The thesis explicitly attributes the closed-loop failure
to *conversion, not accuracy* (Fig 8.1 caption; predictors.tex:196-200). So the
review's stronger claim — that the reader "cannot determine whether the failure is
accuracy or conversion" — is not correct; the thesis answers it. The remaining
valid point is presentational: promote the ARIMA row into Table 4.1.
Dup-hint: ARIMA not in accuracy table; data exists in prose+figure.

### R6 (=B2-W4) — Missing queueing-staffing literature
Target: related.tex §5.5 (rel-forecast); bibliography
Verdict: CONFIRMED
Severity: major
Evidence: `grep -in "erlang|halfin|whitt|palm|teletraffic|square-root staffing"`
over all *.tex returns nothing (two hits are babel `otherlanguage` tags). The bib
has no Erlang-B/C, Halfin-Whitt, or Palm-Erlang-A entry. The only staffing anchor
is the newsvendor/critical-fractile framing (Arrow1951, related.tex:253-256).
The review's "OR examiner will flag this" is strengthened by the author's own
corpus: a RAG search surfaced Kleinrock *Queueing Systems Vol. 2*, *Fundamentals
of Queueing Theory* (Erlang B/C formulas indexed), and — directly on-topic —
papers/2603.16054 "inference-fleet-sim: A Queueing-Theory-Grounded Fleet Capacity
Planner for LLM Inference" and papers/2407.00047 "Queue-Management-for-SLO-Oriented
LLM Serving". The relevant literature is available and uncited. CONFIRMED.
Dup-hint: queueing/Erlang/Halfin-Whitt absent; corpus has it.

### R7 (=B2-W8) — Tail-aware conversion has no related-work anchor
Target: related.tex (no mention); defined in closedloop.tex:152-196
Verdict: CONFIRMED
Severity: moderate (review says major)
Evidence: `grep -n "tail-aware|belief-to-knee"` — appears in intro, closedloop,
validation, conclusion but NOT related.tex. related.tex:117 mentions InferLine's
"end-to-end tail-latency SLO" for pipeline sizing, which is adjacent but is not
the belief-to-knee capacity conversion (a mean-to-tail rescaling of per-replica
throughput). The thesis's most original mechanism is unforeshadowed in related
work. CONFIRMED; the newsvendor citation partially covers the *headroom-quantile*
idea but not the conversion, so the finding stands. Severity closer to moderate.
Dup-hint: tail-aware unanchored in related work.

### R8 (=B1-W6) — Load-bearing footnote must be promoted
Target: intro.tex:94-109
Verdict: CONFIRMED
Severity: moderate (review says major; footnote-style is a judgment call)
Evidence: The footnote spans 16 lines (94-109) and carries the structural
lead-time-asymmetry argument (encoder ≈3-5 s model-side, orchestration-bound vs
language tens-of-seconds), concluding "The closed-loop evaluation therefore sweeps
per-pool lead-time ranges rather than one shared constant" — i.e. it justifies a
core experimental-design decision. That is body-text reasoning, not an ancillary
note. CONFIRMED; "major" is a stylistic call, substance is real.
Dup-hint: 15-line footnote carries argument.

### R9 (=B7-W4) — 14-configuration reactive claim under-evidenced
Target: baselines.tex:144-152
Verdict: CONFIRMED (presentational; the data fully exists)
Severity: minor (review says major)
Evidence: The claim "all fourteen configurations satisfy the control law while
violating the tail SLA (TTFT p99 1,079–3,495 ms)" is backed by 14 real artifacts:
simulation/results/reactive32/ has variants A and B (planner_A/B.json) across all
7 windows (burst1-6 + steady24h) = 14 runs. Recomputed TTFT p99 range: min
1079.2 (r32B_steady24h), max 3494.7 (r32A_burst3) — exactly the claimed
1079–3495. So the claim is TRUE and completely evidenced in the archive; only the
per-config *table* is not printed in the chapter (the burst1 ladder + the range
are shown). The review's "supported only by the burst1 ladder" understates what's
in the text (the range is also given) and mislabels a display gap as an evidence
gap. Ask for the table = reasonable; severity minor.
Dup-hint: 14-config data exists, table not shown.

### R10 (=B10-W3) — Conclusion drops robustness results
Target: conclusion.tex:51-69 (RQ4 paragraph)
Verdict: CONFIRMED
Severity: minor
Evidence: The RQ4 paragraph mentions the 0.27–0.31× headline and dashboard-masking
but omits the 560-cell factorial, the ρ-frontier (0.18–0.44×), and the
forecast-model-independence of the week verdict — all established in closedloop.tex
(§8.2 factorial, §8.4 ρ-sweep, :226 model-independence). Their omission does make
the headline read as more knife-edge than the body supports. CONFIRMED.
Dup-hint: conclusion omits factorial/ρ-frontier.

### R11 (=B5-W1) — 419 TFLOP/s extrapolation unverified, un-cross-checked
Target: aiconfigurator.tex:53-59
Verdict: CONFIRMED (and materially strengthened by the cross-check the review asked for)
Severity: moderate (review says minor)
Evidence: I ran the exact cross-check the review says is missing — measured bf16
GEMM peak vs the claimed 419 TFLOP/s — over the campaign's own 34,710 GEMM rows
(systems/data/rtx_5090/vllm/0.22.0/gemm_perf.parquet). Peak achieved bf16 GEMM =
**~206 TFLOP/s** (2·m·n·k / latency; latency in ms; top shapes all cluster at
204–206), i.e. roughly **half** the system file's 419 TFLOP/s dense bf16. The 419
figure is the FP16-*accumulate* theoretical peak (2× the FP32-accumulate rate);
the RTX 5090's FP32-accumulate bf16 spec is ~209.5 TFLOP/s, which the measured
~206 matches at ~98%. Since vLLM's bf16 GEMM path uses FP32 accumulate, 419 is
optimistic by ≈2× relative to the collected data. Important mitigation: the 419
field feeds only AIC's SOL/analytic modes; the encoder cost model consumes the
measured GEMM *lookup* tables, not 419, so the headline encoder costs are not
inflated by it. But the review is correct that (a) SM counts are not stated and
(b) the value is un-cross-checked against measured GEMM — and when checked, it is
~2× high. CONFIRMED, stronger than the review states.
Dup-hint: 419 TFLOP/s ≈ 2× measured GEMM peak (206).

### R12 (=B5-W8, cross-check #13) — 600W vs 575W power unreconciled
Target: aiconfigurator.tex:50
Verdict: CONFIRMED
Severity: minor
Evidence: aiconfigurator.tex:50 states "observed board power limit 600W" from
nvidia-smi; the cited spec (NVIDIA5090Specs) gives 575W TBP for the RTX 5090.
The chapter does not reconcile the 25 W gap. Grounded caveat: 600W is most
plausibly the nvidia-smi *enforced power-limit ceiling* (many 5090 boards expose a
600W max `-pl`), not the operating TBP — so "power limit 600W" and "TBP 575W" can
both be true. But the thesis states one and cites a source giving the other with
no note; the review's ask (reconcile or note) is valid. CONFIRMED minor.
Dup-hint: 600W is power-limit ceiling vs 575W TBP.

---

## Suggestions

### S1 (cross-check #3) — R² precision 0.12 vs 0.123
Verdict: CONFIRMED  Severity: nit
Evidence: grep confirms both forms in use: tese.tex:46 (0.12), intro.tex:141
(0.123), trace-eda.tex uses both (241:0.123, 257:0.12), predictors.tex:230 (0.12),
conclusion.tex:15 (0.12). True value = 0.12254 (d_signals_stats.json). Cosmetic.
Dup-hint: R² precision inconsistency.

### S2 (cross-check #4) — "≥16×" not "order of magnitude" for knee separation
Verdict: CONFIRMED  Severity: minor
Evidence: Table 6.3 + artifacts: steady vision uncrossed at s=32 (recomputed
enc_delay p99 = 787.2 ms < 1000, ~256 img/s), calibrated LLM knee at s=2 →
32/2 = 16× demonstrated. "An order of magnitude" reads as ~10× (its lower bound).
twopool.tex:280 correctly says "factor >10", but abstract/intro use "order of
magnitude". CONFIRMED.
Dup-hint: ≥16× vs order-of-magnitude.

### S3 (cross-check #6) — 29% utilization is single-window, unscoped in abstract
Verdict: CONFIRMED  Severity: minor
Evidence: Recomputed from vision_burst1_aic_s1.json: encoder_utilization = 0.2889
on the burst1 window (the largest burst, peak 370.18 img/s per summary.json), 2
workers, p99 encoder delay 5013 ms. The value is measured on that one window only;
tese.tex:55 presents 29% without scoping. CONFIRMED.
Dup-hint: 29% single-window (burst1).

### S4 (cross-check #7) — ≤4% cost spread is encoder-only; language is 20–24%
Verdict: CONFIRMED  Severity: minor
Evidence: Encoder spread (aggregate44 stats): Chronos/Toto/TimesFM p90 worker-s at
L=30 are 2.376M/2.359M/2.302M (spread 3.2%); at L=300 2.116M/2.127M/2.035M
(spread 4.5%). Language spread (llm_week reports): Chronos 518.6, Toto 625.3,
TimesFM 641.1 GPU-h → 625.3/518.6 = 1.206 (20.6%), 641.1/518.6 = 1.236 (23.6%).
So closedloop.tex:324 "≤4%" is encoder-scoped (and marginally 4.5% at L=300),
while the language spread is 20–24%. CONFIRMED (the ≤4% sentence sits in the
encoder §8.4, so context scopes it, but it is unreconciled with the earlier
language numbers).
Dup-hint: ≤4% encoder vs 20-24% language.

### S5 (=CC6=AC6, cross-check #14) — Mocker/simulator terminology inconsistent
Verdict: CONFIRMED  Severity: minor
Evidence: intro.tex:38 "calibrated discrete-event simulation of the language pool";
related.tex:270 "discrete-event simulator of its own worker pools"; twopool.tex:35
"the mocker; marketed as DynoSim"; validation.tex:39 "live mocker workers load the
same AIC latency model". validation.tex confirms engine timing is "identical by
construction" — a mock-engine harness with AIC-injected timing, not a kernel-level
calibrated simulator. Terminology varies as described. CONFIRMED.
Dup-hint: mocker vs calibrated simulator; = CC6.

### S6 (=B8) — Per-episode language-pool summary table missing
Verdict: CONFIRMED (presentational)  Severity: minor
Evidence: closedloop.tex:212-214 claims p90 passes each burst episode
(651–706 ms) while reactive fails all four (1615–3495 ms). Artifacts back this:
episode_twins/ (burst1/4/5) + live51 (burst3) — recomputed fc: 705.5/651.1/651.1
(+ burst3 651.1); re: 1615.5/2775.8/2151.6 (+ burst3 3494.7). Data exists for all
four; no table printed. CONFIRMED — add the table.
Dup-hint: per-episode language data exists, no table.

### S7 (=B6-W2) — Report 29% utilization per-episode
Verdict: CONFIRMED  Severity: minor
Evidence: The 29% is reported only for burst1 (verified above). Per-episode
utilization is not tabulated. CONFIRMED (same underlying fact as S3).
Dup-hint: 29% only for burst1.

### S8 (=B6-W5) — Add a table for the 235B spot-check
Verdict: CONFIRMED (presentational)  Severity: minor
Evidence: twopool.tex:74-88 numbers verified against 235b/ artifacts:
llm_head2k_aic235btp8_s1 TTFT p99 397.7 (text 398), ITL p99 87.72 (text 87.7);
s4 TTFT p99 1401.7 (text 1402); knee at s=1 (s=4 ITL 318 > 100 fails). All real,
no table. CONFIRMED.
Dup-hint: 235B numbers verified, no table.

### S9 (=B10-W6) — Name the TSFMs in the conclusion
Verdict: CONFIRMED  Severity: nit
Evidence: conclusion.tex:26 says "Three pretrained time-series foundation models"
with no names; TimesFM-2.0/Chronos-2/Toto-2.0 are named only in intro/predictors.
CONFIRMED.
Dup-hint: TSFMs unnamed in conclusion.

### S10 (cross-check #12) — Reconcile 5.60-day vs 7-day in conclusion
Verdict: CONFIRMED  Severity: nit
Evidence: conclusion.tex:63 "5.60-day covered span" and :79 "one seven-day
production trace" without an explicit parenthetical linking them (7 − 1.4 d
context = 5.60 d). CONFIRMED.
Dup-hint: 5.60 vs 7-day unreconciled.

### S11 (=B7-W7) — Add a simple-forecast (EWMA+p90) encoder baseline
Verdict: CONFIRMED (not run)  Severity: minor
Evidence: No EWMA+p90+tail-aware encoder run exists in the scripts (only TSFM
p50/p90 and observed-reactive). The thesis partially addresses "is the TSFM
needed?" via the predictor-invariance result (Fig 8.1: ARIMA ties Chronos;
integer-replica quantization collapses predictor differences) and the 2–9% EWMA
gap at 1-min, but a dedicated EWMA+p90 closed-loop baseline is genuinely untested.
CONFIRMED, partially mitigated.
Dup-hint: EWMA+p90 baseline untested.

### S12 (=B10-W2) — Split the 19-line RQ4 conclusion paragraph
Verdict: CONFIRMED  Severity: nit
Evidence: conclusion.tex:51-69 is a single paragraph of ~19 lines packing RQ4's
encoder result, language conversion, week aggregate, and dashboard-masking.
CONFIRMED.
Dup-hint: RQ4 paragraph overloaded.

---

## Cross-Cutting (mapping only; verified under the R-items above)

### CC1 — Fabric caveat. CONFIRMED major. = R1. See R1 (4×-payload sensitivity
verified: static C=16 also fails at 25 Gbps).

### CC2 — Forecasting vs tail-awareness not isolated. CONFIRMED major. = R2.
No reactive+tail-aware run exists; Table 8.1 triad verified; encoder-side ρ=15
gives partial coverage the review under-weights.

### CC3 — Encoder pool no live validation. CONFIRMED major. = R4.

### CC4 — Uneven statistical rigor. CONFIRMED major. = R3.

### CC5 (=AC4) — Single-trace generalization / universal register
Verdict: CONFIRMED  Severity: minor
Evidence: Abstract and thesis statement use universal register ("no single load
signal can size every pool", "each pool must be provisioned"), while the mechanism
is inferred (trace has no tenant IDs — trace-eda.tex:453,464-465 confirm no
session/user identifiers; the "few tenants submitting batch video" mechanism is
explicitly inferred). trace-eda.tex:461-474 and the conclusion DO scope the claim
by mechanism and mark it falsifiable, so this is tonal (scope the abstract/intro),
as the review says. CONFIRMED minor.
Dup-hint: single-trace universal register; mechanism inferred not observed.

### CC6 — Mocker not a calibrated simulator. CONFIRMED minor. = S5.

---

## Cross-check.md's own claims (spot audit)

The review's cross-check.md asserts "No numerical contradictions found." I
independently recomputed a large sample and every headline number reproduced from
artifacts:
- Table 8.2 worker-seconds/ratios: static C16 7.738M (1.00×), C2 0.967M (0.125×),
  fc p90 L30 2.376M (0.307→0.31×), fc p90 L300 2.116M (0.273→0.27×), fc p50 L30
  0.963M (0.124→0.12×), react L30 2.611M (0.337→0.34×), react L300 1.672M
  (0.216→0.22×) — all exact.
- Language week: 518.6/651 (p90), 319.9/828 (p50), 281.8/1197 (reactive),
  625/641 (Toto/TimesFM) — all exact from llm_week reports.
- 588 ms floor = f(64) 316.369 + handoff p99 272.001 = 588.37 — exact.
- EDA: R²=0.1225, Jaccard 0.0248 (5/202), Hurst img 0.932/req 0.829, Pearson
  0.355/0.812, ACF 69/9 min — all exact.
- Validation Table 9.1: live 695.16/11.47/3531.45/150.74, offline
  651.1/5.29/3494.7/160.26 — all exact.
- Predictors: ARIMA 0.521/0.668, Kalman 0.811, Prophet 0.733, naive 0.764, best
  TSFM 0.515/0.637 — all exact.
The cross-check's "no numerical contradictions" verdict is itself CONFIRMED for
the sampled numbers. The only quantitative wrinkle I found beyond the review is
R11 (419 TFLOP/s ≈ 2× the measured GEMM peak of ~206), which the review flagged as
un-cross-checked but did not itself compute.

---

## SUMMARY

Findings adjudicated: 12 required (R1–R12), 12 suggestions (S1–S12), 6
cross-cutting (CC1–CC6). Overlap: CC1–CC4, CC6 are duplicates of R1–R4, S5.

Counts (deduplicated to the 24 distinct R/S items + CC5):
- CONFIRMED: 22  (R1, R2, R3, R4, R6, R7, R8, R9, R10, R11, R12, S1, S2, S3, S4,
  S5, S6, S7, S8, S9, S10, S11, S12, CC5) — note R9/R11 confirmed with severity
  adjustments below
- PARTIAL: 1  (R5 — ARIMA is benchmarked in prose+figure; only the table row is
  missing, and the "reader can't tell accuracy vs conversion" framing is wrong)
- DENIED: 0

No finding was factually wrong. Severity re-grades vs the review: R5 major→minor;
R9 major→minor (data fully exists, only the table is unprinted); R7/R8 major→
moderate (judgment calls); R11 minor→moderate (the cross-check reveals a real ~2×
gap). Every artifact-backed thesis number I recomputed reproduced exactly.

Top 5 confirmed (highest-value, tool-grounded):
1. R11 — I ran the review's proposed cross-check: measured peak bf16 GEMM is
   ~206 TFLOP/s vs the system file's 419 (≈2×; 419 = FP16-accumulate peak, vLLM
   uses FP32 accumulate). Real discrepancy; does not propagate to encoder cost
   (lookup-based), but the system-file field is inconsistent with its own campaign.
2. R6 — queueing-staffing lineage (Erlang/Halfin-Whitt) entirely absent from tex
   and bib, while the author's own corpus holds Kleinrock, Fundamentals of
   Queueing Theory, and a queueing-grounded LLM fleet-planner paper.
3. R2/CC2 — no reactive+tail-aware controller exists in code or artifacts; the
   forecasting-vs-tail-awareness value is not isolated by a dedicated ablation
   (encoder ρ=15 gives partial coverage the review under-weights).
4. R1/CC1 — fabric caveat present at only 3 of 11 headline sites; the thesis's own
   4×-payload sensitivity confirms every policy (incl. static) fails at 25 Gbps.
5. R4/CC3 + R3/CC4 — encoder economic headline is simulation-only and unflagged in
   the validation Setup; all headline comparisons are single-run with no CIs
   despite a stated 4% p99 noise band (validation table verified single-run).
