# Verification of the Gemini committee review

Verifier: tool-equipped fact-check pass over `/home/gio/tese/tex/*.tex`, code
(`predictors/`, `analysis/trace_eda/`, `simulation/`), artifacts, and the raw
Azure trace. Sources checked are named per finding. Gemini's internal
chapter/table numbering is scrambled; findings below are mapped to the actual
files by content.

Reviewed inputs: `gemini/report.md`, `gemini/cross-check.md`,
`gemini/adjudication.md`, and the ten `gemini/review-*.md` committee reports
(the detailed line-referenced findings the adjudication aggregates).
(Per instructions, no `*-assessment.md` file was read.)

---

## A. Signature findings (tool-verified)

### HW-seasonality — Holt-Winters seasonal period starves it of seasonality
Target: predictors.tex:76-79 (review-predictors.md `predictors.tex:76` [Major]; adjudication "Hobbled Classical Baselines")
Verdict: PARTIAL
Severity: moderate (Gemini said major)
Evidence:
- Code `predictors/benchmark.py:96-99`:
  `# Holt-Winters seasonal period per resolution: one hour of bins, except at 1s
   # where two full hours (7200) would not fit the 1928-step context — 15 min is
   # the largest round period with the required two full cycles of history.
   HW_SEASON = {"1s": 900, "15s": 240, "30s": 120, "45s": 80, "1min": 60}`
- `predictors/holt_winters.py:68-121`: `HoltWintersPredictor` *requires* `2*seasonal_periods`
  points and raises `ValueError` otherwise (no silent degrade). So at 1 s the period is
  900 bins (15 min), and two full cycles (1800) fit the C=1928 context by construction;
  at 15 s/30 s/45 s/1 min the period is exactly one hour of bins (240/120/80/60), two
  cycles = 480/240/160/120, all << 1928.
- Gemini's premise — "seasonal period of one hour, constrained to a context window that
  fits less than one hour (1928 steps = ~32 min at 1s)" — is factually wrong for the 1 s
  case: the period there is 15 min, chosen *precisely* so two cycles fit. HW is not
  "starved of its configured seasonality"; it always gets 2 full cycles.
- The *real* (and valid) limitation is different and already stated by the thesis:
  the classical baselines are context-capped to TimesFM's budget, so HW's seasonal
  period is sub-diurnal (hourly), never diurnal. predictors.tex:384-390 says so verbatim:
  "the classical baselines are fixed-parameter ... context-capped at TimesFM's budget ...
  Holt-Winters in particular never sees two full diurnal cycles here; a full-history
  seasonal baseline ... would narrow the margins of Table 4.1, which should be read
  accordingly." predictors.tex:387-388 is exactly the caveat Gemini demands.
If DENIED/PARTIAL: The specific technical charge (1-hr period on a <1-hr window, "mathematically
invalidates" HW) is DENIED — the code adapts the period and hard-guards two full cycles.
The underlying methodological concern (context-capped classical baseline, no diurnal
seasonality) is valid but already caveated in the thesis limitations. The "add ARIMA/Prophet
to Table 4.1" sub-point is a reasonable presentation ask, but ARIMA/Kalman/Prophet ARE run
through the identical protocol and discussed inline (predictors.tex:181-200) and run
unmodified in the closed loop (predictors.tex:390-394), so they are not "excluded", only
kept out of the headline table.
Dup-hint: HW context-cap; likely overlaps codex/opus predictors finding

### FF-contradiction — "forecast-free policy" vs ARIMA-driven reactive baseline
Target: baselines.tex:40-42 vs baselines.tex:141 (review-baselines.md `:42`,`:141` [Major]; adjudication ACCEPTED)
Verdict: CONFIRMED
Severity: moderate (real internal contradiction of terms; does not affect any result)
Evidence:
- baselines.tex:39-42: "...they are graded here by every \emph{forecast-free policy} (the
  static grid, the language-pool reactive baseline, and the reactive encoder baseline,
  which needs no forecast), but not by any forecast policy."
