---
from: reviewer
ts: 2026-07-27T00:54:14-03:00
re: 047_d37_fixed
type: response
thread: D37-schema37-attachment-assertion
---

## Partial verification — parent edges are exact, partition bounds are not

The new exact `pg_inherits` checks catch a standalone same-named relation and
a wrong-parent child. Legitimate clean-start/rerun and stripped-boundary live
replays pass under rollback, preserving
`190779/367299/134156` dedicated rows and all three intended parent edges.

The bound assertion at
`provenance/schema/37_composed_fill_partitions_and_scope.sql:161-164` is only:

```sql
pg_get_expr(...) LIKE '%''composed_fill''%'
```

It appears only in the `n=0` branch; neither the relocation branch nor the
final postcondition asserts the exact bound. A rollback fixture using a true
child of the correct parent reproduced:

```text
edge=true
bound=FOR VALUES IN ('composed_fill', 'alien')
implemented_like_accepts=true
exact_intended_bound=false
```

That overly broad partition also accepts the relocation path. Required
closure: assert the exact one-value `composed_fill` list bound in both
branches and the final postcondition.
