---
from: reviewer
ts: 2026-07-27T20:17:23-03:00
re: new
type: ack
---

## Author intent clarification — put the final RQ3 victory on absolute,
full-trace grounds

The author confirms the desired hierarchy: minimize conventions in the final
result. Burst boundaries should diagnose masking and mechanism, not carry the
headline. Likewise, a single SLA threshold should not be the primary axis when
the raw full-trace comparison supports a stronger statement.

### Primary, convention-minimized result

I independently recomputed these values from the two tracked aggregate raw
traces
`simulation/results/comparator_frontier/eval/aggregate_fc_L30.jsonl.zst` and
`aggregate_re_L30.jsonl.zst`, using the same request-index reconstruction as
`metric_stack.py:46-83`:

1. **Absolute resource-time:** forecast provisions 2,410,754.7 worker-s
   (669.654 h) versus reactive's 2,611,319.7 worker-s (725.367 h): a saving
   of **200,565.0 worker-s = 55.7125 worker-h = 7.6806%**.
2. **Threshold-free aggregate delay mass:** over the same 749,601 requests
   (350,168 image-bearing), forecast accumulates **30,277.488
   request-seconds** of encoder delay versus **34,015.615 request-seconds**:
   **3,738.127 request-seconds less, a 10.9894% reduction**.
3. That second quantity is not an arbitrary mean convention: it is exactly
   the area under the complete empirical exceedance-count curve,
   \(\sum_i d_i = \int_0^\infty N(d_i>t)\,dt\). It integrates every possible
   threshold instead of privileging the 1 s SLA.
4. The complete empirical survival comparison is nearly ordered: forecast
   has no more exceedances than reactive at every possible cut except the
   single interval **[25.079583, 26.230949) s**, where it has 3 versus 2.
   Both maxima are 35.902512 s. State this exact exception; do not call it
   first-order dominance.
5. On the corresponding threshold-free cost/delay frontier, the M1--M2
   floor interpolated to forecast's total-delay mass costs **754.352 h**,
   **12.648% more** than forecast. No warm floor exists at forecast's lower
   cost because reactive/M1 is already the cheapest floor.

This is the clean final claim: **forecast strictly improves both absolute
worker-time and total full-trace encoder-delay burden over the identically
informed reactive controller.** It does not require a burst definition, an
SLA cut, or a percentile selection.

### Evidence hierarchy for the manuscript

1. Lead with worker-hours + total delay mass + the full survival-curve
   exception above.
2. Keep the six-threshold sweep, p99 ladder and 1 s excess mass as
   **sensitivity/interpretation**, not as the proof of victory.
3. Keep the window grid as a **masking and mechanism check**: it shows where
   aggregate metrics can conceal a localized failure, but the final
   resource/delay comparison is full-span.

### Minimal implementation target

- Add `total_delay_request_s` to `metric_stack.py/json` for every arm and gate
  it from the raw traces.
- Make the principal cost-versus-delay figure use total delay mass (or add it
  as the primary panel); the current excess-mass-over-1-s figure remains a
  threshold-specific sensitivity.
- Replace “convention-free” with “convention-minimized,”
  “full-span,” or “threshold-integrated.” The denominator, delay definition
  and resource conversion are still declared design choices.
- Bind table columns and claim operands structurally in A5c; do not use
  literal-presence checks.
- Say tightening the bound **never erodes the advantage over the tested
  interval and widens it at comparator crossings**, not “every tightening
  widens.”
- Correct “Table grades every arm”: the visible table prints 6 of 20 arms and
  3 of 6 thresholds; the artifact/figure carry the full set.

Important distinction: the sorted-vector comparison has
41,989/707,611/1 lower/equal/higher **order-statistic ranks**. Those are not
paired request outcomes. Exact request pairing is 6,742 forecast-better,
738,027 ties and 4,832 forecast-worse; do not mislabel either population.

Please use this hierarchy while finishing D64/D65. It focuses the victory on
the strongest absolute evidence and removes pressure to overstate a finite
threshold sweep.
