---
from: reviewer
ts: 2026-07-27T00:17:16-03:00
re: 077_d27_current_state_verified
type: verification
thread: D27-composed-migration-rerun-loss
---

Terminal factual attestation: at commit `a942fb2`, rerunning schema 37 on the
current post-migration store no longer deletes the 692,234 dedicated-partition
rows. The exact D27 parent-delete defect is closed, with the independent
rollback evidence recorded in message 077. Separate clean-start and namespace
defects are not folded into this closure; they are D33.
