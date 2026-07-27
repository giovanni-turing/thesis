---
from: reviewer
ts: 2026-07-27T01:06:32-03:00
re: 090_d36_null_projection_residual
type: escalation
thread: D36-composed-projection-exactness
---

## Escalation — the in-band NULL sentinel preserves the exactness collision

Round 9 makes canonical SQL `NULL -> ''` observable in both the A6 digest and
the semantic gate, and ordinary mutations across all fourteen loader-owned
columns are observed.

However, `coalesce(model,'<NULL>')` at
`provenance/verify_all.sh:119,403-405`, paired with the same expected sentinel
at `:429-435`, merely moves the collision. A rollback-only mutation of
canonical static-arm `model` from SQL NULL to literal text `'<NULL>'`
produced:

```text
actual_model='<NULL>'
digest_changed=false
gate_observation_changed=false
```

The live canonical value was reconfirmed as SQL NULL after rollback. At the
two-response ceiling, D36 is escalated. Exact full-projection closure requires
an out-of-band null flag or structured/length-aware encoding that cannot
collide with any text value.
