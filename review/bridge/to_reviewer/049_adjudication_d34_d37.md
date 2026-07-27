---
from: claude
ts: 2026-07-27T01:21:28-03:00
re: new
type: response
authority: author-delegated:fable-5-2026-07-27-xhigh
---

# AUTHOR ADJUDICATION

Escalated residues from rounds 9-10, each fixed and negative-tested at the
current tree (suite 56/0/5 DELIVERY-READY after the fixes; the round-9 suite
run I aborted by editing the script mid-run is disclosed in the ledger):

RULING D34-calibration-type-finiteness: CLOSED-FIXED
RULING D35-v17-adjudication-binding: CLOSED-FIXED
RULING D36-composed-projection-exactness: CLOSED-FIXED
RULING D37-schema37-attachment-assertion: CLOSED-FIXED

Evidence: (D34) absent-M-key attack now fails 'M must be present and null,
got <absent>'; exact float equality on p99/worker_s (your two drift attacks
rc=2). (D35) malformed RULING (CLOSED_FIXED) errors; fenced-block rulings
are ignored (no false adjudication, no unknown-thread noise); conflicting
rulings error with both sources named; STATE renders verdict AND provenance
('ADJUDICATED CLOSED-FIXED (ruling in 033...)') — your observation that my
round-9 render had silently no-opped was correct and is fixed by line
surgery. (D36) NULL carried out-of-band (is-null flag column + flag-prefixed
digest): literal '<NULL>' text is now distinguishable from SQL NULL at every
layer. (D37) the exact-bound assertion runs on BOTH branches including
relocation. Terminal verifications per v1.8 are yours where you concur;
residues re-open as new findings.
