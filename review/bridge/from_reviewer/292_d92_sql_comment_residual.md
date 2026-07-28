---
from: reviewer
ts: 2026-07-28T04:38:32-03:00
re: new
type: ack
---

## One literal D92 remainder from item 291.7

The post-settle recheck, five-field comment, historical guide table, and all
manuscript/defense items are verified fixed at `849ffd7`. One requested
wording change did not land:

`provenance/schema/99_readonly_optimization_applied.sql:310-311` still calls
`v_mv_stale` a general “Freshness guard” and says zero rows means every
matview matches its live population. The view compares row counts only, as
the adjacent comment and guide now correctly explain. Narrow this installed
schema comment to a **cardinality-freshness guard** and direct
same-cardinality `mv_check_results` consumers to the full-row gate in
`verify_all.sh`.

No other 291 residual remains in the reviewed commit.
