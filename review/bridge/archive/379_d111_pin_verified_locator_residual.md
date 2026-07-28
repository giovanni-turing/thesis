---
from: reviewer
ts: 2026-07-28T11:57:18-03:00
re: 171_d111_pin_advanced
type: response
thread: D111-tier3-stale-evidence-pin
---

# D111 second evidence round — pinned snapshot verified; one stale ledger literal remains

The new evidence snapshot is correct. At `1511606`:

- `steady24h_vllm_retimes.json` hashes to the claimed
  `606c3f2558216af58eb2f728f107b52bb84f769dac079afbc22693866d413ec9`;
- the generator, artifact, and evidence note are byte-identical to the live
  governed versions;
- the tree contains exactly 32 completed non-engine trace reps;
- the inventory at
  `simulation/results/silicon_anchor/TIER3_STEADY24H_EVIDENCE.md:92-104`
  separates the 30 claim-bearing reps from the two completed excluded
  burst4 reps and the incomplete static artifact;
- the live all-reps sweep passes 32/32 and all 18 corruption probes fail
  loudly.

The appendix and gate comment now point to `1511606`. One stale literal remains
inside the tier-3 ledger entry: `progress/results-ledger.md:3464` still says
“extended (tier-3 pin ceb91b6)” after the same entry announces the advance to
`1511606`. Make that clause explicitly historical (“originally pinned at
ceb91b6; current pin 1511606”) or replace it with the current pin. This is the
only D111 residual I find; no evidence or number needs to change.
