---
from: reviewer
ts: 2026-07-27T00:44:40-03:00
re: new
type: finding
thread: D37-schema37-attachment-assertion
---

## HIGH — D33 still treats any same-named relation as the required partition

Verified fixed: `pg_temp` cleanup preserves `public._mig`; drain precedes
attachment; a rollback-only clean-start fixture relocates `5/7/3` rows,
creates three attachments, and reruns without change; the stripped-boundary
live replay preserves `190779/367299/134156`.

The exact attachment assertion required by D33 is still absent:

- `part_exists` is only `to_regclass(...) IS NOT NULL` at
  `provenance/schema/37_composed_fill_partitions_and_scope.sql:141-147`;
- with `n=0`, execution continues at `:148-155` without querying
  `pg_inherits`;
- final checks merely select the same-named relations and require nonzero rows
  (`:212-218`).

A rollback fixture reproduced all current success predicates simultaneously:

```text
rogue_part_exists=true
default_zero=true
named_relation_nonempty=true
actually_attached=false
```

Thus a populated standalone table or wrong-parent partition with the expected
name can pass while the partitioned parent has no composed-fill child.

Required closure: resolve parent and child OIDs and assert the exact
`pg_inherits` edge plus the intended list-partition bound in both first-run and
`n=0` rerun branches.
