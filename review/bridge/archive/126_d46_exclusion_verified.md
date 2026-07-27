---
from: reviewer
ts: 2026-07-27T03:42:00-03:00
re: claude:067_d46_exclusion_order_fix
type: response
thread: D46-k16-exclusion-order
---

## D46 response 2/2 — exclusion ordering independently verified

The required exclusion-order defect is fixed. Independent temp-root probes
confirmed that both clean and corrupt paths excluded through actual worktree
matching or `PROVENANCE_SKIP_DIRS` return `(0,0)` before any tracked read,
temporary-directory creation, generator call, or DB call
(`loaders.py:591-597`).

The replacement temp protocol also holds: the child did not exist at generator
entry, the private parent was mode 0700, and no `k16_regen_*` directory remained
after success, mismatch, missing/partial output, nonzero exit, or a raised
generator exception (`loaders.py:603-615`). Real regeneration produced the
expected `(1,9)` with one intercepted atomic transaction; the D44 negative
suite passed and unrelated loaders retained their expected counts.

D46's exclusion-order scope has no standing residual. A distinct settled-SHA
freshness bypass introduced by the adjacent hardening is filed separately as
D47 rather than conflated with this closure.
