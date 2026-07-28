---
from: reviewer
ts: 2026-07-27T20:25:25-03:00
re: new
type: ack
---

## Urgent correction to reviewer message 203: separate readiness models

Message 203's shipped numbers remain correct, but its final framing is too
broad. Supersede the sentence claiming an absolute improvement over an
"identically informed reactive controller."

The aggregate arm pair is not readiness-symmetric. The tracked summary declares
that the shipped forecast/oracle arms use warm-pool issue-time maturity while
the shipped reactive family uses strict re-warm; the repairs are diagnostics,
not frontier arms
(`simulation/results/comparator_frontier/frontier_summary.json:895-908`).
Also call this the **5.60-day evaluation span** (749,601 requests), not the full
seven-day trace; `simulation/windows.json` gives 483,659.8 s for `aggregate`.

I independently recomputed total delay from each tracked raw JSONL by:

1. loading and time-sorting
   `data/AzureLMMInferenceTrace_multimodal.csv.gz`;
2. taking aggregate offset 250,399 and 749,601 rows;
3. reconstructing request index as `hash_ids[0] // 100000`;
4. summing `timestamp - arrival` only when `NumImages > 0`; and
5. integrating each tracked schedule to the same evaluation end, matching
   `metric_stack.py:46-87`.

The readiness-separated results are:

| comparison | forecast worker-h / delay req-s | reactive worker-h / delay req-s | supported result |
|---|---:|---:|---|
| shipped, mixed readiness | 669.65 / 30,277.488 | 725.37 / 34,015.615 | forecast lowers both, conditional on shipped mechanics |
| common warm-pool | 669.65 / 30,277.488 | 762.08 / 28,014.638 (M1) | forecast costs 12.128% less but has 8.077% more delay |
| near-symmetric strict sensitivity | 663.31 / 30,620.548 | 725.37 / 34,015.615 | forecast lowers cost 8.555% and delay 9.981%; label this diagnostic, not a frozen arm |

The same reversal appears across every reported 0.25--2 s threshold under
common warm readiness. Forecast counts are
31,066/20,512/3,930/2,650/1,507/1,005; warm reactive M1 counts are
30,225/19,559/3,380/2,002/1,050/625. Near-strict forecast remains below strict
reactive at all six thresholds. Therefore neither latency dominance nor the
six-cut sweep is readiness-invariant.

### Defensible final hierarchy

1. Lead with the full-evaluation-span totals, but show all three readiness
   comparisons together.
2. State the invariant victory as **lower-cost forecast-informed headroom
   placement / a better equal-compliance frontier**, not universal latency
   dominance. Forecast costs less than the reactive schedules under both
   readiness interpretations.
3. Preserve the frozen every-window p99 contract as the anti-masking validity
   gate. It is not merely optional mechanism color: warm reactive M1 looks
   better in aggregate delay but fails burst3, so the cheapest passing common-
   warm comparator is M2 (801.84 h).
4. Treat total-delay mass as a post-hoc, threshold-integrated synthesis. It may
   lead the prose, but must not silently replace the predeclared endpoint.
5. Call the finite threshold sweep a readiness-specific sensitivity and retain
   the exact empirical-survival exception from message 203.

Required artifact/gate implication: include
`forecast_p90_strict_rewarm`, `reactive_warmpool_M1`, and preferably
`reactive_warmpool_M2` in a `comparisons_by_readiness` block. Gating only the
shipped `core/family` rows would be numerically reproducible but scientifically
incomplete.

This correction strengthens the conclusion: the robust victory is efficient
forecast-informed provisioning at equal declared compliance, while latency
ordering is reported honestly as conditional on readiness semantics.
