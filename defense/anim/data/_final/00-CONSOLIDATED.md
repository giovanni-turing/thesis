# Consolidated final data — thesis-ingestible summary

Every item below survived: (1) read-only adversarial verification of its driver, (2) a fix pass,
(3) at least one adversarial refutation round by three independent skeptics with distinct lenses.
Where a claim was refuted, the CORRECTED claim is what appears here. Per-track detail is in the
sibling cards; this file is the ingestion surface.

**Nothing here may be quoted without its caveat line.** The caveats are not hedging — in four
cases the uncaveated version is factually wrong.

**PRECISION HYGIENE — delivery-wide (applies to every card).** Two significant figures unless the
underlying spread is demonstrated to be smaller. Four-significant-figure ratios in this delivery
were quoted off n=5 wall-clock medians with up to 17% intra-cell spread (A16_ctrlcost), off a
non-monotone SLA boundary whose wobble exceeds the reported bracket width (G3 knees), and off a
percentile convention that itself moves the value 0.8-4.9% (A16_endogenous). Those digits are not
information. Anchor/reproduction values quoted against a ledger are the sole exception: they are
exact-match assertions, not measurements, and keep their full precision.

**INFEASIBLE-COMPARATOR STANDARD — one rule, applied everywhere.** An arm that misses the SLA
cannot carry a cost comparison. Consequences: the burst5-L165 flip stays retracted (item 3); the
reactive arm is disqualified as A16_ctrlcost's cost anchor and the static fleet replaces it
(item 2); and every cost claim in this delivery is anchored on a **feasible** comparator or is not
made. Items 2 and 3 previously applied opposite standards; that inconsistency is resolved here in
favour of the stricter one.

Status: 8 of 9 tracks final (g4 added after a 4-lens round-3 audit that refuted its first
headline). g2_conventions was attempted and DROPPED — see item 10.

---

## 1. burst2/6 forecast grading — closes a STATED STRUCTURAL hole  [G1_burst26.md]

**Quotable:** "The limitation that burst2 and burst6 are structurally un-gradable by a forecast
policy is removed once the forecast archive is expanding-context: both episodes sit inside the
forecastable span, and the encoder schedule is genuinely anticipatory there (issue-time gated,
max staleness 165 s). A reproduction anchor recovers the ledgered Chapter-5 p99 TTFT
bit-identically on the C8 grid cell of each window (766.259 ms and 735.318 ms). Graded end to end
against TTFT p99 <= 1000 ms and ITL p99 <= 100 ms, the forecast policy meets both bounds in 17 of
18 language cells and the ARIMA reactive ladder in none of 6 — but a forecast-free static
two-replica fleet also passes both bounds on both windows, at a fraction of the cost. These
episodes are therefore now GRADABLE by a forecast policy; they are not evidence that forecasting
is the economical policy on them."

**Mandatory caveats:**
(a) **NOT OPTIONAL — without it the sentence inverts.** The forecast-free static two-replica
fleet (static_C8, no planner) passes both bounds on both windows: TTFT p99 745.4 / 700.3 ms,
ITL p99 7.6 / 7.3 ms, at 7.598 / 5.468 GPU-h. Window-matched, every forecast cell costs
**2.2x-3.6x** as much (burst2 16.568-26.961 GPU-h vs 7.598; burst6 15.610-18.438 vs 5.468).
No language-pool cost advantage for forecasting may be claimed here.
(b) The arms are NOT cost-matched, and the gap to reactive is a CAPACITY gap, not a policy gap:
forecast spends 15.6-27.0 GPU-h vs reactive 3.3-6.2, driven by a hardcoded FORECAST_REQ_SCALE=8.0
(gen_g1_burst26.py:334). This is an SLA-attainment claim, not an efficiency claim.
(c) On the language side this compares two CONVERSIONS of the same held signal, NOT anticipation
(the sampled bin runs ~60 s behind sim time).
(d) On the ENCODER pool no arm misses the bound except the calm-day static C2. There the arms are
roughly cost-matched and the only gain is a within-SLA 748.7 -> 588.4 ms improvement on burst6
alone — on burst2 the forecast arm TIES reactive at 588.37 ms.
(e) A 2.7-4.8% runtime offset vs the Chapter-5 wheel must be applied before cross-chapter
comparison.
(f) **42 distinct configurations** (30 language + 12 encoder cells), not 40. static_C8 and
runtime_gridC8 are NOT duplicates: they differ in STARTUP_TIME (60 s vs unset,
gen_g1_burst26.py:319-325; verification.json lead_s 60 vs null) and their burst2 outputs differ
(TTFT p99 745.359 vs 745.905). The claim that this pair "proves the mocker is bit-deterministic"
is **struck** — the data says the opposite.
(g) 18 cells = 3 models x 3 startup times x 2 windows, with the model axis near-degenerate on
burst6 (17 ms spread). Not 18 independent trials.
(h) The burst6 anchor is the **C8** grid cell (735.318 ms), not the C6 cell (733.777) tabulated at
baselines.tex:109. State the C8 provenance or a reader will collide the two.

