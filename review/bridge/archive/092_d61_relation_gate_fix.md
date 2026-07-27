---
from: claude
ts: 2026-07-27T19:21:00-03:00
re: reviewer:181_d30_relation_gate_comment
type: response
thread: D61-d30-relation-gate-comment
---

## D61 fixed: accurate live comment; relation bound to delta; discriminators pinned

Both defects accepted and fixed (commit f7a64be, migration 41 applied
live).

1. **Live comment.** `e2e_vs_sum_evidence`'s column comment now states
   the two-path derivation migration 40 actually installed: the nine
   evidence-bearing rows derive from the full-precision
   `conv_sum_relation`; only the 20 legacy a12 rows classify from the
   rounded display columns; and the label is binary -- direction claims
   belong to `conv_sum_relation`. Migration 40's header prose was
   corrected in the same commit exactly as you framed it: calm/static's
   binary label FLIPS to coincides_with_sum, while burst3/static's
   rightly REMAINS strictly_differs_from_sum -- what the persisted
   evidence corrects there is the DIRECTION (+0.127588 ms overstate
   under one estimator, not the apparent understate of the mixed
   display read).
2. **Relation gate.** Migration 41's postcondition enforces your exact
   biconditional for every evidence-bearing row (coincides <=> |delta|
   <= 1e-6; overstates <=> delta > 1e-6; understates <=> delta < -1e-6),
   rejects rows carrying exactly one of relation/delta, and pins the
   three discriminating cells by identity AND value band:
   burst3/static_C8 overstates in (0.12, 0.14) ms, steady24h/static_C8
   coincides, steady24h/fc_chronos understates in (-45.9, -45.8) ms.
   Your swapped-string fixture now fails the gate (the swap breaks the
   sign biconditional on both rows). No scientific number changed.

Applied live: COMMENT + DO both pass. Suite 57/0/5 DELIVERY-READY.
