---
from: reviewer
ts: 2026-07-27T01:26:49-03:00
re: new
type: finding
thread: D40-schema37-round10-replay
---

## BLOCKER — the committed schema-37 migration does not compile

Exact-file replay of
`provenance/schema/37_composed_fill_partitions_and_scope.sql` at `852221f`,
with its transaction wrapper stripped and an outer rollback, fails while
compiling the PL/pgSQL block:

```text
ERROR: too many parameters specified for RAISE
```

At line 187, the statement supplies `t` to a message with no `%` placeholder:

```sql
RAISE EXCEPTION
  '37/D37: relocation-branch bound is not exactly FOR VALUES IN (composed_fill)', t;
```

Because the block compiles as a unit, even the legitimate live `n=0` rerun
cannot complete.

Isolated predicate tests confirm that the intended exact checks now reject a
broad bound in both loop branches. The final postcondition at lines 242-249,
however, still checks only parent edges and nonempty relations: three
broad-bound children satisfy `edge_count=3`, `all_nonempty=true`, while
`exact_bound_count=0`.

Required closure: repair the `RAISE`, assert all three exact one-value bounds
in the final postcondition, and replay the exact migration file under
rollback. All probes rolled back; live rows and bounds remain unchanged.
