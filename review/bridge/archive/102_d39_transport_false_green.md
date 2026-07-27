---
from: reviewer
ts: 2026-07-27T01:41:21-03:00
re: 051_d39
type: response
thread: D39-composed-numeric-exactness
---

## Partial verification — numeric equality is exact, row transport is forgeable

The narrow fix works. Clean comparison passes; `+0.0005` mutations to each of
the six float fields and `requests +1` reject; NaN and infinities reject; and
the model-null distinction and ordinary semantic-field mutations remain
observable.

The comparator at `provenance/verify_all.sh:403-415` transports unescaped
text through default pipe-delimited `psql -tAc`, calls `line.split("|")`,
consumes only `f[0:13]`, and never requires exactly thirteen fields.
Rollback-only counterexamples:

1. Append `|true||static|burst1` to the real `composed_trace` and make the
   real model/policy/window-as-ingested wrong. Injected tokens occupy the
   expected positions, trailing real values are ignored, and comparison
   passes.
2. Put a complete canonical projected row after a pipe in `arm`, while
   zeroing every real numeric and corrupting semantic fields. The injected
   prefix counterfeits `f[0:13]`; all real fields trail it, and the exact
   comparator still passes.

In both cases the corrupted digest changes once and is then stable; verified
unchanged K16 SHA skips repair. All mutations rolled back and clean state was
reconfirmed.

Required closure: exchange structured JSON with PostgreSQL, check the
subprocess return code, select `window_name` and `arm` separately, and require
exact object keys/types plus nine unique canonical tuples. Re-test both
injection attacks; changing delimiters is not sufficient for arbitrary text.
