---
from: reviewer
ts: 2026-07-26T23:35:11-03:00
re: new
type: finding
thread: D27-composed-migration-rerun-loss
---

## CRITICAL — schema 37 is destructive on its second run

`provenance/schema/37_composed_fill_partitions_and_scope.sql:20-21`
claims the migration is idempotent. It is not:

- `:127-130` copies matching rows only from each `*_default` partition into
  `_cf`.
- `:131` then deletes through the partitioned **parent** table, so the delete
  reaches both the default and the already-attached `*_composed_fill`
  partition.
- `:134` restores only `_cf`.

On the first run this happens to work because the rows begin in the default
partitions. On a second run `_cf` is empty, the parent delete removes every
row already routed to the dedicated partition, and the empty `_cf` restores
nothing.

Live read-only evidence before any rerun:

```text
provenance.composed_request_composed_fill  190779
provenance.encoder_series_composed_fill    134156
provenance.llm_request_composed_fill       367299
```

Derived with:

```sql
SELECT tableoid::regclass::text, count(*)
FROM provenance.<parent>
WHERE run_id LIKE 'composed_fill:%'
GROUP BY 1;
```

Thus a rerun would delete 692,234 raw rows. The postcondition at `:167-175`
would still pass because it checks only `misc` runs and the three default
partitions; all would remain zero after the loss.

Do not rerun schema 37 in its present form. The relocation delete must be
scoped to the default child (not the parent), and the postcondition needs to
assert preservation of the dedicated-partition populations. This is a
data-loss defect, not a documentation-only idempotency nit.
