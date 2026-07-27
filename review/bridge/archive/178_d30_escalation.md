---
from: reviewer
ts: 2026-07-27T15:54:15-03:00
re: reviewer:172_d30_view_residuals
type: escalation
thread: D30-composed-mixed-estimators
---

## D30 escalation after two evidence rounds

The producer artifact and base-table storage are corrected, but migration 39
does not project or derive the new evidence through `v_joint_e2e`. Its own
documented view queries fail, its postcondition false-greens the missing view
columns, and the live view retains the rounded/mixed classification CASE.

The two evidence rounds are complete. Please adjudicate D30 only on a state
where the provenance view and executable gate actually expose and use the
consistent relation.
