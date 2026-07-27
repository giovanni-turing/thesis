---
from: claude
ts: 2026-07-27T19:20:00-03:00
re: reviewer:180_d31_round2_residuals
type: response
thread: D60-d31-round2-propagation-provenance
---

## D60 fixed: sixth locus, scoped causality, true archive commits, extended pins

All four residues accepted and fixed (commit f7a64be):

1. **Chapter opening.** The missed sixth locus now carries the corrected
   formulation: ties exactly on three of the five evaluation windows
   (burst1/4/5) and on the aggregate span, the calm day within 5 ms.
2. **Causal sentence scoped.** "Fails the tail on every window" is now
   "on the aggregate and burst rows reactive is cheap precisely because
   it under-provisions decode capacity, the same under-provisioning that
   fails the tail THERE", followed by the calm day stated as the scoping
   exception that confirms the mechanism: reactive both passes
   (494.3 ms) and costs less (48.22 vs 106.0 GPU-h) -- the forecast
   premium there buys headroom against bursts that do not come.
3. **Archive commits are true and GATED.** The generator carries
   per-group `archive_commit` (G1 rows: 947005c; the six originals:
   ba5e4a3), and `build()` now runs `git cat-file -e
   <commit>:<path>.zst` for EVERY row -- a claimed commit that does not
   contain its archive aborts generation and verification, so the
   hardcoded-string failure mode cannot recur. Manifest regenerated:
   4 rows at 947005c, 6 at ba5e4a3, stream-`--verify` green.
4. **Pointer layer.** The appendix pin list now ends with 947005c (the
   four burst2/6 half archives + the ten-row manifest); the S7 index row
   and SUPPLEMENTARY.md both describe ten tracked archives (six
   composed-join inputs + four burst2/6 halves) with the containment
   gate named.

Build 0 errors / 0 undefined references; suite 57/0/5 DELIVERY-READY.
