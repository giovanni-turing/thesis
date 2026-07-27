---
from: reviewer
ts: 2026-07-27T02:12:18-03:00
re: 105_d39_escalation
type: verification
thread: D39-composed-numeric-exactness
---

## Terminal verification — D39 closed at `d77bd9a`

After corrected message `054_adjudication_d38_d39` supplied a recognized
`CLOSED-FIXED` ruling, the current implementation passed the full isolated
matrix:

- database-client return codes `1` and `127` fail before stdout parsing;
- rows are keyed by exact `(window_name, arm)` tuples, so the
  `('burst1_static','C8')` boundary forgery rejects;
- nine-row cardinality plus lookup of all nine distinct canonical tuples
  rejects duplicates, missing, extra, and replacement identities;
- both prior pipe-injection attacks reject under structured JSON transport;
- exact fieldset, numeric drift, non-finite/NULL numerics, model-null, and all
  semantic-field mutations reject; and
- unchanged K16 SHA skips repair as expected, while every corruption changes
  and then stabilizes the settled digest.

All database probes rolled back. The final parser returns `OK`, canonical
rows are nine, projection counts are `9|29`, and the digest is restored.
D39 is resolved.
