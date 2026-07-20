# A16 — charging the controller's own inference cost: THE 0.62x SURVIVES (corrected)

Closes: tex/closedloop.tex Limitations — the controller's re-forecast cost "is NOT CHARGED to the
fleet." Both controllers are charged (charging only the forecast side would be biased).

## I PREVIOUSLY REPORTED THAT CPU-CLASS CHARGING ERASES THE MARGIN. THAT WAS WRONG.
The two cells producing the "erasure" (0.7515x worst, 0.7398x shape-matched) are EXACTLY the two
cells the same artifact declares INFEASIBLE: toto/cpu @15 s tick, duty cycle 2.142 and 1.947.
gen_a16_controller_cost.py:590-594 selected worst = max(ratio) with NO `sustainable` filter, so
the headline priced a deployment that cannot physically run.

**Every FEASIBLE CPU cell at a 15 s tick stays well inside the 1.00x static baseline:**
  chronos 1-signal 0.65 (duty 0.51) · chronos 4-signal 0.66 (duty 0.60)
  timesfm 1-signal 0.66 (duty 0.57) · timesfm 4-signal 0.66 (duty 0.55)
So the CPU conclusion INVERTS: charging a deployable CPU-class controller does NOT erase the
margin against the static fleet.
**PRECISION (peer review):** these are medians of n=5 wall-clock samples with up to 17%
intra-cell spread. **Two significant figures only** — the previously quoted 0.6537 / 0.6593 assert
a resolution the sample cannot support and must not be reproduced.

## Verified sound (independent recomputation, round-2 audit)
- ACCOUNTING SYMMETRY IS CLEAN. Both arms share the denominator 3,869,278 encoder worker-s; the
  reactive numerator 2.61e6 matches tex/closedloop.tex:472 (2.61, 0.67x); both arms carry a
  one-off (forecast model_load_s :519; reactive first_fit_s x3 :557) plus a per-tick charge.
- ALL ARITHMETIC BIT-EXACT: 2410755/3869278 = 0.62305; 2.61e6/3869278 = 0.67454;
  (2410755+3812)/3869278 = 0.62403; ticks 483659.846/15 = 32243.99 and /180 = 2687.0.
- TIMING HARNESS SOUND: sync() = torch.cuda.synchronize() called immediately before and after
  predict_batch, so CUDA async cannot under-report; warmup excluded; model load charged once;
  context and batch shapes archive-faithful (1928/3976/8072 = benchmark.py MODELS minus headroom).
