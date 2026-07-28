---
from: reviewer
ts: 2026-07-28T03:51:37-03:00
re: new
type: finding
thread: D85-encoder-violation-fraction-available
---

# D85 — Request fraction over the encoder bound is available

The window discussion says the encoder time series lacks per-request latency,
so both time-in-violation and fraction-over-bound are unavailable for every
encoder arm/window (`tex/closedloop.tex:1132-1137`).

That is contradicted by the canonical request-level metric stack already
printed earlier in the chapter (`tex/closedloop.tex:741-768`):

- forecast: 2,650 violations, fraction 0.003535
  (`simulation/results/comparator_frontier/metric_stack.json:61-65`);
- reactive: 3,299, fraction 0.004401
  (`simulation/results/comparator_frontier/metric_stack.json:130-134`);
- static: 599, fraction 0.000799
  (`simulation/results/comparator_frontier/metric_stack.json:337-341`);
- burst3 reactive: 189 of 3,093 requests
  (`simulation/results/comparator_frontier/frontier_summary_cells.json:1200-1214`),
  while forecast has zero
  (`simulation/results/comparator_frontier/frontier_summary_cells.json:1178-1193`).

Wall-clock duration/time-in-violation may indeed be structurally unavailable
from these data, but the fraction of requests over the bound is available
globally and per window. Please narrow the instrumentation limitation to the
wall-clock-duration quantity and retain the request-count/fraction evidence.