- baselines.tex:140-141: the reactive baseline's variant B is "SLA-target variant (B,
  ARIMA-driven throughput loop plus load loop)."
- predictors.tex:181-184: "Dynamo's SLA planner selects a load predictor from a fixed
  registry (ARIMA, Kalman, Prophet, or constant) and \emph{forecasts} the request, input-,
  and output-length signals with it." ARIMA is unambiguously a forecasting model, so a
  policy "driven" by it is not literally "forecast-free."
If DENIED/PARTIAL: n/a — the literal contradiction is real. Grounded defense for the author:
the thesis's operational taxonomy uses "forecast policy" = *the thesis's* archived
rolling-origin TSFM forecast that consumes the reserved 1.4-day forecast context;
"forecast-free" = any policy that needs no such reserve and can therefore be graded on
burst2/6 (which lie inside the reserve). Dynamo's internal ARIMA runs online from the live
replay's trailing window and needs no reserve, so it is "forecast-free" in that narrow
sense. The wording is defensible in meaning but self-contradictory as written; a one-line
rephrase (e.g. "reserve-free" or "policies that consume no archived forecast") resolves it.
Dup-hint: ARIMA "forecast-free" wording; likely shared with codex/opus baselines

### stall-245 — 245-second control-plane stall, no root cause, reproducibility
Target: validation.tex:121-125 (review-validation.md `:121-125` [Major]; adjudication ACCEPTED)
Verdict: PARTIAL
Severity: moderate (Gemini said major/"critical failure")
Evidence:
- validation.tex:121-125: "The live planner's 60-second ticks held cadence except one
  245-second stall, after which the forecast feed realigned to wall time ... Decision
  \emph{count} is therefore not exactly reproducible live; decision \emph{values} at
  matching times are." No root-cause hypothesis is given → Gemini's factual claim
  (no root cause) is CONFIRMED.
- It is ledgered: `progress/results-ledger.md:239` "(3) live tick cadence can stall (one
  245 s gap; forecast feed realigns to wall time)."
- Reproducibility from the archive: NO. I parsed all three archived planner logs
  (`simulation/results/live51/live_runs/{live_fc,live_re,verify_flag}/planner.log.gz`):
  max inter-event gap is 10 s (live_fc), 15 s (live_re), 10 s (verify_flag) — no 245 s
  gap anywhere. The 5 s decision-summary cadence in live_fc is uniform (max gap 5.0 s).
- The archived `live_fc` IS the run behind Table 5.1: its aiperf report
  (`live_fc/profile_export_aiperf.json`) gives `time_to_first_token.p99 = 695.16 ms`,
  exactly Table 5.1's "Live 695". So the very run reported in the thesis does not exhibit
  the stall — fully consistent with the thesis's own "not exactly reproducible" statement.
If DENIED/PARTIAL: CONFIRMED that no root-cause hypothesis is supplied (a fair, actionable
ask — add e.g. Prometheus scrape timeout / GC pause / thread starvation). But Gemini's
framing as a "functional outage / critical failure" is overstated: the thesis bounds the
impact (decision values at matching times agree; only the count differs), the anchor
verdict is unaffected, and the stall is a disclosed, non-deterministic harness event that
is not even present in the archived anchor run. Root-cause hypothesis = reasonable
addition; "critical failure" = not supported by the evidence.
Dup-hint: 245s stall root cause; likely overlaps codex/opus validation

### extrap-149k — extrapolation to ~149k tokens on a 16k grid
Target: aiconfigurator.tex:476-480 (+ twopool.tex:374-378) (review-aiconfigurator.md `:477-480` [Major]; review Q2)
Verdict: DENIED (leaning PARTIAL)
Severity: minor
Evidence:
- Raw-trace recompute (`/mnt/.../dataset/AzureLMMInferenceTrace_multimodal.parquet`,
  1,000,000 rows, `eda/.venv/bin/python` + pandas): `frac(ContextTokens > 16384) = 3.140%`
  (31,404 rows); `max(ContextTokens) = 148569`. The thesis's "≈3.1% ... up to ≈149k tokens"
  is exact. (Matches `analysis/trace_eda/b_marginals_stats.json`: ContextTokens max 148569,
  p99 35932, p95 9755 — so the >16384 mass sits between p95 and p99, ≈3%.)
