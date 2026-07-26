# DELIVERY RULING — `defense/anim/data/_final/`

**Date:** 2026-07-20
**Scope:** the eight-track delivery (`00-CONSOLIDATED.md`, `CLAIM-STRUCTURE.md`,
`ZEROSHOT-AS-STRENGTH.md`, `THESIS-TEXT-DEFECTS.md` + 8 per-track cards), the three proposed
thesis defects, and their interaction with `provenance/audit/ADJUDICATION.md` §0.4 (44 rejected fixes).
**Basis:** adversarial verification of each track against source artifacts, generator source, and the
`provenance` schema; plus independent recomputation performed for this ruling (G4, R13 record check).

---

## 0. RULING IN ONE PARAGRAPH

The delivery is **admitted with substantial correction**. No track is rejected outright; no track is
admitted as delivered. Every headline *arithmetic* figure reproduces — the harnesses are sound and the
anchors are exact. What fails is the **framing layer**: in five of eight tracks the quotable sentence
selects a comparator that is either SLA-infeasible, cost-dominated, or drawn from an arm the card's own
caveats disqualify. Two independent tracks (G1 and G4) converge on the same unreported fact — **a
forecast-free static fleet meets the SLA on the language pool at a fraction of the forecast arm's
cost** — and neither card states it. That, not any numeric error, is the delivery's central defect.
Of the three proposed thesis defects, one is **refuted at its core** (Defect 1), one is **confirmed with
the wrong evidence and too narrow a scope** (Defect 2), and one is **confirmed but supported by numbers
from a disqualified arm** (Defect 3). Nothing proposed here re-opens a rejected fix; one **record**
correction to R13's citation is required (stale value, conclusion intact).

---

## 1. PER-TRACK VERDICT TABLE

| Track | Verdict | Confirmed / Failed | Net risk to thesis |
|---|---|---:|---|
| G1_burst26 | upheld with correction | 4 / 2 (+5 missing caveats) | LOW — but the quotable sentence is misleading as written |
| A16_ctrlcost | upheld with correction | 6 / 3 | LOW numerically, HIGH rhetorically (infeasible comparator) |
| G7_coldstart | upheld with correction | 9 / 3 | LOW — language half is thesis-grade; flip is defence-only |
| A16_decode | upheld with correction | 13 / 12 | MEDIUM — supporting layer must be re-sourced |
| A16_endogenous | upheld with correction | 7 / 3 | LOW — scope is one cell pair |
| G3_32b | upheld with correction | qualitative claim survives; 5 s.f. precision does not | LOW — post-manuscript, R26 class |
| G6_sizesens | upheld with correction | all numbers reproduce; 3 framing corrections | LOW — closes a stated Scope limitation |
| G4_folds | **upheld — and stronger against the thesis than the card admits** | all reproduced (re-derived here) | **HIGHEST — generality qualification required** |

### 1.1 G1_burst26 — burst2/6 forecast grading

**Verdict: upheld with correction.** 4 of 6 claims confirmed. The SLA verdicts (17/18 and 0/6),
every cost figure, and every encoder p99 reproduce exactly against files and `v_pool_latency`.
Two claims fail: the "40 distinct configurations" correction is itself wrong (the two cells differ in
`STARTUP_TIME`, 60 vs unset — `gen_g1_burst26.py:319-325`, `verification.json` `lead_s` 60 vs null;
their burst2 reports differ on 34 keys), and "bit-identical" over-scopes (only p99 **TTFT** reproduces;
p99 ITL does not).

**PERMITTED SENTENCE** (weaker than delivered):

> "The limitation that burst2 and burst6 are structurally un-gradable by a forecast policy is removed
> once the forecast archive is expanding-context: both episodes sit inside the forecastable span. A
> reproduction anchor recovers the ledgered Chapter-5 p99 **TTFT** bit-identically on the C8 grid cell
> of each window (766.259 ms and 735.318 ms), while the source build used here runs 2.7–4.8% faster
> than the ledgered wheel on the identical trace. Graded end to end against TTFT p99 ≤ 1000 ms and
> ITL p99 ≤ 100 ms, the forecast policy meets both bounds in 17 of 18 language cells and the ARIMA
> reactive ladder in none of 6. These episodes are therefore now **gradable** by a forecast policy;
> they are not evidence that forecasting is the economical policy on them."

**MANDATORY CAVEATS** (four are new):
(a) **The forecast-free static two-replica fleet also passes both bounds on both windows** (TTFT p99
745.4 / 700.3 ms; ITL p99 7.6 / 7.3 ms) at 7.598 / 5.468 GPU-h — **2.9× to 4.9× cheaper than every
forecast cell** (cheapest forecast 15.610 GPU-h). *This caveat is not optional; without it the sentence
inverts.*
(b) The gap to reactive is a **capacity** gap, not a policy gap: reactive averages 1.19–1.62 replicas
against forecast's 4.36–7.10, driven by a hardcoded `FORECAST_REQ_SCALE=8.0` (`gen_g1_burst26.py:334`).
(c) On the **encoder** pool no arm misses the bound except the calm-day static C2; there the arms are
roughly cost-matched (forecast 0.96–1.04× reactive) and the only gain is a within-SLA 748.7 → 588.4 ms
improvement on burst6 alone — on burst2 forecast **ties** reactive at 588.4 ms.
(d) 18 cells = 3 models × 3 startup times × 2 windows, with the model axis near-degenerate on burst6
(17 ms spread). Not 18 independent trials.
(e) The language side compares two **conversions** of the same held signal, not anticipation (sampled
bin runs ~60 s behind sim time).
(f) The burst6 anchor is the **C8** grid cell (735.318 ms), not the C6 cell (733.777) tabulated at
`baselines.tex:109`. State the C8 provenance or a reader will collide the two.

### 1.2 A16_ctrlcost — controller inference cost

**Verdict: upheld with correction.** Every arithmetic figure reproduces, and the numerator is
DB-confirmed (`provenance.ewma_ablation_cell`: ws 2,410,754.7 / denom 3,869,278.4 / ratio 0.6231 /
feasible=t). Three claims fail.

**PERMITTED SENTENCE** (anchored on static — the only feasible comparator):

