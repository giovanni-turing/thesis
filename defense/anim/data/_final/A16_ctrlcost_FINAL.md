# A16 — charging the controller's own inference cost: THE 0.62x SURVIVES (corrected)

Closes: tex/closedloop.tex Limitations — the controller's re-forecast cost "is NOT CHARGED to the
fleet." Both controllers are charged (charging only the forecast side would be biased).

## I PREVIOUSLY REPORTED THAT CPU-CLASS CHARGING ERASES THE MARGIN. THAT WAS WRONG.
The two cells producing the "erasure" (0.7515x worst, 0.7398x shape-matched) are EXACTLY the two
cells the same artifact declares INFEASIBLE: toto/cpu @15 s tick, duty cycle 2.142 and 1.947.
gen_a16_controller_cost.py:590-594 selected worst = max(ratio) with NO `sustainable` filter, so
the headline priced a deployment that cannot physically run.

**Every FEASIBLE CPU cell at a 15 s tick PRESERVES the ordering:**
  chronos 1-signal 0.6537 (duty 0.511) · chronos 4-signal 0.6593 (duty 0.604)
  timesfm cells likewise below the reactive 0.6747x
So the CPU conclusion INVERTS: charging a deployable CPU-class controller does NOT erase the
forecast-vs-reactive margin.

## Verified sound (independent recomputation, round-2 audit)
- ACCOUNTING SYMMETRY IS CLEAN. Both arms share the denominator 3,869,278 encoder worker-s; the
  reactive numerator 2.61e6 matches tex/closedloop.tex:472 (2.61, 0.67x); both arms carry a
  one-off (forecast model_load_s :519; reactive first_fit_s x3 :557) plus a per-tick charge.
- ALL ARITHMETIC BIT-EXACT: 2410755/3869278 = 0.62305; 2.61e6/3869278 = 0.67454;
  (2410755+3812)/3869278 = 0.62403; ticks 483659.846/15 = 32243.99 and /180 = 2687.0.
- TIMING HARNESS SOUND: sync() = torch.cuda.synchronize() called immediately before and after
  predict_batch, so CUDA async cannot under-report; warmup excluded; model load charged once;
  context and batch shapes archive-faithful (1928/3976/8072 = benchmark.py MODELS minus headroom).
- THE ENCODER-DENOMINATOR OBJECTION IS UNFOUNDED: charging a 4-signal fleet controller against the
  encoder-only denominator does not manufacture anything — the shape-matched 1-signal cell behaves
  the same way.

## Result
| model | ratio | ordering preserved |
|---|---:|---|
| controller free (baseline) | 0.6231x | — |
| GPU duty-cycle, worst cell (toto 4-sig @15 s) | 0.6240x | YES |
| GPU whole-GPU reservation | preserved | YES |
| CPU-class, every FEASIBLE cell @15 s | 0.6537-0.6593x | YES |
| reactive + its own ARIMA | 0.6745 -> 0.6747x | (its controller is nearly free) |
| CPU-class toto @15 s | 0.7398-0.7515x | INFEASIBLE — not a deployable configuration |

## The feasibility finding stands and is the real CPU story
A forward slower than its tick period cannot be deployed at that rate at all:
  toto/cpu 1 signal @15 s -> duty 1.947 (29.198 s forward)
  toto/cpu 4 signals @15 s -> duty 2.142 (32.123 s forward)
Chronos (9.06 s) and TimesFM (8.27 s) fit inside a 15 s tick with real headroom. So the honest
CPU statement is about MODEL CHOICE feasibility, not about cost erasing the margin.

## What may be written
"Charging both controllers their own inference cost leaves the result intact: on GPU the ratio
moves from 0.623x to 0.624x, and on CPU-class hardware every deployable configuration
(Chronos, TimesFM) stays between 0.65x and 0.66x, still below the reactive baseline's 0.675x.
The only configurations that would erase the margin are ones that cannot hold their own tick
period — Toto on CPU requires 29-32 s for a 15 s tick — so the constraint they express is model
feasibility, not controller cost."
