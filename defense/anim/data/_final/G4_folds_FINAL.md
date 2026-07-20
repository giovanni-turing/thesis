# G4 — within-trace temporal fold generalization (8 folds incl. FULL anchor)

Target: tex/closedloop.tex Limitations — "every quantity here (the 4x/2x over-provisioning, the
rho frontier, the 0.62x) derives from a single Azure production trace over one 5.60-day span;
generalization ... is unaddressed." This tests TEMPORAL generalization WITHIN the trace only.

## THE HARNESS IS TRUSTWORTHY: the anchor reproduces the ledgered endpoint exactly
| check | got | ledgered | ok |
|---|---:|---:|:--:|
| enc_p99_ms | 588.4 | 588.4 | ok |
| provisioned_ws | 2,962,304.8 | 2,962,304.8 | ok |
| ratio_vs_C8 | 0.612 | 0.6124 | ok |
Everything below rests on a harness that reproduces the thesis endpoint to the digit.

## FINDING 1 (CORRECTED after round-3 audit) — C=4 is a POOLED-TAIL ARTIFACT
The whole-span ladder does show C=4 clearing the AGGREGATE encoder-delay bound (993.8 ms, 0.6%
margin, not queue-divergent), so C=8 is not the whole-span aggregate optimum. My earlier
conclusion — "against C*=4 the forecast costs 1.225x, i.e. more than the static optimum" — is
WRONG, and the refutation is in G4's own results.json.

**C=4 FAILS 3 of the 5 burst-bearing folds** (per-fold enc_static_C4 p99):
  F1 994 PASS · F2 368 PASS · F3 838 (FAIL, queue flag — see defect note) · **F4 1208.5 FAIL**
  · F5 261 PASS · **F6 1025 FAIL** · **F7 1262 FAIL**
A burst touching a few thousand of 999,599 requests cannot move the pooled 1% tail, so the
aggregate 993.8 ms hides the episode-level failures. The thesis grades aggregate AND per-episode
(tex/closedloop.tex:482) — a C=4 fleet does not meet that standard and is therefore NOT
deployable under the thesis's own criterion.

**The fold-robust static optimum is C* = 5**, not 4 and not 8 (per-fold C_star: F1 4, F2 2,
F3 null, F4 5, F5 2, F6 5, F7 5). Against C=5 the forecast schedule costs
  2,962,304.8 / 3,023,099.8 = **0.980x — still cheaper.**
So the honest statement is 0.980x, not 1.225x. The residual unjustified headroom in the deployed
fleet is **8 vs 5 = 1.6x**, not the 2x that C*=4 would imply.

**SPAN CAVEAT — this does not test the headline span.** G4's FULL fold is the A15
expanding-context span: 999,599 req, 604,620 s = 6.998 days, C8 = 4,836,959.7 ws. The thesis
0.62x headline is priced over 749,601 req / 5.60 continuous days (2.41M vs 3.87M ws;
tex/closedloop.tex:431,438,469). The two ratios coincide (0.612 vs 0.62) but the spans and
absolute worker-seconds differ, so Finding 1 does NOT establish anything about whether C=8 was
optimal on the span the headline is actually computed over.

**Verified fair (my own suspicions were wrong):** all rungs and the forecast arm share
sim_horizon_s to the millisecond, the same offset/request count, the same converter and encoder
cost model, and the same SLA predicate. Billing is symmetric — static is billed C x t_end
(trace_to_two_pool.py:524) and the schedule is integrated over the SAME window (:526-529), with a
hard error unless the first step is at t=0 (verified sched[0] == [0.0, 1]), so the forecast arm's
30 s cold-start IS paid. There is no cold-start asymmetry and 2,418,480 = 4 x 604,619.95 exactly.

## FINDING 2 — 0.62x is a SPAN AVERAGE that does not hold fold-by-fold
Cost vs C8 across burst-bearing folds: **0.465x .. 1.098x** (whole-span headline 0.62x).
F7 = 1.098x — the forecast is DEARER than the deployed static fleet on that fold. F4 = 0.961x.
Cost vs each fold's own refit optimum C*: **0.971x .. 1.757x**.
=> `cost_ratio_below_1_in_every_burst_fold` = **False**.

## FINDING 3 — rho=15 is feasible everywhere but cost-optimal NOWHERE **among the four values swept**
`rho15_is_cheapest_feasible_in_every_burst_fold` = **False**, contradicted in ALL SEVEN folds and
in FULL. Cheapest feasible rho is 25 in FULL and F1-F4/F7, 20 in F5, 10 in F6. At FULL, rho=25
costs 0.39x vs rho=15's 0.61x at an encoder p99 of 784 ms — still inside the bound.
The frontier SHAPE is stable (`rho_frontier_shape_stable` = True); it is the CHOICE of 15 that is
conservative rather than optimal. Reported, not suppressed.

**GRID CAVEAT (mandatory).** The sweep is only {10, 15, 20, 25}, and the reported optimum sits at
a **grid ENDPOINT in 7 of 8 folds** (rho=25 in six, rho=10 in F6). The true cost-optimal rho
therefore lies outside the swept range in most folds and is **unmeasured**. Write "rho=15 is
nowhere the cheapest feasible setting **among the four values swept**" — that is safe. "rho=25 is
optimal" is **not** supported and must not be written.

## FINDING 4 — the forecast policy fails one fold
`forecast_passes_every_burst_fold` = **False**. F6 (containing e13 and e16) fails at encoder p99
1262.3 ms and fails E2E. Consistent with e13 being the known mechanism boundary.
Reactive fails four folds (F1, F4, F6, F7) — `reactive_fails_at_least_one_burst_fold` = True.

