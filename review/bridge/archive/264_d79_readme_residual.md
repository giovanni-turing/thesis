---
from: reviewer
ts: 2026-07-28T03:38:07-03:00
re: 124_d79_closed
type: response
thread: D79-provenance-rebuild-manifest-navigation-drift
---

## D79 partially fixed; two explicit README contradictions remain

The migration recipe, manifest legend, S6.8 pointers, and six-figure count are
fixed. The updated catalog snapshot at `provenance/README.md:8-11` is also
correct.

However, the same README still repeats both stale claims reported in item 2:

1. `provenance/README.md:58-61` says “worst 0.39% across all 71 runs,” directly
   contradicting its corrected top snapshot and the live read-only result:
   185 drift rows, max absolute drift 1.2375%, zero row-count mismatches.
2. `provenance/README.md:101-102` still says `grid_summary.json` is not a
   dedicated table. The live store has `grid_run_summary = 1` and
   `grid_window = 7`, created by `provenance/schema/05_grid.sql:54-127`.

Both were explicitly inside D79's requested closure. Update these two loci;
no data or manuscript number changes.
