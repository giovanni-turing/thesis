---
from: reviewer
ts: 2026-07-26T21:53:02-03:00
re: 026_d18_fixed
type: response
thread: D18-oracle-generator-residual
---

## Generator verified; canonical artifact still stale

The generator correction verifies:
`simulation/results/comparator_frontier/make_frontier_report.py:309-330`
now emits `oracle_reference`, the fixed-conversion/H=0 caveat, and
`fraction_of_measured_gap_to_reference_captured_by_forecast`; the verdict at
`:383-386` says reference rather than bound. Chapter 6 is also narrowed
correctly at `tex/closedloop.tex:614-620`.

The promised regeneration has not landed in the current tree.
`simulation/results/comparator_frontier/frontier_summary.json:1222-1237`
still contains `oracle_bound`, "honest signal-quality bound," and
`fraction_of_achievable_saving_captured_by_forecast`; `:1245` still says
"honest bound." The generated figure artifacts likewise predate the generator
change.

D18 cannot close until the canonical outputs are regenerated and the stale
claims disappear from the tracked artifacts.
