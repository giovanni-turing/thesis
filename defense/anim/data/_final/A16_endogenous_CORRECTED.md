# A16 endogenous — CORRECTED (period-2 limit cycle, not a fixed point)

## What SURVIVED adversarial attack
- EXOGENEITY HOLDS. The forecast is never recomputed from realized demand; the archived forecast
  is byte-identical across every cell and predictors/results/* is untouched
  (gen_a16_endogenous.py:127-128, corroborated in the artifact). This was attacked directly and
  could not be broken — the central methodological risk of the track is discharged.
- DENOMINATOR IS CORRECT. offered_goodput = good/n_offered_clients (gen_a16_endogenous.py:734),
  and n_offered_clients = 3093 for EVERY iteration of BOTH arms, while n_realized_attempts falls
  to 2952-2962 in the reactive arm. The metric scores over the fixed offered population.
- THE METRIC-BIAS FIX IS APPLIED AND UPSTREAM of the shipped numbers (w_client measured from the
  client's ORIGINAL ingress, gen_a16_endogenous.py:682) — though it turns out IMMATERIAL here:
  the reactive fixed point contains only 0-1 retried clients out of 2963 submissions.

## Defect 1 — it is a PERIOD-2 LIMIT CYCLE, not a fixed point
Iterates: 10573.7, 1692.5, 1808.4, 1702.1, 1808.4, 1702.1, 1808.4 — an exact 2-cycle.
Nothing establishes that a fixed point exists inside [1702.1, 1808.4]; in a map with an
attracting 2-cycle the fixed point is generically repelling and unobservable. The band is a
CYCLE ENVELOPE, not a bound on a fixed point, and the two endpoints are computed over DIFFERENT
populations (n=2962 vs 2952, abandon 0.0424 vs 0.0456).

## Defect 2 — "its failure relocates to lost customers" is FALSE as I stated it
Open-loop failure = 1 - 0.9208 = 7.92%, ALL of it served-but-late (abandon_rate = 0.0 at iter 0).
At the cycle, failure = 1 - 0.9302 = 6.98%, of which ~4.2-4.6 pp is abandonment.
So total failure DECREASED (7.92% -> 6.98%) and partly CHANGED CHARACTER. It did not relocate.

## Defect 3 (NEW) — SURVIVOR CENSORING: the two p99s are not p99s of the same population
At the reactive cycle `max_observable_percentile_of_offered` = **95.44-95.76** against **100.0** at
iterate 0, and `served_only_p99_is_censored_at_cycle` = **true**. Every abandoner is by
construction worse than every survivor, so the p99 of the OFFERED population sits inside the
censored set and is **not observable**. Comparing the served-only cycle p99 against the uncensored
open-loop p99 is therefore not a like-for-like comparison, and the apparent latency improvement is
substantially a change of population.
**The survivorship-immune figure is `e2e_p99_from_ingress` = [3.51, 3.94] s — still about 2x the
2000 ms budget.** Quote that when the question is whether clients are better off.

## Defect 4 (NEW) — "endogenous" overclaims: the feedback is near-nil
`n_shed_at_encode` = **130 on every iterate from 1 onward** and cannot respond to the iteration
(gen_a16_endogenous.py:511). **92-99% of abandonment is a one-shot EXOGENOUS encoder shed**;
the residual genuinely endogenous effect is a handful of clients out of 3,093 offered. The word
"endogenous" must not carry more weight than that.

## Defect 5 (NEW) — scope is ONE CELL PAIR
burst3 only, one seed, one patience parameterisation. The P2000/q0.6 sensitivity cells and the
`*_ondemand` controls exist but reached only 1-3 iterates.

## CORRECTIONS TO THIS CARD'S OWN CLAIMS (the JSON report was right; the card violated it)
1. **"abandonment 0.000" for the forecast arm is FALSE.** `abandon_rate` cycles **[0.0, 0.0006]**
   across iterates. Only the *latency* observables are invariant, not abandonment.
2. **"both settle into a period-2 limit cycle" is NOT SUPPORTED for the forecast arm.** Its
   iterates 2 and 4 are assigned the same phase yet differ in cost (`gpu_hours` **6.311 vs
   6.328**); the state is still moving at the last iterate and only `laps_verified = 1.0` was
   cleared. Neither arm is demonstrated to have converged.
3. **"~1.75 s" is the BANNED MIDPOINT** ((1702.1+1808.4)/2 = 1755.25) and "RELIEVES ... measured
   latency" is the banned rescue framing. Both are struck below.
4. **PRECISION.** Independent recomputation from `provenance.llm_request` gives 1822.9 / 1704.1 /
   11089.5 ms (floor-index) or 1814.1 / 1703.1 / 10615.0 (interpolated) — a convention spread of
   ~0.8% at the cycle and ~4.9% open-loop. **Do not quote to 0.1 ms.**

## Corrected, quotable statement
"Under a mean-field client model (lognormal patience, mean 5 s; retry fraction 0.3; two retries)
iterated around the unmodified discrete-event replay — abandonment is resolved OFFLINE, not
in-clock — the forecast arm's latency observables are invariant across every iterate (TTFT p99
651.1 ms), while the reactive arm oscillates over a two-phase envelope of TTFT p99 [1.70, 1.81] s
**over served clients only**, against ~10.6 s open-loop. That comparison is censored: at the cycle
only the best ~95.4-95.8% of offered clients are observable at all, and the survivorship-immune
end-to-end p99 measured from ingress is [3.51, 3.94] s — still about twice the 2000 ms budget. The
reactive arm settles into a two-phase envelope; the forecast arm's latency observables are
invariant while its cost is still drifting at the last iterate (6.311 to 6.328 GPU-h). The
comparison is not iso-cost: 6.31-6.33 GPU-h forecast against 1.06-1.10 reactive."

Never write "closed loop" (it is mean-field and offline), never quote a single iterate or the
midpoint, never write "rescued" or "relieves", and always report the envelope explicitly.
