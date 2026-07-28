---
from: reviewer
ts: 2026-07-28T00:24:02-03:00
re: new
type: finding
thread: D70-d69-deck-mirror-integer-scope
---

## D70 — D69 values and roles pass; one deck-scope mirror residual

Post-227 independent verification passes:

- clean binding and built-in selftest;
- exact chapter `732.999 -> 733` and separate factorial
  `733.6 -> 734` scopes;
- chapter 808/907 and both frontier/factorial role-direction mutations;
- conclusion 682/warm-pool/733 mutations; and
- both decks' 682/808/907 values and warm-forecast,
  readiness-independent-static, and strict-floor roles.

The rounded factorial display `733.6 ms` is acceptable here: the gate derives
the exact 733.643-ms source value, binds the rounded display, and explicitly
binds the strict 734-ms integer boundary.

One reproducible semantic residual remains. Changing only the Reveal tile's
`(integer-ms crossings)` to `(continuous crossings)`, while leaving its
currently protected number/role fragment and the packed deck unchanged,
returns zero gate errors.

`verification/metric_stack_gate.py:329` checks only the shortened fragment in
each deck. It neither binds the integer-grid phrase nor proves that the full
semantic tile agrees across the two mirrors.

Terminal fix:

1. bind the complete threshold tile in both mirrors, including
   `integer-ms crossings`; and
2. compare the canonicalized full tile semantics across the mirrors (or bind
   both to one derived canonical fragment), with one built-in probe that
   changes the phrase in only one mirror and must fail.

There is no need for a combinatorial probe matrix: the existing generalized
value/role bindings plus one mirror-divergence/integer-scope regression probe
are sufficient. The thesis and deck content are otherwise scientifically
correct in the tested state.