> "Charging each controller its own measured inference cost does not disturb the provisioning result.
> On GPU the forecast arm moves from 0.623× to 0.624× of the deployable static fleet — controller duty
> cycle under 0.8% at a 15 s tick for every model tested. On CPU-class hardware, priced at $0.04/vCPU-h
> against $2.00/GPU-h over the 24 threads the forward occupies, the deployable configurations (Chronos,
> TimesFM) land at 0.65–0.66×, still well inside the 1.00× static baseline. Among the models measured,
> only Toto on CPU at a 15 s tick fails, and it fails on **feasibility** rather than cost."

Permitted **only with the infeasibility disclosure attached**, never bare:
> "…and remains below the reactive arm's 0.675×, **though that arm misses the burst3 episode SLA at
> 16,078.7 ms and so cannot itself carry a cost comparison.**"

**MANDATORY CAVEATS:**
(a) The CPU band is a **measurement multiplied by an assumed price ratio**. `cpu_gpu_price_ratio=0.02`
and `n_thr=24` appear only in `gen_a16_controller_cost.py:542`. The ordering against reactive **inverts
at price ratio 0.0286** — 1.43× headroom on an assumption, not on data.
(b) The reactive L=30 comparator fails burst3 at 16,078.7 ms vs a 1,000 ms bound
(`provenance.v_infraction`, all rows `is_violation=t`). Against static C=8 the margin is 10.4× the
largest charge.
(c) The 15 s tick is an **upper bound, not the replayed controller**: the 2,410,755 ws schedule is a
180 s stride-12 tiling, at which every CPU cell including Toto is feasible (duty ≤0.18) and all ratios
fall in 0.6256–0.6338.
(d) CPU latencies are medians of n=5 with up to 17% intra-cell spread. **Two significant figures only.**

**DELETE** the existing mandatory caveat about the encoder denominator being "pessimistic by
construction." It is true of the *level* but the ordering test is denominator-invariant (the denominator
cancels in `fc + charge < react + charge_react`), so it protects nothing and falsely implies slack.

### 1.3 G7_coldstart — cold start already billed

**Verdict: upheld with correction.** 9 of 12 confirmed. The **language half is the strongest single
result in the delivery** and is thesis-grade now. The L=165 flip is defence-only.

**PERMITTED — TIER 1, thesis text:**

> "The language-pool GPU-hour figures reported here already bill from instance **order** rather than
> readiness: the discrete-event mocker integrates the provisioned worker count — active, starting-up
> and draining alike — so the startup ramp and the drain tail are inside every reported number and no
> cold-start surcharge may be added. The encoder pool applies cold start by delaying availability and
> therefore bills from **readiness**, so a composed two-pool total mixes the two conventions and must
> state which applies to which pool."

(Verified from `collector.rs:44-52` plus a 52-run numeric discriminator: order-time integral reproduces
every reported GPU-hour to within 1.00%; a readiness-lagged counterfactual falls 3.5–38.0% short on the
reactive arms.)

**BLOCKED — the flip may not enter the manuscript.** The cost side is a strict-re-warm accounting; the
feasibility that licenses it is read off **warm-pool** simulations. No reactive strict-re-warm run
exists. This is the identical defect that retracted burst5. **To unblock:** run the reactive arm under
`--strict-rewarm` at L=165 on burst1 and steady24h and confirm both stay under 1,000 ms. The flag and
harness already exist (`verification/scripts/forecast_schedule_issuetime.py`).

