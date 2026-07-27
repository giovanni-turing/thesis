---
from: reviewer
ts: 2026-07-27T01:06:33-03:00
re: 091_d37_exact_bound_residual
type: escalation
thread: D37-schema37-attachment-assertion
---

## Escalation — exact bound validation covers only the no-row branch

Round 9's exact equality at
`provenance/schema/37_composed_fill_partitions_and_scope.sql:161-164`
correctly accepts the intended one-value bound and rejects
`FOR VALUES IN ('composed_fill','alien')` when `n=0`.

The relocation branch at `:169-191` still checks only the exact parent edge
and `post=pre+n`. A broader-bound fixture passed that path with:

```text
edge=true
pre_plus_moved_equals_post=true
default_zero=true
exact_bound=false
```

The final postcondition at `:238-245` likewise checks only three edges and
nonempty relations; three broader children produced
`final_edge_count=3`, `all_nonempty=true`, `exact_bound_count=0`.

At the two-response ceiling, D37 is escalated. Apply the same exact one-value
bound assertion to the relocation branch and the final three-partition
postcondition before terminal verification.
