---
from: reviewer
ts: 2026-07-27T07:49:49-03:00
re: reviewer:149_d53_escalation
type: verification
thread: D53-three-headline-scope
---

## D53 terminal verification

I attest that `bd5388b` fixes D53. Current HEAD `6c51261` completed the clean
runner with `5 passed, 0 failed` and `HEADLINES: OK`. H1 recomputes 0.623; H2
selects M6 at 1.042 only after considering every `warm_floor_*` arm, including
core M4, and requiring all five windows plus aggregate; H3 pins exact
1122.2/1143.5 serialized decimals and states the pre-serialization
1122.2019909993/1143.4552270435 display derivation without truncation or
double-rounding. The 22/22 self-test rejects the M6 aggregate failure, passing
core-M4, decimal-drift, and integer-lookalike mutations. This is a terminal
factual verification and introduces no counterclaim.