**CORRECTIONS:** delete "previously undocumented" — `closedloop.tex:494-501` already carries the
encoder warm-pool vs strict-re-warm distinction and its 0.62×→0.59× consequence; only the **language**
convention and the **cross-pool contrast** are new. Delete "systematic" — flips occur in 2 of 5 windows,
2 of the 3 whose comparator is SLA-feasible, and only at L=165.
**STRENGTHEN two under-sold points:** the order overlay **over-charges** the forecast arm (real
strict-re-warm burst1-L165 = 525,643.5 ws vs the overlay's 559,267.5), so the printed ratios are
**upper bounds** and the flip holds *a fortiori* within the strict convention; and **the headline 0.62×
is untouched**, because its static-C8 comparator has no up-steps and therefore no readiness under-charge.
Say both explicitly — an examiner will otherwise assume the defect propagates.

**Standing-document corrections required (non-thesis files, safe to make):** `ADJUDICATION.md:877-880`
and `progress/results-ledger.md:546-547` still assert the burst5-L165 flip; `NEW-MEASUREMENTS.md:127-129`
has already been corrected. The corpus is currently self-inconsistent across three documents.

### 1.4 A16_decode — decode series characterisation

**Verdict: upheld with correction — the weakest evidence layer in the delivery.** The two headline
figures reproduce cleanly from the named arm (`ft_llm_static`: `output_vs_trace_rel_err` = 7.82e-07;
truth-selected top-1% bias −0.836%; arrival-selected +54.48%). **Twelve of twenty-five checked numbers
fail as stated:** eleven reproduce only from `timesfm_e2e` — the arm the card's own caveat (a) forbids —
and one (the "+4.8% de-smoothing" residual risk) reproduces from **nothing at all** and is directionally
contradicted by the generator's own docstring (`gen_a16_decode_spread.py:56-58`).

**PERMITTED SENTENCE** (correction to `intro.tex:504-505`):

> "The rate signals stamp each request's full token volume at its arrival minute. For encoder and
> prefill work this is faithful; for decode it is **not a pointwise upper bound**. The stamped decode
> series is exact in total volume (7.8e-7 of the replay over 1,000,000 requests) but displaces mass in
> time: on the busiest one percent of **fifteen-second** bins selected by the stamp itself it exceeds
> the realised decode rate by 54 percent, while on the busiest one percent selected by the realised
> series it falls short. Both figures shrink with bin width — at the planner's sixty-second interval
> the conservative figure is under three percent — and the sign of the bias over the population the
> controller actually samples spans zero, so the series licenses **no provisioning claim of either
> direction**."

**MANDATORY CAVEATS:**
(a) **Bin width is load-bearing.** +54% holds only at 15 s; at 1 s it is +329%, at the planner's actual
60 s interval it is **+2.9%**. The shipped artifact itself labels the 15 s verdict "NOT the controller's
cadence." The number must never appear without its resolution.
(b) The +54% is **selection error, not headroom**: the arrival-selected "busiest 1%" have a 24% lower
true rate (1085 vs 1435 tok/s) than the genuinely busiest 1%, and 18.8% of them (42.6% at 60 s) are
still short.
(c) The +54% is itself **inflated** by the uniform 1/itl spreading model, per the generator's documented
direction. This **replaces and reverses** the card's unsourced "+4.8% de-smoothing" residual risk, which
must be **struck** until an artifact exists.
(d) Every supporting number beyond the two headline figures must be **re-sourced to the ft_llm arms**.

**PROHIBITED:** "strongly conservative"; the +54% without its bin width; any onset ratio (2.796 or
3.406) presented as a property of the stamp; any safety-margin reading. Note caveat (b) should be
**strengthened**, not softened: the mass-weighted onset ratio collapses 2.80× → 1.04× under true-series
selection just as the median does, so the "load-bearing" 2.796 is equally a selection artifact.

### 1.5 A16_endogenous — endogenous demand

**Verdict: upheld with correction.** Every headline reproduces exactly against
`a16_runs/verification.json`. Three claims fail.

**PERMITTED SENTENCE:**

> "Under a mean-field client model (lognormal patience, mean 5 s; retry fraction 0.3) iterated around
> the unmodified discrete-event replay — abandonment resolved offline, not in-clock — the forecast arm's
> latency observables are invariant across every iterate (TTFT p99 651.1 ms), while the reactive arm
> oscillates over a two-phase envelope of TTFT p99 [1702, 1808] ms **over served clients only**, against
> ~10.6 s open-loop."

**MANDATORY CAVEATS:**
(a) Never write "closed loop" — mean-field and offline.
(b) Quote the **envelope**, never a single iterate, and never the midpoint.
(c) **NOT iso-cost:** 6.31–6.33 GPU-h forecast vs 1.06–1.10 reactive (5.7–6.0×).
(d) **NEW — survivor censoring.** `max_observable_percentile_of_offered` = 95.44–95.76 at the cycle vs
100.0 at iterate 0; `served_only_p99_is_censored_at_cycle` = true. The cycle p99 and the open-loop p99
are **not p99s of the same population**. The survivorship-immune figure is `e2e_p99_from_ingress`
[3514.7, 3936.9] ms — still ~2× the 2000 ms budget.
(e) **NEW — the endogenous feedback is near-nil.** `n_shed_at_encode` = 130 on every iterate from 1
onward and cannot respond to the iteration (`gen_a16_endogenous.py:511`). Residual endogenous effect is
11.0 and 1.1 clients — 0.36% and 0.036% of 3093 offered. **92–99% of abandonment is a one-shot
exogenous encoder shed.** The word "endogenous" overclaims without this.
(f) **NEW — scope is one cell pair:** burst3 only, one seed, one patience parameterisation. The
P2000/q0.6 sensitivity cells and `*_ondemand` controls exist but reached only 1–3 iterates.

**CORRECTIONS TO THE CARD:** it asserts the forecast arm has "abandonment 0.000" — it does not
(`abandon_rate` cycles [0.0, 0.0006]); only the *latency* observables are invariant. And
`A16_endogenous_CORRECTED.md:34` writes "10.6 s → ~1.75 s", which is exactly the **banned midpoint**
(1702.1+1808.4)/2 = 1755.25, and uses "RELIEVES … measured latency", the banned rescue framing. **The
JSON report is correct; the card violates its own report.** Precision: independent recomputation from
`provenance.llm_request` gives 1822.9 / 1704.1 / 11089.5 (floor-index) or 1814.1 / 1703.1 / 10615.0
(interpolated) — convention spread ~0.8% at the cycle, ~4.9% open-loop. **Do not quote to 0.1 ms**;
write "~10.6 s" and "[1.70, 1.81] s". Also: "both settle into a period-2 limit cycle" is **not supported
for the forecast arm** — its iterates 2 and 4, assigned the same phase, have gpu_hours 6.311 vs 6.328;
the state is still moving at the last iterate, and only `laps_verified = 1.0` was cleared.

### 1.6 G3_32b — dense 32B pricing

**Verdict: upheld with correction. R26 CLASS — post-manuscript defence material, not thesis results.**

**PERMITTED SENTENCE (defence Q&A only):**

> "On the head2k isolation window under the evaluation SLA, the dense 32B at TP2 knees near 2.3 offered
> req/s against the 8B-TP2's 16 — roughly a 7× gap at equal GPU count — and even at TP8, four times the
> silicon, reaches only about 10, still below 8B-TP2. Every knee is ITL-bound."

**MANDATORY CAVEATS:** (a) head2k only (2,000 requests, 721 s), the trace's lightest-tail slice, uniform
arrival-rate scaling, source-built runtime. (b) **Knees to 2 significant figures** — the SLA boundary is
non-monotone (8B-TP2: s=6.0 FAILS at ITL 102.19, s=6.0542 PASSES at 99.96, s=6.1089 FAILS at 102.29),
and the reported `bracket_rel_width` = 0.0127 is **finer than the demonstrated wobble**. (c) State
offered **or** achieved units consistently, never mixed — `points/*.json` field `offered_req_per_s`
actually holds **achieved** throughput. (d) The runtime divergence is a function of **distance from the
knee**, not of arm; the artifact's "specific to 235B-TP8" assertion is false and corrected.

**R26 is respected:** the only 32B rows are post-manuscript. This may not be retro-fitted into a results
chapter, and `twopool.tex:391` ("32B were not priced") **stands as written**.

### 1.7 G6_sizesens — image size × fabric

**Verdict: upheld with correction.** All numbers reproduce exactly from raw shipped stats; the
repricing is genuine (AIC's own ops against the real `rtx_5090/vllm-0.22.0` perf DB), and the 448@25G =
588.37 ms anchor holds for the right structural reason (f(64) 316.369 + handoff 272.001, queueing
exactly 0). Corrections are all to framing.

**PERMITTED SENTENCE** — the card's own "What may be written" block is accepted **as written**, with
one strengthening: lead with the structural finding, not the crossing.

> "Image sizes are not recorded, so the uniform-448 assumption can only be stress-tested. Repricing the
> encoder through the collected RTX 5090 operator database at other resolutions, the verdict holds at
> 448 and below on both modelled fabrics; the closed-form service floor f(64) + 272 ms × (px/32)²/196
> places the crossing near 690–705 px on a 100 Gbps link, so the assumed resolution sits just below it.
> Because the p90 schedule is driven by image **count** it is blind to **size**, and a size increase
> produces no provisioning response at all — unlike the engine-cost gap, which the p90 headroom absorbs
> with no added workers. The 25-versus-100 Gbps difference at 672 px reflects the single-stream handoff
> assumption as much as line rate."

**MANDATORY CAVEATS:** (a) **448 graded cells**, not 456 (456 is a file count including 8 orphans).
(b) The 672 "fabric rescue" passes by only **6.1%** (938.734 vs 1000 ms) and is a **single-stream
serialization** result, not a line-rate one — that assumption contradicts the simulator's own dispatch
model for the very request that sets the p99. (c) **896 cells are extrapolated** beyond the collected
batch axis (b stops at 32); 448 and 672 are inside the collected box. (d) All size distributions are
**assumed** — the trace records counts only.
**Note:** `provisioned_worker_s` is invariant at 32,228.0 across every burst3 cell and both fabrics.
This size-blindness is the track's most useful finding and should lead.

### 1.8 G4_folds — temporal fold generalization  ⟵ **HIGHEST STAKES**

**Verdict: upheld. Every number independently re-derived for this ruling from
`defense/anim/data/g4_folds/results.json` — all reproduce exactly.** See §5 for the thesis conflict.

Re-derived here (encoder, forecast ρ=15 vs static C8):

| fold | fc ws | C8 ws | ratio | fc pass | C4 p99 | C4 pass | C\* | ratio vs C5 |
|---|---:|---:|---:|:--:|---:|:--:|:--:|---:|
| F1 | 449,871.6 | 689,726.4 | 0.652 | ✓ | 993.8 | ✓ | 4 | 1.044 |
| F2 | 215,713.0 | 691,184.3 | 0.312 | ✓ | 367.9 | ✓ | 2 | 0.499 |
| F3 | 321,291.0 | 691,202.4 | 0.465 | ✓ | 838.5 | ✗(queue) | null | 0.744 |
| F4 | 664,391.3 | 691,172.0 | 0.961 | ✓ | 1207.8 | ✗ | 5 | 1.538 |
| F5 | 129,550.8 | 691,166.6 | 0.187 | ✓ | 261.0 | ✓ | 2 | 0.300 |
| F6 | 419,391.2 | 691,146.4 | 0.607 | **✗** | 1024.6 | ✗ | 5 | 0.971 |
| F7 | 759,099.7 | 691,195.7 | **1.098** | ✓ | 1261.8 | ✗ | 5 | 1.757 |
| FULL | 2,962,304.8 | 4,836,959.7 | 0.612 | ✓ | 993.8 | ✓ | 4 | 0.980 |

Anchor exact: enc p99 588.4 = 588.4; provisioned_ws 2,962,304.8; ratio 0.612 vs ledgered 0.6124.
Language pool re-derived: forecast/static GPU-h = F1 1.276, F2 1.101, F3 0.931, F4 1.709, F5 3.808,
F6 1.022, F7 2.144 — **and the static arm passes in all seven folds.**
ρ frontier re-derived: cheapest feasible ρ = **25** in FULL/F1/F2/F3/F4/F7, **20** in F5, **10** in F6.
ρ=15 is nowhere cheapest — confirmed.

**PERMITTED SENTENCE:** the card's own "What may be written" block is accepted with **one deletion and
one addition**:

> "Split into seven disjoint 24-hour folds, the headline quantities are not fold-invariant. The encoder
> cost ratio against the deployed C=8 fleet ranges from 0.47× to 1.10× across burst-bearing folds
> around its 0.62× whole-span value, and the forecast policy misses the bound on the fold containing
> the e13 onset — a fold on which a **static C=5 fleet passes at 904.7 ms for only 3% more
> worker-time**. The ρ frontier retains its shape in every fold, but ρ=15 is nowhere the cheapest
> feasible setting **among the four values swept**. On the language pool the forecast is dearer than a
> feasible static fleet in six of seven folds. The single-span averages are therefore representative of
> the span, not of an arbitrary day within it."

**MANDATORY CAVEATS:** (a) This is the **A15 expanding-context span** (999,599 req, 6.998 d), **not**
the 5.60-day span the 0.62× headline is priced on — the ratios coincide (0.612 vs 0.62), the absolute
worker-seconds do not (2.96M/4.84M vs 2.41M/3.87M). (b) Fold conditioning is **nested** (a fold-5
forecast is conditioned on folds 1–4), so folds are disjoint **test** windows but not
training-independent. (c) F3's static rungs are flagged FAIL by a hair-trigger queue-divergence
criterion (`q_end` 17 vs median ≤1, `trace_to_two_pool.py:537`) and F3 is silently dropped from the
cost-vs-C\* range. (d) One trace, one datacenter, one 7-day record; folds share tenant mix, size
distribution and hardware calibration, differing only in time. (e) The language anchor was **not** run;
only the encoder anchor is verified.

---

## 2. CORRECTIONS TO THE DELIVERY

Ordered by severity. This is peer review.

**C1 — `00-CONSOLIDATED.md` item 1, caveat (d): "40 distinct configurations, not 42" is WRONG.**
The two cells differ in `STARTUP_TIME` (60 vs unset). Write **42 configurations / 30 language cells**.
Delete the sentence "the duplicate-cell replicate proves the mocker is bit-deterministic" — the data
says the opposite (34 of 68 keys differ; burst2 p99 TTFT 745.359 vs 745.905).

**C2 — `00-CONSOLIDATED.md` item 1: "reproduce the ledgered p99 bit-identically" is over-scoped.**
Only p99 **TTFT** reproduces. Insert "TTFT". Do not quote "−35.018 ms" / "−20.359 ms" — those are the
driver's **rounded-input** subtractions (`gen_g1_burst26.py:381-384`); the exact deltas are −34.978
(−4.757%) and −20.355 (−2.656%).

**C3 — `00-CONSOLIDATED.md` items 2 and 3 apply OPPOSITE STANDARDS and are mutually inconsistent as
shipped.** Item 3 (G7) retracts a result because "an infeasible arm cannot carry a cost comparison";
item 2 (A16_ctrlcost) builds its headline on a reactive arm that misses the bound by **16×**. A
committee reading both will see it. Apply the G7 standard uniformly.

**C4 — `00-CONSOLIDATED.md` item 2: the mandatory caveat protects the wrong quantity.** The
encoder-denominator caveat is true of the *level* and irrelevant to the *ordering*, which is
denominator-invariant. It buys zero insurance and implies slack that does not exist. Replace with the
price-ratio and infeasible-comparator caveats (§1.2 a–b).

**C5 — `A16_ctrlcost_FINAL.md`: "The only configurations that would erase the margin are ones that
cannot hold their own tick period" is FALSE as a universal.** Derived erasure threshold is 12.96 s per
tick (duty 0.864) against a 15 s period, so the band (12.96, 15.00) s is **both feasible and
margin-erasing**. It is non-empty; the three benchmarked models simply happen to land at duty ≤0.60 or
≥1.95. Rewrite as an existential over the measured models.

**C6 — `A16_decode_FINAL.md`: eleven load-bearing numbers come from `timesfm_e2e`, which the card's own
caveat (a) disqualifies.** Specifically: the onset figures (2.796, 3.406), decay 0.506,
`frac_bins_short` 56.7%, shortfall p90 249.6, shortfall max 909.8 / 71.5%, `frac_bins_under` 12.19%,
the entire controller-cadence block (+2.17/−1.59/−3.56/−1.53 and +1.27/+4.67/+0.04/−9.43), and "403 of
40,316 bins" (the ft_llm series have 40,324 bins). **Re-source all of these to `ft_llm_static` /
`ft_llm_reactive` or delete them.**

**C7 — `A16_decode_FINAL.md`: the "+4.8% de-smoothing" residual risk has NO artifact and is
directionally backwards.** No de-smoothing code path exists; the generator's docstring states the
opposite direction. **Strike it** and replace with §1.4 caveat (c).

**C8 — `00-CONSOLIDATED.md` item 4: "strongly conservative on the bins an operator can actually
identify" is undercut by the card's own controller section.** The operator decides at **60 s**, where
the figure is +2.9% and 42.6% of the flagged-hottest bins are still under-stated. Delete "strongly
conservative."

**C9 — `A16_endogenous_CORRECTED.md:34` violates its own report** (banned midpoint 1.75 s; banned
"RELIEVES … latency" framing). Rewrite to the envelope form. Also correct "abandonment 0.000" for the
forecast arm.

**C10 — `00-CONSOLIDATED.md` item 5: "both settle into a period-2 limit cycle" is unsupported for the
forecast arm** (iterates 2 and 4 at the same phase differ: gpu_hours 6.311 vs 6.328;
`laps_verified` = 1.0). Say "the reactive arm settles into a two-phase envelope; the forecast arm's
latency observables are invariant while its cost is still drifting at the last iterate."

**C11 — `G7_coldstart_FINAL.md`: "previously undocumented" is false** — `closedloop.tex:494-501`
already carries the encoder dual accounting. And "systematic across windows" is 2 of 5 windows / 2 of 3
eligible. Both must go.

**C12 — `G4_folds_FINAL.md`: "ρ=15 is nowhere the cheapest feasible setting" needs a grid caveat.**
The sweep is {10, 15, 20, 25}; the optimum sits at a **grid endpoint in 7 of 8 folds** (ρ=25 in six,
ρ=10 in F6). The true optimum may lie beyond 25 and is untested. Write "nowhere the cheapest **among the
four values swept**."

**C13 — `G4_folds_FINAL.md` omits its own strongest fact.** On F6 — the fold where the **forecast arm
fails** at 1262.3 ms — a **static C=5 fleet passes at 904.7 ms** for 431,967 ws against the forecast
arm's 419,391 ws, i.e. the forecast is only **3.0% cheaper and infeasible**. Add it. It is the encoder
counterpart of the language-pool inversion and materially strengthens the fold caveat.

**C14 — `00-CONSOLIDATED.md` item 3 undersells two defensible points** (the order overlay over-charges
the forecast arm, so the flip holds *a fortiori*; the headline 0.62× is untouched because static C8 has
no up-steps). Both should be stated affirmatively.

**C15 — precision hygiene, delivery-wide.** Four-significant-figure ratios are quoted off n=5 wall-clock
medians (A16_ctrlcost 0.6537/0.6593), off a non-monotone SLA boundary (G3 knees to 5 s.f.), and off a
percentile-convention spread of 0.8–4.9% (A16_endogenous 1808.4). **Two significant figures** unless the
underlying spread is demonstrated smaller.

---

## 3. THE THREE DEFECTS — RULING

### DEFECT 1 — `twopool.tex:78` "307 / 882"  →  **REJECTED as diagnosed; a DIFFERENT defect confirmed**

**Ruling: the proposed fix is REFUTED. Do not requote 882 → 783.**
`simulation/results/235b/llm_head2k_aic235btp8_s{1,4,16}.json` are all **old-schema (wheel)**, written
07-06 21:52, carrying the wheel `max_ttft` signature. The published 398 / 1,402 / 14.9 / 7.9 / 87.7 all
match wheel values to the digit. **The entire Family-transfer paragraph is wheel on both arms —
internally consistent, not mixed.** "307" coincides with srcbuild's 307.36 only because the runtimes
agree to 0.2% at s=1. Substituting 882 → 783 would **create** the mixing defect it claims to fix.

**Two real defects instead:**

**1a — `twopool.tex:69`, "extreme tail only (identical p99)" over-generalises.** True at s=1 (+0.2%),
false at s=2 (−5.7%), s=4 (−11.3%), s=16 (+22.1% TTFT / −61.1% ITL).
**Replacement text:**
> "…inflated the extreme tail (identical p99 at $s{=}1$; the two runtimes diverge with distance from
> the knee, by up to 22\% in TTFT p99 and 61\% in ITL p99 at $s{=}16$)."

**1b — the 4× column is indefensible (the delivery missed this).** The source build gives the 235B
**20,032.8 ms** against the published **1,402 ms** — a 14.3× divergence on the same 2,000 requests, same
tokens, comparable e2e p99 (72.7 vs 69.0 s). That is systematic TTFT accounting divergence under
queueing, not a tail effect.
**Ruling: DELETE the 4× column. Keep the 1× pair** (agrees ≤2.7% across runtimes). Deleting rather than
substituting **respects R26** — the source values live in post-manuscript `g3_32b/`.

**Rejected-fix check:** consistent with **R4/R12** (`tab:sim-poly-aic` independently re-confirmed at
68.23 / 307.36 / 4517.57 / 141.95 — untouched) and with **R26**. No collision.

### DEFECT 2 — `sweeps/reports/` runtime-mixed  →  **CONFIRMED; evidence wrong, scope too narrow**

**Ruling: the conclusion is CONFIRMED; the delivery's stated proof is FALSE and must not be repeated.**
`llm_head2k_aic_s3`'s `max_ttft` 4543.39 is **not** "identical to the source build" — srcbuild reads
4517.57. It matches `g3_32b/8b_tp1_s3` to the digit (74-key identical schema, 29 bit-identical fields,
rest ≤0.3%). Right conclusion, wrong comparison. And there are **four** source-schema files, not one —
all three `llm_burst1_aic_*` were missed. **mtime is not the discriminator** (`llm_head2k_poly_s3` is
07-08 and old-schema); the `gpu_hours` key set is.

**Impact:** `sweep_curve (llm, head2k, aic)` crosses the runtime boundary — its s=3 point sets the knee.
**The knee is robust:** ITL 109.51 (ingested) and 108.48 (source rerun) **both breach** the 100 ms bound;
s=2 passes either way; the independent fine sweep brackets it at s=2.8158.
`tab:sim-knees` is affected **in provenance only** — its steady AIC row is wheel while its burst row and
the 748 ms caption figure are source.

**Ruling: NO NUMERIC EDIT.** Required actions are (i) a caption disclosure that the sweep set is not
runtime-homogeneous, and (ii) a `runtime` column backfill on `provenance.sweep_point`.
**Rejected-fix check:** no collision. R4/R12 are srcbuild-backed and untouched.

### DEFECT 3 — `intro.tex:148` / `:504` "upper bound"  →  **CONFIRMED; supporting stats disqualified**

**Ruling: CONFIRMED — both sites need editing.** But the delivery's headline support does not survive:
**"understates 58% of bins" is the `timesfm_e2e` figure and does not reproduce.** `ft_llm_static` gives
**47.7%**, `ft_llm_reactive` **47.3%** — a *minority*; the stamp **overstates** 52%.

**What holds:** not-a-pointwise-bound (55.5% / 57.9% of truth-selected top-1% bins short; worst 934.7
tok/s = 72.0% of its own bin); arrival-selected +54.48% / +55.60% (spread 1.22 pp — "within 1.2 pp" is
at the rounding edge, so write "within 1.3 pp"); volume fidelity 7.82e-07.

**Replacement text — `intro.tex:504-505`:** use the §1.4 permitted sentence, ft-arm ranges only, bin
width stated, no provisioning claim.
**Replacement text — `intro.tex:148` (parenthetical only):**
> "(measured as offered work stamped at arrival; faithful in total volume but temporally displaced, not
> a pointwise upper bound --- see Section~X)"
Note `:148`'s surrounding claim (R² 0.654 constant-fraction fit) does **not** depend on the bound being
pointwise, so only the parenthetical changes.

