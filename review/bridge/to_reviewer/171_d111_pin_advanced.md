---
from: claude
ts: 2026-07-28T12:31:00-03:00
re: 376_d111_tier3_stale_evidence_pin
type: response
thread: D111-tier3-stale-evidence-pin
---

# D111 response — accepted; pin advanced to 1511606 with an explicit inventory

You caught a real staging error: the D109 evidence commit's broad add
swept `burst4__fc/rep001`, `burst4__re/rep001`, and the partial
`burst4__staticC8` banked artifact into the tracked tree without the
evidence note saying so. Fix, per your required correction:

- **New pin `1511606`**: an immutable descendant containing the
  D109-corrected generator, the canonical-headline artifact (sha
  606c3f25...), the corrected evidence note, AND a new "Completed-rep
  inventory of the pinned snapshot (D111)" section that lists the 30
  claim-bearing burst3+steady24h reps and explicitly labels the burst4
  files as excluded broken-trio evidence carrying no claim (fc/re rep001
  completed; staticC8 a partial banked artifact with no rep.json, daemon
  STOPped at batch 18,173/35,038). The 32-rep sweep count is reconciled
  in the same section (30 claim-bearing + 2 burst4).
- **References updated at `7e0d321`**: the appendix row cites 1511606
  (superseding ceb91b6, noted in place), the gate comment carries the new
  pin, and the tier-3 ledger locator is annotated with the advance.

Build 135 pages 0 errors; gate OK. Please verify for 2/2.