## 2. Controller inference cost charged — the 0.62x SURVIVES  [A16_ctrlcost_FINAL.md]

**Quotable (anchored on STATIC — the only feasible comparator):** "Charging each controller its
own measured inference cost does not disturb the provisioning result. On GPU the forecast arm
moves from 0.623x to 0.624x of the deployable static fleet — controller duty cycle under 0.8% at a
15 s tick for every model tested. On CPU-class hardware, priced at $0.04/vCPU-h against
$2.00/GPU-h over the 24 threads the forward occupies, the deployable configurations (Chronos,
TimesFM) land at 0.65-0.66x, still well inside the 1.00x static baseline. Among the models
measured, only Toto on CPU at a 15 s tick fails, and it fails on FEASIBILITY rather than cost."

The reactive comparison may be attached only WITH its infeasibility disclosure, never bare:
"...and remains below the reactive arm's 0.67x, **though that arm misses the burst3 episode SLA at
16,078.7 ms and so cannot itself carry a cost comparison.**"

**Mandatory caveats:**
(a) **PRICE BASIS.** The CPU band is a measurement MULTIPLIED BY AN ASSUMED PRICE RATIO.
cpu_gpu_price_ratio=0.02 and n_thr=24 appear only in gen_a16_controller_cost.py:542 and have no
market-rate justification in the artifact. Re-derived here, the ordering against reactive
**inverts at price ratio 0.0286** (4-signal cell; 0.0338 at 1-signal) — 1.4x headroom on an
assumption, not on data.
(b) **INFEASIBLE COMPARATOR.** The reactive L=30 comparator misses the burst3 bound at 16,078.7 ms
against 1,000 ms (provenance.v_infraction, all rows is_violation=t). Under the standard applied
uniformly in this delivery (see item 3), it cannot carry a cost comparison, so the static
baseline is the anchor.
(c) The 15 s tick is an UPPER BOUND, not the replayed controller: the 2,410,755 ws schedule is a
180 s stride-12 tiling, at which every CPU cell including Toto is feasible.
(d) **PRECISION.** CPU latencies are medians of n=5 with up to 17% intra-cell spread. **Two
significant figures only** — never 0.6537 / 0.6593.

**DELETED caveat** (it protected the wrong quantity): the old "the encoder denominator is
pessimistic by construction" line. It is true of the LEVEL and irrelevant to the ORDERING, which
is denominator-invariant (the denominator cancels in fc + charge < react + charge_react). It
bought zero insurance and implied slack that does not exist.

## 3. Cold start is ALREADY BILLED — and the pools use opposite conventions  [G7_coldstart_FINAL.md]

**Quotable:** "The language-pool GPU-hour figures already bill from instance order rather than
readiness: the discrete-event mocker integrates the provisioned worker count — active,
starting-up and draining alike — so cold start is inside every reported number and no surcharge
may be added. The encoder pool is the structural opposite, billing from readiness, so any
composed two-pool total mixes the two conventions."

