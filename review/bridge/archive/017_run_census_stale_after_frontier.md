---
from: reviewer
ts: 2026-07-26T21:08:04-03:00
re: 009_rereview_request
type: finding
thread: D08-frontier-census-regression
---

## Moderate preservation regression — the run census predates the frontier now reported above it

`tex/closedloop.tex:917-923` says the provenance store "behind every number
above" held 2,666 current runs. That was the old Finding 9 finalize census
(`verification/adversarial_review_resolution.md:172-180`), before the new
frontier ingestion.

Current read-only SQL:

```sql
select count(*) as total,
       count(*) filter (where is_current) as current,
       count(*) filter
         (where is_current and experiment='comparator_frontier') as frontier
from provenance.runs;
```

returns:

```
total=3665 | current=2979 | frontier=313
```

The exact delta is `2979 - 2666 = 313`, the new comparator-frontier rows.
The check-definition counts remain 75 defined / 74 enabled. A historical
2,666-run snapshot can remain only if identified as predating the frontier;
it cannot be the store "behind every number above" when the preceding section
now reports the ingested frontier. This means old Finding 9 did not survive
the new integration unchanged.

