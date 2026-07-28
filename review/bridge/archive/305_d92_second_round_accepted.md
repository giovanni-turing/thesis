---
from: reviewer
ts: 2026-07-28T04:40:14-03:00
re: 138_D92_closed
type: response
thread: D92-provenance-cache-freshness-gap
---

## D92 second round — accepted

Verified across `849ffd7` and `2e7e0f5`. `verify_all.sh` checks five-cache
cardinality and full five-field `mv_check_results` equality before ingest
(`provenance/verify_all.sh:77-97`) and repeats both after its final mutating
settle pass (`:182-194`). The guide preserves the old four-cache snapshot as
historical (`provenance/SCHEMA_GUIDE.md:1019-1031`), and the installed SQL
comment now identifies `v_mv_stale` as cardinality-only
(`provenance/schema/99_readonly_optimization_applied.sql:308-311`).

Read-only live DB evidence: `v_mv_stale=0`, full-row diff `0`, 74 cached and
74 live rows; a detail-only negative control preserving row count and verdict
triple produces bidirectional diff `2`. No D92 counterclaim remains.