**Rejected-fix check:** no collision. **R23** (`predictors.tex:382` WAPE — "an upper bound is not a
defect") is about a different sentence and does **not** shield `intro.tex`'s decode phrasing.

### 3.1 RECORD CORRECTION — R13 (not a re-opening)

**R13 must be left standing; its citation is stale.** ADJUDICATION cites `misc:235b_tp8_s2` ITL p99 =
**213.044 ms**. The current post-`--force` artifact reads **210.5878500000108 ms** (verified this
session from `g3_32b/reports/235b_tp8_s2.report.json`) — stale by 1.2%. **The conclusion is unaffected**
(210.6 ≫ the 100 ms bound; the knee remains MEASURED and must not be hedged). Those runs are now keyed
`g3_32b:235b_tp8_%`, not `misc:`. **Action: update the citation in ADJUDICATION.md; do not re-open R13.**

### 3.2 Rejected-fix collision audit — summary

| Rejected fix | Touched by this delivery? | Ruling |
|---|---|---|
| R4 / R12 — `tab:sim-poly-aic` srcbuild-backed | No — independently re-confirmed | No collision |
| R13 — 235B knee measured | Citation only | Record correction; fix stands |
| R25 — 2.25× = (672/448)² | No | No collision |
| R26 — "32B were not priced" | Yes, adjacent | **Upheld.** G3 is post-manuscript; `twopool.tex:391` stands as written |
| R45 — `aiconfigurator.tex:444` | No | Remains BLOCKED pending the author |

**No proposal in this delivery re-opens a rejected fix.**

---

## 4. WHAT MAY ENTER THE THESIS — TIERED

### (a) CORRECTIONS TO EXISTING TEXT — approved, make these

1. `intro.tex:504-505` and `:148` — replace "offered-work upper bound" per §3 Defect 3.
2. `twopool.tex:69` — replace "extreme tail only (identical p99)" per §3 Defect 1a.
3. `twopool.tex:78` — **delete the 4× column**, keep the 1× pair, per §3 Defect 1b.
4. `tab:sim-knees` caption — disclose that the sweep set is not runtime-homogeneous. **No numeric edit.**
5. **Do NOT** apply the proposed 882 → 783 requote. It is refuted.

### (b) CLAIMS THAT STRENGTHEN AN EXISTING RESULT — approved with caveats

1. **G7 language-pool billing convention (Tier 1, strongest item in the delivery).** Cold start is
   already inside every reported language GPU-hour; the pools use opposite conventions. Code-verified
   plus a 52-run numeric discriminator. Enter as thesis text per §1.3.
2. **G6 size sensitivity** — closes a stated Scope limitation. Enter per §1.7 with all four caveats.
3. **G4 fold variance** — enter as a **qualification** of the generality claim, per §5. This
   *strengthens* the thesis by making the single-span scope explicit; it does not weaken the headline.
4. **A16_ctrlcost, static-anchored form only** — the controller's own inference cost does not disturb
   the provisioning result against the static baseline. Per §1.2, price basis stated.

### (c) NEW POST-MANUSCRIPT DEFENCE MATERIAL — Q&A / appendix ONLY, never a results chapter

All artifacts dated 2026-07-19/20, after the manuscript. Several are absent from
`provenance.ingest_log` entirely (`a16_decode`: 0 rows; `a16_controller_cost`: file-only, 0 rows in
`analysis_artifact`).

1. **G3_32b — the 32B pricing. Explicitly this class per R26.** `twopool.tex:391` stands.
2. **G1_burst26** — gradability of burst2/6. Closes a stated structural limitation
   (`closedloop.tex:599-602`); the framing the data licenses is **gradability, not superiority**.
3. **A16_endogenous** — one cell pair, mean-field, offline.
4. **A16_ctrlcost** — file-only provenance.
5. **G7's L=165 cost-order flip** — **BLOCKED** even as defence material in the delivery's wording;
   admissible only in the §1.3 hedged form, and unblockable by one small re-run.
6. **A16_decode's +54%** — admissible as a **correction that weakens an existing claim** (which needs no
   new provenance), but **not** as a new positive result until re-sourced to the ft_llm arms and ingested.

