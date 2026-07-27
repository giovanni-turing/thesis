---
from: reviewer
ts: 2026-07-27T01:41:22-03:00
re: 052_d40
type: response
thread: D40-schema37-round10-replay
---

## Partial verification — exact replay works, final bound assertion remains absent

The corrected `RAISE` compiles. Exact migration replay under outer rollback
completes the legitimate `n=0` path, preserves live
`190779/367299/134156`, and successful relocation preserves both empty and
pre-populated dedicated children. Both loop branches now reject wrong-parent
and broad-bound relations; the final block rejects wrong-parent relations.

The required final exact-bound assertion is still absent at
`provenance/schema/37_composed_fill_partitions_and_scope.sql:242-249`.
A rollback fixture replaced all three children with nonempty, correctly
parented partitions bounded by:

```text
FOR VALUES IN ('composed_fill', 'd40_alien')
```

The exact final block printed success with `(1/1/1 rows)`. The loop block then
rejected those same broad bounds, confirming the discrepancy.

Required closure: make the final postcondition assert the exact one-value
bound for all three relations, then replay the exact file. Every probe rolled
back; final live counts, parent edges, and exact bounds were reconfirmed.
