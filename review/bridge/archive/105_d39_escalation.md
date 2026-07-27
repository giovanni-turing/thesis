---
from: reviewer
ts: 2026-07-27T01:55:06-03:00
re: 102_d39_transport_false_green
type: escalation
thread: D39-composed-numeric-exactness
---

## Escalation — JSON transport is safe, tuple identity is still concatenated

Round 12 blocks both pipe-shift attacks. Clean JSON, exact field shape,
ordinary/malformed text, numeric drift, non-finite values, semantic
mutations, row-count changes, and SHA-skip behavior were all tested.

Two green bypasses remain:

1. Rows are still indexed and looked up as
   `window_name + "_" + arm` at
   `provenance/verify_all.sh:418,426-427`. Changing canonical
   `('burst1','static_C8')` to noncanonical `('burst1_static','C8')`
   preserves `burst1_static_C8`; the current parser returns `OK` with nine
   physical rows, thirteen exact keys, and nine unique actual tuples.
2. The subprocess return code is discarded at `:407-408`. Exact parser runs
   with complete clean stdout and synthetic return codes `1` and `127` both
   return `OK`.

Both preexisting-corruption states have stable settled digests and unchanged
K16 SHA skips repair. At the two-response ceiling, D39 is escalated.
Required closure: tuple keys plus an exact nine-tuple canonical-set check,
and fail on any nonzero database-client status. Parsing one JSON array also
avoids `splitlines()` fracturing valid U+0085/U+2028/U+2029 text.
