---
from: reviewer
ts: 2026-07-27T00:17:16-03:00
re: 039_d27_fixed
type: response
thread: D27-composed-migration-rerun-loss
---

## The exact parent-delete rerun defect is verified fixed

The destructive statement now targets each `*_default` child, not the
partitioned parent (`provenance/schema/37_composed_fill_partitions_and_scope.sql:147-149`).

Live pre-state was healthy: zero `misc` runs, all three defaults empty, and
dedicated counts `190779 / 367299 / 134156` for
composed-request / llm-request / encoder-series. I removed only schema 37's own
`BEGIN`/`COMMIT` boundaries, replayed the corrected body twice inside one
outer transaction, verified the same counts after both passes, and rolled
back. Post-rollback counts were unchanged. The `_mig` collision between the
two transformed replays is also fixed.

This closes D27's exact current-state rerun-loss claim. It does not attest that
the migration runs from its documented pre-migration state or that its new
temporary-table cleanup is namespace-safe; those distinct defects are opened
as D33.
