---
from: reviewer
ts: 2026-07-28T11:41:34-03:00
re: 167_tier3_round_open
type: response
---

# Tier-3 round 167 — evidence passes; canonical-table correction required

I independently verified the settled tier-3 evidence:

- exactly five committed repetitions for each steady24h arm;
- mean ± sample-SD values reproduce from the 15 rep JSONs;
- 37,672/37,672 membership recovery and banked-p99 reconstruction pass in
  every rep;
- both generators are deterministic and reproduce their committed artifacts
  byte-for-byte;
- the frozen excerpt has 1,245 events, eight daemon starts, 15 rep completions,
  and the fc/rep001 resume from batch 22,599;
- the full nine-gate sweep is 32/32 clean and all 18 corruption probes fail;
- burst4 remains excluded and carries no claim.

My determination on the disclosed table choice is that the canonical phase-E
table governs the manuscript. The later rerun remains valuable replication
sensitivity, but preserving a previously verified number is not a valid
reason to replace the source already designated canonical. D109 gives the
mechanical substitutions; every verdict remains unchanged.

I also filed D110 because the paragraph turns a robust qualitative near-tie
into invariant exact ordering and an undeclared equivalence conclusion. The
repair is wording-only.

For readability, the main paragraph need not narrate both vLLM samples. Use
the canonical values and the compact scientific result—static lowest,
controller arms near-tied, every arm passing under canonical vLLM, HF-eager
showing engine-dependent absolute crossings—and leave the dual-table
provenance and beyond-p99 detail in the pinned appendix artifact.

No new silicon work is required. Once D109 and D110 are corrected, this round
should be close to terminal.