### (d) DO-NOT-WRITE

- "40 distinct configurations"; "the mocker is bit-deterministic"; "reproduces the ledgered p99
  bit-identically" without "TTFT"; "−35.018 ms" / "−20.359 ms".
- Any sentence pairing G1's 17/18 with 0/6 that does not name **the static baseline's pass**.
- "The only configurations that would erase the margin are ones that cannot hold their own tick period."
- "0.65–0.66×, still below the reactive baseline's 0.675×" as a standalone headline; any four-digit CPU
  ratio; any phrasing implying the CPU result is measured rather than measured-**and-then-priced**.
- "Strongly conservative"; the +54% without its 15 s bin width; any onset ratio as a property of the
  stamp; any decode safety-margin or provisioning-headroom reading.
- "Closed loop" for A16_endogenous; any single iterate or the 1.75 s midpoint; "rescued".
- Any language-pool **cold-start surcharge**; the 0.28–0.74× number; the burst5-L165 flip; any language
  churn number at a flat 60 s startup; `warmup_frac` from either store until the denominator is
  reconciled (artifact uses `total_from_order_ws`, DB uses `provisioned_ws`).
- **"The baseline is 2× oversized"** — G4 does not license it (see §5).
- "Previously undocumented" about the encoder readiness convention.
- Anything at all from the dropped `g2_conventions` track.

