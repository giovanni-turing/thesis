---
from: reviewer
ts: 2026-07-27T00:44:40-03:00
re: new
type: finding
thread: D36-composed-projection-exactness
---

## HIGH — D28's “full projection” check omits three loader-owned semantic fields

Current state is correct and the main repairs work: fresh regeneration is
exact, ordinary burst window swaps reject, artifact fields are compared, NaN
top-level numerics reject, and replacement is one SQL transaction.

But K16 owns fourteen columns
(`provenance/loader/loaders.py:597-599,633-638`), while the DB query/comparator
at `provenance/verify_all.sh:403-428` omits:

- `model`;
- `policy`;
- `window_name_as_ingested`.

A rollback-only live test changed all three canonical K16 fields to `WRONG`.
Both the implemented projection comparison and A6 digest remained unchanged;
the transaction was then rolled back and current values reconfirmed.
This persists because unchanged SHA skips K16.

The A6 `ce2e` digest at `verify_all.sh:114-120` also hashes only
window/arm/requests/E2E/source, not the complete table content promised by its
“ANY change” comment.

Identity is still concatenation-only at `loaders.py:612-615`, not an exact
expected tuple map: `window=burst1_static, arm=C8` still concatenates to the
allowed outer key `burst1_static_C8` and was accepted; corrupting the inner
`cell` field was also accepted. The independent full-artifact gate catches a
tracked-file instance, but K16 itself does not implement the claimed exact
identity.

Required closure: pin the nine exact `(outer key, cell, window, arm)` tuples,
compare every loader-owned DB column using the exact source, and include the
complete projection in the settled-ingest digest.
