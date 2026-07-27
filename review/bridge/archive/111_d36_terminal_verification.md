---
from: reviewer
ts: 2026-07-27T02:17:25-03:00
re: 094_d36_escalation
type: verification
thread: D36-composed-projection-exactness
---

## Terminal verification — D36 closed at `8a0bd6b`

After the recognized `CLOSED-FIXED` ruling in
`049_adjudication_d34_d37`, the completed D39 audit verifies D36's full
projection requirement:

- K16 pins all nine exact `(outer key, inner cell, window, arm)` tuples and
  rejects identity attacks before any database call;
- all fourteen loader-owned columns are observed through structured JSON,
  exact tuple keys, exact cardinality, finite/exact numerics, and NULL-aware
  model comparison;
- SQL NULL, empty text, and literal `<NULL>` are distinct;
- A6 hashes all fourteen columns with an out-of-band model-null flag;
- unchanged SHA cannot conceal drift because the exact database comparator
  still executes; and
- replacement remains one atomic `BEGIN; DELETE; INSERT; ingest-log; COMMIT`
  call.

All mutation and failure-path probes rolled back. Live counts remain `9|29`,
the exact comparator returns `OK`, and the digest is restored. D36 is
resolved.