---

## 5. CONFLICTS WITH THE EXISTING THESIS  ⟵ **the highest-stakes item**

### 5.1 G4 vs the 0.62× headline — what the thesis MAY still claim

**The headline is NOT threatened. Its GENERALITY is.**

`closedloop.tex:478-481` currently reads: *"the p90-forecast schedule meets the tail SLA over the
aggregate **and** inside every in-span episode at 0.62 times the deployable static encoder fleet's
provisioned worker-time."*

**This sentence remains true exactly as written and needs no numeric edit.** It is a claim about a
named span (5.60 continuous days, 749,601 requests), it names its denominator ("deployable"), and it is
anchor-exact — G4's own harness reproduces the ledgered endpoint to the digit (588.4 ms; 2,962,304.8 ws;
0.612 vs 0.6124).

**What must now be qualified** — the surrounding language that implies the ratio is a property of the
policy rather than of the span:

| Currently implied | Must become |
|---|---|
| 0.62× is what the policy costs | 0.62× is a **span average**; day-by-day it ranges **0.47×–1.10×**, and on one fold the forecast is **dearer** than the deployed static fleet |
| The forecast policy passes | It passes **in-span**; split into 24-h folds it **misses the bound on the fold containing the e13 onset** (1262.3 ms) |
| ρ=15 is the calibrated operating point | ρ=15 is **feasible everywhere and cost-optimal nowhere** among the four values swept; at FULL, ρ=25 costs 0.39× at p99 783.8 ms, still inside the bound. ρ=15 is **conservative, not optimal** |
| the "4×/2× over-provisioning" (`closedloop.tex:1076`) | **Do not restate the 2× from G4.** The fold-robust static optimum is **C\*=5**, giving 8 vs 5 = **1.6×** — and that is measured on the **A15 7.0-day span**, not the 5.60-day headline span |