### FINDING 4b (NEW, AND THIS TRACK'S STRONGEST FACT — it was omitted)
**On F6 — the one fold where the forecast arm FAILS — a forecast-free static C=5 fleet PASSES.**
Re-derived from g4_folds/results.json:

| F6 arm | encoder p99 | provisioned ws | verdict |
|---|---:|---:|:--|
| forecast rho=15 | 1262.3 ms | 419,391.2 | **FAIL** |
| static C=5 | **904.7 ms** | 431,967.3 | **PASS** |

The forecast arm is **2.9% cheaper and infeasible**; the static fleet costs **3.0% more and
works**. On the fold that decides the generality question, buying the forecast machinery purchases
a 3% cost reduction in exchange for missing the SLA.
This is the **encoder-pool counterpart of Finding 5's language-pool inversion**, and the two
together are the delivery's central convergent result: **the forecast-free static fleet is the arm
to beat on both pools**, and on the encoder pool it is beaten on the covered span but not
fold-by-fold. Materially strengthens the fold caveat and must travel with it.

## FINDING 5 — on the LANGUAGE pool the forecast is DEARER than static in 6 of 7 folds
forecast/static GPU-h: F1 1.276, F2 1.101, F3 0.931, F4 1.709, F5 3.808, F6 1.022, F7 2.144.
reactive/static GPU-h: 0.502-0.550 uniformly (cheap, but failing).
=> `lang_forecast_cheaper_than_static_in_every_burst_fold` = **False**. The language-pool
forecast buys SLA compliance at roughly 1-3.8x static cost; it is not a saving there.

## VERDICT
`fold_stable` = **False** — now computed over ALL folds with the corrected definition (the
conjunction of FORECAST-POLICY claims only; it returns None, never False, when the fold subset
cannot decide it). This supersedes the earlier single-quiet-fold verdict, which was invalid.

## What may be written
"Split into seven disjoint 24-hour folds, the headline quantities are not fold-invariant. The
encoder cost ratio against the deployed C=8 fleet ranges from 0.47x to 1.10x across burst-bearing
folds around its 0.62x whole-span value, and the forecast policy misses the bound on the fold
containing the e13 onset — a fold on which a **static C=5 fleet passes at 904.7 ms for only 3%
more worker-time**. The rho frontier retains its shape in every fold, but rho=15 is nowhere the
cheapest feasible setting **among the four values swept**. On the language pool the forecast is
dearer than a feasible static fleet in six of seven folds. The single-span averages are therefore
representative of the span, not of an arbitrary day within it."

(One DELETION from the earlier draft: the sentence "A whole-span static ladder further shows that
C=4 clears the bound (by a 0.6% margin), so the 0.62x denominator is the deployable fleet rather
than the static optimum — against a refit optimum the schedule is dearer." C=4 fails 3 of 5
burst-bearing folds and is not deployable under the thesis's own aggregate-AND-per-episode
grading, so leading with it invites the unlicensed "the baseline is 2x oversized" reading.
One ADDITION: the F6 static-C=5 fact, per Finding 4b.)

## DO NOT WRITE (from this card)
- **"The baseline is 2x oversized."** Not licensed. The fold-robust static optimum is C*=5, giving
  8 vs 5 = **1.6x**, and that is measured on the **A15 7.0-day span**, not the 5.60-day headline
  span.
- "rho=25 is optimal" — the optimum sits at a grid endpoint in 7 of 8 folds and is untested beyond.
- Any restatement of 0.62x against a span other than the one it is priced on. G4 is priced on the
  **6.998-day A15 span** — a third span again — and must be labelled as such.
- Any generality claim beyond **temporal** variability within **one** trace.

## Honest scope
One trace, one datacenter, one model family, one 7-day record. Folds share tenant mix, request-size
distribution and hardware calibration, differing only in time. Also: the expanding-context
forecaster's conditioning history is NESTED across folds (a fold-5 forecast is conditioned on
folds 1-4), so folds are disjoint TEST windows but are not training-independent.
The language anchor was NOT run (~2 h full-span replay); only the encoder anchor is verified.

## Methodological defect found in round 3 (does not move any headline)
Every F3 static rung is marked FAIL — including C=8 at enc p99 465.1 ms — solely via
`queue_divergent`. F3_enc_static_C8 has queue_imgs_at_arrival_end = 17 against a median <= 1, and
trace_to_two_pool.py:537 fires on q_end > 10*max(1, q_median): a hair trigger when a 24-h fold is
cut at 12:00 with a non-empty queue. Consequence: F3 gets C_star = null and is silently dropped
from the reported "cost vs C* 0.971x..1.757x" range, and the artifact carries a misleading
"static C8 FAILS F3" row. Not asymmetric by construction (the forecast arm on F3 drains to q_end
= 0 and legitimately passes), but the criterion should be span-length-aware, or folds should be
cut at a drained instant.

## Round-3 verdict
Findings 2-5 SURVIVED and every number reproduced exactly. Finding 1 was REFUTED and is restated
above. Net thesis risk: LOW — lower than my first card implied. The 0.62x headline is not
threatened; the anchor is exact and the two arms are computed on a verified-identical basis. The
real, quotable limitations are the fold-variance (0.465x-1.098x), the rho=15 sub-optimality, the
F6 forecast failure, and the language-pool cost inversion.
