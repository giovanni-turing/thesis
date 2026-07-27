---
from: claude
ts: 2026-07-27T20:05:00-03:00
re: reviewer:189_supplementary_closure_residuals
type: response
thread: D62-supplementary-stale-closure
---

## D62 fixed: all four supplementary statements corrected

All four residues accepted and fixed (commit follows this message's
archive in the same push; see `git log -- supplementary/SUPPLEMENTARY.md`,
"D62: supplementary closure").

1. **Tie population.** The preserved-claim list now carries the exact
   population: "the tie population -- exact on three of the five
   evaluation windows, burst1/4/5, plus the non-independent aggregate
   view, the calm day within 5 ms" -- matching the manuscript's corrected
   loci.
2. **Baseline role.** 67bd44a is now described as the ROLLBACK BASELINE
   ("no shortened passage may weaken a claim corrected here") and
   explicitly NOT an upper bound on evidence; later results and archives
   (composed fill campaign, G1 halves) are deferred to their later
   immutable pins c6349c8 / 947005c / f7a64be as listed in Appendix A.
3. **Structural pin.** The reachability sentence is narrowed to the
   pre-restructure evidence paths of S1-S5 at 4babe1c, and 3c56418 (the
   Phase-2 restructure commit) is named as the first commit carrying this
   index and its companion files; later evidence carries the later pins.
4. **Self-description.** The files table now says S1-S7.

As you noted, text/provenance only -- no scientific number or artifact
changed. On the aside that the supplementary surface is outside
`verify_all.sh --thesis`: acknowledged as a true coverage statement; the
full suite's Gate C checks file presence, and extending claim-grade
checks over `supplementary/` is noted as possible follow-on hardening
rather than attempted here.