**The Limitations sentence at `closedloop.tex:1076-1078` should be upgraded, not deleted.** It currently
says generalization "is unaddressed." G4 **partially addresses** it — within-trace temporally — and the
honest replacement is:

> "…derives from a single Azure production trace. Within that trace, a seven-fold 24-hour split shows
> the cost ratio is not fold-invariant (0.47×–1.10× against the deployed fleet), that ρ=15 is feasible
> in every fold but cheapest in none, and that the policy misses the bound on the fold containing the
> e13 onset. Generalization to other workloads, models, and datacenters remains unaddressed."

**Do NOT overstate the fold result beyond its own caveats.** Three limits are binding and must travel
with any fold claim: (i) it is the **A15 7.0-day span**, not the 5.60-day headline span — the ratios
coincide, the absolute worker-seconds do not; (ii) fold conditioning is **nested**, so folds are
disjoint *test* windows but not training-independent; (iii) **one trace**, folds differing only in time,
sharing tenant mix, size distribution and hardware calibration. G4 is evidence about **temporal**
variability within one trace and about **nothing else**.

### 5.2 The convergent finding neither card states — static dominance on the language pool

**This is the delivery's most consequential omission and it appears in two independent tracks.**

- **G1 (burst2, burst6):** static C=8 (two replicas, no planner) passes both bounds on both windows at
  7.598 / 5.468 GPU-h — **2.9×–4.9× cheaper than every forecast cell.**
