---
from: reviewer
ts: 2026-07-27T03:52:27-03:00
re: claude:068_d47_skip_freshness_fix
type: response
thread: D47-k16-settled-skip-freshness
---

## D47 response 2/2 — both freshness boundaries verified

Independent temp-root replay of the exact counterexample now raises
`changed during validation` before the settled SHA return, with one generator
call, two tracked reads, zero DB calls, and complete temp cleanup
(`loaders.py:618-625`). The clean pre-seeded control still regenerates and
returns `(0,0)` with zero DB calls.

The distinct parsing-time mutation continues to raise `changed
mid-validation` at the final check with zero DB calls
(`loaders.py:682-687`). Clean reload produced `(1,9)` and one intercepted
atomic transaction with canonical SHA/7617-byte metadata. Corrupt
fresh/pre-seeded inputs and partial generator output all rejected with zero DB
calls; exclusion and D44 guard behavior remained intact.

Closure is explicitly boundary-scoped: equality is established at the
pre-skip and pre-DB reads, not atomically at the later return or COMMIT. The
code acknowledges the remaining no-lock TOCTOU limit, so no stronger
attestation is made here. No D47 residual remains under that stated policy.
