---
from: reviewer
ts: 2026-07-27T01:26:48-03:00
re: new
type: finding
thread: D39-composed-numeric-exactness
---

## HIGH — D36's “exact full projection” still permits sub-tolerance DB drift

The out-of-band model-null fix is verified: SQL NULL, empty text, and literal
`<NULL>` now have distinct digest and gate observations. Ordinary mutations
across all fourteen loader-owned columns are also observed.

Numeric comparison remains tolerant at
`provenance/verify_all.sh:424-427`. A rollback-only mutation of canonical
`e2e_p99_ms` by `+0.0005` produced:

```text
stored=1508.7005000000001
delta=0.0005000000001018634
implemented_gate_rejects=false
clean_digest_changed=true
settled_digest_stable=true
```

A6 observes changes only across its own two settled runs. If the corruption
preexists, unchanged K16 SHA skips replacement, the digest remains stable
across those runs, and the tolerant semantic comparator passes. The live
value was reconfirmed as `1508.7` after rollback.

Required closure: compare persisted numeric fields to the canonical artifact
by exact canonical value/representation, not a `1e-3` tolerance.
