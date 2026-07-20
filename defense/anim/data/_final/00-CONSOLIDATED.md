# Consolidated final data — thesis-ingestible summary

Every item below survived: (1) read-only adversarial verification of its driver, (2) a fix pass,
(3) at least one adversarial refutation round by three independent skeptics with distinct lenses.
Where a claim was refuted, the CORRECTED claim is what appears here. Per-track detail is in the
sibling cards; this file is the ingestion surface.

**Nothing here may be quoted without its caveat line.** The caveats are not hedging — in four
cases the uncaveated version is factually wrong.

Status: 8 of 9 tracks final (g4 added after a 4-lens round-3 audit that refuted its first
headline). g2_conventions was attempted and DROPPED — see item 10.

---

## 1. burst2/6 forecast grading — closes a STATED STRUCTURAL hole  [G1_burst26.md]

**Quotable:** "With expanding-context forecasts the two out-of-span episodes are no longer
structurally un-gradable, and the encoder schedule is genuinely anticipatory there (issue-time
gated, max staleness 165 s). Graded end to end, the forecast policy meets the SLA in 17 of 18
language cells against the reactive baseline's 0 of 6, which violate both bounds. The
reproduction anchors reproduce the ledgered p99 bit-identically."

**Mandatory caveats:** (a) the arms are NOT cost-matched — forecast spends 15.6-27.0 GPU-h vs
reactive 3.3-6.2; this is an SLA-attainment claim, not an efficiency claim. (b) On the language
side this compares two CONVERSIONS of the same held signal, NOT anticipation (the sampled bin
runs ~60 s behind sim time). (c) A 2.7-4.8% runtime offset vs the Chapter-5 wheel must be applied
before cross-chapter comparison. (d) 40 distinct configurations, not 42 (two cells are duplicates).

## 2. Controller inference cost charged — the 0.62x SURVIVES  [A16_ctrlcost_FINAL.md]

**Quotable:** "Charging both controllers their own inference cost leaves the result intact: on GPU
the ratio moves from 0.623x to 0.624x, and on CPU-class hardware every deployable configuration
(Chronos, TimesFM) stays between 0.65x and 0.66x, still below the reactive baseline's 0.675x. The
only configurations that would erase the margin cannot hold their own tick period — Toto on CPU
needs 29-32 s for a 15 s tick — so the constraint they express is model feasibility, not cost."

**Mandatory caveat:** the 0.62x is an ENCODER-pool worker-second ratio; the 4-signal fleet
controller provisions both pools yet is billed against the encoder denominator alone (pessimistic
by construction).

## 3. Cold start is ALREADY BILLED — and the pools use opposite conventions  [G7_coldstart_FINAL.md]

**Quotable:** "The language-pool GPU-hour figures already bill from instance order rather than
readiness: the discrete-event mocker integrates the provisioned worker count — active,
starting-up and draining alike — so cold start is inside every reported number and no surcharge
may be added. The encoder pool is the structural opposite, billing from readiness, so any
composed two-pool total mixes the two conventions."

**Also quotable:** two SLA-feasible encoder cost-order flips at the L=165 cold-pool lead —
burst1 (1.1444 -> 0.9698) and steady24h (1.1392 -> 0.9172).

**Mandatory caveats:** (a) the previously-reported burst5-L165 flip is RETRACTED — its reactive
comparator misses the SLA at 3,250 ms and an infeasible arm cannot carry a cost comparison.
(b) The language churn share is L=60-specific and partly tautological; never present it as a
surcharge.

## 4. Decode series — "upper bound" replaced by a sign-flip finding  [A16_decode_FINAL.md]

**Quotable:** "The decode series is exact in total volume to within 8e-7 of the replay, and
strongly conservative on the bins an operator can actually identify (+54% on the busiest 1%
selected by the arrival stamp itself); it is not a pointwise upper bound, and its shortfalls
concentrate in bins identifiable only in hindsight."

**Mandatory caveats:** (a) source from the ft_llm arms (n=1,000,000, usable trace join), NOT
timesfm_e2e (join unusable, falls back to composed arrival). (b) The onset ratio is a SELECTION
statistic — defining onsets on the true series collapses it from 3.41x to 1.02x. (c) The series
reaches the planner only as osl = gen/req, so no bin-level bias has been shown to propagate to a
replica decision: any provisioning-risk sentence is one inferential step short.

## 5. Endogenous demand — bounded under a stated mean-field model  [A16_endogenous_CORRECTED.md]

**Quotable:** "Under a mean-field client model (lognormal patience, mean 5 s; retry fraction 0.3)
iterated around the unmodified discrete-event replay — abandonment resolved offline, not in-clock
— neither arm reaches a fixed point; both settle into a period-2 limit cycle. The forecast arm's
latency observables are invariant across every iterate (TTFT p99 651.1 ms); the reactive arm
cycles over TTFT p99 [1702.1, 1808.4] ms with offered goodput 0.9302, against 0.9208 open-loop."

**Mandatory caveats:** (a) NEVER write "closed loop" — it is mean-field and offline. (b) Quote the
cycle envelope, never a single iterate. (c) The comparison is NOT iso-cost: 6.31-6.33 GPU-h
forecast vs 1.06-1.10 reactive (5.7-6.0x). (d) Retry is modelled but effectively inactive — this
is an ABANDONMENT experiment. (e) Exogeneity was attacked directly and SURVIVED: the archived
forecast is byte-identical across cells and never recomputed from realized demand.

## 6. Dense 32B intermediate priced  [G3_32b_CORRECTED.md]

**Quotable:** "On the head2k isolation window under the evaluation SLA, the dense 32B at TP2 knees
at 2.3 offered req/s against the 8B-TP2's 16 — a 7.2x gap at equal GPU count — and even at TP8,
four times the silicon, reaches only 10, still below 8B-TP2. Every knee is ITL-bound."

**Mandatory caveats:** (a) head2k only (2,000 requests, 721 s), the trace's lightest-tail slice.
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
(b) The 672 "fabric rescue" passes by only 6.1% and is a SINGLE-STREAM SERIALIZATION result, not a
line-rate one. (c) 896 cells are extrapolated beyond the collected batch axis. (d) All size
distributions are ASSUMED — the trace records counts only.

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
bound on the fold containing the e13 onset. The rho frontier retains its shape in every fold, but
rho=15 is nowhere the cheapest feasible setting; on the language pool the forecast is dearer than
static in six of seven folds. The single-span averages are representative of the span, not of an
arbitrary day within it."

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
cost-vs-C* range. (d) One trace, one datacenter, one 7-day record.

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

1. **tex/twopool.tex:76-77** — the 882 ms is a WHEEL-runtime number sitting under a sentence
   (:66-72) asserting the artifact inflated "the extreme tail only (identical p99)". That holds at
   s=1 (+0.2%) and FAILS at s=4 (882.08 wheel vs 782.68 source, -11.3%).
2. **simulation/results/sweeps/reports/** is RUNTIME-MIXED — s=3 was written 2026-07-08 with a
   different schema; s=1/2/4/16 on 07-06..07. Not a homogeneous ledgered set.
3. **tex/intro.tex:504 and :148** — "offered-work upper bound" is not supportable; replacement
   wording in A16_decode_FINAL.md.

NO tex/ FILE HAS BEEN MODIFIED. These are reported for the author's decision.
