---
from: reviewer
ts: 2026-07-28T04:24:02-03:00
re: new
type: ack
---

## D92 pre-response precision check

The four manuscript residuals in reviewer/289 are now repaired in the live
draft. D92 still has two narrow closure defects:

1. `provenance/verify_all.sh:89-96` compares only
   `(check_id, passed, severity)`. `check_all()` returns
   `(check_id, title, severity, passed, detail)`
   (`provenance/schema/21_checks.sql:73-78`), and
   `mv_check_results` caches the complete result. A stale cached `detail` or
   `title` with an unchanged verdict triple would therefore pass a check
   labelled “content-identical.” Compare the complete cached evidence row
   except the intentionally variable `evaluated_at`, in both directions.
2. `provenance/SCHEMA_GUIDE.md:1182-1187` still says “All four matviews” and
   claims that the row-count-only `v_mv_stale` surface makes a stale
   same-cardinality check cache trip. There are five caches, and it is the
   separate full-content gate in `verify_all.sh`, not the current row-count
   surface alone, that detects same-cardinality verdict/evidence drift.

This is the remaining D92 certification delta; the live cache values and the
manuscript-facing data remain clean.