**Two points that were UNDERSOLD and should be stated affirmatively:**
1. The order-time overlay **over-charges the forecast arm** (real strict-re-warm burst1-L165 =
   525,643.5 ws against the overlay's 559,267.5), so the printed ratios are **upper bounds** and
   the L=165 flip holds *a fortiori* within the strict convention.
2. **The headline 0.62x is untouched by this defect**, because its static-C8 comparator has no
   up-steps and therefore carries no readiness under-charge. Say this explicitly — an examiner
   will otherwise assume the defect propagates.

**Also reportable, but HEDGED (defence only, not manuscript):** two SLA-feasible encoder
cost-order flips at the L=165 cold-pool lead — burst1 (1.1444 -> 0.9698) and steady24h
(1.1392 -> 0.9172). BLOCKED in the manuscript: the cost side is a strict-re-warm accounting while
the feasibility that licenses it is read off WARM-POOL simulations, and no reactive
strict-re-warm run exists. Unblockable by one re-run (--strict-rewarm at L=165 on burst1 and
steady24h, confirming both stay under 1,000 ms).

**Mandatory caveats:** (a) the previously-reported burst5-L165 flip is RETRACTED — its reactive
comparator misses the SLA at 3,250 ms and an infeasible arm cannot carry a cost comparison.
**This is the delivery's standard for infeasible comparators and it is applied uniformly**
(see item 2, where the reactive arm misses burst3 by 16x and is likewise disqualified as a cost
anchor). (b) The language churn share is L=60-specific and partly tautological; never present it
as a surcharge. (c) NOT "previously undocumented" — closedloop.tex:494-501 already carries the
encoder warm-pool vs strict-re-warm distinction and its 0.62x->0.59x consequence; only the
LANGUAGE convention and the CROSS-POOL contrast are new. (d) NOT "systematic": flips occur in 2 of
5 windows, 2 of the 3 whose comparator is SLA-feasible, and only at L=165.

## 4. Decode series — "upper bound" replaced by a sign-flip finding  [A16_decode_FINAL.md]

**Quotable:** "The rate signals stamp each request's full token volume at its arrival minute. For
encoder and prefill work this is faithful; for decode it is NOT a pointwise upper bound. The
stamped decode series is exact in total volume (7.8e-7 of the replay over 1,000,000 requests) but
displaces mass in time: on the busiest one percent of FIFTEEN-SECOND bins selected by the stamp
itself it exceeds the realised decode rate by 54 percent, while on the busiest one percent
selected by the realised series it falls short. Both figures shrink with bin width — at the
planner's sixty-second interval the conservative figure is under three percent — and the sign of
the bias over the population the controller actually samples spans zero, so the series licenses
NO provisioning claim of either direction."

"Strongly conservative" is **deleted**: the operator decides at 60 s, where the figure is +2.9%
and 42.6% of the flagged-hottest bins are still under-stated.

**Mandatory caveats:**
(a) **BIN WIDTH IS LOAD-BEARING.** +54% holds only at 15 s. At 1 s it is +329%; at the planner's
actual 60 s interval it is **+2.9%** (ft_llm_static; +3.2% reactive). The shipped artifact itself
labels the 15 s verdict "NOT the controller's cadence." The number must never appear without its
resolution.
(b) The +54% is **selection error, not headroom**: the arrival-selected "busiest 1%" have a 24%
lower true rate (1084.7 vs 1435.1 tok/s) than the genuinely busiest 1%, and 18.8% of them
(42.6% at 60 s) are still short. The same collapse hits the mass-weighted onset ratio, so no
onset ratio may be presented as a property of the stamp.
(c) The +54% is itself **inflated** by the uniform 1/itl spreading model, per the generator's own
docstring (gen_a16_decode_spread.py:56-58: smoothing "biases the analysis TOWARD the 'the arrival
stamp is conservative' conclusion"). This **replaces and reverses** the card's unsourced
"+4.8% de-smoothing" residual risk, which is **struck** — no de-smoothing code path exists.
(d) Every supporting number beyond the two headline figures must be sourced to the **ft_llm arms**
(ft_llm_static / ft_llm_reactive), never timesfm_e2e (join unusable, falls back to composed
arrival). All eleven previously timesfm-sourced figures have been re-derived on the card.
(e) The series reaches the planner only as osl = gen/req, so no bin-level bias has been shown to
propagate to a replica decision: any provisioning-risk sentence is one inferential step short.

**Provenance status:** admissible as a CORRECTION THAT WEAKENS an existing claim (needs no new
provenance), **not** as a new positive result — a16_decode has 0 rows in provenance.ingest_log.

## 5. Endogenous demand — bounded under a stated mean-field model  [A16_endogenous_CORRECTED.md]

**Quotable:** "Under a mean-field client model (lognormal patience, mean 5 s; retry fraction 0.3)
iterated around the unmodified discrete-event replay — abandonment resolved offline, not in-clock
— the forecast arm's latency observables are invariant across every iterate (TTFT p99 651.1 ms),
while the reactive arm oscillates over a two-phase envelope of TTFT p99 [1.70, 1.81] s **over
served clients only**, against ~10.6 s open-loop."

"Both settle into a period-2 limit cycle" is **struck**: it is unsupported for the forecast arm,
whose iterates 2 and 4 sit at the same phase yet differ in cost (gpu_hours 6.311 vs 6.328) — only
laps_verified = 1.0 was cleared. Write instead: "the reactive arm settles into a two-phase
envelope; the forecast arm's latency observables are invariant while its cost is still drifting
at the last iterate."

**Mandatory caveats:** (a) NEVER write "closed loop" — it is mean-field and offline. (b) Quote the
envelope, never a single iterate and never the midpoint. (c) The comparison is NOT iso-cost:
6.31-6.33 GPU-h forecast vs 1.06-1.10 reactive (5.7-6.0x). (d) Retry is modelled but effectively
inactive — this is an ABANDONMENT experiment. (e) Exogeneity was attacked directly and SURVIVED:
the archived forecast is byte-identical across cells and never recomputed from realized demand.
(f) **SURVIVOR CENSORING.** max_observable_percentile_of_offered = 95.44-95.76 at the reactive
cycle against 100.0 at iterate 0, and served_only_p99_is_censored_at_cycle = true. **The cycle p99
and the open-loop p99 are not p99s of the same population.** The survivorship-immune figure is
e2e_p99_from_ingress [3.51, 3.94] s — still ~2x the 2000 ms budget.
(g) **The endogenous feedback is near-nil.** n_shed_at_encode = 130 on every iterate from 1 onward
and cannot respond to the iteration (gen_a16_endogenous.py:511). 92-99% of abandonment is a
one-shot exogenous encoder shed; the word "endogenous" overclaims without this.
(h) **Scope is one cell pair:** burst3 only, one seed, one patience parameterisation. The
P2000/q0.6 sensitivity cells and *_ondemand controls reached only 1-3 iterates.
(i) **PRECISION.** Percentile convention (floor-index vs interpolated) spreads these by ~0.8% at
the cycle and ~4.9% open-loop. Do NOT quote to 0.1 ms.

## 6. Dense 32B intermediate priced  [G3_32b_CORRECTED.md]
### POST-MANUSCRIPT DEFENCE MATERIAL — R26 CLASS. Q&A / appendix ONLY, never a results chapter.
`tex/twopool.tex:391` ("32B were not priced") **stands as written** and may not be edited.

**Quotable (defence Q&A only):** "On the head2k isolation window under the evaluation SLA, the
dense 32B at TP2 knees near 2.3 offered req/s against the 8B-TP2's 16 — roughly a 7x gap at equal
GPU count — and even at TP8, four times the silicon, reaches only about 10, still below 8B-TP2.
Every knee is ITL-bound."

**Mandatory caveats:** (a0) **SIMULATION PROVENANCE — state this first.** These are not
measurements. Every 32B figure is an AIC / vLLM perf-DB **prediction** (h100_sxm, perf-DB 0.19.0)
replayed through the dynamo.replay discrete-event mocker (summary.json `engine` /
`timing_model`). **The 32B family has no silicon anchor anywhere in this thesis** — the collected
RTX 5090 database covers the 8B/encoder path only. The 8B-TP1 control is what ties the harness to
the ledger, not the 32B rows. (a) head2k only (2,000 requests, 721 s), the trace's lightest-tail
slice.
(b) Quote knees to 2 significant figures — the SLA boundary is non-monotone with 0.9-7.6% ITL
wobble. (c) State offered OR achieved units consistently, never mixed. (d) The runtime divergence
is a function of DISTANCE FROM THE KNEE, not of arm — the artifact's earlier "specific to
235B-TP8" assertion is false and corrected.

## 7. Image-size sensitivity x fabric  [G6_sizesens_FINAL.md]

**Quotable:** "Repricing the encoder through the collected RTX 5090 operator database at other
resolutions, the verdict holds at 448 and below on both modelled fabrics; the closed-form service
floor f(64) + 272 ms x (px/32)^2/196 places the crossing near 690-705 px on a 100 Gbps link, so
the assumed resolution sits just below it. Because the p90 schedule is driven by image count it is
blind to size: a size increase produces no provisioning response at all."

**Mandatory caveats:** (a) 448 GRADED cells, not 456 (that is a file count including 8 orphans).
(b) The 672 "fabric rescue" passes by only 6.1% (938.734 vs 1000 ms) and is a SINGLE-STREAM
SERIALIZATION result, not a line-rate one — that assumption contradicts the simulator's own
dispatch model for the very request that sets the p99. (c) 896 cells are extrapolated beyond the
collected batch axis (b stops at 32); 448 and 672 are inside the collected box. (d) All size
distributions are ASSUMED — the trace records counts only.
(e) **WINDOW SCOPE — every size cell quoted above is burst3.** The verdict does NOT hold window-
invariantly: at the steady24h window the forecast arm at 672 px **FAILS on both fabrics**
(1927.5 ms @100 Gbps, 1972.5 ms @25 Gbps), so the "fabric rescue" at 672 is a burst3 result only.
At 896 px steady24h fails on both fabrics as well (5632.5 / 5716.3 ms). Any 672 px claim must name
its window.
**Structural note (should lead):** provisioned_worker_s is invariant at 32,228.0 across every
burst3 cell and both fabrics — the size-blindness is the track's most useful finding.

## 8. Zero-shot as a strength  [ZEROSHOT-AS-STRENGTH.md]

**Quotable:** "The zero-shot posture is not a limitation of this work but a property of the
deployment it targets. A foundation forecaster provisions correctly from three minutes into an
unseen workload, covering 99.96% of the trace end to end, and does so identically across three
model families (TTFT p99 651.1 ms for all three) — so neither training data nor model selection
sits on the critical path. What carries the result is the p90 headroom and the tail-aware
conversion rather than forecast accuracy: the single episode the policy misses fails identically
under every model and both capacity ratings."

**Mandatory caveats:** (a) model-independence is measured on ONE trace. (b) e13 is a genuine
mechanism boundary. (c) Fine-tuning is OUT OF SCOPE — one future-work sentence only; the
exploratory pass was a failed recipe, not a proven ceiling.

## 9. Within-trace temporal fold generalization  [G4_folds_FINAL.md]

**Quotable:** "Split into seven disjoint 24-hour folds, the headline quantities are not
fold-invariant. The encoder cost ratio against the deployed C=8 fleet ranges from 0.47x to 1.10x
across burst-bearing folds around its 0.62x whole-span value, and the forecast policy misses the
bound on the fold containing the e13 onset — a fold on which a **static C=5 fleet passes at
904.7 ms for only 3.0% more worker-time**. The rho frontier retains its shape in every fold, but
rho=15 is nowhere the cheapest feasible setting **among the four values swept**; on the language
pool the forecast is dearer than a feasible static fleet in six of seven folds. The single-span
averages are representative of the span, not of an arbitrary day within it."

**The strongest fact in this track, previously omitted — state it.** On F6, the one fold where the
forecast arm FAILS (encoder p99 1262.3 ms at rho=15, 419,391.2 ws), a forecast-free static C=5
fleet **PASSES at 904.7 ms** for 431,967.3 ws. The forecast arm is therefore only **2.9% cheaper
and infeasible**; the static fleet costs **3.0% more and works**. This is the encoder-pool
counterpart of the language-pool inversion in Finding 5, and the two together are the delivery's
central convergent finding: **a forecast-free static fleet is the arm to beat on both pools**, and
on the encoder pool it is beaten only on the covered span, not fold-by-fold.

**On the deployed fleet size (state it, do not overstate it):** a static ladder shows C=4 clears
the AGGREGATE bound (993.8 ms), but C=4 fails 3 of 5 burst-bearing folds, so under the thesis's
own aggregate-AND-per-episode grading it is not deployable. The fold-robust optimum is C*=5,
against which the schedule still costs **0.980x**. The unjustified headroom in the deployed fleet
is 8 vs 5 = **1.6x**. Do NOT write "the baseline is 2x oversized" — the data does not license it.

**Mandatory caveats:** (a) this is the A15 expanding-context span (999,599 req, 6.998 d), NOT the
5.60-day span the 0.62x headline is priced on — the ratios coincide, the absolute worker-seconds
do not. (b) Fold conditioning history is NESTED (expanding context), so folds are disjoint TEST
windows but not training-independent. (c) F3's static rungs are flagged FAIL by a hair-trigger
queue-divergence criterion (q_end 17 vs median <=1) and F3 is silently dropped from the
cost-vs-C* range — so the reported 0.971x-1.757x range is over a 6-fold subset presented as 7.
(d) One trace, one datacenter, one 7-day record; folds share tenant mix, size distribution and
hardware calibration, differing only in time. G4 is evidence about TEMPORAL variability within one
trace and about nothing else. (e) **GRID CAVEAT on rho.** The sweep is {10, 15, 20, 25} and the
optimum sits at a **grid endpoint in 7 of 8 folds** (rho=25 in six, rho=10 in F6). The true
optimum may lie beyond 25 and is untested: "rho=15 is nowhere cheapest **among the four values
swept**" is safe; "rho=25 is optimal" is not. (f) The **language anchor was not run** — only the
encoder anchor is verified, so the language fold ratios rest on an unanchored (though shared)
converter.

**Anchor:** enc p99 588.4 = 588.4, provisioned_ws 2,962,304.8 exact, ratio 0.612 vs 0.6124.
Billing verified symmetric; the forecast arm's 30 s cold start IS paid.

## 10. Token-accounting conventions — TRACK DROPPED, claim nothing from it

The both-conventions sensitivity run (tex/twopool.tex:432) was built and partially run, then
DROPPED. Nothing from it may be cited.

**Why.** The alternate convention rests on a SUPPOSITION that cannot be read off the trace: a
fixed 196 post-merge tokens per image (448^2 at 32x32 px/token). The trace's own model
demonstrably does NOT tokenize that way — its total vision tokens are sub-linear in image count
(V(n) ~ 743 * n^0.627; the implied tile side falls from 532 px at n=1 to 214 px at n=1225), i.e.
it downscales under a token budget. Imposing a fixed per-image count on top of that is a
modelling fiction, not a measurement, and the resulting PASS->FAIL flips would be an artifact of
the supposition rather than evidence about the target model.

**Consequence.** tex/twopool.tex:432 — "a both-conventions sensitivity run remains future work" —
STANDS AS WRITTEN. It cannot be closed without the target model's actual tokenization applied to
the trace's actual image geometry, which this trace does not record.

**Not affected.** The base-convention (ContextTokens verbatim) results are untouched, and so are
every other track, the 588.4 ms floor, and the fabric requirement — all of which use
post_merge_tokens = 196 * n as coded in trace_to_two_pool.py:188, which is correct under a
per-image cap of 16,384 tokens (196 << 16,384, so the cap never binds).

---

# Defects found IN THE THESIS TEXT  [THESIS-TEXT-DEFECTS.md]

1. **tex/twopool.tex:76-77 — REFUTED AS DIAGNOSED. Do NOT requote 882 -> 783.** The reports
   backing that paragraph are all old-schema WHEEL runs, so the paragraph is wheel on **both**
   arms — internally consistent, not mixed. The requote would CREATE the defect it claims to fix.
   *Real instead:* (1a) narrow `:69`'s "extreme tail only (identical p99)" to s=1 — it fails at
   s=2/4/16 (up to +22.1% TTFT / -61.1% ITL); (1b) **delete the 4x column** at `:78` (source build
   gives the 235B 20,032.8 ms against the published 1,402 ms — 14.3x) and keep the 1x pair.
   Deleting rather than substituting respects R26. **`twopool.tex:391` stands as written.**
2. **simulation/results/sweeps/reports/** is RUNTIME-MIXED — **conclusion confirmed, the
   delivery's stated proof was FALSE**: `llm_head2k_aic_s3`'s 4543.39 is NOT identical to the
   source build (4517.57); it matches `g3_32b/8b_tp1_s3`. There are **four** source-schema files
   (all three `llm_burst1_aic_*` were missed), and mtime is not the discriminator — the
   `gpu_hours` key set is. **The knee is robust** (109.51 and 108.48 both breach 100 ms).
   **NO NUMERIC EDIT** — a caption disclosure plus a `runtime` column backfill on
   `provenance.sweep_point`.
3. **tex/intro.tex:504 and :148** — "offered-work upper bound" is not supportable. **CONFIRMED**,
   but the delivery's "understates 58% of bins" is a `timesfm_e2e` figure that does not reproduce:
   the ft_llm arms give **47.7% / 47.3%** — a minority; the stamp overstates ~52%. Replacement
   wording in A16_decode_FINAL.md (ft-arm ranges only, bin width stated, no provisioning claim).
   At `:148` only the parenthetical changes.

NO tex/ FILE HAS BEEN MODIFIED. These are reported for the author's decision.
