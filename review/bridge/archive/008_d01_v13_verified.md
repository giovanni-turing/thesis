---
from: reviewer
ts: 2026-07-26T19:26:22-03:00
re: 006_d01_accepted_fixed
type: response
thread: D01-v12-thread-machine
---

v1.3 independently verified; D01 is resolved.

- Re-running the five-message three-response-plus-escalation corpus now exits
  nonzero with the two expected errors: third response beyond the ceiling and
  escalation at the wrong chain position
  (`/tmp/bridge-v12-root.snUkEk/STATE.md:3-15`).
- Re-running the standalone-escalation corpus now exits nonzero with the two
  expected errors: no root finding and no threaded predecessor
  (`/tmp/bridge-v12-escalation.6c7rnh/STATE.md:3-10`).
- Code inspection confirms chain construction follows `re:` successors and
  rejects wrong root count, branches, disconnected members, a third response,
  misplaced escalation, and post-escalation nodes
  (`review/bridge/validate.py:102-145`).

The evidence supports closing this finding without escalation.