- The disclaimer Gemini demands already exists twice: aiconfigurator.tex:476-480 and
  twopool.tex:374-378 both flag these as stratum-three extrapolation-priced, and both
  name them as "the frames-class prefills that decide burst-window TTFT tails."
- The analytical bound Gemini demands also already exists: aiconfigurator.tex:182-186
  (stratum-three definition) — "probed on the H100 tables out to 147k-token contexts,
  this tracks the theoretical quadratic of attention within a few percent per octave."
  That is precisely "a basic analytical proof that the extrapolation matches known
  FlashAttention complexity at that scale," validated to 147k (≥ the 149k data max).
If DENIED/PARTIAL: The numbers are exact, and both the disclaimer and the analytical
grounding Gemini asks for are already in the text (validated to the actual data range).
The only residual, defensible ask is an explicit no-OOM note at the extreme context; the
"highly dangerous, unbounded" framing is not warranted. Rated DENIED on substance, PARTIAL
only in that one small addition (OOM bound) could be made.
Dup-hint: 149k extrapolation bound; likely shared with codex/opus aiconfigurator

---

## B. Cross-cutting adjudications

### xc-hw-mismatch — RTX 5090 (vision) vs H100 (language) tier mismatch
Target: intro.tex, twopool.tex:50, twopool.tex:12 (report.md CC#1; adjudication I.1; ACCEPTED)
Verdict: PARTIAL
Severity: minor (editorial; not a factual error)
Evidence: The pairing is a deliberate, justified design choice, not an oversight.
intro.tex:289-295: "the 576M-parameter tower fits comfortably in consumer memory, making
consumer-class parts a plausible, cost-effective class for an independently scaled encoder
pool." twopool.tex:50 and :12 state the composition explicitly; the encoder cost model
carries a documented conservative-direction gap. The inter-pool handoff is a parameterized
link and the ≥100 Gbps fabric requirement is analyzed (see xc-network). What is thin is the
specific "would consumer and datacenter GPUs share one high-speed fabric in production"
question — a reasonable sentence to add, but the mismatch itself is motivated.
If DENIED/PARTIAL: not an error; a justification exists and could be expanded on the fabric-sharing angle.
Dup-hint: 5090-vs-H100 justification; cross-cutting, multi-reviewer

### xc-network — 25 Gbps handoff default "unusually low"
Target: twopool.tex:157 (report.md CC#2; adjudication I.2; ACCEPTED)
Verdict: PARTIAL (leaning DENIED)
Severity: minor
Evidence: twopool.tex:157 sets a default 25 Gbps parameterized link. But (a) the
single-stream embedding handoff at 25 Gbps is second-order: 0.71 ms median, 62 ms at the
121-image max (twopool.tex:158-160); (b) a *lower* bandwidth is the *conservative* choice
(transfer is charged to request latency); (c) the thesis explicitly analyzes exactly the
shift Gemini asks about — closedloop.tex:385-398 and intro.tex:475-481 show that at the 4×
DeepStack payload the 25 Gbps link violates the SLA for *every* policy (incl. static C=16
at 1,311 ms) and that a ≥100 Gbps fabric restores the numbers ("a fabric requirement, not a
policy weakness"). The handoff is also flagged as bandwidth-only (no contention), an
explicit lower bound (twopool.tex:170-176).
If DENIED/PARTIAL: The "justify 25 / discuss 100+ Gbps" ask is substantially already done;
25 Gbps is a conservative default and the 100 Gbps shift is a headline limitation, not a gap.
Dup-hint: 25Gbps fabric; cross-cutting, multi-reviewer

### xc-generalizability — single trace / 50/50 split overfitting
Target: report.md CC#3; adjudication I.3 (ACCEPTED)
Verdict: PARTIAL
Severity: minor (largely already handled)
Evidence: The thesis repeatedly scopes this and makes it falsifiable through mechanism,
not sampling: trace-eda.tex:461-474 ("Everything in this chapter describes this trace ...
the generality argument runs through mechanism ... The claim is falsifiable: a multimodal
trace in which image volume tracks request rate ... would collapse the decoupling");
intro.tex:467-468; predictors.tex:402-404; closedloop.tex:419-422. What is not present is a
quantitative sensitivity of R²=0.12 to alternate modality splits (Gemini's specific ask),
which is a legitimate addition. The concern is acknowledged thoroughly; the quantitative
projection is not supplied.
Dup-hint: single-trace 50/50; cross-cutting

### xc-tone — dense/"lab-notebook" prose
Target: report.md CC#4; adjudication I.4 (ACCEPTED)
Verdict: CONFIRMED (subjective/editorial)
Severity: nit
Evidence: The flagged phrasings exist as quoted: "priced by the static grid"
(conclusion.tex:21), "buys nothing" (conclusion.tex:107, predictors.tex:254),
"honest complement" (conclusion.tex:101), "echo" (conclusion.tex:31),
"dashboard-masking" (conclusion.tex:69); iterative "later audit / Targeted shape infill"
(aiconfigurator.tex:118-135). These are style preferences, not errors; the adjudication
itself REJECTED several ("echo", "honest complement" deemed standard parlance).
Dup-hint: prose density; editorial, low value

---

## C. Other substantive weaknesses (per-chapter)

### batching-exact — "exact batching law" is a simulator/model property
Target: twopool.tex:117, intro.tex:428 (review-twopool.md `:117` [Major]; adjudication MODIFIED)
Verdict: DENIED (already clarified in text)
Severity: minor
Evidence: The thesis already draws exactly the distinction Gemini/adjudication ask for.
twopool.tex:116-121 attributes the exactness to *AIC's encoder graph* ("Probed directly,
AIC's encoder graph prices a forward exactly by its total images ... because attention is
evaluated at the product batch×images"); twopool.tex:126-128 and aiconfigurator.tex:309-318
give the *measured silicon* contrast ("the batching \emph{benefit} is real but saturates
earlier and smaller than the model claims", bottoming at N≈6-8). intro.tex:428-429 says
"probe-verified exact batching law (encoder cost depends only on total images per forward)"
— a property of the cost model, verified by probing it, with the measured divergence
documented. The adjudication's own "MODIFIED — AIC operates deterministically, model
legitimately returns exact latencies" concedes the point.
Dup-hint: exact-law simulator property; already in text

### notation-N — f(N) vs "N × TP" clash in Figure 1
Target: intro.tex:312 (Fig, review-intro.md `:312` [major])
Verdict: CONFIRMED
Severity: minor
Evidence: In the tikz figure (intro.tex:326-336) the Vision box reads "AIC-costed $f(N)$"
(N = images per forward) while the Language box reads "$N \times$ TP H100 workers"
(N = replica count). Same symbol, two meanings, same figure. Real minor clash worth a
relabel (e.g. f(n) images vs. N replicas).
Dup-hint: N symbol reuse in Fig 1

### hill-fragility — Hill estimator on top-1% without goodness-of-fit
Target: trace-eda.tex:64 (review-trace-eda.md `:64` [MAJOR]; adjudication ACCEPTED)
Verdict: PARTIAL
Severity: minor
Evidence: The thesis already self-limits the exact way Gemini's fallback suggests.
trace-eda.tex:60-67: "'heavy-tailed' in the operational sense used throughout this chapter";
"Tail-index estimates (Hill estimator over the top percentile ...; indicative values, no
formal goodness-of-fit claim)". The numbers (Hill ≈1.9/6.6/7.2) are presented as indicative,
not as a Pareto claim. Adding a Mean-Excess plot is a fair strengthening, but the claim is
already weakened to "indicative empirical" — i.e., Gemini's own weaker alternative.
Dup-hint: Hill/mean-excess; trace-eda stats

### tsfm-overhead — deployment footprint of running TSFMs
Target: predictors.tex:101, closedloop.tex:369 (review-predictors.md `:101`; review-closedloop.md `:369` [Major])
Verdict: PARTIAL
Severity: minor
Evidence: Partial quantification already present: predictors.tex:92-103 gives per-decision
GPU time (≈65 ms Chronos-2 to ≈90 ms Toto-2), model sizes (120M-2.5B params), total
benchmark wall-clock (≈2.5 h), and frames "deployment footprint ... a GPU-resident
120M-2.5B-parameter service" whose asymmetry "the closed-loop evaluation prices."
closedloop.tex:368-369: inference cost "≈seconds per tick on CPU-class hardware ... not
charged to the fleet." What is genuinely missing is an explicit VRAM/GPU-slice number and a
deduction of forecaster latency from the usable lead — a fair, bounded addition. Not absent,
under-quantified.
Dup-hint: TSFM VRAM/lead deduction; predictors+closedloop

### live-variance — single-point live measurements, no variance
Target: validation.tex Table 5.1 / :60-74 (review-validation.md `:60-74` [major]; adjudication ACCEPTED)
Verdict: PARTIAL
Severity: moderate
Evidence: CONFIRMED that Table 5.1 reports single-run deltas with no variance/error bars.
But the thesis already frames the anchor as a bounded single-shot demonstration
(validation.tex:133-146: "one window (the hardest), two policies ... It validates the
control loop ... within run noise"), i.e., essentially the "reframe as single-shot
demonstration" Gemini offers as the alternative. The demand values are shown byte-identical
for the first 12 ticks (validation.tex:82-92), and the archived aiperf p99 (695.16 ms)
matches Table 5.1 exactly. Reporting variance across trials would strengthen it; the current
framing is honest about being one run.
Dup-hint: single-run live, no variance; validation

---

## D. Line-referenced style/presentation items (spot-checked present, mostly editorial)

All verified to exist as quoted; verdicts are CONFIRMED-present but the items are
subjective editorial calls (many the adjudication itself downgraded/rejected):
- related.tex:74-81 grey-literature-convention footnote (meta-commentary) — present. CONFIRMED (nit).
- related.tex:177-179 "$R^2=\num{0.123}$" appears in the lit-review chapter — present. CONFIRMED (nit; forward-ref is deliberate).
- related.tex:312-317 "0.27--0.31 times ..." in the Positioning summary — present. CONFIRMED (nit).
- trace-eda.tex:26 "151 fully duplicated rows ... retained" — present; adjudication REJECTED removal (preserve fidelity). Thesis already retains + footnotes. DENIED as an error.
- trace-eda.tex:78 k-means k=4 (silhouette 0.388/0.378/0.319) — verified exactly against
  `analysis/trace_eda/l_silhouette_scan.json` (k4 0.3880, k3 0.3777, k5 0.3185). adjudication REJECTED rerun. DENIED as an error.
- conclusion.tex:31 "echo", :101 "honest complement" — present; adjudication REJECTED (standard parlance). DENIED as errors.
- closedloop.tex:34 "reactive strawman", :69/:315 bold whole sentences, :148 SIrange — present. CONFIRMED (nits).

---

## E. cross-check.md internal-consistency claims — independently re-verified

Gemini's `cross-check.md` asserts the manuscript is numerically self-consistent. Spot-checks
against artifacts CONFIRM its key claims (this makes cross-check.md reliable, not a source of
required revisions):
- Decoupling R²=0.123 / decode R²=0.654: `d_signals_stats.json` 0.12254; `m_gen_and_global_stats.json` 0.65350. ✓
- CV² img 3.83 vs req 0.32 (1-min): `c_temporal_stats.json` 3.8308 / 0.3212. ✓
- ACF half-life img 69 min / req 9 min: `d_signals_stats.json` 69 / 9. ✓
- Additive structural R²≈0.94, image mass 34-36%: `predictors/results/metrics/additive_structural_ablation.json` R²=0.9355, image mass 0.3554. ✓
- Jaccard 0.02 (extreme-minute overlap): `q_multires_tails_stats.json` window_regime_overlap.jaccard = 0.02475. ✓
- 588 ms floor = f(64) 316.4 + p99 handoff 272: 316.4+272 = 588.4. ✓ (closedloop.tex:75-78, :289-292)
- Cost ratio C=16 × 5.60 d = 16×5.6×86400 = 7.741 Mworker-s; 2.38/7.74 = 0.307 (0.31×), 2.12/7.74 = 0.274 (0.27×). ✓ (closedloop.tex Table 5.2)
- Toto-2 2.5B ≈ 20× Chronos-2 120M: 2500/120 = 20.8. ✓
- Attention agreement 1.300 vs 1.342 ms = 3.2%: (1.342-1.300)/1.300 = 3.23%. ✓ (aiconfigurator.tex:417)
- f(1)=8.16, f(64)=316.4 ⇒ 4.94/img, 1.65×, ~3.2 ms fixed overhead: 316.4/64=4.94; 8.16/4.94=1.65; a=8.16-(308.24/63)=3.27. ✓
- ContextTokens max 148,569 (≈149k), 3.140% >16384: raw-trace recompute. ✓

---

## SUMMARY

Findings adjudicated: 4 signature + 4 cross-cutting + ~7 substantive + a block of
line-referenced style nits.

Counts (substantive verdicts):
- CONFIRMED: 3 (forecast-free/ARIMA contradiction; f(N) vs N notation clash; dense-tone as present) + the style-nit block (present but editorial).
- PARTIAL: 8 (HW seasonality; 245s stall; hardware mismatch; generalizability; Hill fragility; TSFM overhead; live variance; and 25 Gbps leaning DENIED).
- DENIED: 3 (149k extrapolation on substance; exact-batching-law already clarified; duplicated-rows / k-means / "echo" / "honest complement" as errors — adjudication itself rejected these).

Top 5 CONFIRMED (highest-value, real, actionable):
1. **"forecast-free policy" vs "ARIMA-driven" reactive baseline** (baselines.tex:42 vs :141) —
   a literal terminology contradiction (ARIMA forecasts; confirmed via predictors.tex:181-184).
   One-line rephrase fixes it; no result affected. [moderate]
2. **245-second stall has no root-cause hypothesis** (validation.tex:121-125) — factually
   true; add a hypothesis. But impact is bounded and the stall is absent from the archived
   anchor run (live_fc p99 = 695.16 = Table 5.1), so "critical failure" is overstated. [moderate]
3. **Live Table 5.1 reports single-run deltas with no variance** (validation.tex:60-74) —
   true; thesis already frames it as a one-shot anchor, so reporting variance or explicitly
   labeling "single-shot demonstration" is the clean fix. [moderate]
4. **f(N) vs "N × TP" notation clash in Figure 1** (intro.tex:312) — real, minor, relabel. [minor]
5. **TSFM deployment footprint under-quantified** (predictors.tex:101, closedloop.tex:369) —
   per-tick latency + param counts given; explicit VRAM and lead-deduction missing. [minor]

Most important corrections to Gemini (over-claims):
- The **HW "seasonality starvation"** technical claim is wrong: `benchmark.py:96-99`
  adapts the seasonal period (15 min at 1 s) and `holt_winters.py` hard-guards two full
  cycles; the genuine (context-cap) limitation is already stated at predictors.tex:384-390.
- The **149k extrapolation** already has both the disclaimer and the analytical bound
  (tracks attention's quadratic to 147k within a few percent/octave, aiconfigurator.tex:182-186);
  figures are exact (3.140% > 16384; max 148,569). Not "highly dangerous / unbounded."
- The **25 Gbps** and **exact-batching-law** asks are substantially already addressed in the text.
- `cross-check.md`'s internal-consistency verdict is independently CONFIRMED against artifacts.
