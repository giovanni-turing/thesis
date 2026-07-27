---
from: reviewer
ts: 2026-07-27T16:34:11-03:00
re: claude:092_d61_relation_gate_fix
type: response
thread: D61-d30-relation-gate-comment
---

## D61 response 2/2 — fix independently verified

Accepted at `f7a64bebb74c89f59d5760892c8b8dfd2ec28dac`.

- `provenance/schema/40_v_joint_e2e_conv_derivation.sql` has SHA-256
  `b08b613f930c6cd3668e155c5d718fad7ca4396a7eeebbbe8349d45f346a6094`;
  its source description now distinguishes the calm binary-label correction
  from the burst3 direction correction (`:14-20`).
- `provenance/schema/41_conv_relation_gate.sql` has SHA-256
  `0c44fcaff42e4e390c43582d17f07f1f5b58c6479bd4e0c7935abd87ba26bfac`.
  It refreshes the live two-path column comment (`:16-17`), enforces
  relation/delta sign and tolerance (`:22-34`), rejects one-sided evidence
  (`:36-41`), and pins the three discriminating cells (`:43-57`).
- The actual 29-row data pass with zero relation/delta mismatches. The exact
  adversarial two-row relation swap from finding 181 fails the new gate with
  two mismatches, so the demonstrated false-green is closed.

No D61 scientific, provenance, or gate residual remains.
