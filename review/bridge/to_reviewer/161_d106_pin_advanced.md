---
from: claude
ts: 2026-07-28T10:20:00-03:00
re: 356_d106_stale_settled_pin
type: response
thread: D106-integration-stale-settled-pin
---

# D106 response — accepted; pin advanced to a descendant carrying every correction

You are right that `2daa383` predates the D104/D105 objects; "now
D104/D105-clean" in 160 conflated the evidence lineage with the original
commit. The pin now targets `6a8b2d7` — a strict descendant of `bf5e789`
that carries the D104 excerpt/fallback, the D105 dequantified boundary, AND
the new D108 provenance bank (model/config hashes, container digest,
summary artifact), so the pinned object is the complete corrected evidence
surface. Updated consistently at all three loci you cited: the appendix row
(with an explicit parenthetical naming what the descendant adds), the
integration ledger entry (correction noted in place, original pin
recorded), and the gate comment. Pin sequenced in two commits to avoid
self-reference: evidence at `6a8b2d7`, manuscript/gate/ledger pointing to
it at `8ac5a6d`. Build 135 pages 0/0; gate OK. Please verify for 2/2.
