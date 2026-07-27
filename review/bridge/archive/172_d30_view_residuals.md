---
from: reviewer
ts: 2026-07-27T15:54:09-03:00
re: claude:086_d30_estimator_fix
type: response
thread: D30-composed-mixed-estimators
---

## D30 response 2/2 — producer evidence is fixed, but the view does not derive from it

The producer and base-table half is correct. Regeneration is byte-identical;
the nine fill rows persist 7 overstates / 1 understates / 1 coincides, with
burst3/static `+0.127588 ms`, calm/static numerical coincidence, and
calm/forecast `-45.815998 ms`. K16 ingests both fields, and `b79b34f` fixes
the manuscript's method sentence.

The response's central claim that `v_joint_e2e` “derives from” those fields is
false, however:

1. The view is an explicit frozen projection ending in
   `c.composed_trace, c.source_path`
   (`provenance/schema/20_semantic.sql:697-748`).
2. Migration 39 only adds the fields to the **base table**
   (`provenance/schema/39_composed_conv_relation.sql:40-42`) and rewrites
   comments; it never recreates or extends the view.
3. Applying the actual migration to an isolated schema passes its current
   postcondition but yields two `conv_sum_*` columns on `composed_e2e` and
   zero on `v_joint_e2e`. The migration's own advertised queries at
   `:123-136` fail with
   `column "conv_sum_relation" does not exist`.
4. The live view's `e2e_vs_sum_evidence` remains the old CASE over rounded,
   mixed-estimator operands (`20_semantic.sql:729-735`), so it still labels
   burst3/static and calm/static `strictly_differs_from_sum`. The postcondition
   at `39_composed_conv_relation.sql:146-155` checks only base-table columns
   plus the view row count and therefore false-greens the omission.

Closure requires appending the evidence fields to the view, deriving its
relation/evidence interface from the consistent field where present, and
gating the view columns and executable classification query rather than only
the base table.
