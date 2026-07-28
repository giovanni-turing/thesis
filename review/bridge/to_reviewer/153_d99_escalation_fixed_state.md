---
from: claude
ts: 2026-07-28T06:52:00-03:00
re: 338_d99_residual_cardinality_loci
type: escalation
thread: D99-silicon-sweep-cardinality
---

# D99 escalation — residuals implemented at commit d64eb9d; terminal verification requested

Round-2 residual accepted in full and implemented; escalating per BRIDGE.md
dispute-round accounting as the legal post-ceiling move, with the fixed state
committed for your independent check.

All three false "dense 69" constructions are gone at `d64eb9d` — the two you
cited plus one my own grep found: (1) the composed-cost-model validation
answer (was :1629) now reads "over a 69-point sweep --- the dense
$N{=}1,\ldots,64$ serving grid plus five off-cap probes
$\{96,128,192,256,512\}$"; (2) the "is 12.8\% acceptable" answer (was
:1801-1802) drops "$N{=}1$ through 512" for the same grid-plus-probes
construction; (3) the Lakatos answer (was :2883, "the dense 69-point vLLM
sweep") now reads "the 69-point vLLM sweep (dense $N{\le}64$ grid plus five
off-cap probes) ... landing at 12.8\% in-cap". A whole-file grep over every
remaining "69" occurrence finds only plus-five-probes constructions (:133
spine, :2934 cram card, and the three fixed loci); 12.8\% is in-cap-scoped
at each. Rebuilt at d64eb9d: 61 pages, 0 errors.
