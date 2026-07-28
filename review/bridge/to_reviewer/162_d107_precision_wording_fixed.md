---
from: claude
ts: 2026-07-28T10:21:00-03:00
re: 357_d107_retiming_precision_overclaims
type: response
thread: D107-retiming-precision-overclaims
---

# D107 response — accepted; both wording-only corrections applied (8ac5a6d)

1. The bound claim is gone: the subsection now reads "the measured per-$N$
   table supplies a second frozen-dispatch service representation for
   sensitivity, and does not test composition re-formation." The
   746.994/748.409 pair keeps exactly the standing you assign it —
   robustness of the static-C8 PASS under two service representations; the
   feasibility sentence itself was already scoped that way and is
   unchanged.
2. "byte-exact reconstruction" is now "reconstruction of the banked
   simulation percentiles within the declared numerical tolerances"; the
   integration ledger entry says "reconstruction within declared
   tolerances" correspondingly. (The settled evidence file's separate
   "replayed == banked" statement is a true equality of the recorded JSON
   values and was not touched.)

No number changed. Build 135 pages 0/0; gate OK, selftest green. Please
verify for 2/2.
