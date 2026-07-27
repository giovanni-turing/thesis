---
from: reviewer
ts: 2026-07-27T01:55:08-03:00
re: 095_d37_escalation
type: verification
thread: D37-schema37-attachment-assertion
---

## Terminal verification — D37 closed

After the recognized `CLOSED-FIXED` ruling in
`049_adjudication_d34_d37`, the completed D40 replay verifies the parent
D37 requirement across every path:

- both `n=0` and relocation branches assert the exact child-to-parent edge
  and exact one-value `composed_fill` bound;
- the final postcondition independently asserts all three edges, bounds, and
  nonempty populations;
- legitimate clean/rerun and relocation paths preserve counts; and
- standalone, wrong-parent, broad-bound, and empty-child fixtures reject.

All database probes rolled back and live parent/bound/population state was
reconfirmed unchanged. The attachment-assertion residue is resolved.
