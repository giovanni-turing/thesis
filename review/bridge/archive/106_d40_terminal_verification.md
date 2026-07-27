---
from: reviewer
ts: 2026-07-27T01:55:07-03:00
re: 103_d40_final_bound_residual
type: verification
thread: D40-schema37-round10-replay
---

## Terminal verification — D40 closed

Verified against the round-12 schema-37 file, SHA-256
`875907846d728a3d7250bd843f1330f328a73748948ecb1f37edace7460f3e22`:

- exact full-file replay under outer rollback compiles and passes the
  legitimate `n=0` path;
- relocation preserves newly created and pre-populated exact partitions;
- final checks require nonempty children, three exact parent edges, and three
  exact one-value bounds;
- broad-bound, wrong-parent, and empty-population fixtures each reject at
  their intended independent guard.

All probes rolled back. Live dedicated counts remain
`190779/367299/134156`, default counts remain zero, and all three live parent
edges and bounds remain exact. D40 is resolved.
