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

## Corrected, quotable statement
"Under a mean-field client model (lognormal patience, mean 5 s; retry fraction 0.3; two retries)
iterated around the unmodified discrete-event replay — abandonment is resolved OFFLINE, not
in-clock — the forecast arm is invariant across every iterate (TTFT p99 651.1 ms, offered
goodput 0.9990-0.9997, abandonment 0.000). The reactive arm does not converge: it settles into a
period-2 limit cycle with TTFT p99 alternating 1702.1/1808.4 ms and offered goodput 0.9302,
against 0.9208 open-loop. Endogenous client behaviour therefore RELIEVES the reactive arm's
measured latency (10.6 s open-loop -> ~1.75 s) because 4.2-4.6% of clients abandon, while its
offered-goodput shortfall persists at ~7%."

Never write "closed loop" (it is mean-field), never quote the last iterate as a point estimate,
and always report the cycle explicitly.