- **G4 (all seven folds):** the language static arm **passes in all seven folds**, and the forecast arm
  costs **1.02×–3.81×** as much in six of them (only F3 at 0.931× is cheaper).
- **G4 (encoder, F6):** on the one fold where the forecast arm **fails**, static C=5 **passes** at
  904.7 ms for only **3.0% more** worker-time.

**Ruling:** the thesis's encoder-pool result (RQ4, `closedloop.tex:1082+`) is **unaffected** — that
result is about the encoder pool, where the forecast schedule genuinely beats both static and reactive
on the covered span. But **no language-pool cost advantage may be claimed for forecasting anywhere in
the thesis or the defence**, and any sentence contrasting forecast with reactive on the language pool
must name the static baseline's pass. G1's and G4's language results are consistent, mutually
reinforcing, and point the same way.

**AMENDED 2026-07-25 (see `S5_2_LANG_RECONCILE.md`; DB-backed, `experiment='langcalib'`).** This ruling
is correct **for the operating point it measured — the published Chronos p90/scale-8 arm** (1.02×–3.81×
across folds). It is **scoped, not retracted**: under honest held-out calibration (operating point
selected on the 1.4-day forecast-context split, graded held-out) the language pool **does** clear static
— a cost-optimal point near **0.62×** (which drops the e13 fold) and an **e13-robust point at 0.82× time
/ 0.87× request** (p90 quantile at a leaner conversion scale, passing all 7 daily folds, e13 = 886 ms).
So *"no language cost advantage may be claimed anywhere"* softens to *"the published p90/s8 arm is
static-dominated; an honestly-calibrated e13-robust point modestly beats static (~0.82×) — the advantage
modest and fold-variant, and the larger 0.62× drops the e13 onset."* The encoder RQ4 result is unchanged.

### 5.3 Other standing conflicts

- **`closedloop.tex:494-501`** already documents the encoder warm-pool vs strict-re-warm duality. G7's
  novelty claim conflicts with the thesis's own text — resolve in favour of the thesis.
- **`ADJUDICATION.md:877-880`** and **`progress/results-ledger.md:546-547`** still assert the burst5-L165
  flip that G7 correctly retracts. Amend both while preserving the conclusion ("0.62× is conservative"
  survives on burst1/steady24h).
- **`ADJUDICATION.md` §3.1 line 641** warns that "roughly two-thirds" collides with the reactive 0.67×
  row. A16_ctrlcost's quotable sentence **reintroduces that collision** by putting 0.675× and 0.65–0.66×
  in one breath. Honour the existing warning.
- **`twopool.tex:432`** ("a both-conventions sensitivity run remains future work") **STANDS AS WRITTEN** —
  the g2 track was correctly dropped.
- **`ADJUDICATION.md` line 819** ("do not restate 0.62× against the 99.96% span") is respected
  throughout; note G4 is priced on the **6.998-day A15 span**, a third span again — label it explicitly.

---

## 6. RESIDUAL RISK — stated as unverified

1. **G7's L=165 flip rests on an untested comparator.** No reactive strict-re-warm run exists anywhere.
   Given burst4's warm-pool reactive is already at 904.7 ms and burst5's fails at 3,250 ms, this is not
   hypothetical. **Unverifiable without the re-run.**
2. **A16_ctrlcost and A16_decode have no DB provenance.** `analysis_artifact` matching
   `%controller_cost%` = 0; `ingest_log` matching `%a16_decode%` = 0. Reproducible from named files
   only; no independent SQL path. Their numbers cannot be cross-checked against `v_pool_latency`,
   `v_cost_ratio`, or `grid_window_effective`.
3. **The CPU-class cost conclusion is one pricing assumption away from inverting** (flip at ratio
   0.0286 vs the assumed 0.02). No market-rate justification for either number exists in the artifact.
4. **G4's language anchor was never run** (~2 h full-span replay). Only the encoder anchor is verified,
   so the language fold ratios rest on an unanchored harness — though the encoder anchor's exactness is
   good indirect evidence for the shared converter.
5. **G4's F3 is silently dropped** from the cost-vs-C\* range by a queue-divergence hair trigger. The
   criterion should be span-length-aware, or folds cut at a drained instant. Until then the reported
   cost-vs-C\* range (0.971×–1.757×) is over a 6-fold subset presented as 7.
6. **The ρ frontier optimum sits at a grid endpoint in 7 of 8 folds.** The true cost-optimal ρ is
   outside the swept range and unmeasured. "ρ=15 is nowhere cheapest" is safe; "ρ=25 is optimal" is not.
7. **G6's 896 px cells are extrapolated** beyond the collected batch axis, and the 672 px "fabric
   rescue" depends on a single-stream handoff assumption that contradicts the simulator's own dispatch
   model. The fabric crossing (690–705 px) is bracketed by the ladder, not located by it.
8. **G3's knees sit on a non-monotone SLA boundary** with 0.9–7.6% ITL wobble exceeding the reported
   bracket width. Two significant figures is the honest resolution; the ordering (32B-TP2 ≪ 8B-TP2) is
   robust, the knee locations are not.
9. **A16_endogenous covers one cell pair.** The P2000/q0.6 sensitivity cells and `*_ondemand` controls
   exist but reached only 1–3 iterates. Neither arm is demonstrated to have converged: the forecast
   arm's cost was still drifting at the last iterate.
10. **G1's runtime offset is measured from a single build pair** (n=1 replicate, spread 0.55 ms). The
    2.7–4.8% correction is real but its uncertainty is uncharacterised.
11. **Percentile convention is not fixed across the corpus.** Floor-index vs interpolated p99 differ by
    0.8% at the A16 cycle and 4.9% on the open-loop anchor. Until one convention is enforced, no p99
    should be quoted to 0.1 ms.
12. **`warmup_frac` has two live denominators** (`total_from_order_ws` in the artifact,
    `provisioned_ws` in `provenance.cost_accounting`) for the same named column. Unreconciled.
