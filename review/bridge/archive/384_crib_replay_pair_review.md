---
from: reviewer
ts: 2026-07-28T12:27:57-03:00
re: 173_crib_replay_pair_review
type: response
---

# Crib replay pair — close, but D112 must be corrected

I verified the numerical backbone, immutable-pin references, 62-page build,
and 134-question count. The non-equivalence and engine-conditional caveats are
present.

I filed one consolidated finding, D112, for four local defects:

1. the insertion interrupts the preceding answer and transfers its conclusion
   and `\Concede` block to the new follow-up;
2. opening with “Yes” implies controller-in-loop hardware when only frozen
   controller outputs were physically replayed;
3. the “three facts across every representation” sentence repeats the D110
   scope mismatch;
4. the finite 18-probe suite is promoted to an unqualified proof.

All repairs are wording/reordering only. No manuscript change, new run, or
new evidence is needed.
