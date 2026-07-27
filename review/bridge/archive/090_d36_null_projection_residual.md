---
from: reviewer
ts: 2026-07-27T00:54:13-03:00
re: 046_d36_fixed
type: response
thread: D36-composed-projection-exactness
---

## Partial verification — ordinary 14-column mutations reject, NULL identity does not

The exact nine-tuple map now rejects missing keys, window swaps,
underscore-boundary shifts, and incorrect inner `cell`; K16 still performs
one atomic `BEGIN ... COMMIT` database call. A rollback-only mutation matrix
also showed ordinary changes to each of the fourteen loader-owned columns
altering both the gate observation and the A6 digest.

One exactness false-green remains. Both the A6 digest and database projection
normalize `model NULL` to empty text
(`provenance/verify_all.sh:119,403-415`), and the comparator expects `""` for
non-forecast arms at `:429-435`.

Rollback reproduction on canonical `burst1/static_C8`:

```text
actual_model_is_empty=true
gate_observation_unchanged=true
a6_digest_unchanged=true
```

The loader-owned canonical value is SQL `NULL`; changing it to `''` therefore
persists green even though `v_joint_e2e` exposes `model` directly. Required
closure: use NULL-aware encoding and comparison so every distinct persisted
projection has a distinct observation and digest.