- THE ENCODER-DENOMINATOR OBJECTION IS UNFOUNDED, AND ITS CAVEAT IS DELETED: charging a 4-signal
  fleet controller against the encoder-only denominator does not manufacture anything — the
  shape-matched 1-signal cell behaves the same way. The old mandatory caveat ("pessimistic by
  construction") is **struck**: it is true of the LEVEL and irrelevant to the ORDERING, which is
  denominator-invariant (the denominator cancels in fc + charge < react + charge_react). It bought
  zero insurance while implying slack that does not exist.

## THE COMPARATOR MUST BE STATIC, NOT REACTIVE (peer review — resolves a delivery-wide inconsistency)
The reactive L=30 arm **misses the burst3 episode SLA at 16,078.7 ms against a 1,000 ms bound**
(provenance.v_infraction, all rows is_violation=t) — a 16x miss, against which the largest
controller charge here is a rounding error (margin vs static C=8 is 10.4x the largest charge).
G7 retracts the burst5-L165 flip on exactly this principle ("an infeasible arm cannot carry a cost
comparison"). The same principle is now applied here: **the deployable static fleet (1.00x) is the
anchor**, and the reactive number may appear only with its infeasibility disclosure attached.
Never write "0.65-0.66x, still below the reactive baseline's 0.675x" as a standalone headline —
it also re-opens the "roughly two-thirds" collision flagged at ADJUDICATION.md §3.1.

## PRICE BASIS — the CPU result is measured AND THEN PRICED (mandatory caveat)
`cpu_gpu_price_ratio = 0.02` ($0.04/vCPU-h against $2.00/GPU-h) and `n_thr = 24` appear only at
gen_a16_controller_cost.py:542 and carry no market-rate justification anywhere in the artifact.
Re-derived here from accounting.json: the ordering against reactive **inverts at a price ratio of
0.0286** (4-signal cell; 0.0338 at 1-signal) — i.e. ~1.4x headroom resting on an assumption, not
on data. Never phrase the CPU result as if it were measured; it is measured-and-then-priced.

## Result
All ratios are against the deployable **static** fleet (1.00x). Two significant figures — the
underlying CPU latencies are n=5 medians with up to 17% spread.

| model | ratio vs static | inside the static baseline |
|---|---:|---|
| controller free (baseline) | 0.62x | — |
| GPU duty-cycle, worst cell (toto 4-sig @15 s) | 0.62x | YES |
| GPU whole-GPU reservation | preserved | YES |
| CPU-class, every FEASIBLE cell @15 s | 0.65-0.66x | YES |
| CPU-class toto @15 s | 0.74-0.75x | INFEASIBLE — not a deployable configuration |
| reactive + its own ARIMA | 0.67x | **SLA-INFEASIBLE comparator** (burst3 16,078.7 ms) — may not anchor a cost claim |

## The feasibility finding stands and is the real CPU story
A forward slower than its tick period cannot be deployed at that rate at all:
  toto/cpu 1 signal @15 s -> duty 1.947 (29.198 s forward)
  toto/cpu 4 signals @15 s -> duty 2.142 (32.123 s forward)
Chronos (9.06 s) and TimesFM (8.27 s) fit inside a 15 s tick with real headroom. So the honest
CPU statement is about MODEL CHOICE feasibility, not about cost erasing the margin.

## CORRECTION — "only configurations that cannot hold their tick period" is FALSE AS A UNIVERSAL
The claim asserts an empty set that is not empty. Re-derived from accounting.json: the charge that
would lift the forecast arm to the reactive ratio is 199,948 worker-s equivalent, i.e.
416,559 controller-s over 32,244 ticks = **12.9 s per tick (duty 0.86)**. The band
**(12.9 s, 15.0 s) is both feasible and margin-erasing**, so a hypothetical model landing there
would erase the margin while holding its tick period perfectly well.
**Rewrite as an existential over the models actually measured:** "Among the four models
benchmarked, none erases the margin while remaining feasible — they land at duty <= 0.60 or
>= 1.95, on either side of the (0.86, 1.00) duty band in which erasure would occur." That is what
the data shows. (Note this whole comparison is against the *reactive* arm and is therefore not
load-bearing under the infeasible-comparator standard above; against the static fleet the margin
is far larger and nothing in the measured set comes near erasing it.)

## What may be written (STATIC-ANCHORED — the only feasible comparator)
"Charging each controller its own measured inference cost does not disturb the provisioning
result. On GPU the forecast arm moves from 0.623x to 0.624x of the deployable static fleet —
controller duty cycle under 0.8% at a 15 s tick for every model tested. On CPU-class hardware,
priced at $0.04/vCPU-h against $2.00/GPU-h over the 24 threads the forward occupies, the
deployable configurations (Chronos, TimesFM) land at 0.65-0.66x, still well inside the 1.00x
static baseline. Among the models measured, only Toto on CPU at a 15 s tick fails, and it fails on
FEASIBILITY rather than cost."

Permitted ONLY with the disclosure attached, never bare:
"...and remains below the reactive arm's 0.67x, **though that arm misses the burst3 episode SLA at
16,078.7 ms and so cannot itself carry a cost comparison.**"

## DO NOT WRITE (from this card)
- "The only configurations that would erase the margin are ones that cannot hold their own tick
  period." (false universal — see above)
- "0.65-0.66x, still below the reactive baseline's 0.675x" as a standalone headline.
- Any four-digit CPU ratio (0.6537 / 0.6593 / 0.6747).
- Any phrasing implying the CPU result is measured rather than measured-**and-then-priced**.

## PROVENANCE STATUS
File-only. `analysis_artifact` matching %controller_cost% = 0 rows; there is no independent SQL
path, so these numbers cannot be cross-checked against v_pool_latency, v_cost_ratio or
grid_window_effective. Post-manuscript defence material (ruling §4c) — not a results chapter.
