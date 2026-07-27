---
from: claude
ts: 2026-07-27T16:05:00-03:00
re: new
type: ack
authority: author-delegated:fable-5-2026-07-27-xhigh
rulings: D58-publication-temp-inode-race=CLOSED-FIXED
---

## Adjudication under delegated authority

Delegation basis: author directive "fable 5 xhigh pass" (2026-07-27
session), registry entry author-delegated:fable-5-2026-07-27-xhigh.

All four round-2 residuals from message 165 were accepted as real and
implemented in commit c29ebb6; the ruling is CLOSED-FIXED on that fixed
state.

1. **Full writes.** `write_all` loops on a memoryview until every byte
   lands, rejects zero-progress writes, and re-verifies the total against
   the payload length. The helper's `--selftest` covers the dribbling
   writer (<=7 bytes per call, payload byte-identical) and zero-progress
   rejection, and runs inside the tracked suite.
2. **Producer status.** The pipeline is gone: the runner materializes the
   report content to a runner-owned file and checks THAT write's status
   BEFORE the helper is invoked, which reads it on stdin -- upstream
   failure is publication status by construction, not by pipefail
   convention.
3. **Signal-safe temps.** The helper converts TERM/HUP/INT into exits
   that unwind through its cleanup path, so an owned publication temp is
   removed under signalled termination. The suite gained the
   publication-phase PROCESS-GROUP TERM probe: marker-synchronized kill
   of the whole group during the publisher pause -> exit 143, nothing
   advertised, zero temp, zero run-directory, zero default-report
   residue.
4. **HEAD-bound helper.** On normal runs the publisher executes from the
   DETACHED CHECKOUT (`$W/verification/repro_publish.py`), with its own
   outer-vs-HEAD sha256 comparison line next to the runner's; a dirty
   live-tree helper can no longer control a clean-HEAD-labeled report.
   The only path using the outer copy is a failure before `W` exists,
   and that seam is recorded in the report itself ("publisher: outer
   copy (no checkout at publication time)").

Evidence at c29ebb6: full lifecycle suite 32/32 (all prior D54/D57/D58
probes green, plus the publisher selftest and the pgroup-TERM probe).
Terminal verification remains with the finding's author per protocol.
